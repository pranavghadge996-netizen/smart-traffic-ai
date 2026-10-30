import cv2
from ultralytics import YOLO

VIDEO = "camera_feeds/camera_01.mp4"
MODEL = "models/anpr/license_plate_detector.pt"

cap = cv2.VideoCapture(VIDEO)
cap.set(cv2.CAP_PROP_POS_FRAMES, 380)

ok, frame = cap.read()

if not ok:
    print("Could not read frame")
    raise SystemExit

model = YOLO(MODEL)

result = model(
    frame,
    conf=0.10,
    imgsz=1280,
    verbose=False
)[0]

print("Detections:", len(result.boxes))

for i, box in enumerate(result.boxes):
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    conf = float(box.conf[0])

    w = x2 - x1
    h = y2 - y1

    print(
        f"{i+1}: conf={conf:.3f} "
        f"box=({x1},{y1},{x2},{y2}) "
        f"size={w}x{h}"
    )

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        3
    )

    cv2.putText(
        frame,
        f"PLATE {i+1} {conf:.2f}",
        (x1, max(30, y1 - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

cv2.imwrite("debug_plate_1280_frame.jpg", frame)

cap.release()

print("")
print("Saved: debug_plate_1280_frame.jpg")