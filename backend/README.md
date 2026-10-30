# Smart Traffic AI — Hackathon Edition

This is a real computer-vision pipeline, not demo numbers.

Features:
- Real video upload
- YOLO vehicle detection
- ByteTrack tracking IDs
- Car / motorcycle / bus / truck counts
- Virtual counting line
- Left/right lane counts
- Approximate speed estimation
- Speed-limit violation count
- Congestion estimate
- Annotated processed video

## Python 3.12 setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs

The first run downloads yolo11n.pt automatically.

### Speed calibration
Speed is only meaningful when calibrated to the camera. Edit:
`app/services/traffic_ai.py`

Set `METERS_PER_PIXEL` using a known road distance. For a hackathon,
label the dashboard as "approximate speed" unless you perform proper camera
calibration/homography.

### Important
A pretrained COCO model does not reliably identify every special vehicle
such as ambulances or police cars. Do not claim those detections unless you
train/use a model that supports them.

### Ambulance detector
Install a local open-vocabulary YOLOv8s-World v2 detector prompted for
`ambulance`:

```powershell
python install_ambulance_model.py
```

The first run downloads the official Ultralytics checkpoint and saves the
prompted model to `models/ambulance/ambulance_detector.pt`; restart the backend
after installation. This zero-shot model is a useful baseline, not a
locally-trained ambulance classifier. For better accuracy on your camera views,
fine-tune a one-class model on labeled ambulance and ordinary-traffic footage:

```powershell
python train_ambulance_model.py --data path\to\ambulance-data.yaml
```

The dataset YAML must define an `ambulance` class and valid train/validation
image and label paths. Include varied ambulance views and ordinary traffic
without ambulance labels as negative examples. The training script copies
`best.pt` to the model path above; restart the backend afterward. Until those
trained weights are present, the UI reports ambulance detection as unavailable
instead of displaying a misleading zero.
