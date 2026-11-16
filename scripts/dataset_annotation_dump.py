"""Inspect raw YOLO annotation files for sample images in a dataset split."""

import argparse
from pathlib import Path

from _dataset_io import DEFAULT_IMAGES_DIR, DEFAULT_LABELS_DIR, list_images, resolve_label_path


def dump_annotations(images_dir: Path, labels_dir: Path | None, limit: int) -> None:
    """Print raw YOLO label lines for up to *limit* images."""
    images = list_images(images_dir)[:limit]
    if not images:
        print(f"No images found in {images_dir}.")
        return
    for img_path in images:
        txt_path = resolve_label_path(img_path, labels_dir)
        print(f"\n===== {img_path.name} ({txt_path.name}) =====")
        if not txt_path.exists():
            print("[LABEL FILE NOT FOUND]")
            continue
        content = txt_path.read_text(encoding="utf-8", errors="ignore").strip()
        print(content if content else "[EMPTY FILE]")


def main() -> None:
    """Parse arguments and print sample YOLO annotations."""
    parser = argparse.ArgumentParser(description="Inspect sample YOLO ground-truth annotations.")
    parser.add_argument("--images", "-i", type=Path, default=DEFAULT_IMAGES_DIR, help="Images directory.")
    parser.add_argument("--labels", "-l", type=Path, default=DEFAULT_LABELS_DIR, help="Labels directory.")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Number of sample images to inspect.")
    args = parser.parse_args()
    dump_annotations(args.images, args.labels, args.limit)


if __name__ == "__main__":
    main()
