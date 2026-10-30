from pathlib import Path
import cv2
from app.services.helmet_detector import HelmetDetector

image = Path("helmet_debug/crop_001_frame_0_unknown.jpg")

detector = HelmetDetector(
    "models/helmet/helmet_detector.pt",
    confidence=0.05
)

frame = cv2.imread(str(image))

for confidence in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:

    detector.confidence = confidence

    result = detector.detect(frame)

    print(
        f"Confidence {confidence:.2f}: "
        f"status={result['helmet_status']}, "
        f"result_confidence={result['confidence']}, "
        f"detections={len(result['detections'])}"
    )