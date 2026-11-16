"""
server.py
---------
Flask REST API for AI Media Processing (Cotton Weed Detection).
Supports OpenVINO GPU acceleration and H.264 web-optimized video.
I don't have NVIDIA GPUs, so this is designed to run on CPU/GPU-agnostic OpenVINO for broad compatibility.
"""

import io
import json
import os
import shutil
import threading
import uuid
import zipfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

_SERVER_DIR  = Path(__file__).resolve().parent
# Resolve backend root (parent of this file's directory)
# Server defaults to serving media from a "data" folder at the backend root, which contains uploads, frames, annotated, and output subfolders.
# It's important to keep this structure organized, especially since we dynamically create job-specific subfolders in the output directory for results and datasets.

_BACKEND_DIR = _SERVER_DIR.parent
# Focus over the backend folder, like cd ..

import sys
sys.path.insert(0, str(_BACKEND_DIR.parent))  
# project root on path; main directories with access to each other
# Helpful for relative imports in scripts and utils, and allows us to run this server.py directly without worrying about PYTHONPATH or package structure.


# Importing the variables from various modules after adjusting sys.path

from backend.utils.path_manager import (
    ensure_dirs, get_upload_path, get_frames_path,
    get_annotated_path, get_output_video_path, get_job_dataset_path,
    get_job_output_path, UPLOADS_DIR, OUTPUT_DIR, ANNOTATED_DIR, DATA_DIR
)

from backend.utils.file_naming import generate_timestamp
from backend.utils.logger import get_logger, get_log_file_path
from backend.scripts.video2image import extract_frames
from backend.scripts.annotation  import annotate_frames, annotate_single_image, _DEFAULT_MODEL
from backend.scripts.convert      import images_to_video, _find_ffmpeg

logger = get_logger("server")

# ---------------------------------------------------------------------------
app = Flask(__name__) # Added __name__ for working in any name even if not run as main
CORS(app) # Allowing frontend calls 
ensure_dirs() # Safety Check

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv"}
ALLOWED_EXT       = ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT

# -----------------------------------------------------------------------------

# In-memory job tracking 
# Each job_id maps to a dict with keys: status, message, result, progress
# Added _ before _jobs to indicate it's a private variable, 
# and a lock for thread safety since jobs are updated from worker threads.

_jobs: dict = {}
_jobs_lock = threading.Lock()
# Mutex Lock to ensure thread-safe access to the _jobs dictionary
# I learned about this in the my professor course on Operating Systems COMP 340 

def _safe_job_dir(job_id: str) -> Path | None:
    """Resolve *job_id* directory under OUTPUT_DIR safely."""
    clean_id = secure_filename(job_id)
    if not clean_id or clean_id != job_id:
        return None
    candidate = (OUTPUT_DIR / clean_id).resolve()
    if not str(candidate).startswith(str(OUTPUT_DIR.resolve())):
        return None
    return candidate


