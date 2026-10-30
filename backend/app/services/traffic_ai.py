from pathlib import Path
from collections import defaultdict, Counter, deque
import os
import re
import subprocess

import cv2
import easyocr
from ultralytics import YOLO

from app.services.helmet_detector import HelmetDetector


# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).resolve().parents[2]

MODEL = "yolo11n.pt"

PLATE_MODEL = (
    BASE
    / "models"
    / "anpr"
    / "license_plate_detector.pt"
)

ACCIDENT_MODEL = (
    BASE
    / "models"
    / "accident"
    / "weights"
    / "epoch61.pt"
)

HELMET_MODEL = (
    BASE
    / "models"
    / "helmet"
    / "helmet_detector.pt"
)

AMBULANCE_MODEL_PATH = BASE / "models" / "ambulance" / "ambulance_detector.pt"
AMBULANCE_MODEL_NAME = "YOLOv8s-World v2 (zero-shot, prompt: ambulance)"

HELMET_CROPS_DIR = (
    BASE
    / "videos"
    / "helmet_crops"
)

ACCIDENT_EVIDENCE_DIR = BASE / "videos" / "accident_evidence"
ROAD_EVIDENCE_DIR = BASE / "videos" / "road_evidence"

HELMET_CROPS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)
ACCIDENT_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
ROAD_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# VEHICLE SETTINGS
# ============================================================

CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

AUTO_RICKSHAW_CLASS = "auto_rickshaw"
TAXI_CLASS = "taxi"
AMBULANCE_CLASS = "ambulance"
VAN_CLASS = "van"
HEAVY_VEHICLE_CLASS = "heavy_vehicle"
UNCERTAIN_VEHICLE_CLASS = "uncertain_vehicle"
AMBULANCE_DETECTION_INTERVAL = 12
AMBULANCE_CONFIDENCE = 0.35
VAN_DETECTION_INTERVAL = 12
VAN_WORLD_CLASS_ID = 1
VAN_WORLD_OUTPUT_CONFIDENCE = 0.20
VAN_MATCH_CONFIDENCE = 0.35
VAN_MATCH_IOU = 0.25
VAN_REQUIRED_HITS = 2
VAN_MIN_CUMULATIVE_CONFIDENCE = 0.85
VEHICLE_WORLD_PROMPTS = ["ambulance", "van", "car", "truck", "bus", "motorcycle"]

VEHICLE_CONFIDENCE = 0.25
HEAVY_CLASS_MIN_OBSERVATIONS = 5
HEAVY_CLASS_MIN_DOMINANCE = 0.65

METERS_PER_PIXEL = 0.03

SPEED_LIMIT_KMH = 50

LINE_Y_RATIO = 0.55

TRAJECTORY_LENGTH = 40


# ============================================================
# ANPR SETTINGS
# ============================================================

PLATE_DETECTION_INTERVAL = 8

PLATE_FULL_FRAME_CONFIDENCE = 0.04
PLATE_MOTORCYCLE_CROP_CONFIDENCE = 0.005
PLATE_MOTORCYCLE_CROP_SIZE = 1280

OCR_CONFIDENCE = 0.10

MAX_PLATE_LENGTH = 12

PLATE_IMAGE_SIZE = 416

ANPR_CLASSES = {
    "car",
    "motorcycle",
    "truck",
    "bus",
    AUTO_RICKSHAW_CLASS,
    TAXI_CLASS,
    AMBULANCE_CLASS,
    VAN_CLASS,
    HEAVY_VEHICLE_CLASS,
    UNCERTAIN_VEHICLE_CLASS,
}


# ============================================================
# ACCIDENT SETTINGS
# ============================================================

ACCIDENT_DETECTION_INTERVAL = 5

ACCIDENT_CONFIDENCE = 0.50

ACCIDENT_REQUIRED_FRAMES = 2
ACCIDENT_CONFIRMATION_WINDOW = 5

# Helmet detection runs only on motorcycle/rider crops.
HELMET_MODEL_CONFIDENCE = 0.01
HELMET_WITH_HELMET_MIN_CONFIDENCE = 0.02
HELMET_NO_HELMET_MIN_CONFIDENCE = 0.55
HELMET_HEAD_NO_HELMET_MIN_CONFIDENCE = 0.15
HELMET_NO_HELMET_MIN_SAMPLES = 2
HELMET_NO_HELMET_AGGREGATE_MIN_CONFIDENCE = 0.72
HELMET_DETECTION_INTERVAL = 15
HELMET_CROP_X_PADDING = 0.18
HELMET_CROP_TOP_RATIO = 1.35
HELMET_CROP_BOTTOM_RATIO = 0.90


# ============================================================
# LOAD MODELS
# ============================================================

print("Loading vehicle detection model...")

vehicle_model = YOLO(MODEL)
vehicle_model_names = vehicle_model.names or {}
if isinstance(vehicle_model_names, list):
    vehicle_model_names = dict(enumerate(vehicle_model_names))
invalid_vehicle_classes = {
    class_id: {
        "expected": expected_name,
        "model": vehicle_model_names.get(class_id),
    }
    for class_id, expected_name in CLASSES.items()
    if str(vehicle_model_names.get(class_id, "")).strip().lower()
    != expected_name
}
if invalid_vehicle_classes:
    raise RuntimeError(
        "Vehicle model class names do not match COCO IDs: "
        f"{invalid_vehicle_classes}"
    )
print("Verified COCO vehicle classes: car=2, motorcycle=3, bus=5, truck=7")

ambulance_model = None
ambulance_model_class_ids = set()
van_detection_available = False
if AMBULANCE_MODEL_PATH.is_file():
    print(f"Loading ambulance detection model: {AMBULANCE_MODEL_NAME}...")
    ambulance_model = YOLO(str(AMBULANCE_MODEL_PATH))
    model_names = ambulance_model.names
    model_names = model_names.values() if isinstance(model_names, dict) else model_names
    ambulance_model_class_ids = {
        class_id
        for class_id, name in enumerate(model_names)
        if str(name).strip().lower().replace(" ", "_").startswith("ambulance")
    }
    if not ambulance_model_class_ids:
        print("Ambulance model has no 'ambulance' class; disabling it.")
        ambulance_model = None
    elif hasattr(ambulance_model, "set_classes"):
        try:
            # Keep ambulance first so its existing class-0 check stays valid.
            ambulance_model.set_classes(VEHICLE_WORLD_PROMPTS)
            van_detection_available = True
            print("YOLO-World prompts enabled, including van detection.")
        except Exception as error:
            print(f"Van prompt unavailable; using COCO vehicle classes only: {error}")
else:
    print(
        "Ambulance detection unavailable: run backend/install_ambulance_model.py "
        f"to install {AMBULANCE_MODEL_NAME} at {AMBULANCE_MODEL_PATH}"
    )


def crop_is_ambulance(box, frame):
    """Check a tracked vehicle crop with the installed ambulance detector."""
    if ambulance_model is None or not ambulance_model_class_ids:
        return False
    x1, y1, x2, y2 = map(int, box)
    crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
    if crop.size == 0:
        return False
    predictions = ambulance_model.predict(
        crop,
        conf=AMBULANCE_CONFIDENCE,
        imgsz=640,
        verbose=False,
    )
    return any(
        prediction.boxes is not None
        and any(
            int(class_id) in ambulance_model_class_ids
            and float(confidence) >= AMBULANCE_CONFIDENCE
            for class_id, confidence in zip(
                prediction.boxes.cls.cpu().tolist(),
                prediction.boxes.conf.cpu().tolist(),
            )
        )
        for prediction in predictions
    )


def detect_world_vans(frame):
    """Find van boxes with the installed open-vocabulary YOLO-World model."""
    if ambulance_model is None or not van_detection_available:
        return []

    predictions = ambulance_model.predict(
        frame,
        conf=VAN_WORLD_OUTPUT_CONFIDENCE,
        imgsz=640,
        max_det=40,
        verbose=False,
    )
    detections = []
    for prediction in predictions:
        if prediction.boxes is None:
            continue
        for box in prediction.boxes:
            if int(box.cls[0]) != VAN_WORLD_CLASS_ID:
                continue
            detections.append(
                {
                    "bbox": list(map(int, box.xyxy[0])),
                    "confidence": float(box.conf[0]),
                }
            )
    return detections


def matched_van_confidence(vehicle_box, van_detections):
    """Return confidence only when a world-model van box overlaps this track."""
    x1, y1, x2, y2 = map(float, vehicle_box)
    vehicle_area = max(1.0, (x2 - x1) * (y2 - y1))
    best_confidence = 0.0
    for detection in van_detections:
        vx1, vy1, vx2, vy2 = detection["bbox"]
        intersection_width = max(0.0, min(x2, vx2) - max(x1, vx1))
        intersection_height = max(0.0, min(y2, vy2) - max(y1, vy1))
        intersection = intersection_width * intersection_height
        detection_area = max(1.0, (vx2 - vx1) * (vy2 - vy1))
        iou = intersection / max(1.0, vehicle_area + detection_area - intersection)
        vehicle_coverage = intersection / vehicle_area
        if iou >= VAN_MATCH_IOU or vehicle_coverage >= 0.55:
            best_confidence = max(best_confidence, detection["confidence"])
    return best_confidence


print("Loading license plate detection model...")

plate_model = YOLO(
    str(PLATE_MODEL)
)

print("Loading accident detection model...")

accident_model = YOLO(
    str(ACCIDENT_MODEL)
)

print("Loading helmet detection model...")
helmet_detector = HelmetDetector(
    str(HELMET_MODEL),
    confidence=HELMET_MODEL_CONFIDENCE,
)

print("Loading EasyOCR...")

ocr_reader = easyocr.Reader(
    ["en"],
    gpu=False,
)

print(
    "Vehicle model + ANPR + accident detection + helmet detection + OCR ready."
)


# ============================================================
# CLEAN PLATE TEXT
# ============================================================

