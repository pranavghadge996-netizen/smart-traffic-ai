from pathlib import Path
import cv2
from ultralytics import YOLO


class AccidentDetector:
    """
    Traffic accident detector using a YOLO accident model.
    """

    def __init__(
        self,
        model_path: str,
        confidence: float = 0.60,
        required_frames: int = 3,
    ):
        self.model_path = Path(model_path)
        self.confidence = confidence
        self.required_frames = required_frames

        self.model = YOLO(str(self.model_path))

        # The model classes are:
        # 0 = accident
        # 1 = vehicle
        self.accident_class_id = 0

        self.consecutive_accident_frames = 0

    def detect(self, frame):
        """
        Detect accidents in one frame.

        Returns:
            {
                "accident": bool,
                "confidence": float,
                "detections": list
            }
        """

        results = self.model(
            frame,
            conf=self.confidence,
            verbose=False,
        )

        detections = []
        highest_confidence = 0.0

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                if class_id != self.accident_class_id:
                    continue

                if confidence < self.confidence:
                    continue

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                highest_confidence = max(
                    highest_confidence,
                    confidence
                )

                detections.append({
                    "class": "accident",
                    "confidence": round(confidence, 3),
                    "bbox": [x1, y1, x2, y2],
                })

        # Require multiple consecutive frames.
        if detections:
            self.consecutive_accident_frames += 1
        else:
            self.consecutive_accident_frames = 0

        accident_confirmed = (
            self.consecutive_accident_frames
            >= self.required_frames
        )

        return {
            "accident": accident_confirmed,
            "confidence": round(highest_confidence, 3),
            "detections": detections,
        }


def draw_accidents(frame, result):
    """
    Draw accident detections on a frame.
    """

    for detection in result["detections"]:
        x1, y1, x2, y2 = detection["bbox"]
        confidence = detection["confidence"]

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 0, 255),
            3,
        )

        label = f"ACCIDENT {confidence:.0%}"

        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 10, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )

    if result["accident"]:
        cv2.rectangle(
            frame,
            (0, 0),
            (frame.shape[1] - 1, frame.shape[0] - 1),
            (0, 0, 255),
            8,
        )

        cv2.putText(
            frame,
            "!!! ACCIDENT DETECTED !!!",
            (40, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 0, 255),
            3,
        )

    return frame