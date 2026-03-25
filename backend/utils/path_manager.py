import os
from pathlib import Path

# Base data directory (relative to this file's grandparent — the backend folder)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = _BACKEND_DIR / "data"

UPLOADS_DIR   = DATA_DIR / "uploads"
FRAMES_DIR    = DATA_DIR / "frames"
ANNOTATED_DIR = DATA_DIR / "annotated"
OUTPUT_DIR    = DATA_DIR / "output"


def ensure_dirs():
    """Create all base data directories if they don't exist."""
    for d in [UPLOADS_DIR, FRAMES_DIR, ANNOTATED_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def get_frames_path(timestamp: str) -> Path:
    path = FRAMES_DIR / f"frames_{timestamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_annotated_path(timestamp: str) -> Path:
    path = ANNOTATED_DIR / f"annotated_{timestamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_job_output_path(job_id: str) -> Path:
    """Return a base directory for a specific job's results."""
    path = OUTPUT_DIR / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_output_video_path(job_id: str, timestamp: str) -> Path:
    job_dir = get_job_output_path(job_id)
    return job_dir / f"output_{timestamp}.mp4"


def get_job_dataset_path(job_id: str) -> Path:
    """Return a directory for the paired YOLO dataset (images + labels) within a job's folder."""
    job_dir = get_job_output_path(job_id)
    path = job_dir / "dataset"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_upload_path(filename: str) -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR / filename