def clean_plate_text(text):

    if not text:
        return ""

    text = str(text).upper().strip()

    text = re.sub(
        r"[^A-Z0-9]",
        "",
        text,
    )

    if not text:
        return ""

    if len(text) < 7:
        return ""

    if len(text) > MAX_PLATE_LENGTH:
        return ""

    if not re.search(
        r"[A-Z]",
        text,
    ):
        return ""

    if not re.search(
        r"\d",
        text,
    ):
        return ""

    garbage_patterns = [
        "KMH",
        "KMPH",
        "MPH",
        "SPEED",
        "STOCK",
        "SPORT",
        "TOYOTA",
        "HONDA",
        "SUZUKI",
        "TATA",
        "HYUNDAI",
        "VOLKSWAGEN",
        "BMW",
        "AUDI",
        "MERCEDES",
    ]

    for pattern in garbage_patterns:

        if pattern in text:
            return ""

    return text


# ============================================================
# OCR PLATE NORMALIZATION
# ============================================================

def normalize_plate_prefix(text):
    """
    Correct common EasyOCR confusions in Maharashtra registration
    prefixes without changing the rest of the plate.

    Common examples from this traffic footage:
        HH01EB2570  -> MH01EB2570
        HH02F14729  -> MH02F14729
        MMH02D10644 -> MH02D10644
        MMH02...    -> MH02...

    We only apply these corrections when the plate starts with a
    known OCR-confusion pattern and is followed by a plausible
    Maharashtra registration number.
    """
    if not text:
        return ""

    text = str(text).upper().strip()

    # Maharashtra registration plates start with MH.
    # EasyOCR can confuse the first two letters, especially M/H.
    #
    # Examples seen in the uploaded traffic video:
    #   HHL84L1381  -> MHL84L1381
    #   HH01EB2570  -> MH01EB2570
    #   MM01EB2570  -> MH01EB2570
    #   MMH02D10644 -> MH02D10644
    #
    # For this project we treat a leading HH as an MH OCR confusion
    # because the tested footage contains Maharashtra plates.
    if text.startswith("MMH"):
        text = "MH" + text[3:]
    elif text.startswith("HH"):
        text = "MH" + text[2:]
    elif text.startswith("MM"):
        text = "MH" + text[2:]

    return text


def normalize_indian_plate(text):
    """Return only a well-formed Maharashtra registration candidate.

    OCR character substitutions are limited to positions that must be
    numeric, and no more than one substitution is allowed. This favors
    withholding an uncertain read over inventing a plausible plate.
    """
    text = normalize_plate_prefix(clean_plate_text(text))
    if not text or not text.startswith("MH") or len(text) not in {9, 10}:
        return ""

    number_confusions = {
        "O": "0", "Q": "0", "D": "0",
        "I": "1", "L": "1", "Z": "2",
        "S": "5", "B": "8",
    }
    chars = list(text)
    corrections = 0

    # Maharashtra registration format: MH + district (2 digits) +
    # series (1 or 2 letters) + registration number (4 digits).
    digit_positions = (2, 3, *range(len(chars) - 4, len(chars)))
    for index in digit_positions:
        replacement = number_confusions.get(chars[index])
        if replacement:
            chars[index] = replacement
            corrections += 1

    candidate = "".join(chars)
    if corrections > 1:
        return ""
    if not re.fullmatch(r"MH\d{2}[A-Z]{1,2}\d{4}", candidate):
        return ""
    return candidate


# ============================================================
# OCR
# ============================================================

def read_plate(crop):

    if crop is None:
        return "", 0.0

    if crop.size == 0:
        return "", 0.0

    try:

        height, width = crop.shape[:2]

        target_width = min(640, max(320, width * 2))
        scale = target_width / max(1, width)
        crop = cv2.resize(
            crop,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC if scale >= 1 else cv2.INTER_AREA,
        )

        gray = cv2.cvtColor(
            crop,
            cv2.COLOR_BGR2GRAY,
        )

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8),
        ).apply(gray)

        candidates = Counter()
        candidate_confidence = defaultdict(float)
        best_observed_confidence = 0.0
        ocr_images = (
            enhanced,
            gray,
            cv2.GaussianBlur(gray, (3, 3), 0),
            cv2.adaptiveThreshold(
                enhanced,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                9,
            ),
        )

        for ocr_image in ocr_images:
            results = ocr_reader.readtext(
                ocr_image,
                detail=1,
                paragraph=False,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            )

            fragments = []
            best_valid_confidence = 0.0
            for item in results:
                if len(item) < 3:
                    continue

                confidence = float(item[2])
                best_observed_confidence = max(best_observed_confidence, confidence)
                if confidence < OCR_CONFIDENCE:
                    continue

                fragment = clean_plate_text(item[1])
                if not fragment:
                    continue

                fragments.append((item[0], fragment, confidence))
                cleaned = normalize_indian_plate(fragment)
                if not cleaned:
                    continue

                candidates[cleaned] += 1
                candidate_confidence[cleaned] = max(
                    candidate_confidence[cleaned], confidence
                )
                best_valid_confidence = max(best_valid_confidence, confidence)

            # OCR sometimes splits a plate into two text regions. Join the
            # fragments left-to-right and validate the combined registration.
            if len(fragments) > 1:
                fragments.sort(
                    key=lambda item: sum(point[0] for point in item[0])
                    / len(item[0])
                )
                joined = "".join(item[1] for item in fragments)
                cleaned = normalize_indian_plate(joined)
                if cleaned:
                    candidates[cleaned] += 1
                    candidate_confidence[cleaned] = max(
                        candidate_confidence[cleaned],
                        sum(item[2] for item in fragments) / len(fragments),
                    )

            # Plate syntax validation plus temporal voting across frames
            # already provides a second check. Stop early on a usable read;
            # run slower preprocessing variants only when the first pass is
            # weak or cannot produce a valid plate.
            if best_valid_confidence >= 0.55:
                break

        if not candidates:
            return "", best_observed_confidence

        best_text = max(
            candidates,
            key=lambda value: (candidates[value], candidate_confidence[value]),
        )
        return best_text, candidate_confidence[best_text]

    except Exception as e:

        print(
            "OCR error:",
            e,
        )

        return "", 0.0


# ============================================================
# VEHICLE CLASS RESOLUTION
# ============================================================

def resolve_vehicle_track_class(class_counts, class_scores, previous_class=None):
    """Keep track labels stable and surface conflicting classes as uncertain."""
    bus_count = class_counts.get("bus", 0)
    truck_count = class_counts.get("truck", 0)
    heavy_observations = bus_count + truck_count
    observed_classes = [
        name for name, count in class_counts.items() if count > 0
    ]
    if not observed_classes:
        return previous_class

    winner = max(
        observed_classes,
        key=lambda name: (
            class_scores.get(name, 0.0),
            class_counts[name],
            name == previous_class,
        ),
    )
    total_score = sum(class_scores.get(name, 0.0) for name in observed_classes)
    winning_share = (
        class_scores.get(winner, 0.0) / total_score
        if total_score > 0
        else class_counts[winner] / max(1, sum(class_counts.values()))
    )

    if bus_count and truck_count and set(observed_classes) <= {"bus", "truck"}:
        if (
            heavy_observations < HEAVY_CLASS_MIN_OBSERVATIONS
            or winning_share < HEAVY_CLASS_MIN_DOMINANCE
        ):
            return HEAVY_VEHICLE_CLASS
        return winner

    if len(observed_classes) > 1 and winning_share < HEAVY_CLASS_MIN_DOMINANCE:
        return UNCERTAIN_VEHICLE_CLASS

    return winner


# ============================================================
# VEHICLE COLORS
# ============================================================

def get_vehicle_color(class_name):

    if class_name == "car":
        return (255, 180, 0)

    if class_name == "motorcycle":
        return (0, 200, 255)

    if class_name == "bus":
        return (255, 0, 255)

    if class_name == "truck":
        return (0, 255, 255)

    if class_name == AUTO_RICKSHAW_CLASS:
        return (80, 220, 80)

    if class_name == TAXI_CLASS:
        return (0, 210, 255)

    if class_name == VAN_CLASS:
        return (255, 145, 70)

    if class_name == AMBULANCE_CLASS:
        return (0, 70, 255)

    if class_name == HEAVY_VEHICLE_CLASS:
        return (0, 180, 255)

    if class_name == UNCERTAIN_VEHICLE_CLASS:
        return (0, 180, 255)

    return (255, 255, 255)


def vehicle_color_ratios(frame, box):
    """Estimate yellow and green paint ratios in the visible vehicle body."""
    x1, y1, x2, y2 = map(int, box)
    frame_height, frame_width = frame.shape[:2]
    width, height = x2 - x1, y2 - y1
    if width < 8 or height < 8:
        return 0.0, 0.0

    # Ignore much of the windscreen and surrounding background.
    left = max(0, x1 + int(width * 0.12))
    right = min(frame_width, x2 - int(width * 0.12))
    top = max(0, y1 + int(height * 0.30))
    bottom = min(frame_height, y2 - int(height * 0.08))
    crop = frame[top:bottom, left:right]
    if crop.size == 0:
        return 0.0, 0.0

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    yellow = cv2.inRange(hsv, (15, 75, 65), (40, 255, 255))
    green = cv2.inRange(hsv, (36, 55, 35), (92, 255, 255))
    total = max(1, crop.shape[0] * crop.shape[1])
    return cv2.countNonZero(yellow) / total, cv2.countNonZero(green) / total


def looks_like_auto_rickshaw(box, frame_shape, frame=None):
    """Conservative shape/color estimate; COCO has no auto-rickshaw label."""
    x1, y1, x2, y2 = box
    frame_height, frame_width = frame_shape[:2]
    width = max(0, x2 - x1)
    height = max(0, y2 - y1)
    if not width or not height or not frame_width or not frame_height:
        return False

    aspect_ratio = width / height
    frame_area_ratio = (width * height) / (frame_width * frame_height)
    width_ratio = width / frame_width
    height_ratio = height / frame_height

    shape_match = (
        1.05 <= aspect_ratio <= 2.05
        and 0.002 <= frame_area_ratio <= 0.055
        and width_ratio <= 0.38
        and height_ratio <= 0.48
    )
    if not shape_match:
        return False

    # Requiring characteristic yellow/green body color reduces the chance of
    # turning compact yellow taxis into auto-rickshaws. This remains a heuristic.
    if frame is None:
        return False
    yellow_ratio, green_ratio = vehicle_color_ratios(frame, box)
    return green_ratio >= 0.035 or (yellow_ratio >= 0.18 and aspect_ratio <= 1.62)


