import cv2
from ultralytics import YOLO

VIDEO = "camera_feeds/camera_01.mp4"
MODEL = "models/anpr/license_plate_detector.pt"

cap = cv2.VideoCapture(VIDEO)
model = YOLO(MODEL)

best = None

print("Scanning for valid plate-shaped detections...")

for frame_no in range(0, 1000, 10):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ok, frame = cap.read()

    if not ok:
        continue

    results = model(frame, conf=0.10, verbose=False)

    for result in results:
        for box in result.boxes:

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])

            w = x2 - x1
            h = y2 - y1

            # Minimum size
            if w < 25 or h < 8:
                continue

            # Number plate should normally be wider than tall
            aspect_ratio = w / h

            if aspect_ratio < 1.5 or aspect_ratio > 6.0:
                continue

            # Prefer larger and more confident detections
            score = conf * w * h

            if best is None or score > best[0]:
                best = (
                    score,
                    frame_no,
                    conf,
                    x1,
                    y1,
                    x2,
                    y2,
                    frame.copy()
                )

cap.release()

if best is None:
    print("")
    print("================================")
    print("NO VALID PLATE DETECTION FOUND")
    print("================================")
    print("")
    raise SystemExit

score, frame_no, conf, x1, y1, x2, y2, frame = best

print("")
print("================================")
print("BEST VALID PLATE DETECTION")
print("================================")
print("Frame:", frame_no)
print("Confidence:", round(conf, 3))
print("Box:", x1, y1, x2, y2)
print("Width:", x2 - x1)
print("Height:", y2 - y1)
print("Aspect ratio:", round((x2 - x1) / (y2 - y1), 2))
print("================================")

# Crop the detected plate
plate = frame[y1:y2, x1:x2]

if plate.size == 0:
    print("ERROR: Empty plate crop")
    raise SystemExit

# Save original crop
cv2.imwrite("debug_plate_original.jpg", plate)

# Upscale for easier inspection
plate_big = cv2.resize(
    plate,
    None,
    fx=5,
    fy=5,
    interpolation=cv2.INTER_CUBIC
)

cv2.imwrite("debug_plate_upscaled.jpg", plate_big)

# Draw detection on full frame
cv2.rectangle(
    frame,
    (x1, y1),
    (x2, y2),
    (0, 255, 0),
    4
)

cv2.putText(
    frame,
    f"PLATE {conf:.2f}",
    (x1, max(30, y1 - 10)),
    cv2.FONT_HERSHEY_SIMPLEX,
    1,
    (0, 255, 0),
    2
)

cv2.imwrite("debug_plate_frame.jpg", frame)

print("")
print("Saved files:")
print("debug_plate_original.jpg")
print("debug_plate_upscaled.jpg")
print("debug_plate_frame.jpg")