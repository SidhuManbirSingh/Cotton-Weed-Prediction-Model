"""
convert.py
----------
Assembles frame images into an MP4 video.

Two-pass encoding:
  1. OpenCV writes raw mp4v frames to a temporary .mp4 file
  2. ffmpeg re-encodes to H.264 (libx264) with -movflags +faststart when available,
     or falls back cleanly to the OpenCV mp4v file.

Usage (CLI):
    python convert.py --input <images_dir> --output <output.mp4_or_dir> [--fps 30] [--speed 1.0]

Usage (import):
    from backend.scripts.convert import images_to_video
    images_to_video(input_dir="...", output_path="...", fps=30, speed_factor=1.0)
"""

import argparse
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def _resolve_output_path(output_path: str | Path, input_dir: Path) -> Path:
    """Resolve CLI/API output target to a concrete .mp4 file path."""
    path = Path(output_path)
    if path.exists() and path.is_dir():
        name = path.name or input_dir.name or "output"
        path = path / f"{name}.mp4"
    elif not path.suffix:
        path = path.with_suffix(".mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _fit_frame_to_canvas(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    """Scale and letterbox *frame* onto a fixed (width, height) canvas."""
    fh, fw = frame.shape[:2]
    if fw == width and fh == height:
        return frame

    scale = min(width / fw, height / fh)
    new_w = max(1, int(round(fw * scale)))
    new_h = max(1, int(round(fh * scale)))
    resized = frame if (new_w == fw and new_h == fh) else cv2.resize(
        frame, (new_w, new_h), interpolation=cv2.INTER_AREA
    )

    canvas = np.zeros((height, width, 3), dtype=frame.dtype)
    y_off = (height - new_h) // 2
    x_off = (width - new_w) // 2
    canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized
    return canvas


def _find_ffmpeg() -> str | None:
    """Return path to ffmpeg executable from system PATH or imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def images_to_video(
    input_dir: str,
    output_path: str,
    fps: float = 30.0,
    speed_factor: float = 1.0,
) -> str:
    """
    Combine all images in *input_dir* into a single MP4 video at *output_path*.

    Parameters
    ----------
    input_dir    : Directory containing input frame images (sorted alphabetically).
    output_path  : Destination .mp4 file path or target directory.
    fps          : Frames-per-second for the output video.
    speed_factor : Playback speed multiplier (e.g. 0.25 = quarter speed, repeating
                   each frame 4x for slow-motion playback).

    Returns
    -------
    Absolute path of the created video file.
    """
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    if speed_factor <= 0:
        raise ValueError(f"speed_factor must be positive, got {speed_factor}")

    in_dir = Path(input_dir)
    if not in_dir.exists() or not in_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {in_dir}")

    out_file = _resolve_output_path(output_path, in_dir)

    images = sorted(
        f for f in in_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        raise FileNotFoundError(f"No images found in: {in_dir}")

    first_frame = cv2.imread(str(images[0]))
    if first_frame is None:
        raise RuntimeError(f"Failed to read first image: {images[0]}")

    raw_h, raw_w = first_frame.shape[:2]
    # Ensure even dimensions for H.264 / yuv420p and broad MP4 player compatibility.
    width = raw_w + (raw_w % 2)
    height = raw_h + (raw_h % 2)
    repeat = max(1, int(round(1.0 / speed_factor)))

    # --- Pass 1: OpenCV raw mp4v ---
    raw_path = out_file.with_name(f"raw_{out_file.name}")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(raw_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        writer.release()
        raise RuntimeError(f"Failed to initialize OpenCV VideoWriter for: {raw_path}")

    print("[convert] Pass 1 - OpenCV raw write")
    print(f"[convert] Input   : {in_dir}  ({len(images)} images)")
    print(f"[convert] Output  : {out_file}  ({width}x{height})")
    print(f"[convert] FPS={fps}  speed_factor={speed_factor}  repeat={repeat}x")

    written = 0
    try:
        for img_path in images:
            frame = cv2.imread(str(img_path))
            if frame is None:
                print(f"[convert] WARNING: skipping unreadable image: {img_path.name}")
                continue
            fitted = _fit_frame_to_canvas(frame, width, height)
            for _ in range(repeat):
                writer.write(fitted)
            written += 1
    finally:
        writer.release()

    if written == 0 or not raw_path.exists():
        raise RuntimeError(f"No frames were written to intermediate video: {raw_path}")

    print(f"[convert] Pass 1 done - wrote {written} frames -> '{raw_path}'")

    # --- Pass 2: ffmpeg H.264 re-encode ---
    ffmpeg_bin = _find_ffmpeg()
    if not ffmpeg_bin:
        print("[convert] WARNING: ffmpeg not found; using OpenCV mp4v output")
        raw_path.replace(out_file)
        print(f"[convert] Done -> '{out_file}'")
        return str(out_file.resolve())

    ffmpeg_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(raw_path),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_file),
    ]
    print("[convert] Pass 2 - ffmpeg H.264 re-encode")
    print(f"[convert] Command : {' '.join(ffmpeg_cmd)}")

    result = subprocess.run(
        ffmpeg_cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        print(f"[convert] WARNING: ffmpeg failed (exit {result.returncode}); keeping mp4v output")
        if result.stderr:
            print(f"[convert] ffmpeg stderr: {result.stderr[-400:]}")
        raw_path.replace(out_file)
        return str(out_file.resolve())

    raw_path.unlink(missing_ok=True)
    print(f"[convert] Pass 2 done - H.264 video -> '{out_file}'")
    return str(out_file.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a directory of images into an MP4 video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", "-i", required=True, help="Directory of input images")
    parser.add_argument("--output", "-o", required=True, help="Output .mp4 file path or directory")
    parser.add_argument("--fps", type=float, default=30.0, help="Frames per second")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed factor (e.g. 0.25 for slow-mo)")

    args = parser.parse_args()
    images_to_video(
        input_dir=args.input,
        output_path=args.output,
        fps=args.fps,
        speed_factor=args.speed,
    )