def looks_like_yellow_taxi(box, frame, frame_shape):
    """Flag compact, yellow passenger-car-shaped boxes as likely taxis."""
    x1, y1, x2, y2 = box
    frame_height, frame_width = frame_shape[:2]
    width, height = max(0, x2 - x1), max(0, y2 - y1)
    if not width or not height:
        return False
    aspect_ratio = width / height
    area_ratio = (width * height) / max(1, frame_width * frame_height)
    if not (1.2 <= aspect_ratio <= 3.0 and area_ratio <= 0.12 and height / max(1, frame_height) <= 0.55):
        return False
    yellow_ratio, _ = vehicle_color_ratios(frame, box)
    return yellow_ratio >= 0.20


# ============================================================
# LABEL
# ============================================================

def draw_label(
    frame,
    text,
    x,
    y,
    color=(255, 255, 255),
    scale=0.55,
):

    font = cv2.FONT_HERSHEY_SIMPLEX

    (tw, th), _ = cv2.getTextSize(
        text,
        font,
        scale,
        2,
    )

    x = max(0, x)

    y = max(
        th + 8,
        y,
    )

    cv2.rectangle(
        frame,
        (
            x,
            y - th - 8,
        ),
        (
            x + tw + 8,
            y,
        ),
        (0, 0, 0),
        -1,
    )

    cv2.putText(
        frame,
        text,
        (
            x + 4,
            y - 4,
        ),
        font,
        scale,
        color,
        2,
        cv2.LINE_AA,
    )


# ============================================================
# VEHICLE BOX
# ============================================================

def draw_vehicle_box(
    frame,
    x1,
    y1,
    x2,
    y2,
    class_name,
    track_id,
    speed=None,
    plate="",
    helmet_status="",
    helmet_confidence=0.0,
):

    color = get_vehicle_color(class_name)
    if class_name == "motorcycle":
        if helmet_status == "without_helmet":
            color = (0, 0, 255)
        elif helmet_status == "with_helmet":
            color = (0, 220, 80)

    cv2.rectangle(
        frame,
        (
            x1,
            y1,
        ),
        (
            x2,
            y2,
        ),
        color,
        3 if class_name == "motorcycle" and helmet_status == "without_helmet" else 2,
    )

    if track_id != 0:

        label = (
            f"{class_name.replace('_', ' ').upper()} "
            f"#{track_id}"
        )

    else:

        label = class_name.replace("_", " ").upper()

    if speed is not None:

        label += (
            f" | {speed:.1f} km/h"
        )

    draw_label(
        frame,
        label,
        x1,
        y1,
        color=color,
        scale=0.5,
    )

    if plate:

        draw_label(
            frame,
            f"PLATE: {plate}",
            x1,
            y2 + 25,
            color=(0, 255, 255),
            scale=0.5,
        )

    if class_name == "motorcycle" and helmet_status:
        if helmet_status == "without_helmet":
            helmet_text = "NO HELMET"
            helmet_color = (0, 0, 255)
        elif helmet_status == "with_helmet":
            helmet_text = "HELMET OK"
            helmet_color = (0, 255, 0)
        else:
            helmet_text = "HELMET UNKNOWN"
            helmet_color = (0, 165, 255)

        if helmet_confidence > 0:
            helmet_text += f" {helmet_confidence:.0%}"

        draw_label(
            frame,
            helmet_text,
            x1,
            y2 + 50,
            color=helmet_color,
            scale=0.5,
        )


# ============================================================
# PLATE BOX
# ============================================================

def draw_plate_box(
    frame,
    x1,
    y1,
    x2,
    y2,
    plate_text="",
):

    cv2.rectangle(
        frame,
        (
            x1,
            y1,
        ),
        (
            x2,
            y2,
        ),
        (0, 255, 255),
        2,
    )

    if plate_text:

        draw_label(
            frame,
            f"PLATE {plate_text}",
            x1,
            max(
                y1 - 5,
                25,
            ),
            color=(0, 255, 255),
            scale=0.5,
        )


# ============================================================
# CONGESTION
# ============================================================

def get_congestion(
    active_count,
):

    if active_count >= 45:
        return "SEVERE"

    if active_count >= 30:
        return "HIGH"

    if active_count >= 15:
        return "MEDIUM"

    return "LOW"


# ============================================================
# ACCIDENT DRAWING
# ============================================================

def draw_accident_alert(
    frame,
    accident_detections,
    accident_confirmed,
):

    for detection in accident_detections:

        x1, y1, x2, y2 = (
            detection["bbox"]
        )

        confidence = detection[
            "confidence"
        ]

        cv2.rectangle(
            frame,
            (
                x1,
                y1,
            ),
            (
                x2,
                y2,
            ),
            (0, 0, 255),
            4,
        )

        draw_label(
            frame,
            f"ACCIDENT {confidence:.0%}",
            x1,
            max(
                y1 - 5,
                30,
            ),
            color=(0, 0, 255),
            scale=0.7,
        )

    if accident_confirmed:

        cv2.rectangle(
            frame,
            (
                0,
                0,
            ),
            (
                frame.shape[1] - 1,
                frame.shape[0] - 1,
            ),
            (0, 0, 255),
            8,
        )

        banner_height = 90

        cv2.rectangle(
            frame,
            (
                0,
                0,
            ),
            (
                frame.shape[1],
                banner_height,
            ),
            (0, 0, 180),
            -1,
        )

        text = (
            "!!! ACCIDENT DETECTED !!!"
        )

        font = cv2.FONT_HERSHEY_SIMPLEX

        scale = 1.2

        thickness = 3

        (tw, th), _ = cv2.getTextSize(
            text,
            font,
            scale,
            thickness,
        )

        x = (
            frame.shape[1] - tw
        ) // 2

        cv2.putText(
            frame,
            text,
            (
                x,
                60,
            ),
            font,
            scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )

    return frame


# ============================================================
# HELMET CROP
# ============================================================

def get_helmet_crop(raw_frame, bbox, frame_width, frame_height):
    x1, y1, x2, y2 = bbox

    vehicle_width = max(1, x2 - x1)
    vehicle_height = max(1, y2 - y1)

    padding_x = int(vehicle_width * HELMET_CROP_X_PADDING)
    crop_x1 = max(0, x1 - padding_x)
    crop_x2 = min(frame_width, x2 + padding_x)

    # Motorcycle detections can start below the rider's head. Shift the crop
    # upward and focus on the rider's upper body instead of including mostly
    # wheels and road, which makes the helmet too small for the model.
    crop_y1 = max(0, y1 - int(vehicle_height * HELMET_CROP_TOP_RATIO))
    crop_y2 = min(
        frame_height,
        y1 + int(vehicle_height * HELMET_CROP_BOTTOM_RATIO),
    )

    if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
        return None

    crop = raw_frame[crop_y1:crop_y2, crop_x1:crop_x2]

    if crop.size == 0:
        return None

    return crop


def get_helmet_display_crop(raw_frame, bbox, frame_width, frame_height):
    """Return a wider context crop so review cards show the rider and bike."""
    x1, y1, x2, y2 = map(int, bbox)
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)

    crop_x1 = max(0, x1 - int(box_width * 0.5))
    crop_x2 = min(frame_width, x2 + int(box_width * 0.5))
    # Motorcycle boxes often omit the rider's upper body. Expand upward enough
    # to include the whole person while retaining the motorcycle below.
    crop_y1 = max(0, y1 - int(box_height * 1.6))
    crop_y2 = min(frame_height, y2 + int(box_height * 0.25))

    if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
        return None
    crop = raw_frame[crop_y1:crop_y2, crop_x1:crop_x2].copy()
    return (crop, crop_x1, crop_y1) if crop.size else None


# ============================================================
# PROCESS VIDEO
# ============================================================



def get_rider_person_boxes(crop, rider_x_range=None):
    """Return visible person boxes centered within a motorcycle's rider area."""
    if crop is None or crop.size == 0:
        return []

    try:
        person_boxes = []
        person_results = vehicle_model.predict(
            crop,
            classes=[0],  # COCO class 0 = person
            conf=0.20,
            imgsz=640,
            max_det=5,
            verbose=False,
        )

        for result in person_results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                confidence = float(box.conf[0])
                if confidence >= 0.20:
                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0].tolist(),
                    )

                    person_center_x = (x1 + x2) / 2
                    if rider_x_range and not (
                        rider_x_range[0] <= person_center_x <= rider_x_range[1]
                    ):
                        continue

                    crop_width = crop.shape[1]
                    crop_height = crop.shape[0]

                    box_width = max(0, x2 - x1)
                    box_height = max(0, y2 - y1)

                    # Ignore tiny accidental detections.
                    if (
                        box_width >= crop_width * 0.08
                        and box_height >= crop_height * 0.12
                        # A pedestrian beside or behind the motorcycle can
                        # overlap its horizontal corridor. A rider's person
                        # box should also reach down into the bike/seat area.
                        and y2 >= crop_height * 0.55
                    ):
                        person_boxes.append([x1, y1, x2, y2])

        return person_boxes

    except Exception as e:
        print("Person-in-rider-crop detection error:", e)

    return []


def aggregate_helmet_history(samples):
    """Return a helmet status only when recent evidence is consistent."""
    wearing = [
        confidence
        for status, confidence in samples
        if status == "with_helmet"
    ]
    not_wearing = [
        confidence
        for status, confidence in samples
        if status == "without_helmet"
    ]
    has_explicit_uncertainty = any(
        status == "uncertain" for status, _ in samples
    )

    if has_explicit_uncertainty or (wearing and not_wearing):
        return "uncertain", 0.0

    if not_wearing:
        average_confidence = sum(not_wearing) / len(not_wearing)
        if (
            len(not_wearing) >= HELMET_NO_HELMET_MIN_SAMPLES
            and average_confidence >= HELMET_NO_HELMET_AGGREGATE_MIN_CONFIDENCE
        ) or max(not_wearing) >= 0.92:
            return "without_helmet", round(average_confidence, 3)
        return "uncertain", 0.0

    if wearing:
        strongest_confidence = max(wearing)
        if strongest_confidence >= 0.10:
            return "with_helmet", round(sum(wearing) / len(wearing), 3)

    return "uncertain", 0.0


