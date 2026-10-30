"""Install a local, open-vocabulary YOLO-World detector for ambulances.

The upstream YOLOv8s-World v2 checkpoint is specialized here with the single
"ambulance" text prompt and saved to the path used by the traffic pipeline.
This is a zero-shot starting model; fine-tuning on local traffic footage is
recommended before relying on it for operational decisions.
"""

import argparse
from pathlib import Path

from ultralytics import YOLO


BACKEND_DIR = Path(__file__).resolve().parent
MODEL_DIR = BACKEND_DIR / "models" / "ambulance"
MODEL_PATH = MODEL_DIR / "ambulance_detector.pt"
BASE_MODEL = "yolov8s-worldv2.pt"


def main():
    parser = argparse.ArgumentParser(description="Install the local ambulance detector")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild the prompted detector even if it is already installed",
    )
    args = parser.parse_args()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # A prompted model should only need its detector weights and saved text
    # embedding. Avoid shipping the much larger CLIP text encoder in the file.
    if MODEL_PATH.is_file() and MODEL_PATH.stat().st_size < 100_000_000 and not args.force:
        print(f"Ambulance model is already installed: {MODEL_PATH}")
        print("Restart the backend to load it into video analysis.")
        return

    print(f"Loading {BASE_MODEL}; Ultralytics will download it if needed...")
    model = YOLO(BASE_MODEL)
    model.set_classes(["ambulance"])
    # set_classes computes and stores the prompt embedding. The CLIP encoder
    # is not needed for inference once that embedding has been created.
    model.model.clip_model = None
    staged_path = MODEL_PATH.with_name("ambulance_detector.staged.pt")
    model.save(str(staged_path))

    installed = YOLO(str(staged_path))
    names = installed.names
    names = names.values() if isinstance(names, dict) else names
    if not any(str(name).strip().lower() == "ambulance" for name in names):
        staged_path.unlink(missing_ok=True)
        raise RuntimeError("Saved model did not retain the ambulance prompt.")
    if getattr(installed.model, "clip_model", None) is not None:
        staged_path.unlink(missing_ok=True)
        raise RuntimeError("Saved model unexpectedly includes the CLIP encoder.")
    if staged_path.stat().st_size >= 100_000_000:
        staged_path.unlink(missing_ok=True)
        raise RuntimeError("Saved model is unexpectedly large; keeping the previous model.")

    staged_path.replace(MODEL_PATH)

    print(f"Ambulance model installed: {MODEL_PATH}")
    print("Restart the backend to load it into video analysis.")


if __name__ == "__main__":
    main()
