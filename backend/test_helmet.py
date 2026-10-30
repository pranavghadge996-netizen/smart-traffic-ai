import cv2
from pathlib import Path
from ultralytics import YOLO
from app.services.helmet_detector import HelmetDetector

vehicle_model = YOLO("models/yolo11n.pt")

helmet_detector = HelmetDetector(
    "models/helmet/helmet_detector.pt",
    confidence=0.20
)

video = "camera_feeds/camera_01.mp4"

output_dir = Path("helmet_debug")
output_dir.mkdir(exist_ok=True)

cap = cv2.VideoCapture(video)

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print("Total frames:", total_frames)
print("Saving motorcycle crops to:", output_dir.resolve())
print()

crop_number = 0

for i in range(10):

    frame_number = int(i * total_frames / 10)

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    ok, frame = cap.read()

    if not ok:
        continue

    results = vehicle_model(
        frame,
        conf=0.25,
        verbose=False
    )

    motorcycles = []

    for result in results:

        if result.boxes is None:
            continue

        for box in result.boxes:

            class_id = int(box.cls[0])

            # COCO class 3 = motorcycle
            if class_id != 3:
                continue

            confidence = float(box.conf[0])

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0].tolist()
            )

            motorcycles.append(
                (x1, y1, x2, y2, confidence)
            )

    print(
        f"Frame {frame_number}: "
        f"{len(motorcycles)} motorcycles"
    )

    for motorcycle_number, (x1, y1, x2, y2, vehicle_conf) in enumerate(
        motorcycles[:5],
        start=1
    ):

        box_width = x2 - x1
        box_height = y2 - y1

        # Expand motorcycle box
        pad_x = int(box_width * 0.30)
        pad_y = int(box_height * 0.25)

        crop_x1 = max(0, x1 - pad_x)
        crop_x2 = min(frame.shape[1], x2 + pad_x)

        crop_y1 = max(0, y1 - pad_y)
        crop_y2 = min(frame.shape[0], y2 + pad_y)

        crop = frame[
            crop_y1:crop_y2,
            crop_x1:crop_x2
        ]

        if crop.size == 0:
            continue

        crop_number += 1

        # Run helmet detection
        helmet_result = helmet_detector.detect(crop)

        filename = (
            output_dir /
            f"crop_{crop_number:03d}"
            f"_frame_{frame_number}"
            f"_{helmet_result['helmet_status']}.jpg"
        )

        # Draw result on crop
        display_crop = crop.copy()

        label = (
            f"{helmet_result['helmet_status']} "
            f"{helmet_result['confidence']:.2f}"
        )

        cv2.putText(
            display_crop,
            label,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.imwrite(
            str(filename),
            display_crop
        )

        print(
            f"  Motorcycle {motorcycle_number}: "
            f"{helmet_result['helmet_status']} "
            f"({helmet_result['confidence']})"
        )

cap.release()

print()
print("==============================")
print("Saved crops:", crop_number)
print("Folder:", output_dir.resolve())
print("==============================")