def assess_road_frame(frame):
    """Estimate wet-surface cues and visibility from the lower-center road area."""
    frame_height, frame_width = frame.shape[:2]
    y1 = int(frame_height * 0.58)
    y2 = int(frame_height * 0.96)
    x1 = int(frame_width * 0.18)
    x2 = int(frame_width * 0.82)
    road_roi = frame[y1:y2, x1:x2]

    if road_roi.size == 0:
        return None

    road_roi = cv2.resize(road_roi, (160, 96), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(road_roi, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(road_roi, cv2.COLOR_BGR2GRAY)

    # Wet asphalt can create broad bright, low-saturation reflections against
    # a darker surface. Bright lane paint and crosswalks can look similar, so
    # a reflection cue alone must never be treated as flood evidence.
    highlight_mask = cv2.inRange(hsv, (0, 0, 185), (179, 95, 255))
    water_like_mask = cv2.inRange(hsv, (0, 0, 80), (179, 110, 255))
    dark_mask = cv2.inRange(gray, 0, 90)
    area = max(1, road_roi.shape[0] * road_roi.shape[1])
    highlight_ratio = cv2.countNonZero(highlight_mask) / area
    water_like_ratio = cv2.countNonZero(water_like_mask) / area
    dark_ratio = cv2.countNonZero(dark_mask) / area

    mean_brightness = cv2.mean(gray)[0]
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

    return {
        "possible_wet": highlight_ratio >= 0.025 and dark_ratio >= 0.18,
        # This is only one cue. Flood risk is confirmed across multiple frames
        # below and must also coincide with a wet-surface cue.
        "possible_flooding": (
            water_like_ratio >= 0.55
            and highlight_ratio >= 0.20
        ),
        "water_like_ratio": round(water_like_ratio, 3),
        "water_reflection_ratio": round(highlight_ratio, 3),
        "limited_visibility": mean_brightness < 48 or mean_brightness > 228 or sharpness < 18,
    }

def process_video(
    input_path,
    output_path,
    progress=None,
):

    input_path = str(
        input_path
    )

    output_path = str(
        output_path
    )

    # ========================================================
    # OPEN VIDEO
    # ========================================================

    cap = cv2.VideoCapture(
        input_path
    )

    if not cap.isOpened():

        raise RuntimeError(
            f"Could not open video: "
            f"{input_path}"
        )

    fps = cap.get(
        cv2.CAP_PROP_FPS
    )

    if fps <= 0:
        fps = 30

    width = int(
        cap.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    height = int(
        cap.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )

    total_frames = int(
        cap.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    if total_frames <= 0:
        total_frames = 1

    print(
        f"Video: {width}x{height} "
        f"| FPS: {fps:.2f} "
        f"| Frames: {total_frames}"
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    raw_output = (
        str(
            Path(
                output_path
            ).with_suffix("")
        )
        + "_raw.mp4"
    )

    fourcc = cv2.VideoWriter_fourcc(
        *"mp4v"
    )

    writer = cv2.VideoWriter(
        raw_output,
        fourcc,
        fps,
        (
            width,
            height,
        ),
    )

    if not writer.isOpened():

        cap.release()

        raise RuntimeError(
            "Could not create output video."
        )

    # ========================================================
    # VEHICLE DATA
    # ========================================================

    unique_ids = set()

    vehicle_class_by_id = {}
    vehicle_class_counts = defaultdict(Counter)
    vehicle_class_scores = defaultdict(lambda: defaultdict(float))
    van_track_ids = set()
    van_evidence_hits = defaultdict(int)
    van_evidence_scores = defaultdict(float)
    ambulance_track_ids = set()

    previous_positions = {}

    trajectories = defaultdict(
        lambda: deque(
            maxlen=TRAJECTORY_LENGTH
        )
    )

    crossed_ids = set()

    lane_history = defaultdict(
        list
    )

    speed_values = []

    speed_violations = set()

    active_sum = 0

    frames_processed = 0

    # ========================================================
    # ANPR DATA
    # ========================================================

    vehicle_plates = {}

    plate_history = defaultdict(
        list
    )
    plate_confidence_by_id = defaultdict(float)
    plate_ocr_confidence_by_id = defaultdict(float)

    plate_seen_ids = set()

    last_plate_boxes = {}

    last_anpr_frame = {}
    last_plate_ocr_frame = {}

    # ========================================================
    # HELMET DATA
    # ========================================================

    helmet_status_by_id = {}
    helmet_confidence_by_id = {}
    helmet_history = defaultdict(list)
    helmet_checked_ids = set()
    last_helmet_frame = {}
    helmet_violation_ids = set()
    helmet_wearing_ids = set()

    helmet_crop_urls = {}

    # ========================================================
    # ACCIDENT DATA
    # ========================================================

    accident_detection_history = deque(
        maxlen=ACCIDENT_CONFIRMATION_WINDOW
    )

    accident_detected = False

    accident_confidence = 0.0

    accident_events = []

    road_condition_samples = []
    road_condition_evidence_frame = None
    road_condition_evidence_time = None
    strongest_road_reflection = -1.0

    # ========================================================
    # COUNTING LINE
    # ========================================================

    line_y = int(
        height * LINE_Y_RATIO
    )

    # ========================================================
    # FRAME LOOP
    # ========================================================

    while True:

        ret, raw_frame = cap.read()

        if not ret:
            break

        frames_processed += 1

        road_frame_check = assess_road_frame(raw_frame)
        if frames_processed % max(1, int(round(fps))) == 0:
            road_sample = road_frame_check
            if road_sample is not None:
                road_sample["time_seconds"] = round(frames_processed / max(fps, 1), 1)
                road_condition_samples.append(dict(road_sample))
                reflection_ratio = road_sample.get("water_reflection_ratio", 0.0)
                # Keep evidence only from samples that have both broad
                # reflection and wet-surface cues. This avoids selecting dry
                # lane markings as flood evidence.
                has_flood_cues = (
                    road_sample.get("possible_flooding")
                    and road_sample.get("possible_wet")
                )
                if has_flood_cues and reflection_ratio > strongest_road_reflection:
                    strongest_road_reflection = reflection_ratio
                    road_condition_evidence_frame = raw_frame.copy()
                    road_condition_evidence_time = road_sample["time_seconds"]

        # Clean frame for AI.
        # All annotations are drawn on a copy.
        frame = raw_frame.copy()

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        if progress:

            percentage = int(
                (
                    frames_processed
                    / total_frames
                )
                * 100
            )

            progress(
                min(
                    percentage,
                    99,
                )
            )

        # ----------------------------------------------------
        # Save old positions
        # ----------------------------------------------------

        old_positions = (
            previous_positions.copy()
        )

        # ====================================================
        # VEHICLE YOLO + BYTETRACK
        #
        # Vehicle detection runs independently
        # from ANPR.
        # ====================================================

        results = vehicle_model.track(
            raw_frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=list(
                CLASSES.keys()
            ),
            conf=VEHICLE_CONFIDENCE,
            iou=0.5,
            verbose=False,
        )

        van_detections = []
        if (
            van_detection_available
            and frames_processed % VAN_DETECTION_INTERVAL == 0
        ):
            van_detections = detect_world_vans(raw_frame)

        active_ids = set()

        current_vehicles = []

        for result in results:

            if result.boxes is None:
                continue

            xyxy = (
                result.boxes.xyxy
                .cpu()
                .tolist()
            )

            classes = (
                result.boxes.cls
                .int()
                .cpu()
                .tolist()
            )

            confidences = (
                result.boxes.conf
                .cpu()
                .tolist()
            )

            if result.boxes.id is not None:

                ids = (
                    result.boxes.id
                    .int()
                    .cpu()
                    .tolist()
                )

            else:

                ids = [
                    None
                    for _ in xyxy
                ]

            for (
                box,
                track_id,
                class_id,
                detection_confidence,
            ) in zip(
                xyxy,
                ids,
                classes,
                confidences,
            ):

                if (
                    class_id
                    not in CLASSES
                ):
                    continue

                x1, y1, x2, y2 = map(
                    int,
                    box,
                )

                class_name = CLASSES[
                    class_id
                ]

                tracked_id = int(track_id) if track_id is not None else None
                if tracked_id is not None and tracked_id in ambulance_track_ids:
                    class_name = AMBULANCE_CLASS
                elif (
                    ambulance_model is not None
                    and class_name in {"car", "truck", "bus"}
                    and frames_processed % AMBULANCE_DETECTION_INTERVAL == 0
                    and crop_is_ambulance((x1, y1, x2, y2), raw_frame)
                ):
                    class_name = AMBULANCE_CLASS
                    if tracked_id is not None:
                        ambulance_track_ids.add(tracked_id)

                if (
                    tracked_id is not None
                    and class_name in {"car", "truck", "bus"}
                    and van_detections
                ):
                    van_confidence = matched_van_confidence(
                        (x1, y1, x2, y2),
                        van_detections,
                    )
                    if van_confidence >= VAN_MATCH_CONFIDENCE:
                        van_evidence_hits[tracked_id] += 1
                        van_evidence_scores[tracked_id] += van_confidence
                        if (
                            van_evidence_hits[tracked_id] >= VAN_REQUIRED_HITS
                            and van_evidence_scores[tracked_id]
                            >= VAN_MIN_CUMULATIVE_CONFIDENCE
                            and tracked_id not in van_track_ids
                        ):
                            van_track_ids.add(tracked_id)
                            vehicle_class_counts[tracked_id].clear()
                            vehicle_class_scores[tracked_id].clear()
                            vehicle_class_by_id[tracked_id] = VAN_CLASS

                if tracked_id in van_track_ids and class_name != AMBULANCE_CLASS:
                    class_name = VAN_CLASS

                if (
                    class_name == "truck"
                    and looks_like_auto_rickshaw(
                        (x1, y1, x2, y2),
                        raw_frame.shape,
                        raw_frame,
                    )
                ):
                    class_name = AUTO_RICKSHAW_CLASS
                elif (
                    class_name in {"car", "truck"}
                    and looks_like_yellow_taxi(
                        (x1, y1, x2, y2),
                        raw_frame,
                        raw_frame.shape,
                    )
                ):
                    # COCO sometimes calls yellow passenger cabs trucks.
                    # A separate likely-taxi label keeps them out of truck totals.
                    class_name = TAXI_CLASS

                # ------------------------------------------------
                # TRACK ID
                # ------------------------------------------------

                if track_id is not None:

                    track_id = int(
                        track_id
                    )

                    active_ids.add(
                        track_id
                    )

                    unique_ids.add(
                        track_id
                    )

                    if class_name == AMBULANCE_CLASS:
                        vehicle_class_counts[track_id].clear()
                        vehicle_class_scores[track_id].clear()
                        vehicle_class_counts[track_id][class_name] = 1
                        vehicle_class_scores[track_id][class_name] = float(
                            detection_confidence
                        )
                        vehicle_class_by_id[track_id] = class_name
                    else:
                        vehicle_class_counts[track_id][class_name] += 1
                        vehicle_class_scores[track_id][class_name] += max(
                            0.01,
                            float(detection_confidence),
                        )
                        previous_class = vehicle_class_by_id.get(track_id)
                        vehicle_class_by_id[track_id] = resolve_vehicle_track_class(
                            vehicle_class_counts[track_id],
                            vehicle_class_scores[track_id],
                            previous_class,
                        )
                    class_name = vehicle_class_by_id[track_id]

                    current_vehicles.append(
                        {
                            "track_id":
                                track_id,
                            "class_name":
                                class_name,
                            "bbox":
                                (
                                    x1,
                                    y1,
                                    x2,
                                    y2,
                                ),
                        }
                    )

                else:

                    track_id = 0

                    current_vehicles.append(
                        {
                            "track_id":
                                0,
                            "class_name":
                                class_name,
                            "bbox":
                                (
                                    x1,
                                    y1,
                                    x2,
                                    y2,
                                ),
                        }
                    )

                # ====================================================
                # CENTER
                # ====================================================

                center_x = (
                    x1 + x2
                ) // 2

                center_y = (
                    y1 + y2
                ) // 2

                # ====================================================
                # SPEED
                # ====================================================

                speed = None

                if (
                    track_id != 0
                    and track_id
                    in old_positions
                ):

                    old_x, old_y = (
                        old_positions[
                            track_id
                        ]
                    )

                    pixel_distance = (
                        (
                            (
                                center_x
                                - old_x
                            ) ** 2
                            +
                            (
                                center_y
                                - old_y
                            ) ** 2
                        )
                        ** 0.5
                    )

                    meters = (
                        pixel_distance
                        * METERS_PER_PIXEL
                    )

                    speed_mps = (
                        meters * fps
                    )

                    speed = (
                        speed_mps * 3.6
                    )

                    if speed < 200:

                        speed_values.append(
                            speed
                        )

                        if (
                            speed
                            > SPEED_LIMIT_KMH
                        ):

                            speed_violations.add(
                                track_id
                            )

                # ====================================================
                # TRAJECTORY
                # ====================================================

                if track_id != 0:

                    trajectories[
                        track_id
                    ].append(
                        (
                            center_x,
                            center_y,
                        )
                    )

                # ====================================================
                # LINE CROSSING
                # ====================================================

                if (
                    track_id != 0
                    and track_id
                    in old_positions
                ):

                    old_y = (
                        old_positions[
                            track_id
                        ][1]
                    )

                    if (
                        old_y < line_y
                        <= center_y
                    ):

                        crossed_ids.add(
                            track_id
                        )

                    elif (
                        old_y > line_y
                        >= center_y
                    ):

                        crossed_ids.add(
                            track_id
                        )

                if track_id != 0:

                    previous_positions[
                        track_id
                    ] = (
                        center_x,
                        center_y,
                    )

                # ====================================================
                # LANE
                # ====================================================

                lane_width = (
                    width / 3
                )

                if (
                    center_x
                    < lane_width
                ):

                    lane = "LEFT"

                elif (
                    center_x
                    < lane_width * 2
                ):

                    lane = "CENTER"

                else:

                    lane = "RIGHT"

                if track_id != 0:

                    lane_history[
                        track_id
                    ].append(
                        lane
                    )

                # ====================================================
                # KNOWN PLATE
                # ====================================================

                plate = ""

                if track_id != 0:

                    plate = (
                        vehicle_plates.get(
                            track_id,
                            "",
                        )
                    )

                # ====================================================
                # KNOWN HELMET
                # ====================================================

                helmet_status = ""
                helmet_confidence = 0.0

                if class_name == "motorcycle" and track_id != 0:
                    helmet_status = helmet_status_by_id.get(
                        track_id,
                        "",
                    )
                    helmet_confidence = helmet_confidence_by_id.get(
                        track_id,
                        0.0,
                    )

                # ====================================================
                # DRAW VEHICLE
                # ====================================================

                draw_vehicle_box(
                    frame,
                    x1,
                    y1,
                    x2,
                    y2,
                    class_name,
                    track_id,
                    speed,
                    plate,
                    helmet_status,
                    helmet_confidence,
                )

                # ====================================================
                # DRAW TRAJECTORY
                # ====================================================

                if track_id != 0:

                    points = list(
                        trajectories[
                            track_id
                        ]
                    )

                    if len(points) >= 2:

                        for i in range(
                            1,
                            len(points),
                        ):

                            cv2.line(
                                frame,
                                points[i - 1],
                                points[i],
                                (0, 255, 0),
                                2,
                            )

        # ====================================================
        # ACTIVE COUNT
        # ====================================================

        active_count = len(
            active_ids
        )

        active_sum += active_count

        # ====================================================
        # HELMET DETECTION
        # ====================================================

        for vehicle in current_vehicles:
            if vehicle["class_name"] != "motorcycle":
                continue

            track_id = vehicle["track_id"]

            if track_id == 0:
                continue

            previous_helmet_frame = last_helmet_frame.get(
                track_id,
                -999999,
            )

            if (
                frames_processed - previous_helmet_frame
                < HELMET_DETECTION_INTERVAL
            ):
                continue

            rider_crop = get_helmet_crop(
                raw_frame,
                vehicle["bbox"],
                width,
                height,
            )

            if rider_crop is None:
                continue

            vehicle_x1, vehicle_y1, vehicle_x2, vehicle_y2 = vehicle["bbox"]
            vehicle_width = max(1, vehicle_x2 - vehicle_x1)
            rider_crop_x1 = max(
                0,
                vehicle_x1 - int(vehicle_width * HELMET_CROP_X_PADDING),
            )
            bike_left_in_crop = vehicle_x1 - rider_crop_x1
            bike_right_in_crop = vehicle_x2 - rider_crop_x1
            bike_center_in_crop = (bike_left_in_crop + bike_right_in_crop) / 2
            rider_x_radius = vehicle_width * 0.55
            rider_x_range = (
                max(0, bike_center_in_crop - rider_x_radius),
                min(rider_crop.shape[1] - 1, bike_center_in_crop + rider_x_radius),
            )

            last_helmet_frame[track_id] = frames_processed

            # CRITICAL SAFETY CHECK:
            # Do not run helmet classification unless an actual
            # person/rider is visible in the motorcycle crop.
            rider_person_boxes = get_rider_person_boxes(
                rider_crop,
                rider_x_range,
            )
            if not rider_person_boxes:
                # A missed person detection is not evidence that the rider
                # disappeared or changed status. Keep earlier samples for
                # temporal voting and retry on the next scheduled frame.
                continue

            helmet_checked_ids.add(track_id)

            helmet_result = helmet_detector.detect(
                rider_crop,
                person_boxes=rider_person_boxes,
            )
            # The enlarged upper crop can contain pedestrians beside the bike.
            # Only accept helmet detections centered over this motorcycle's
            # rider corridor, otherwise a bystander can create a false alert.
            rider_detections = [
                detection
                for detection in helmet_result.get("detections", [])
                if rider_x_range[0]
                <= (detection["bbox"][0] + detection["bbox"][2]) / 2
                <= rider_x_range[1]
            ]

            # Keep the two helmet classes separate. A positive "with helmet"
            # detection must not be discarded just because another region
            # also produced a "without helmet" prediction.
            no_helmet_detections = [
                detection
                for detection in rider_detections
                if "without" in detection["class"]
                and detection["confidence"] >= (
                    HELMET_HEAD_NO_HELMET_MIN_CONFIDENCE
                    if detection.get("head_focused")
                    else HELMET_NO_HELMET_MIN_CONFIDENCE
                )
            ]
            with_helmet_detections = [
                detection
                for detection in rider_detections
                if "with" in detection["class"]
                and detection["confidence"] >= HELMET_WITH_HELMET_MIN_CONFIDENCE
            ]

            if no_helmet_detections and with_helmet_detections:
                helmet_result["helmet_status"] = "uncertain"
                helmet_result["confidence"] = 0.0
                helmet_result["detections"] = rider_detections
            elif no_helmet_detections:
                best_detection = max(
                    no_helmet_detections,
                    key=lambda detection: detection["confidence"],
                )
                helmet_result["helmet_status"] = "without_helmet"
                helmet_result["confidence"] = best_detection["confidence"]
                helmet_result["detections"] = no_helmet_detections
            elif with_helmet_detections:
                best_detection = max(
                    with_helmet_detections,
                    key=lambda detection: detection["confidence"],
                )
                helmet_result["helmet_status"] = "with_helmet"
                helmet_result["confidence"] = best_detection["confidence"]
                helmet_result["detections"] = with_helmet_detections
            else:
                helmet_result["helmet_status"] = "uncertain"
                helmet_result["confidence"] = 0.0
                helmet_result["detections"] = []

            # Save a context image with the whole rider and bike. Draw model
            # detections in that image by translating boxes from the focused
            # rider crop; keep the focused crop only for inference.
            display_data = get_helmet_display_crop(
                raw_frame,
                vehicle["bbox"],
                width,
                height,
            )
            crop_path = HELMET_CROPS_DIR / f"helmet_{track_id}.jpg"
            try:
                if display_data is not None:
                    display_crop, display_x1, display_y1 = display_data
                    vehicle_x1, vehicle_y1, vehicle_x2, vehicle_y2 = vehicle["bbox"]
                    vehicle_width = max(1, vehicle_x2 - vehicle_x1)
                    vehicle_height = max(1, vehicle_y2 - vehicle_y1)
                    rider_x1 = max(0, vehicle_x1 - int(vehicle_width * HELMET_CROP_X_PADDING))
                    rider_y1 = max(0, vehicle_y1 - int(vehicle_height * HELMET_CROP_TOP_RATIO))
                    rider_y2 = min(height, vehicle_y1 + int(vehicle_height * HELMET_CROP_BOTTOM_RATIO))
                    rider_x2 = min(width, vehicle_x2 + int(vehicle_width * HELMET_CROP_X_PADDING))
                    for detection in helmet_result.get("detections", []):
                        dx1, dy1, dx2, dy2 = detection["bbox"]
                        px1 = rider_x1 + dx1 - display_x1
                        py1 = rider_y1 + dy1 - display_y1
                        px2 = rider_x1 + dx2 - display_x1
                        py2 = rider_y1 + dy2 - display_y1
                        px1 = max(0, min(display_crop.shape[1] - 1, px1))
                        py1 = max(0, min(display_crop.shape[0] - 1, py1))
                        px2 = max(0, min(display_crop.shape[1] - 1, px2))
                        py2 = max(0, min(display_crop.shape[0] - 1, py2))
                        box_color = (0, 0, 255) if "without" in detection["class"] else (0, 220, 80)
                        cv2.rectangle(display_crop, (px1, py1), (px2, py2), box_color, 2)
                        draw_label(
                            display_crop,
                            f"{detection['class'].replace('_', ' ').upper()} {detection['confidence']:.0%}",
                            px1,
                            max(22, py1),
                            color=box_color,
                            scale=0.42,
                        )
                else:
                    display_crop = rider_crop

                cv2.imwrite(
                    str(crop_path),
                    display_crop,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 88],
                )
                helmet_crop_urls[track_id] = f"/helmet-crops/{crop_path.name}"
            except Exception as crop_error:
                print(f"Helmet review image save error for track {track_id}: {crop_error}")

            status = helmet_result["helmet_status"]
            confidence = float(helmet_result["confidence"])

            if status in {"with_helmet", "without_helmet", "uncertain"}:
                helmet_history[track_id].append((status, confidence))

            if len(helmet_history[track_id]) > 7:
                helmet_history[track_id] = helmet_history[track_id][-7:]

            best_status, best_confidence = aggregate_helmet_history(
                helmet_history[track_id]
            )

            helmet_status_by_id[track_id] = best_status
            helmet_confidence_by_id[track_id] = best_confidence

            if best_status == "without_helmet":
                helmet_violation_ids.add(track_id)
                helmet_wearing_ids.discard(track_id)
            elif best_status == "with_helmet":
                helmet_wearing_ids.add(track_id)
                helmet_violation_ids.discard(track_id)
            else:
                helmet_wearing_ids.discard(track_id)
                helmet_violation_ids.discard(track_id)

        # Draw the newest helmet result after inference.
        for vehicle in current_vehicles:
            if vehicle["class_name"] != "motorcycle":
                continue

            track_id = vehicle["track_id"]

            if track_id == 0:
                continue

            status = helmet_status_by_id.get(track_id, "")
            confidence = helmet_confidence_by_id.get(track_id, 0.0)

            if not status:
                continue

            x1, y1, x2, y2 = vehicle["bbox"]

            if status == "without_helmet":
                text = "NO HELMET"
                color = (0, 0, 255)
            elif status == "with_helmet":
                text = "HELMET OK"
                color = (0, 255, 0)
            elif status == "uncertain":
                text = "UNCERTAIN"
                color = (0, 190, 255)
            else:
                continue

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                3 if status == "without_helmet" else 2,
            )

            draw_label(
                frame,
                f"{text} {confidence:.0%}",
                x1,
                y2 + 50,
                color=color,
                scale=0.5,
            )

        # ====================================================
        # ANPR - FULL FRAME PLATE DETECTION
        # ====================================================

        if frames_processed % PLATE_DETECTION_INTERVAL == 0:

            last_plate_boxes = {}

            plate_results = plate_model.predict(
                raw_frame,
                conf=PLATE_FULL_FRAME_CONFIDENCE,
                imgsz=1600,
                max_det=100,
                verbose=False,
            )

            plate_candidates = []

            for plate_result in plate_results:

                if plate_result.boxes is None:
                    continue

                for pbox in plate_result.boxes:

                    confidence = float(pbox.conf[0])
                    px1, py1, px2, py2 = map(int, pbox.xyxy[0])

                    pw = px2 - px1
                    ph = py2 - py1

                    if pw <= 0 or ph <= 0:
                        continue

                    # At 4K source resolution, small rear plates can be well
                    # below 20x8 pixels. Do not reject them before a vehicle
                    # crop gets a chance to upscale the plate for detection.
                    if pw < 6 or ph < 3:
                        continue

                    aspect_ratio = pw / ph

                    if aspect_ratio < 1.2 or aspect_ratio > 8.0:
                        continue

                    plate_candidates.append(
                        {
                            "confidence": confidence,
                            "bbox": [px1, py1, px2, py2],
                        }
                    )

            plate_candidates.sort(
                key=lambda p: p["confidence"],
                reverse=True,
            )

            plate_by_track = {}

            for plate_candidate in plate_candidates:

                confidence = plate_candidate["confidence"]
                px1, py1, px2, py2 = plate_candidate["bbox"]

                plate_center_x = (px1 + px2) / 2
                plate_center_y = (py1 + py2) / 2

                best_vehicle = None
                best_distance = float("inf")

                for vehicle in current_vehicles:

                    track_id = vehicle["track_id"]
                    class_name = vehicle["class_name"]

                    if track_id == 0:
                        continue

                    if class_name not in ANPR_CLASSES:
                        continue

                    vx1, vy1, vx2, vy2 = vehicle["bbox"]

                    vehicle_width = max(1, vx2 - vx1)
                    vehicle_height = max(1, vy2 - vy1)
                    # Detector boxes sometimes include a plate just outside
                    # the vehicle box, especially on motorcycles' rear fenders.
                    margin_x = vehicle_width * 0.12
                    margin_top = vehicle_height * 0.06
                    margin_bottom = vehicle_height * 0.24
                    if not (
                        vx1 - margin_x <= plate_center_x <= vx2 + margin_x
                        and vy1 - margin_top <= plate_center_y <= vy2 + margin_bottom
                    ):
                        continue

                    relative_x = (plate_center_x - vx1) / vehicle_width
                    relative_y = (plate_center_y - vy1) / vehicle_height
                    # Plates usually sit near the lower part of a vehicle box.
                    # Normalize by box size so a small distant vehicle doesn't
                    # win association just because its center is close in pixels.
                    distance = abs(relative_x - 0.5) * 0.65 + abs(relative_y - 0.82)

                    if distance < best_distance:
                        best_distance = distance
                        best_vehicle = vehicle

                if best_vehicle is None:
                    continue

                track_id = best_vehicle["track_id"]
                previous = plate_by_track.get(track_id)
                if previous is None or confidence > previous["confidence"]:
                    plate_by_track[track_id] = {
                        "confidence": confidence,
                        "bbox": [px1, py1, px2, py2],
                    }

            # Full-frame inference shrinks tiny plates on distant motorcycles.
            # Retry only motorcycles missed above, at higher effective input
            # resolution, and map crop-local boxes back to frame coordinates.
            for vehicle in current_vehicles:
                track_id = vehicle["track_id"]
                if (
                    track_id == 0
                    or vehicle["class_name"] != "motorcycle"
                    or track_id in plate_by_track
                ):
                    continue

                vx1, vy1, vx2, vy2 = vehicle["bbox"]
                vehicle_width = max(1, vx2 - vx1)
                vehicle_height = max(1, vy2 - vy1)
                crop_x1 = max(0, int(vx1 - vehicle_width * 0.12))
                crop_x2 = min(width, int(vx2 + vehicle_width * 0.12))
                crop_y1 = max(0, int(vy1 - vehicle_height * 0.05))
                crop_y2 = min(height, int(vy2 + vehicle_height * 0.24))
                motorcycle_crop = raw_frame[crop_y1:crop_y2, crop_x1:crop_x2]
                if motorcycle_crop.size == 0:
                    continue

                local_results = plate_model.predict(
                    motorcycle_crop,
                    conf=PLATE_MOTORCYCLE_CROP_CONFIDENCE,
                    imgsz=PLATE_MOTORCYCLE_CROP_SIZE,
                    max_det=8,
                    verbose=False,
                )
                local_candidates = []
                for local_result in local_results:
                    if local_result.boxes is None:
                        continue
                    for local_box in local_result.boxes:
                        confidence = float(local_box.conf[0])
                        lx1, ly1, lx2, ly2 = map(int, local_box.xyxy[0])
                        plate_width = lx2 - lx1
                        plate_height = ly2 - ly1
                        if plate_width < 6 or plate_height < 3:
                            continue
                        aspect_ratio = plate_width / max(1, plate_height)
                        if not 1.2 <= aspect_ratio <= 8.0:
                            continue
                        local_candidates.append({
                            "confidence": confidence,
                            "bbox": [
                                lx1 + crop_x1,
                                ly1 + crop_y1,
                                lx2 + crop_x1,
                                ly2 + crop_y1,
                            ],
                        })

                if local_candidates:
                    plate_by_track[track_id] = max(
                        local_candidates,
                        key=lambda candidate: candidate["confidence"],
                    )

            attempted_ocr_tracks = set()
            for track_id, candidate in plate_by_track.items():
                plate_seen_ids.add(track_id)
                px1, py1, px2, py2 = candidate["bbox"]
                confidence = candidate["confidence"]
                last_plate_boxes[track_id] = {
                    "bbox": [px1, py1, px2, py2],
                    "plate": vehicle_plates.get(track_id, ""),
                }
                plate_confidence_by_id[track_id] = max(
                    plate_confidence_by_id[track_id], confidence
                )

                if (
                    track_id in attempted_ocr_tracks
                    or last_plate_ocr_frame.get(track_id) == frames_processed
                ):
                    continue
                attempted_ocr_tracks.add(track_id)

                pw = max(1, px2 - px1)
                ph = max(1, py2 - py1)
                pad_x = max(3, int(pw * 0.12))
                pad_y = max(3, int(ph * 0.30))
                plate_crop = raw_frame[
                    max(0, py1 - pad_y):min(height, py2 + pad_y),
                    max(0, px1 - pad_x):min(width, px2 + pad_x),
                ]
                if plate_crop.size == 0:
                    continue

                raw_plate_text, ocr_confidence = read_plate(plate_crop)
                plate_text = normalize_indian_plate(raw_plate_text)
                plate_ocr_confidence_by_id[track_id] = max(
                    plate_ocr_confidence_by_id[track_id], ocr_confidence
                )
                if not plate_text:
                    continue

                last_plate_ocr_frame[track_id] = frames_processed
                plate_history[track_id].append(plate_text)
                if len(plate_history[track_id]) > 10:
                    plate_history[track_id] = plate_history[track_id][-10:]

                counter = Counter(plate_history[track_id])
                best_plate = normalize_plate_prefix(counter.most_common(1)[0][0])
                vehicle_plates[track_id] = best_plate
                last_plate_boxes[track_id]["plate"] = best_plate
                print(
                    "ANPR: "
                    f"Vehicle #{track_id} -> {best_plate} "
                    f"(det={confidence:.2f}, reads={counter[best_plate]})"
                )

# ====================================================
        # DRAW PLATE BOXES
        # ====================================================

        for plate in (
            last_plate_boxes.values()
        ):

            x1, y1, x2, y2 = (
                plate["bbox"]
            )

            draw_plate_box(
                frame,
                x1,
                y1,
                x2,
                y2,
                plate["plate"],
            )

        # ====================================================
        # ACCIDENT DETECTION
        # ====================================================

        if (
            frames_processed
            % ACCIDENT_DETECTION_INTERVAL
            == 0
        ):

            try:

                accident_results = (
                    accident_model.predict(
                        raw_frame,
                        conf=ACCIDENT_CONFIDENCE,
                        imgsz=640,
                        verbose=False,
                    )
                )

                current_detections = []

                highest_confidence = 0.0

                for result in (
                    accident_results
                ):

                    if (
                        result.boxes
                        is None
                    ):
                        continue

                    for box in (
                        result.boxes
                    ):

                        class_id = int(
                            box.cls[0]
                        )

                        confidence = float(
                            box.conf[0]
                        )

                        if class_id != 0:
                            continue

                        if (
                            confidence
                            < ACCIDENT_CONFIDENCE
                        ):
                            continue

                        x1, y1, x2, y2 = map(
                            int,
                            box.xyxy[0],
                        )

                        highest_confidence = max(
                            highest_confidence,
                            confidence,
                        )

                        current_detections.append(
                            {
                                "class":
                                    "accident",
                                "confidence":
                                    round(
                                        confidence,
                                        3,
                                    ),
                                "bbox":
                                    [
                                        x1,
                                        y1,
                                        x2,
                                        y2,
                                    ],
                            }
                        )

                accident_detection_history.append(
                    bool(current_detections)
                )
                accident_confidence = (
                    highest_confidence
                    if current_detections
                    else 0.0
                )

                previous_accident_state = (
                    accident_detected
                )

                accident_detected = (
                    sum(accident_detection_history)
                    >= ACCIDENT_REQUIRED_FRAMES
                )

                if (
                    accident_detected
                    and not previous_accident_state
                ):

                    event_number = len(accident_events) + 1
                    analysis_id = Path(output_path).stem.replace(
                        "_processed",
                        "",
                    )
                    evidence_name = f"{analysis_id}_accident_{event_number}.jpg"
                    evidence_path = ACCIDENT_EVIDENCE_DIR / evidence_name
                    evidence_frame = raw_frame.copy()
                    for detection in current_detections:
                        x1, y1, x2, y2 = detection["bbox"]
                        cv2.rectangle(
                            evidence_frame,
                            (x1, y1),
                            (x2, y2),
                            (0, 0, 255),
                            3,
                        )
                        cv2.putText(
                            evidence_frame,
                            f"ACCIDENT {detection['confidence']:.0%}",
                            (x1, max(24, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.75,
                            (0, 0, 255),
                            2,
                            cv2.LINE_AA,
                        )
                    evidence_saved = cv2.imwrite(
                        str(evidence_path),
                        evidence_frame,
                        [int(cv2.IMWRITE_JPEG_QUALITY), 90],
                    )

                    accident_events.append(
                        {
                            "event": event_number,
                            "frame":
                                frames_processed,
                            "time_seconds":
                                round(
                                    frames_processed
                                    / fps,
                                    2,
                                ),
                            "confidence":
                                round(
                                    accident_confidence,
                                    3,
                                ),
                            "evidence_url": (
                                f"/accident-evidence/{evidence_name}"
                                if evidence_saved
                                else ""
                            ),
                        }
                    )

                    print(
                        "!!! ACCIDENT DETECTED !!! "
                        f"Confidence: "
                        f"{accident_confidence:.2f}"
                    )

            except Exception as e:

                print(
                    "Accident detection error:",
                    e,
                )

        # ====================================================
        # COUNTING LINE
        # ====================================================

        cv2.line(
            frame,
            (
                0,
                line_y,
            ),
            (
                width,
                line_y,
            ),
            (255, 255, 0),
            3,
        )

        draw_label(
            frame,
            "COUNTING LINE",
            20,
            line_y - 10,
            color=(255, 255, 0),
            scale=0.5,
        )

        # ====================================================
        # WRITE FRAME
        # ====================================================

        writer.write(
            frame
        )

    # ========================================================
    # RELEASE
    # ========================================================

    cap.release()

    writer.release()

    # ========================================================
    # FFMPEG
    # ========================================================

    ffmpeg_path = (
        r"C:\Users\Asus\AppData\Local"
        r"\Microsoft\WinGet\Packages"
        r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        r"\ffmpeg-9.0.1-full_build"
        r"\bin\ffmpeg.exe"
    )

    if not os.path.exists(
        ffmpeg_path
    ):

        ffmpeg_path = "ffmpeg"

    print(
        "Converting processed video to H.264..."
    )

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        raw_output,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        output_path,
    ]

    try:

        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    except subprocess.CalledProcessError as e:

        print(
            "FFmpeg conversion failed:"
        )

        print(
            e.stderr
        )

        raise

    # ========================================================
    # REMOVE RAW VIDEO
    # ========================================================

    try:

        if os.path.exists(
            raw_output
        ):

            os.remove(
                raw_output
            )

    except Exception as e:

        print(
            "Could not remove raw file:",
            e,
        )

    # ========================================================
    # FINAL STATISTICS
    # ========================================================

    average_active = (
        active_sum
        / frames_processed
        if frames_processed
        else 0
    )

    average_speed = (
        sum(speed_values)
        / len(speed_values)
        if speed_values
        else 0
    )

    detected_plates = list(
        vehicle_plates.values()
    )

    detected_plates = sorted(
        set(
            plate
            for plate in detected_plates
            if plate
        )
    )

    # ========================================================
    # VEHICLE CLASS COUNTS
    # ========================================================

    cars_count = sum(
        1
        for vehicle_class
        in vehicle_class_by_id.values()
        if vehicle_class == "car"
    )

    motorcycles_count = sum(
        1
        for vehicle_class
        in vehicle_class_by_id.values()
        if vehicle_class == "motorcycle"
    )

    buses_count = sum(
        1
        for vehicle_class
        in vehicle_class_by_id.values()
        if vehicle_class == "bus"
    )

    trucks_count = sum(
        1
        for vehicle_class
        in vehicle_class_by_id.values()
        if vehicle_class == "truck"
    )

    vans_count = sum(
        1
        for vehicle_class in vehicle_class_by_id.values()
        if vehicle_class == VAN_CLASS
    )

    heavy_vehicles_count = sum(
        1
        for vehicle_class in vehicle_class_by_id.values()
        if vehicle_class == HEAVY_VEHICLE_CLASS
    )

    uncertain_vehicles_count = sum(
        1
        for vehicle_class in vehicle_class_by_id.values()
        if vehicle_class == UNCERTAIN_VEHICLE_CLASS
    )

    auto_rickshaws_count = sum(
        1
        for vehicle_class in vehicle_class_by_id.values()
        if vehicle_class == AUTO_RICKSHAW_CLASS
    )

    taxis_count = sum(
        1
        for vehicle_class in vehicle_class_by_id.values()
        if vehicle_class == TAXI_CLASS
    )

    ambulances_count = sum(
        1
        for vehicle_class in vehicle_class_by_id.values()
        if vehicle_class == AMBULANCE_CLASS
    )

    # ========================================================
    # HELMET STATISTICS
    # ========================================================

    helmet_records = []

    for track_id in sorted(helmet_checked_ids):
        status = helmet_status_by_id.get(track_id, "uncertain")

        helmet_records.append(
            {
                "vehicle_id": track_id,
                "vehicle": "motorcycle",
                "helmet_status": status,
                "helmet": (
                    "with helmet"
                    if status == "with_helmet"
                    else "without helmet"
                    if status == "without_helmet"
                    else "uncertain"
                ),
                "confidence": round(
                    helmet_confidence_by_id.get(track_id, 0.0),
                    3,
                ),
                "number_plate": vehicle_plates.get(track_id, ""),
                "plate_status": (
                    "readable"
                    if vehicle_plates.get(track_id)
                    else "unreadable"
                    if track_id in plate_seen_ids
                    else "not_detected"
                ),
                "crop_url": helmet_crop_urls.get(track_id, ""),
            }
        )

    helmet_wearing_count = sum(
        1
        for record in helmet_records
        if record["helmet_status"] == "with_helmet"
    )

    helmet_violation_count = sum(
        1
        for record in helmet_records
        if record["helmet_status"] == "without_helmet"
    )

    road_sample_count = len(road_condition_samples)
    wet_sample_ratio = (
        sum(sample["possible_wet"] for sample in road_condition_samples)
        / road_sample_count
        if road_sample_count
        else 0.0
    )
    limited_visibility_ratio = (
        sum(sample["limited_visibility"] for sample in road_condition_samples)
        / road_sample_count
        if road_sample_count
        else 0.0
    )
    flood_samples = [
        sample for sample in road_condition_samples
        if sample.get("possible_flooding") and sample.get("possible_wet")
    ]
    flood_sample_ratio = (
        len(flood_samples) / road_sample_count
        if road_sample_count
        else 0.0
    )
    # Require repeated agreement between broad water-like reflections and a
    # separate wet-surface cue. A single bright frame (for example, a dry
    # zebra crossing or road marking) cannot raise a flood alert.
    flooding_detected = len(flood_samples) >= 2 and flood_sample_ratio >= 0.35
    flood_time_seconds = road_condition_evidence_time if flooding_detected else None
    road_evidence_url = ""
    if flooding_detected and road_condition_evidence_frame is not None:
        evidence_frame = road_condition_evidence_frame.copy()
        evidence_height, evidence_width = evidence_frame.shape[:2]
        road_box = (
            int(evidence_width * 0.18),
            int(evidence_height * 0.58),
            int(evidence_width * 0.82),
            int(evidence_height * 0.96),
        )
        cv2.rectangle(
            evidence_frame,
            (road_box[0], road_box[1]),
            (road_box[2], road_box[3]),
            (0, 190, 255),
            4,
        )
        cv2.putText(
            evidence_frame,
            "POSSIBLE FLOODED ROAD",
            (road_box[0], max(30, road_box[1] - 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 190, 255),
            3,
            cv2.LINE_AA,
        )
        analysis_id = Path(output_path).stem.replace("_processed", "")
        evidence_name = f"{analysis_id}_road_flood.jpg"
        evidence_path = ROAD_EVIDENCE_DIR / evidence_name
        if cv2.imwrite(
            str(evidence_path),
            evidence_frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 92],
        ):
            road_evidence_url = f"/road-evidence/{evidence_name}"
    road_surface_status = (
        "Possible wet surface"
        if road_sample_count and wet_sample_ratio >= 0.35
        else "No strong wet-surface cues"
        if road_sample_count and wet_sample_ratio <= 0.10
        else "Uncertain surface"
        if road_sample_count
        else "Not assessable"
    )
    if flooding_detected:
        road_surface_status = "Possible flooding"
    road_visibility_status = (
        "Limited or variable"
        if road_sample_count and limited_visibility_ratio >= 0.40
        else "Mostly clear"
        if road_sample_count
        else "Not assessable"
    )

    # ========================================================
    # RESULT
    # ========================================================

    result = {

        "unique_vehicles":
            len(unique_ids),

        "tracked_vehicles":
            len(unique_ids),

        # ====================================================
        # IMPORTANT:
        # Frontend expects this "vehicles" object.
        # ====================================================

        "vehicles": {

            "car":
                cars_count,

            "motorcycle":
                motorcycles_count,

            "bus":
                buses_count,

            "truck":
                trucks_count,

            "van":
                vans_count,

            "heavy_vehicle":
                heavy_vehicles_count,

            "uncertain_vehicle":
                uncertain_vehicles_count,

            "auto_rickshaw":
                auto_rickshaws_count,

            "taxi":
                taxis_count,

            "ambulance":
                ambulances_count if ambulance_model is not None else None,
        },

        # Also keep these fields.
        "cars":
            cars_count,

        "motorcycles":
            motorcycles_count,

        "buses":
            buses_count,

        "trucks":
            trucks_count,

        "vans":
            vans_count,

        "heavy_vehicles":
            heavy_vehicles_count,

        "uncertain_vehicles":
            uncertain_vehicles_count,

        "auto_rickshaws":
            auto_rickshaws_count,

        "taxis":
            taxis_count,

        "ambulances":
            ambulances_count if ambulance_model is not None else None,

        "vehicle_breakdown": {

            "car":
                cars_count,

            "motorcycle":
                motorcycles_count,

            "bus":
                buses_count,

            "truck":
                trucks_count,

            "van":
                vans_count,

            "heavy_vehicle":
                heavy_vehicles_count,

            "uncertain_vehicle":
                uncertain_vehicles_count,

            "auto_rickshaw":
                auto_rickshaws_count,

            "taxi":
                taxis_count,

            "ambulance":
                ambulances_count if ambulance_model is not None else None,
        },

        "vehicle_detection_capabilities": {
            "van": {
                "available": van_detection_available,
                "model": "YOLOv8s-World zero-shot (van prompt)"
                if van_detection_available
                else None,
            },
            "ambulance": {
                "available": ambulance_model is not None,
                "reason": None if ambulance_model is not None else (
                    "Run backend/install_ambulance_model.py to install the "
                    "local YOLOv8s-World ambulance detector."
                ),
                "model": AMBULANCE_MODEL_NAME if ambulance_model is not None else None,
                "zero_shot": ambulance_model is not None,
            }
        },

        "frames_processed":
            frames_processed,

        "average_active_vehicles":
            round(
                average_active,
                2,
            ),

        "average_speed_kmh":
            round(
                average_speed,
                2,
            ),

        "speed_violations":
            len(
                speed_violations
            ),

        "vehicles_crossed":
            len(
                crossed_ids
            ),

        "congestion":
            get_congestion(
                int(
                    average_active
                )
            ),

        "trajectory_tracking":
            True,

        "trajectory_length":
            TRAJECTORY_LENGTH,

        # ====================================================
        # ANPR
        # ====================================================

        "anpr":
            True,

        "plate_model":
            str(
                PLATE_MODEL
            ),

        "ocr":
            "EasyOCR",

        "detected_plates":
            detected_plates,

        "total_plates_detected":
            len(
                detected_plates
            ),

        "total_plate_regions": len(plate_seen_ids),

        "vehicle_plates": [
            {
                "vehicle_id": track_id,
                "vehicle": vehicle_class_by_id.get(
                    track_id,
                    "unknown",
                ),
                "number_plate": vehicle_plates.get(track_id, ""),
                "plate_status": (
                    "readable" if vehicle_plates.get(track_id) else "unreadable"
                ),
                "confidence": round(plate_confidence_by_id.get(track_id, 0.0), 3),
                "ocr_confidence": round(plate_ocr_confidence_by_id.get(track_id, 0.0), 3),
                "reads": len(plate_history.get(track_id, [])),
                "agreement": round(
                    Counter(plate_history.get(track_id, [])).get(
                        vehicle_plates.get(track_id, ""),
                        0,
                    ) / max(1, len(plate_history.get(track_id, []))),
                    2,
                ),
            }
            for track_id in sorted(plate_seen_ids)
        ],

        # ====================================================
        # HELMET
        # ====================================================

        "helmet_detection": True,

        "helmet_model": str(HELMET_MODEL),

        "helmet_records": helmet_records,

        "helmet_wearing": helmet_wearing_count,

        "helmet_not_wearing": helmet_violation_count,

        "helmet_violations": helmet_violation_count,

        "total_helmet_checked": len(helmet_records),

        "road_condition": {
            "surface": road_surface_status,
            "visibility": road_visibility_status,
            "frames_checked": road_sample_count,
            "wet_surface_frame_ratio": round(wet_sample_ratio, 2),
            "limited_visibility_frame_ratio": round(limited_visibility_ratio, 2),
            "possible_flooding": flooding_detected,
            "flood_sample_count": len(flood_samples),
            "flood_sample_ratio": round(flood_sample_ratio, 2),
            "flood_time_seconds": flood_time_seconds,
            "evidence_url": road_evidence_url,
            "method": "visual estimate from sampled lower-center video frames",
            "note": "Flood risk is a visual estimate requiring repeated wet-surface and reflection cues. Road markings can still affect the estimate; water depth and safe passability are not verified, and potholes or road damage are not assessed.",
        },

        # ====================================================
        # ACCIDENT
        # ====================================================

        "accident_detection":
            True,

        "accident_detected":
            accident_detected,

        "accident_confidence":
            round(
                accident_confidence,
                3,
            ),

        "accident_events":
            accident_events,

        "total_accidents":
            len(
                accident_events
            ),

        "accident_model":
            "YOLO11x Traffic Accident Detection",

        "accident_classes":
            [
                "accident",
                "vehicle",
            ],
    }

    if progress:

        progress(100)

    # ========================================================
    # TERMINAL SUMMARY
    # ========================================================

    print(
        "\n================================"
    )

    print(
        "VIDEO PROCESSING COMPLETE"
    )

    print(
        "================================"
    )

    print(
        f"Unique vehicles: "
        f"{len(unique_ids)}"
    )

    print(
        f"Cars: "
        f"{cars_count}"
    )

    print(
        f"Motorcycles: "
        f"{motorcycles_count}"
    )

    print(
        f"Buses: "
        f"{buses_count}"
    )

    print(
        f"Trucks: "
        f"{trucks_count}"
    )

    print(
        f"Valid plates: "
        f"{len(detected_plates)}"
    )

    print(
        f"Helmet checked: "
        f"{len(helmet_records)}"
    )

    print(
        f"Helmet wearing: "
        f"{helmet_wearing_count}"
    )

    print(
        f"No helmet: "
        f"{helmet_violation_count}"
    )

    print(
        "Detected plates:"
    )

    for plate in detected_plates:

        print(
            f"  -> {plate}"
        )

    print(
        f"Accidents: "
        f"{len(accident_events)}"
    )

    print(
        "================================"
    )

    return result
