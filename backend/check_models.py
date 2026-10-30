from ultralytics import YOLO

models = {
    "PLATE":  "models/anpr/license_plate_detector.pt",
    "HELMET": "models/helmet/helmet_detector.pt",
    "YOLO11n": "yolo11n.pt",
}

for name, path in models.items():
    print("=" * 50)
    print(f"{name}  ->  {path}")
    print("=" * 50)
    try:
        m = YOLO(path)
        print("  Task    :", m.task)
        print("  Classes :", m.names)
        print("  Count   :", len(m.names))
    except Exception as e:
        print("  ERROR:", e)
    print()