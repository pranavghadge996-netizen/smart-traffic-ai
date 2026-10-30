"""Fine-tune the project's YOLO11n detector for ambulance recognition.

The dataset YAML must define an `ambulance` detection class and point to
train/validation images and YOLO-format bounding-box labels. Include ordinary
cars, vans, trucks, buses and difficult negative examples in the image sets.
"""

import argparse
from pathlib import Path
import shutil

from ultralytics import YOLO


BACKEND_DIR = Path(__file__).resolve().parent
BASE_WEIGHTS = BACKEND_DIR / "models" / "yolo11n.pt"
RUNS_DIR = BACKEND_DIR / "models" / "ambulance" / "training"
DEPLOY_WEIGHTS = BACKEND_DIR / "models" / "ambulance" / "ambulance_detector.pt"


def main():
    parser = argparse.ArgumentParser(description="Train the optional ambulance detector")
    parser.add_argument("--data", required=True, help="Path to YOLO dataset YAML")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()

    data_yaml = Path(args.data).expanduser().resolve()
    if not data_yaml.is_file():
        parser.error(f"Dataset YAML not found: {data_yaml}")
    if not BASE_WEIGHTS.is_file():
        parser.error(f"Base YOLO11n weights not found: {BASE_WEIGHTS}")

    model = YOLO(str(BASE_WEIGHTS))
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str(RUNS_DIR.parent),
        name=RUNS_DIR.name,
        exist_ok=True,
    )

    best_weights = RUNS_DIR / "weights" / "best.pt"
    if not best_weights.is_file():
        raise FileNotFoundError(f"Training did not produce {best_weights}")

    DEPLOY_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_weights, DEPLOY_WEIGHTS)
    print(f"Ambulance detector saved to: {DEPLOY_WEIGHTS}")
    print("Restart the backend to load it into the video-analysis pipeline.")


if __name__ == "__main__":
    main()
