"""
ANPR (Automatic Number Plate Recognition) module for Smart Traffic AI.

Drop-in replacement for the plate detection + OCR section of traffic_ai.py.

Usage:
    from app.services.anpr import ANPR

    anpr = ANPR(
        plate_model_path="models/anpr/license_plate_detector.pt",
        conf=0.45,
        gpu=False,
    )

    plates = anpr.read_plate(frame)          # returns list of dicts
    anpr.read_plate(frame, debug_dir="anpr_debug")  # saves crops for inspection

Each result dict:
    {
        "text": "MH12AB1234" or None,
        "valid": True/False,
        "confidence": 0.87,
        "ocr_confidence": 0.92,
        "bbox": (x1, y1, x2, y2),
    }
"""

from __future__ import annotations

import os
import re
from typing import List, Dict, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False


# ---------------------------------------------------------------------------
# Indian plate formats
# ---------------------------------------------------------------------------

# Standard: MH12AB1234, KA03MN9993, DL8CAF5031
# Older:    MH12A1234
# Short:    MH12A123
INDIAN_PLATE_PATTERNS = [
    re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$"),   # MH12AB1234
    re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{3,4}$"),  # MH12A123
    re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1}[0-9]{4}$"),         # MH12A1234
    re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3}$"),    # older short
]

# Characters EasyOCR commonly confuses in Indian plates
CONFUSION_MAP_NUMERIC = {
    "O": "0", "Q": "0", "D": "0",
    "I": "1", "L": "1",
    "Z": "2",
    "A": "4",
    "S": "5",
    "G": "6",
    "T": "7", "B": "8",
    "g": "9", "q": "9",
}


def _normalize_plate_text(raw: str) -> str:
    """Strip noise, uppercase, remove separators."""
    if not raw:
        return ""
    text = raw.upper()
    text = re.sub(r"[^A-Z0-9]", "", text)
    return text


def _fix_confusions(text: str) -> str:
    """
    Apply confusion fixes positionally:
      - First 2 chars: letters (state code)
      - Next 1-2 chars: digits (district)
      - Rest: letters then digits
    Simple version: fix numeric-looking positions only.
    """
    if len(text) < 6:
        return text

    chars = list(text)
    # Positions: [0,1] = letters, [2,3] = digits, [4..] = mix
    for i in range(len(chars)):
        if 2 <= i <= 3 and chars[i] in CONFUSION_MAP_NUMERIC:
            chars[i] = CONFUSION_MAP_NUMERIC[chars[i]]
    return "".join(chars)


