from pathlib import Path
from app.routes.traffic import router as traffic_router
from app.routes.weather import router as weather_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


app = FastAPI(
    title="Smart Traffic AI",
    description="AI-powered traffic analysis with YOLO, ByteTrack and ANPR",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path(__file__).resolve().parents[1]

UPLOADS_DIR = BASE / "videos" / "uploads"
PROCESSED_DIR = BASE / "videos" / "processed"
HELMET_CROPS_DIR = BASE / "videos" / "helmet_crops"
ACCIDENT_EVIDENCE_DIR = BASE / "videos" / "accident_evidence"
ROAD_EVIDENCE_DIR = BASE / "videos" / "road_evidence"
CAMERA_FEEDS_DIR = BASE / "camera_feeds"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
HELMET_CROPS_DIR.mkdir(parents=True, exist_ok=True)
ACCIDENT_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
ROAD_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
CAMERA_FEEDS_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/videos",
    StaticFiles(directory=str(PROCESSED_DIR)),
    name="videos",
)

app.mount(
    "/helmet-crops",
    StaticFiles(directory=str(HELMET_CROPS_DIR)),
    name="helmet-crops",
)

app.mount(
    "/accident-evidence",
    StaticFiles(directory=str(ACCIDENT_EVIDENCE_DIR)),
    name="accident-evidence",
)

app.mount(
    "/road-evidence",
    StaticFiles(directory=str(ROAD_EVIDENCE_DIR)),
    name="road-evidence",
)

app.mount(
    "/camera-feeds",
    StaticFiles(directory=str(CAMERA_FEEDS_DIR)),
    name="camera-feeds",
)

app.include_router(
    traffic_router,
    prefix="/api",
)

app.include_router(
    weather_router,
    prefix="/api",
)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Smart Traffic AI",
        "version": "1.0.0",
        "features": [
            "YOLO Vehicle Detection",
            "ByteTrack Object Tracking",
            "Traffic Analytics",
            "Trajectory Tracking",
            "ANPR",
            "EasyOCR",
            "Helmet Detection",
        ],
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "ai_engine": "ready",
        "anpr": "ready",
        "helmet_detection": "ready",
    }