def _set_job(job_id: str, status: str, message: str = "", result: dict = None, progress: dict = None):
    payload = {
        "status":   status,
        "message":  message,
        "result":   result or {},
        "progress": progress or {},
    }
    with _jobs_lock:
        _jobs[job_id] = payload
    job_dir = _safe_job_dir(job_id)
    if job_dir is not None:
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _get_job(job_id: str) -> dict | None:
    """Retrieve job status from memory or persisted status.json fallback."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is not None:
        return job
    job_dir = _safe_job_dir(job_id)
    if job_dir is None:
        return None
    status_file = job_dir / "status.json"
    if not status_file.exists():
        return None
    try:
        loaded = json.loads(status_file.read_text(encoding="utf-8"))
        with _jobs_lock:
            _jobs[job_id] = loaded
        return loaded
    except Exception as exc:
        logger.warning("Failed reading persisted job status %s: %s", job_id, exc)
        return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# API Endpoints:
# POST /api/upload - Upload a video or image file.

# In this endpoint is triggered on the upload of a file, 
# it checks for the presence of the file in the request, 
# validates its extension against allowed types, and saves it to the uploads directory. 
# Replies in the JSON format with the filename, type (video or image), and a URL to access the uploaded file.

@app.route("/api/upload", methods=["POST"])
def upload():
    """Accept a file upload."""
    if "file" not in request.files: # IF USER DID NOT UPLOAD A FILE, RETURN ERROR -- AI SUGGESTS DONT UNDERSTAND WHY IT IS NEEDED 
        return jsonify({"error": "No file part"}), 400 
    file = request.files["file"] # Get the uploaded file from the request
    if file.filename == "": # IF USER DID NOT SELECT A FILE, RETURN ERROR
        return jsonify({"error": "No file selected"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Unsupported: {ext}"}), 400

    filename  = secure_filename(file.filename) # secure name to prevent directory traversal, etc.
    save_path = get_upload_path(filename)
    file.save(str(save_path))

    file_type = "video" if ext in ALLOWED_VIDEO_EXT else "image"
    logger.info("Uploaded %s (%s, %d bytes) -> %s", filename, file_type, save_path.stat().st_size, save_path)
    return jsonify({
        "filename": filename,
        "type":     file_type,
        "url":      f"/api/media/uploads/{filename}",
    }) # JSON response with the filename, type, and URL to access the uploaded file


# API endpoint for processing a single image with inference and label export.
@app.route("/api/process-image", methods=["POST"])
def process_image():
    """Single-image inference with label export."""
    data     = request.get_json(force=True) or {}
    filename = data.get("filename", "")
    if not filename: return jsonify({"error": "filename required"}), 400 
    # This endpoint is designed for processing a single image file. 

    upload_path = get_upload_path(filename)
    if not upload_path.exists(): return jsonify({"error": "Not found"}), 404

    # The confidence threshold for annotation can be passed in the request data, defaulting to 0.25 if not provided.
    conf = float(data.get("conf", 0.25))
    # We generate a timestamp + short nonce to create unique output filenames for traceability and cache safety.
    ts   = generate_timestamp()
    nonce = uuid.uuid4().hex[:6]

    try:
        out_name = f"inference_{ts}_{nonce}_{upload_path.name}"
        out_path = OUTPUT_DIR / out_name
        logger.info("Image inference started: %s (conf=%.2f)", upload_path.name, conf)
        res = annotate_single_image(str(upload_path), str(out_path), conf=conf)
        label_name = Path(res["label_path"]).name
        logger.info("Image inference complete: %s -> %s", out_name, res.get("summary", {}))

        return jsonify({
            "annotated_url":  f"/api/media/output/{out_name}",
            "label_url":      f"/api/media/output/{label_name}",
            "labels_zip_url": f"/api/download/image-dataset/{out_name}",
            "timestamp":      ts,
            "summary":        res.get("summary", {}),
        })
    except Exception as exc:
        logger.exception("Image inference failed for %s", upload_path.name)
        return jsonify({"error": str(exc)}), 500 # 500 = Internal Server Error

# For Video Processing, we have a more complex pipeline that involves multiple steps 
@app.route("/api/process", methods=["POST"])
def process():
    """Trigger the full video pipeline."""
    data     = request.get_json(force=True) or {} 
    # Requesting JSON data from the client, which should include the filename of the uploaded video, frame interval for extraction, and confidence threshold for annotation

    filename = data.get("filename", "")
    # File name is assisgned from the request data, and if it's not provided, we return a 400 Bad Request error indicating that the filename is required.
    if not filename: return jsonify({"error": "filename required"}), 400

    # get_upload_path is a utility function that constructs the full path to the uploaded file based on the filename.
    upload_path = get_upload_path(filename)
    if not upload_path.exists(): return jsonify({"error": "Not found"}), 404

    # Assigning default values for frame_interval and confidence threshold if they are not provided in the request data.
    frame_interval = int(data.get("frame_interval", 5))
    conf           = float(data.get("conf", 0.25))

    # Unique Job ID is genberated
    job_id         = str(uuid.uuid4())
    _set_job(job_id, "queued", "Job queued")
    logger.info("Queued video job %s: file=%s interval=%d conf=%.2f", job_id, filename, frame_interval, conf)

    t = threading.Thread(
        target=_run_pipeline, # _run_pipeline is expected to return the result of the video processing pipeline and update the job status accordingly. It takes the job_id, path to the uploaded video, frame interval, and confidence threshold as arguments.
        args=(job_id, str(upload_path), frame_interval, conf), # Arguments passed to the target functions
        daemon=True, # Background thread
    )
    t.start()
 
    return jsonify({"job_id": job_id, "status": "queued"})


@app.route("/api/status/<job_id>", methods=["GET"])
def status(job_id: str): # Just returns the current status of a job based on its ID, including progress and any results if available.
    job = _get_job(job_id)
    if job is None:
        logger.warning("Status requested for unknown job: %s", job_id)
        return jsonify({"error": "Unknown job"}), 404
    return jsonify({"job_id": job_id, **job}) # returns the job id and  whole job dict which has status, message, result, and progress keys in JSON format


@app.route("/api/health", methods=["GET"])
def health():
    """Return backend health, model availability, and log path diagnostics."""
    return jsonify({
        "status": "ok",
        "model_path": str(_DEFAULT_MODEL),
        "model_exists": Path(_DEFAULT_MODEL).exists(),
        "ffmpeg_available": _find_ffmpeg() is not None,
        "log_file": str(get_log_file_path()),
    })


@app.route("/api/logs", methods=["GET"])
def view_logs():
    """Return recent lines from cottonvision.log for diagnostics."""
    lines_requested = max(1, min(500, int(request.args.get("lines", 120))))
    log_path = get_log_file_path()
    if not log_path.exists():
        return jsonify({"log_file": str(log_path), "lines": []})
    all_lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return jsonify({"log_file": str(log_path), "lines": all_lines[-lines_requested:]})


# For the image and videos access or viewing, we have a media endpoint that serves files from the data directory.
@app.route("/api/media/<path:filepath>", methods=["GET"])
def media(filepath: str):
    """Serve media files (images, videos) from data directory with byte-range support."""
    base_dir = DATA_DIR.resolve()
    full_path = (base_dir / filepath).resolve()
    if not str(full_path).startswith(str(base_dir)):
        logger.warning("Blocked directory traversal on /api/media: %s", filepath)
        abort(403)
    if not full_path.exists() or not full_path.is_file():
        logger.warning("Media not found: %s", full_path)
        abort(404)

    ext = full_path.suffix.lower()
    if ext in ('.mp4', '.avi', '.mov', '.mkv'):
        return send_file(str(full_path), mimetype='video/mp4', conditional=True)
    if ext == '.webm':
        return send_file(str(full_path), mimetype='video/webm', conditional=True)
    return send_file(str(full_path), conditional=True)

# Fow downlaoding the paired YOLO dataset for a specific job, we have an endpoint that dynamically zips the dataset directory and serves it as a downloadable file.
@app.route("/api/download/dataset/<job_id>", methods=["GET"])
def download_dataset(job_id: str):
    """Dynamically zip and download the paired YOLO dataset for a job."""
    job = _get_job(job_id)
    if job is None or job["status"] != "done": return abort(404)
    # On demand zipping of the dataset directory for the specified job. It checks if the job exists and is marked as "done". If not, it returns a 404 error. If the job is valid, it retrieves the dataset directory path from the job's result, creates an in-memory zip file of the dataset, and sends it as a downloadable response to the client.
    dataset_dir = job.get("result", {}).get("dataset_dir")
    if not dataset_dir: return abort(404)

    dataset_path = Path(dataset_dir)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(dataset_path.iterdir()):
            if f.is_file(): zf.write(str(f), f.name)

    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True,
                   download_name=f"yolo_dataset_{job_id[:8]}.zip") # Last 8 characters of the job ID are used in the zip file 


@app.route("/api/download/image-dataset/<path:image_filename>", methods=["GET"])
def download_image_dataset(image_filename: str):
    """Zip and download paired annotated image and YOLO .txt label from single-image inference."""
    safe_img = (OUTPUT_DIR / image_filename).resolve()
    if not str(safe_img).startswith(str(OUTPUT_DIR.resolve())):
        return abort(403)
    if not safe_img.exists() or not safe_img.is_file():
        return abort(404)

    safe_lbl = safe_img.with_suffix(".txt")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(safe_img), safe_img.name)
        if safe_lbl.exists() and safe_lbl.is_file():
            zf.write(str(safe_lbl), safe_lbl.name)

    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True,
                     download_name=f"yolo_labels_{safe_img.stem}.zip")


# Downloading the folder endpoint is a more general version of the dataset download, allowing users to download any folder within the output directory. It performs a security check to ensure that the requested folder is indeed within the output directory to prevent unauthorized access to other parts of the filesystem. If the folder exists and is valid, it creates an in-memory zip file of the entire folder and serves it as a downloadable response.
@app.route("/api/download/folder/<path:folder_name>", methods=["GET"])
def download_folder(folder_name: str):
    """
    Zip and download ANY folder inside the output directory (used for manual data recovery).
    Example: /api/download/folder/dataset_20260324_230545
    """
    safe_path = (OUTPUT_DIR / folder_name).resolve()
    # Security: ensure it is inside OUTPUT_DIR
    if not str(safe_path).startswith(str(OUTPUT_DIR.resolve())):
        return abort(403)
    
    if not safe_path.exists() or not safe_path.is_dir():
        return abort(404)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(safe_path.rglob("*")):
            if f.is_file():
                zf.write(str(f), str(f.relative_to(safe_path)))

    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True,
                   download_name=f"{folder_name}.zip")


# ---------------------------------------------------------------------------
# Pipeline worker
# ---------------------------------------------------------------------------

def _run_pipeline(job_id: str, video_path: str, frame_interval: int, conf: float):
    try:
        ts = generate_timestamp()
        logger.info("Job %s started | video=%s | frame_interval=%d | conf=%.2f",
                    job_id, video_path, frame_interval, conf)

        # Step 1 – Extract
        _set_job(job_id, "running", "Extracting frames...", progress={"step": "extracting", "percent": 0})
        frames_dir = get_frames_path(ts)
        info = extract_frames(video_path, str(frames_dir), frame_interval=frame_interval)
        saved_count, source_fps = info["saved_count"], info["source_fps"]
        logger.info("Job %s Step 1 done | extracted=%d source_fps=%.2f dir=%s",
                    job_id, saved_count, source_fps, frames_dir)
        if saved_count == 0:
            raise RuntimeError("No frames could be extracted from the uploaded video.")

        # Step 2 – Annotate + Dataset Export
        _set_job(job_id, "running", "Analyzing frames (YOLOv8 inference)...",
                 progress={"step": "annotating", "current": 0, "total": saved_count, "percent": 0})

        annotated_dir = get_annotated_path(ts)
        dataset_dir   = get_job_dataset_path(job_id)

        def on_progress(current, total):
            pct = int(current / total * 100) if total else 0
            _set_job(job_id, "running", f"Annotating frame {current}/{total}",
                     progress={"step": "annotating", "current": current, "total": total, "percent": pct})

        pipeline_summary: dict = {}
        annotate_frames(str(frames_dir), str(annotated_dir), conf=conf,
                        progress_callback=on_progress, dataset_dir=str(dataset_dir),
                        summary_out=pipeline_summary)
        logger.info("Job %s Step 2 done | summary=%s", job_id, pipeline_summary)

        # Step 3 – Rebuild Video (H.264 browser-playable MP4)
        _set_job(job_id, "running", "Building web-optimized H.264 video...",
                 progress={"step": "converting", "percent": 95})
        output_path = get_output_video_path(job_id, ts)
        target_fps  = source_fps / (frame_interval if frame_interval > 0 else 1)
        out_video_path = Path(images_to_video(str(annotated_dir), str(output_path), fps=target_fps))
        logger.info("Job %s Step 3 done | video=%s (%d bytes) @ %.2f FPS",
                    job_id, out_video_path.name, out_video_path.stat().st_size, target_fps)

        # Snapshot: representative annotated frame
        snapshot_name = None
        first_annotated = sorted(
            p for p in annotated_dir.iterdir()
            if p.is_file() and p.suffix.lower() in ALLOWED_IMAGE_EXT
        )
        if first_annotated:
            snapshot_name = f"snapshot_{ts}.jpg"
            snapshot_dst  = get_job_output_path(job_id) / snapshot_name
            shutil.copy2(str(first_annotated[0]), str(snapshot_dst))

        result = {
            "output_video_url": f"/api/media/output/{job_id}/{out_video_path.name}",
            "snapshot_url":     f"/api/media/output/{job_id}/{snapshot_name}" if snapshot_name else None,
            "labels_url":       f"/api/download/dataset/{job_id}",
            "dataset_dir":      str(dataset_dir),
            "timestamp":        ts,
            "total_frames":     saved_count,
            "summary":          pipeline_summary,
        }
        _set_job(job_id, "done", "Done! Result ready.", result,
                 progress={"step": "done", "percent": 100, "current": saved_count, "total": saved_count})
        logger.info("Job %s completed | output_video_url=%s | snapshot_url=%s",
                    job_id, result["output_video_url"], result["snapshot_url"])

    except Exception as exc:
        logger.exception("Job %s failed in pipeline", job_id)
        _set_job(job_id, "error", str(exc))

# ---------------------------------------------------------------------------
# Frontend static file serving
# ---------------------------------------------------------------------------
_PROJECT_ROOT = _BACKEND_DIR.parent

@app.route("/", methods=["GET"])
@app.route("/index.html", methods=["GET"])
def serve_index():
    index_file = _PROJECT_ROOT / "index.html"
    if index_file.exists():
        return send_file(str(index_file))
    return jsonify({"status": "CottonVision API Active", "version": "1.0.0"})

@app.route("/frontend/<path:filepath>", methods=["GET"])
def serve_frontend_static(filepath: str):
    file_path = (_PROJECT_ROOT / "frontend" / filepath).resolve()
    if file_path.exists() and file_path.is_file():
        return send_file(str(file_path))
    abort(404)

def _send_project_file(*rel_parts: str, mimetype: str | None = None):
    file_path = _PROJECT_ROOT.joinpath(*rel_parts).resolve()
    if not str(file_path).startswith(str(_PROJECT_ROOT.resolve())):
        abort(403)
    if file_path.exists() and file_path.is_file():
        return send_file(str(file_path), mimetype=mimetype)
    abort(404)


@app.route("/presets/<path:filepath>", methods=["GET"])
@app.route("/samples/<path:filepath>", methods=["GET"])
def serve_presets_static(filepath: str):
    return _send_project_file("media", "workbench_presets", filepath)


@app.route("/favicon.svg", methods=["GET"])
def serve_favicon_svg():
    return _send_project_file("frontend", "public", "favicon.svg", mimetype="image/svg+xml")


@app.route("/favicon.ico", methods=["GET"])
def serve_favicon_ico():
    return _send_project_file("frontend", "public", "favicon.ico", mimetype="image/x-icon")


@app.route("/Final_Report.pdf", methods=["GET"])
def serve_final_report():
    return _send_project_file("Final_Report.pdf", mimetype="application/pdf")

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting CottonVision Flask server on http://0.0.0.0:5000 (logs: %s)", get_log_file_path())
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
