from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
import json
import shutil, threading, traceback
from app.services.traffic_ai import process_video

router = APIRouter(tags=["Traffic AI"])
BASE = Path(__file__).resolve().parents[2]
UPLOADS = BASE/"videos"/"uploads"
PROCESSED = BASE/"videos"/"processed"
REPORTS = BASE/"reports"
ACCIDENT_EVIDENCE = BASE/"videos"/"accident_evidence"
ROAD_EVIDENCE = BASE/"videos"/"road_evidence"
REPORTS.mkdir(parents=True, exist_ok=True)
ACCIDENT_EVIDENCE.mkdir(parents=True, exist_ok=True)
ROAD_EVIDENCE.mkdir(parents=True, exist_ok=True)
JOBS = {}
EXTS = {".mp4",".avi",".mov",".mkv",".webm"}

@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in EXTS:
        raise HTTPException(400, "Upload MP4, AVI, MOV, MKV or WEBM.")
    job_id = uuid4().hex
    upload_name = Path(file.filename or "traffic-video").name
    source = UPLOADS/f"{job_id}{ext}"
    output = PROCESSED/f"{job_id}_processed.mp4"
    with source.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    JOBS[job_id] = {"job_id":job_id,"status":"queued","progress":0,"message":"Queued","results":None,"error":None}

    def worker():
        try:
            JOBS[job_id].update(status="processing", message="Running YOLO + ByteTrack...")
            result = process_video(
                str(source), str(output),
                progress=lambda p: JOBS[job_id].update(progress=p, message=f"AI processing {p}%")
            )
            result["video_url"] = f"/videos/{output.name}"
            report = {
                "id": job_id,
                "name": upload_name,
                "type": "VIDEO ANALYSIS",
                "status": "READY",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "results": result,
            }
            report_path = REPORTS / f"{job_id}.json"
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            JOBS[job_id].update(
                status="completed",
                progress=100,
                message="Analysis complete",
                results=result,
                report_id=job_id,
            )
        except Exception as e:
            traceback.print_exc()
            JOBS[job_id].update(status="failed",message="Processing failed",error=str(e))
    threading.Thread(target=worker, daemon=True).start()
    return {"job_id":job_id,"status":"queued"}

@router.get("/reports")
def reports(response: Response):
    # Reports change as analysis jobs finish; never let the browser or an
    # intermediary reuse an older directory listing for the refresh action.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return _read_saved_reports()


@router.post("/reports/refresh")
def refresh_reports(response: Response):
    """Explicitly reload the current report list from persistent storage."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return _read_saved_reports()


def _read_saved_reports():
    saved_reports = []
    for report_path in REPORTS.glob("*.json"):
        try:
            saved_reports.append(json.loads(report_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    saved_reports.sort(key=lambda report: report.get("created_at", ""), reverse=True)
    return saved_reports


@router.delete("/reports/{report_id}")
def delete_report(report_id: str):
    """Delete one saved report and its generated/source video artifacts."""
    if len(report_id) != 32 or not report_id.isalnum():
        raise HTTPException(400, "Invalid report ID.")

    report_path = REPORTS / f"{report_id}.json"
    if not report_path.is_file():
        raise HTTPException(404, "Report not found.")

    job_state = JOBS.get(report_id, {}).get("status")
    if job_state in {"queued", "processing"}:
        raise HTTPException(409, "This analysis is still running.")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(500, f"Could not read report: {error}")

    files_to_remove = [PROCESSED / f"{report_id}_processed.mp4"]
    source_extension = Path(report.get("name", "")).suffix.lower()
    if source_extension in EXTS:
        files_to_remove.append(UPLOADS / f"{report_id}{source_extension}")
    files_to_remove.extend(ACCIDENT_EVIDENCE.glob(f"{report_id}_accident_*.jpg"))
    files_to_remove.extend(ROAD_EVIDENCE.glob(f"{report_id}_road_flood.*"))

    deleted_files = 0
    try:
        for path in files_to_remove:
            if path.is_file():
                path.unlink()
                deleted_files += 1
        report_path.unlink()
    except OSError as error:
        raise HTTPException(500, f"Could not fully delete report files: {error}")

    JOBS.pop(report_id, None)
    return {"deleted": report_id, "deleted_files": deleted_files}

@router.delete("/accident-evidence")
def clear_accident_evidence():
    """Remove saved accident snapshots and their accident alert entries."""
    removed_events = 0
    updated_reports = 0

    for report_path in REPORTS.glob("*.json"):
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        results = report.get("results") or {}
        events = results.get("accident_events") or []
        if not events:
            continue

        removed_events += len(events)
        results["accident_events"] = []
        results["total_accidents"] = 0
        results["accident_detected"] = False
        results["accident_confidence"] = 0.0
        report["results"] = results

        try:
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            updated_reports += 1
        except OSError as error:
            raise HTTPException(500, f"Could not update report {report_path.name}: {error}")

    for job in JOBS.values():
        results = job.get("results") or {}
        if results.get("accident_events"):
            results["accident_events"] = []
            results["total_accidents"] = 0
            results["accident_detected"] = False
            results["accident_confidence"] = 0.0

    deleted_files = 0
    for evidence_file in ACCIDENT_EVIDENCE.iterdir():
        if evidence_file.is_file() and evidence_file.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            try:
                evidence_file.unlink()
                deleted_files += 1
            except OSError as error:
                raise HTTPException(500, f"Could not delete {evidence_file.name}: {error}")

    return {
        "removed_events": removed_events,
        "updated_reports": updated_reports,
        "deleted_files": deleted_files,
    }

@router.get("/jobs/{job_id}")
def job(job_id: str):
    if job_id not in JOBS:
        # Completed reports survive backend restarts. Restore the result from
        # disk so a browser with a saved job ID can still show it.
        report_path = REPORTS / f"{job_id}.json"
        if report_path.is_file():
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "progress": 100,
                    "message": "Analysis complete",
                    "results": report.get("results"),
                    "report_id": job_id,
                }
            except (OSError, json.JSONDecodeError):
                pass
        raise HTTPException(404, "Job not found")
    return JOBS[job_id]
