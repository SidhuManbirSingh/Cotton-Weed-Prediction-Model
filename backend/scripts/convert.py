"""
convert.py
----------
Assembles frame images into a browser-compatible MP4 video.

Two-pass encoding:
  1. OpenCV writes frames using H.264 (avc1/H264) when supported, falling back to mp4v.
  2. If ffmpeg is available (system PATH or imageio-ffmpeg), re-encodes with libx264
     + -movflags +faststart for instant web seeking; otherwise keeps Pass 1 output when
     already H.264 or logs a fallback warning for mp4v.

Usage (CLI):
    python convert.py --input <images_dir> --output <output.mp4_or_dir> [--fps 30] [--speed 1.0]

Usage (import):
    from backend.scripts.convert import images_to_video
    images_to_video(input_dir="...", output_path="...", fps=30, speed_factor=1.0)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.utils.logger import get_logger  # noqa: E402

logger = get_logger("convert")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
_H264_CODECS = {"avc1", "h264"}


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


def _read_video_fourcc(video_path: Path) -> str:
    """Inspect written video FourCC string using OpenCV."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            return "unreadable"
        fc = int(cap.get(cv2.CAP_PROP_FOURCC))
        return "".join(chr((fc >> (8 * i)) & 0xFF) for i in range(4)).strip() or "unknown"
    finally:
        cap.release()


def _write_with_codecs(
    images: list[Path],
    raw_path: Path,
    fps: float,
    width: int,
    height: int,
    repeat: int,
) -> tuple[str, int]:
    """Try H.264 OpenCV codecs first, then mp4v fallback; return (codec_used, written_count)."""
    last_err = "no supported OpenCV video codec opened"
    for codec in ("avc1", "H264", "mp4v"):
        raw_path.unlink(missing_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(str(raw_path), fourcc, fps, (width, height))
        if not writer.isOpened():
            writer.release()
            last_err = f"VideoWriter failed to open codec '{codec}'"
            continue

        written = 0
        try:
            for img_path in images:
                frame = cv2.imread(str(img_path))
                if frame is None:
                    logger.warning("Skipping unreadable image: %s", img_path.name)
                    continue
                fitted = _fit_frame_to_canvas(frame, width, height)
                for _ in range(repeat):
                    writer.write(fitted)
                written += 1
        finally:
            writer.release()

        if written > 0 and raw_path.exists() and raw_path.stat().st_size > 0:
            return codec, written

        last_err = f"Codec '{codec}' produced empty output"

    raise RuntimeError(f"Failed to encode video to {raw_path}: {last_err}")


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
    # Even dimensions are required by yuv420p H.264 encoders.
    width = raw_w + (raw_w % 2)
    height = raw_h + (raw_h % 2)
    repeat = max(1, int(round(1.0 / speed_factor)))

    raw_path = out_file.with_name(f"raw_{out_file.name}")
    logger.info(
        "Pass 1 encoding started: input=%s (%d images) -> output=%s (%dx%d @ %.2f FPS, repeat=%dx)",
        in_dir, len(images), out_file, width, height, fps, repeat,
    )

    codec_used, written = _write_with_codecs(images, raw_path, fps, width, height, repeat)
    actual_fourcc = _read_video_fourcc(raw_path)
    logger.info(
        "Pass 1 complete: wrote %d frames with codec=%s (fourcc=%s, size=%d bytes)",
        written, codec_used, actual_fourcc, raw_path.stat().st_size,
    )

    ffmpeg_bin = _find_ffmpeg()
    if not ffmpeg_bin:
        if codec_used.lower() in _H264_CODECS or actual_fourcc.lower() in _H264_CODECS:
            logger.info("ffmpeg not installed; keeping browser-playable OpenCV H.264 (%s) output", actual_fourcc)
        else:
            logger.warning("ffmpeg not installed and OpenCV fell back to %s (may not play inline in browser)", actual_fourcc)
        raw_path.replace(out_file)
        logger.info("Final video written: %s (%d bytes)", out_file, out_file.stat().st_size)
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
    logger.info("Pass 2 ffmpeg H.264 +faststart re-encode: %s", " ".join(ffmpeg_cmd))

    result = subprocess.run(
        ffmpeg_cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        logger.warning(
            "ffmpeg exited %d (%s); falling back to Pass 1 output (fourcc=%s)",
            result.returncode,
            (result.stderr or "").strip()[-300:],
            actual_fourcc,
        )
        raw_path.replace(out_file)
        return str(out_file.resolve())

    raw_path.unlink(missing_ok=True)
    logger.info("Pass 2 complete: H.264 video -> %s (%d bytes)", out_file, out_file.stat().st_size)
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
