"""Extract JPEG frames from a drone video stored in media/put_mp4_videos_here/."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.scripts.video2image import extract_frames  # noqa: E402

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


def _find_default_video(video_dir: Path) -> Path:
    """Locate the first video inside *video_dir* when --video is omitted."""
    if not video_dir.exists():
        raise FileNotFoundError(f"Video directory not found: {video_dir}")
    candidates = sorted(
        p for p in video_dir.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not candidates:
        raise FileNotFoundError(
            f"No video files found in {video_dir}. Place an .mp4 file there or pass --video."
        )
    return candidates[0]


def main() -> None:
    """Parse arguments and invoke the backend video frame extractor."""
    parser = argparse.ArgumentParser(description="Extract frames from a UAV video file.")
    parser.add_argument(
        "--video", "-v",
        type=Path,
        default=None,
        help="Path to input video (default: first video in media/put_mp4_videos_here).",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "frames" / "cli_extract",
        help="Output folder for extracted JPEG frames.",
    )
    parser.add_argument("--interval", "-n", type=int, default=1, help="Extract every Nth frame.")
    parser.add_argument("--skip-duplicates", action="store_true", help="Skip identical adjacent frames.")
    args = parser.parse_args()

    video_path = args.video or _find_default_video(PROJECT_ROOT / "media" / "put_mp4_videos_here")
    stats = extract_frames(
        video_path=str(video_path),
        output_folder=str(args.output),
        frame_interval=args.interval,
        skip_duplicates=args.skip_duplicates,
    )
    print(f"[video_to_frames] Done: {stats}")


if __name__ == "__main__":
    main()
