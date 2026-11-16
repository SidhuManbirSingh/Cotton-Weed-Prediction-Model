"""Run offline YOLOv8 batch inference over a directory of drone images."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.scripts.annotation import _DEFAULT_MODEL, annotate_frames  # noqa: E402


def main() -> None:
    """Parse CLI arguments and annotate all images in the target folder."""
    parser = argparse.ArgumentParser(description="Batch YOLOv8 cotton/weed inference.")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=PROJECT_ROOT / "media" / "put_images_here",
        help="Input directory of images (default: media/put_images_here).",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "output" / "batch",
        help="Output directory for annotated images.",
    )
    parser.add_argument("--model", "-m", default=_DEFAULT_MODEL, help="Path to YOLO model weights.")
    parser.add_argument("--conf", "-c", type=float, default=0.25, help="Confidence threshold.")
    parser.add_argument("--dataset", "-d", type=Path, default=None, help="Optional YOLO label export directory.")
    args = parser.parse_args()

    summary: dict = {}
    count = annotate_frames(
        input_dir=str(args.input),
        output_dir=str(args.output),
        model_path=args.model,
        conf=args.conf,
        dataset_dir=str(args.dataset) if args.dataset else None,
        summary_out=summary,
    )
    print(f"[batch_inference] Annotated {count} image(s) -> {args.output}")
    if summary:
        print(f"[batch_inference] Summary: {summary}")


if __name__ == "__main__":
    main()
