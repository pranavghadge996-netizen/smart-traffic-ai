from pathlib import Path
from ultralytics import YOLO


class HelmetDetector:
    def __init__(
        self,
        model_path: str,
        confidence: float = 0.25,
    ):
        self.model_path = Path(model_path)
        self.confidence = confidence
        self.model = YOLO(str(self.model_path))
        model_names = self.model.names or {}
        if isinstance(model_names, list):
            model_names = dict(enumerate(model_names))
        self.class_names = {}
        self.class_ids = {}
        for class_id, raw_name in model_names.items():
            name = str(raw_name).strip().lower().replace(" ", "_")
            if "without" in name or name in {"no_helmet", "nohelmet"}:
                canonical = "without_helmet"
            elif "with" in name or name in {"helmet", "wearing_helmet"}:
                canonical = "with_helmet"
            else:
                canonical = name
            normalized_id = int(class_id)
            self.class_names[normalized_id] = canonical
            if canonical in {"with_helmet", "without_helmet"}:
                self.class_ids[canonical] = normalized_id

    def detect(self, frame, person_boxes=None):
        if frame is None or frame.size == 0:
            return {
                "helmet_status": "unknown",
                "confidence": 0.0,
                "detections": [],
            }

        try:
            regions = [(frame, 0, 0, 960, False)]
            frame_height, frame_width = frame.shape[:2]

            # Run the detector on each rider's head/shoulder patch as well as
            # the full motorcycle crop. In distant CCTV frames the helmet can
            # be only a few dozen pixels high and disappear in the full crop.
            for person_box in person_boxes or []:
                x1, y1, x2, y2 = map(int, person_box)
                person_width = max(1, x2 - x1)
                person_height = max(1, y2 - y1)
                head_x1 = max(0, x1 - int(person_width * 0.25))
                head_x2 = min(frame_width, x2 + int(person_width * 0.25))
                head_y1 = max(0, y1 - int(person_height * 0.04))
                head_y2 = min(frame_height, y1 + int(person_height * 0.45))
                head_crop = frame[head_y1:head_y2, head_x1:head_x2]
                if head_crop.size:
                    regions.append((head_crop, head_x1, head_y1, 640, True))

            detections = []
            for region, offset_x, offset_y, image_size, head_focused in regions:
                results = self.model.predict(
                    region,
                    conf=self.confidence,
                    imgsz=image_size,
                    max_det=6,
                    verbose=False,
                )

                for result in results:
                    if result.boxes is None:
                        continue

                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])

                        if confidence < self.confidence:
                            continue

                        x1, y1, x2, y2 = map(
                            int,
                            box.xyxy[0].tolist(),
                        )

                        label = self.class_names.get(class_id, "unknown")

                        detections.append({
                            "class": label,
                            "class_id": class_id,
                            "confidence": round(confidence, 3),
                            "bbox": [
                                x1 + offset_x,
                                y1 + offset_y,
                                x2 + offset_x,
                                y2 + offset_y,
                            ],
                            "head_focused": head_focused,
                        })

            if not detections:
                return {
                    "helmet_status": "unknown",
                    "confidence": 0.0,
                    "detections": [],
                }

            # Merge near-identical predictions from the full and head crops.
            # Keep the strongest box where two predictions cover the same
            # head, including when the model disagrees on its class.
            detections.sort(key=lambda item: item["confidence"], reverse=True)
            unique_detections = []
            for detection in detections:
                x1, y1, x2, y2 = detection["bbox"]
                area = max(1, x2 - x1) * max(1, y2 - y1)
                overlaps_existing = False
                for kept in unique_detections:
                    kx1, ky1, kx2, ky2 = kept["bbox"]
                    ix1, iy1 = max(x1, kx1), max(y1, ky1)
                    ix2, iy2 = min(x2, kx2), min(y2, ky2)
                    intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                    kept_area = max(1, kx2 - kx1) * max(1, ky2 - ky1)
                    union = area + kept_area - intersection
                    if (
                        kept["class"] == detection["class"]
                        and kept["head_focused"] == detection["head_focused"]
                        and intersection / max(1, union) >= 0.50
                    ):
                        overlaps_existing = True
                        break
                if not overlaps_existing:
                    unique_detections.append(detection)

            best = max(unique_detections, key=lambda item: item["confidence"])

            return {
                "helmet_status": best["class"],
                "confidence": best["confidence"],
                "detections": unique_detections,
            }

        except Exception as e:
            print("Helmet detection error:", e)

            return {
                "helmet_status": "unknown",
                "confidence": 0.0,
                "detections": [],
            }
