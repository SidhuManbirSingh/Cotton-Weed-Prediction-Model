"""
server.py
---------
Flask REST API for AI Media Processing (Cotton Weed Detection).
Supports OpenVINO GPU acceleration and H.264 web-optimized video.
"""

import io
import os
import shutil
import threading
import uuid
import zipfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Resolve backend root (parent of this file's directory)
_SERVER_DIR  = Path(__file__).resolve().parent
_BACKEND_DIR = _SERVER_DIR.parent

import sys
sys.path.insert(0, str(_BACKEND_DIR.parent))  # project root on path

from backend.utils.path_manager import (
    ensure_dirs, get_upload_path, get_frames_path,
    get_annotated_path, get_output_video_path, get_job_dataset_path,
    get_job_output_path, UPLOADS_DIR, OUTPUT_DIR, ANNOTATED_DIR, DATA_DIR
)
from backend.utils.file_naming import generate_timestamp
from backend.scripts.video2image import extract_frames
from backend.scripts.annotation  import annotate_frames, annotate_single_image
from backend.scripts.convert      import images_to_video

# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)
ensure_dirs()

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv"}
ALLOWED_EXT       = ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT

_jobs: dict = {}
_jobs_lock = threading.Lock()


def _set_job(job_id: str, status: str, message: str = "", result: dict = None, progress: dict = None):
    with _jobs_lock:
        _jobs[job_id] = {
            "status":   status,
            "message":  message,
            "result":   result or {},
            "progress": progress or {},
        }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/upload", methods=["POST"])
def upload():
    """Accept a file upload."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Unsupported: {ext}"}), 400

    filename  = secure_filename(file.filename)
    save_path = get_upload_path(filename)
    file.save(str(save_path))

    file_type = "video" if ext in ALLOWED_VIDEO_EXT else "image"
    return jsonify({
        "filename": filename,
        "type":     file_type,
        "url":      f"/api/media/uploads/{filename}",
    })


@app.route("/api/process-image", methods=["POST"])
def process_image():
    """Single-image inference with label export."""
    data     = request.get_json(force=True) or {}
    filename = data.get("filename", "")
    if not filename: return jsonify({"error": "filename required"}), 400

    upload_path = get_upload_path(filename)
    if not upload_path.exists(): return jsonify({"error": "Not found"}), 404

    conf = float(data.get("conf", 0.25))
    ts   = generate_timestamp()

    try:
        out_name = f"inference_{ts}_{upload_path.name}"
        out_path = OUTPUT_DIR / out_name
        res = annotate_single_image(str(upload_path), str(out_path), conf=conf)

        return jsonify({
            "annotated_url": f"/api/media/output/{out_name}",
            "label_url":     f"/api/media/output/{Path(res['label_path']).name}",
            "timestamp":     ts,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/process", methods=["POST"])
def process():
    """Trigger the full video pipeline."""
    data     = request.get_json(force=True) or {}
    filename = data.get("filename", "")
    if not filename: return jsonify({"error": "filename required"}), 400

    upload_path = get_upload_path(filename)
    if not upload_path.exists(): return jsonify({"error": "Not found"}), 404

    frame_interval = int(data.get("frame_interval", 5))
    conf           = float(data.get("conf", 0.25))
    job_id         = str(uuid.uuid4())
    _set_job(job_id, "queued", "Job queued")

    t = threading.Thread(
        target=_run_pipeline,
        args=(job_id, str(upload_path), frame_interval, conf),
        daemon=True,
    )
    t.start()
    return jsonify({"job_id": job_id, "status": "queued"})


@app.route("/api/status/<job_id>", methods=["GET"])
def status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None: return jsonify({"error": "Unknown job"}), 404
    return jsonify({"job_id": job_id, **job})


@app.route("/api/media/<path:filepath>", methods=["GET"])
def media(filepath: str):
    """Serve media files (images, videos) from data directory."""
    full_path = _BACKEND_DIR / "data" / filepath
    if not full_path.exists():
        abort(404)

    ext = full_path.suffix.lower()
    if ext in ('.mp4', '.avi', '.mov', '.mkv'):
        return send_file(str(full_path), mimetype='video/mp4')
    return send_file(str(full_path))


@app.route("/api/download/dataset/<job_id>", methods=["GET"])
def download_dataset(job_id: str):
    """Dynamically zip and download the paired YOLO dataset for a job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None or job["status"] != "done": return abort(404)

    dataset_dir = job.get("result", {}).get("dataset_dir")
    if not dataset_dir: return abort(404)

    dataset_path = Path(dataset_dir)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(dataset_path.iterdir()):
            if f.is_file(): zf.write(str(f), f.name)

    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True,
                   download_name=f"yolo_dataset_{job_id[:8]}.zip")


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

        # Step 1 – Extract
        _set_job(job_id, "running", "Extracting frames…", progress={"step": "extracting", "percent": 0})
        frames_dir = get_frames_path(ts)
        info = extract_frames(video_path, str(frames_dir), frame_interval=frame_interval)
        saved_count, source_fps = info["saved_count"], info["source_fps"]

        # Step 2 – Annotate + Dataset Export
        _set_job(job_id, "running", "Analyzing frames (GPU acceleration enabled)…",
                 progress={"step": "annotating", "current": 0, "total": saved_count, "percent": 0})
        
        annotated_dir = get_annotated_path(ts)
        dataset_dir   = get_job_dataset_path(job_id)

        def on_progress(current, total):
            pct = int(current / total * 100) if total else 0
            _set_job(job_id, "running", f"Annotating frame {current}/{total}",
                     progress={"step": "annotating", "current": current, "total": total, "percent": pct})

        annotate_frames(str(frames_dir), str(annotated_dir), conf=conf,
                        progress_callback=on_progress, dataset_dir=str(dataset_dir))

        # Step 3 – Rebuild Video (H.264 via ffmpeg)
        _set_job(job_id, "running", "Building web-optimized video…", progress={"step": "converting", "percent": 95})
        output_path = get_output_video_path(job_id, ts)
        target_fps  = source_fps / (frame_interval if frame_interval > 0 else 1)
        images_to_video(str(annotated_dir), str(output_path), fps=target_fps)

        # Snapshot: representative frame
        snapshot_name = None
        first_annotated = sorted(annotated_dir.iterdir())
        if first_annotated:
            snapshot_name = f"snapshot_{ts}.jpg"
            snapshot_dst  = get_job_output_path(job_id) / snapshot_name
            shutil.copy2(str(first_annotated[0]), str(snapshot_dst))

        # Handshake Result (Task 1: labels_url)
        # We serve job-id subfolders via /api/media/output/<job_id>/<file>
        result = {
            "output_video_url": f"/api/media/output/{job_id}/{output_path.name}",
            "snapshot_url":     f"/api/media/output/{job_id}/{snapshot_name}" if snapshot_name else None,
            "labels_url":       f"/api/download/dataset/{job_id}",
            "dataset_dir":      str(dataset_dir),
            "timestamp":        ts,
            "total_frames":     saved_count,
        }
        _set_job(job_id, "done", "Done! Result ready for download.", result,
                 progress={"step": "done", "percent": 100, "current": saved_count, "total": saved_count})

    except Exception as exc:
        _set_job(job_id, "error", str(exc))
        raise

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
