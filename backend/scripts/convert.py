"""
convert.py
----------
Assembles annotated frame images into an MP4 video.

Two-pass encoding:
  1. OpenCV writes raw mp4v frames to a temporary file
  2. ffmpeg re-encodes to H.264 (libx264) with -movflags +faststart

Usage (CLI):
    python convert.py --input <annotated_dir> --output <output.mp4> [--fps 30] [--speed 1.0]

Usage (import):
    from backend.scripts.convert import images_to_video
    images_to_video(input_dir="...", output_path="...", fps=30, speed_factor=1.0)
"""

import cv2
import os
import subprocess
import argparse
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def images_to_video(
    input_dir: str,
    output_path: str,
    fps: float = 30.0,
    speed_factor: float = 1.0,
) -> str:
    """
    Combine all images in *input_dir* into a single MP4 video at *output_path*.

    Two-pass process:
      Pass 1 — OpenCV writes raw mp4v to a temporary file
      Pass 2 — ffmpeg re-encodes to H.264 with -movflags +faststart

    Parameters
    ----------
    input_dir    : Directory containing annotated frame images (sorted alphabetically).
    output_path  : Destination .mp4 file path.
    fps          : Frames-per-second for the output video.
    speed_factor : Playback speed multiplier (e.g. 0.25 = quarter speed, which repeats
                   each frame 4× to achieve a slow-motion effect).

    Returns
    -------
    Absolute path of the created video file.
    """
    input_dir   = Path(input_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    images = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not images:
        raise FileNotFoundError(f"No images found in: {input_dir}")

    # Calculate repeat count for slow-motion (speed_factor < 1 repeats frames)
    repeat = max(1, int(round(1.0 / speed_factor)))

    first_frame = cv2.imread(str(images[0]))
    if first_frame is None:
        raise RuntimeError(f"Failed to read first image: {images[0]}")
    height, width = first_frame.shape[:2]

    # --- Pass 1: OpenCV raw mp4v ---
    raw_path = output_path.with_name(f"raw_{output_path.name}")
    codec = "mp4v"
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(str(raw_path), fourcc, fps, (width, height))

    print(f"[convert] Pass 1 — OpenCV raw write")
    print(f"[convert] Input   : {input_dir}  ({len(images)} images)")
    print(f"[convert] Raw out : {raw_path}")
    print(f"[convert] FPS={fps}  speed_factor={speed_factor}  repeat={repeat}x")

    written = 0
    for img_path in images:
        frame = cv2.imread(str(img_path))
        if frame is None:
            print(f"[convert] WARNING: skipping unreadable image: {img_path.name}")
            continue
        for _ in range(repeat):
            writer.write(frame)
        written += 1

    writer.release()
    print(f"[convert] Pass 1 done — wrote {written} frames → '{raw_path}'")

    # --- Pass 2: ffmpeg H.264 re-encode ---
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_path),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]

    print(f"[convert] Pass 2 — ffmpeg H.264 re-encode")
    print(f"[convert] Command : {' '.join(ffmpeg_cmd)}")

    try:
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout
        )
        if result.returncode != 0:
            print(f"[convert] ffmpeg stderr: {result.stderr[-500:]}")
            raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")

        # Remove raw intermediate file
        raw_path.unlink(missing_ok=True)
        print(f"[convert] Pass 2 done — H.264 video → '{output_path}'")

    except FileNotFoundError:
        # ffmpeg not installed — fall back to raw mp4v
        print("[convert] WARNING: ffmpeg not found! Using raw mp4v output (may not play in browser)")
        raw_path.rename(output_path)

    return str(output_path.resolve())


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a directory of images into an MP4 video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input",  "-i", required=True,          help="Directory of input images")
    parser.add_argument("--output", "-o", required=True,          help="Output .mp4 file path")
    parser.add_argument("--fps",         type=float, default=30.0, help="Frames per second")
    parser.add_argument("--speed",       type=float, default=1.0,  help="Playback speed factor (e.g. 0.25 for slow-mo)")

    args = parser.parse_args()
    images_to_video(
        input_dir=args.input,
        output_path=args.output,
        fps=args.fps,
        speed_factor=args.speed,
    )