def is_valid_indian_plate(text: str) -> bool:
    if not text:
        return False
    cleaned = _fix_confusions(_normalize_plate_text(text))
    return any(p.match(cleaned) for p in INDIAN_PLATE_PATTERNS)


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def preprocess_plate(plate_bgr: np.ndarray) -> np.ndarray:
    """
    Upscale, denoise, CLAHE, Otsu threshold.

    Returns a 3-channel BGR image because EasyOCR expects 3 channels,
    but the content is effectively grayscale.
    """
    if plate_bgr is None or plate_bgr.size == 0:
        return plate_bgr

    # 1. Upscale for small crops
    h, w = plate_bgr.shape[:2]
    if w < 200:
        scale = max(1, int(200 / max(w, 1)))
        plate_bgr = cv2.resize(
            plate_bgr,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

    # 2. Grayscale
    gray = cv2.cvtColor(plate_bgr, cv2.COLOR_BGR2GRAY)

    # 3. CLAHE for uneven Indian lighting
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # 4. Bilateral filter (edge-preserving denoise)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)

    # 5. Otsu threshold
    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # EasyOCR wants 3 channels
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# ANPR class
# ---------------------------------------------------------------------------

class ANPR:
    def __init__(
        self,
        plate_model_path: str = "models/anpr/license_plate_detector.pt",
        conf: float = 0.45,
        imgsz: int = 1280,
        gpu: bool = False,
        ocr_langs: Optional[List[str]] = None,
    ):
        print(f"[ANPR] Loading plate detector: {plate_model_path}")
        self.model = YOLO(plate_model_path)
        self.conf = conf
        self.imgsz = imgsz

        if not _EASYOCR_AVAILABLE:
            raise RuntimeError(
                "easyocr is not installed. Run: pip install easyocr"
            )

        print("[ANPR] Loading EasyOCR...")
        self.reader = easyocr.Reader(
            ocr_langs or ["en"],
            gpu=gpu,
        )
        print("[ANPR] Ready.")

        self._debug_counter = 0

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_plates(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """
        Returns list of (x1, y1, x2, y2, conf).
        """
        results = self.model(
            frame,
            conf=self.conf,
            imgsz=self.imgsz,
            verbose=False,
        )
        out = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                c = float(box.conf[0])
                # Sanity check: skip tiny boxes
                if (x2 - x1) < 20 or (y2 - y1) < 8:
                    continue
                out.append((x1, y1, x2, y2, c))
        return out

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

    def _read_crop(self, crop_bgr: np.ndarray):
        """Run EasyOCR on a preprocessed crop. Returns list of (text, conf)."""
        processed = preprocess_plate(crop_bgr)
        try:
            results = self.reader.readtext(
                processed,
                detail=1,
                paragraph=False,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            )
        except Exception as e:
            print(f"[ANPR] EasyOCR error: {e}")
            return []

        out = []
        for item in results:
            # EasyOCR returns (bbox, text, conf)
            if len(item) >= 3:
                out.append((item[1], float(item[2])))
        return out

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_plate(
        self,
        frame: np.ndarray,
        debug_dir: Optional[str] = None,
    ) -> List[Dict]:
        """
        Run full ANPR on a frame.

        Args:
            frame: BGR image.
            debug_dir: if set, save crops + processed images here.

        Returns:
            List of dicts (one per detected plate).
        """
        plates = self.detect_plates(frame)

        if debug_dir:
            os.makedirs(debug_dir, exist_ok=True)

        results_out: List[Dict] = []

        for (x1, y1, x2, y2, det_conf) in plates:
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            idx = self._debug_counter
            self._debug_counter += 1

            if debug_dir:
                cv2.imwrite(
                    os.path.join(debug_dir, f"crop_{idx:04d}.jpg"),
                    crop,
                )
                processed = preprocess_plate(crop)
                cv2.imwrite(
                    os.path.join(debug_dir, f"processed_{idx:04d}.jpg"),
                    processed,
                )

            ocr_items = self._read_crop(crop)

            if not ocr_items:
                results_out.append({
                    "text": None,
                    "valid": False,
                    "confidence": det_conf,
                    "ocr_confidence": 0.0,
                    "bbox": (x1, y1, x2, y2),
                })
                continue

            # Pick the highest-confidence OCR item
            ocr_items.sort(key=lambda t: t[1], reverse=True)
            best_text, best_ocr_conf = ocr_items[0]

            normalized = _fix_confusions(_normalize_plate_text(best_text))
            valid = is_valid_indian_plate(normalized)

            results_out.append({
                "text": normalized if valid else best_text.strip(),
                "valid": valid,
                "confidence": det_conf,
                "ocr_confidence": best_ocr_conf,
                "bbox": (x1, y1, x2, y2),
            })

        return results_out

    def annotate(
        self,
        frame: np.ndarray,
        results: List[Dict],
    ) -> np.ndarray:
        """Draw boxes + plate text on the frame. Returns a copy."""
        out = frame.copy()
        for r in results:
            x1, y1, x2, y2 = r["bbox"]
            valid = r["valid"]
            color = (0, 255, 0) if valid else (0, 165, 255)

            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

            label = r["text"] if r["text"] else "?"
            if r["text"] and not valid:
                label += " ?"
            cv2.putText(
                out,
                label,
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )
        return out