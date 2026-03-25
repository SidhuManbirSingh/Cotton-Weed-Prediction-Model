"""
video2image.py
--------------
Extracts frames from a video file and saves them as JPEG images.

Usage (CLI):
    python video2image.py --video <path> --output <dir> [--interval N] [--skip-duplicates]

Usage (import):
    from backend.scripts.video2image import extract_frames
    saved = extract_frames(video_path="...", output_folder="...", frame_interval=1)
"""

import cv2
import os
import argparse
import hashlib
from pathlib import Path


def _frame_hash(frame) -> str:
    """Return the MD5 hash of a JPEG-encoded frame (used for duplicate detection)."""
    _, buf = cv2.imencode(".jpg", frame)
    return hashlib.md5(buf.tobytes()).hexdigest()


def extract_frames(
    video_path: str,
    output_folder: str,
    frame_interval: int = 1,
    skip_duplicates: bool = False,
) -> dict:
    """
    Extract frames from *video_path* and write them to *output_folder*.

    Parameters
    ----------
    video_path      : Path to the source video file.
    output_folder   : Directory where extracted frames will be saved.
    frame_interval  : Save every Nth frame (1 = every frame, 30 = 1 per second @30fps).
    skip_duplicates : When True, frames identical to the previous saved frame are skipped.

    Returns
    -------
    dict with keys: saved_count, source_fps, total_frames
    """
    video_path = str(video_path)
    output_folder = str(output_folder)

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: '{video_path}'")

    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: '{video_path}'")

    source_fps   = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[video2image] Source  : {video_path}")
    print(f"[video2image] Output  : {output_folder}")
    print(f"[video2image] FPS     : {source_fps:.2f}  |  Total frames: {total_frames}")
    print(f"[video2image] Interval: every {frame_interval} frame(s)")

    frame_count = 0
    saved_count = 0
    prev_hash   = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            if skip_duplicates:
                curr_hash = _frame_hash(frame)
                if prev_hash is not None and curr_hash == prev_hash:
                    frame_count += 1
                    continue
                prev_hash = curr_hash

            out_path = os.path.join(output_folder, f"frame_{frame_count:06d}.jpg")
            cv2.imwrite(out_path, frame)
            saved_count += 1

            if saved_count % 100 == 0:
                print(f"[video2image] Saved {saved_count} frames so far…")

        frame_count += 1

    cap.release()
    print(f"[video2image] Done — extracted {saved_count} frame(s) to '{output_folder}'")
    return {
        "saved_count":  saved_count,
        "source_fps":   source_fps,
        "total_frames": total_frames,
    }


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract frames from a video file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--video",  "-v", required=True,       help="Path to input video")
    parser.add_argument("--output", "-o", required=True,       help="Output folder for extracted frames")
    parser.add_argument("--interval", "-i", type=int, default=1, help="Extract every N-th frame")
    parser.add_argument("--skip-duplicates", action="store_true", help="Skip duplicate frames")

    args = parser.parse_args()
    extract_frames(
        video_path=args.video,
        output_folder=args.output,
        frame_interval=args.interval,
        skip_duplicates=args.skip_duplicates,
    )
