import cv2
import easyocr

video = "camera_feeds/camera_01.mp4"

cap = cv2.VideoCapture(video)

# Best frame found above
cap.set(cv2.CAP_PROP_POS_FRAMES, 325)

ok, frame = cap.read()

if not ok:
    print("Could not read frame")
    raise SystemExit

# Best detected plate box
x1, y1, x2, y2 = 1165, 880, 1427, 1067

plate = frame[y1:y2, x1:x2]

# Save original crop
cv2.imwrite("best_plate_original.jpg", plate)

# Upscale
plate_big = cv2.resize(
    plate,
    None,
    fx=3,
    fy=3,
    interpolation=cv2.INTER_CUBIC
)

cv2.imwrite("best_plate_upscaled.jpg", plate_big)

print("Original size:", plate.shape)
print("Upscaled size:", plate_big.shape)

reader = easyocr.Reader(
    ["en"],
    gpu=False
)

result = reader.readtext(
    plate_big,
    detail=1,
    paragraph=False,
    allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
)

print()
print("==============================")
print("OCR RESULT")
print("==============================")

for item in result:
    print(
        "Text:",
        item[1],
        "Confidence:",
        round(float(item[2]), 3)
    )

cap.release()