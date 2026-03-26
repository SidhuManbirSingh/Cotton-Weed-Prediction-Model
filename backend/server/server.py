"""
server.py
---------
Flask REST API for AI Media Processing (Cotton Weed Detection).
Supports OpenVINO GPU acceleration and H.264 web-optimized video.
I don't have NVIDIA GPUs, so this is designed to run on CPU/GPU-agnostic OpenVINO for broad compatibility.
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
from backend.scripts.video2image import extract_frames
from backend.scripts.annotation  import annotate_frames, annotate_single_image
from backend.scripts.convert      import images_to_video

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
    # We generate a timestamp to create unique output filenames for the annotated image and label file.
    ts   = generate_timestamp()

    try: 
        out_name = f"inference_{ts}_{upload_path.name}" # Output filename includes timestamp and original name for traceability
        out_path = OUTPUT_DIR / out_name 
        res = annotate_single_image(str(upload_path), str(out_path), conf=conf)
        # res is expected to contain keys like "label_path" for the generated label file path
        # res is the reason behind of the txt file that is generated with the same name as the image but with .txt extension, which contains the labels in YOLO format.
        
        return jsonify({
            "annotated_url": f"/api/media/output/{out_name}",
            "label_url":     f"/api/media/output/{Path(res['label_path']).name}",
            "timestamp":     ts,
        })
    except Exception as exc:
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

    t = threading.Thread(
        target=_run_pipeline, # _run_pipeline is expected to return the result of the video processing pipeline and update the job status accordingly. It takes the job_id, path to the uploaded video, frame interval, and confidence threshold as arguments.
        args=(job_id, str(upload_path), frame_interval, conf), # Arguments passed to the target functions
        daemon=True, # Background thread
    )
    t.start()
 
    return jsonify({"job_id": job_id, "status": "queued"})


@app.route("/api/status/<job_id>", methods=["GET"])
def status(job_id: str): # Just returns the current status of a job based on its ID, including progress and any results if available.  
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None: return jsonify({"error": "Unknown job"}), 404
    return jsonify({"job_id": job_id, **job}) # returns the job id and  whole job dict which has status, message, result, and progress keys in JSON format


# For the image and videos access or viewing, we have a media endpoint that serves files from the data directory.
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

# Fow downlaoding the paired YOLO dataset for a specific job, we have an endpoint that dynamically zips the dataset directory and serves it as a downloadable file.
@app.route("/api/download/dataset/<job_id>", methods=["GET"])
def download_dataset(job_id: str):
    """Dynamically zip and download the paired YOLO dataset for a job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
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

        # Overall Pipeline Steps:
        # 1. Extract frames from the uploaded video at the specified interval.
        # 2. Annotate the extracted frames using the specified confidence threshold, and export the paired YOLO dataset (images + labels).
        # 3. Rebuild the annotated frames into a web-optimized video using H.264 encoding via ffmpeg.
        # 4. Generate a snapshot image from the first annotated frame for quick preview.
        # 5. Update the job

        # Step 1 – Extract
        _set_job(job_id, "running", "Extracting frames…", progress={"step": "extracting", "percent": 0})
        frames_dir = get_frames_path(ts)
        info = extract_frames(video_path, str(frames_dir), frame_interval=frame_interval)
        saved_count, source_fps = info["saved_count"], info["source_fps"]

        # getting the frames inside of the frame directory and counting them


        # Step 2 – Annotate + Dataset Export
        _set_job(job_id, "running", "Analyzing frames (GPU acceleration enabled)…",
                 progress={"step": "annotating", "current": 0, "total": saved_count, "percent": 0})
        
        annotated_dir = get_annotated_path(ts)
        dataset_dir   = get_job_dataset_path(job_id)

        # annotate_frames is expected to process all the extracted frames, save the annotated images to the annotated_dir, and export the corresponding YOLO label files to the dataset_dir. 

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
