"""Compute class annotation counts for a YOLO label split directory."""

import argparse
from collections import Counter
from pathlib import Path

from _dataset_io import CLASS_NAMES, DEFAULT_LABELS_DIR, parse_yolo_labels


def count_classes(label_dir: Path) -> tuple[Counter, int]:
    """Return per-class box counts and total .txt files scanned inside *label_dir*."""
    if not label_dir.exists():
        raise FileNotFoundError(f"Labels directory not found: {label_dir}")
    stats: Counter = Counter()
    file_count = 0
    for txt_path in sorted(label_dir.glob("*.txt")):
        file_count += 1
        for cls_id, *_ in parse_yolo_labels(txt_path):
            stats[cls_id] += 1
    return stats, file_count


def main() -> None:
    """Print dataset annotation statistics as a Markdown table."""
    parser = argparse.ArgumentParser(description="Summarize YOLO annotation class counts.")
    parser.add_argument("--labels", "-l", type=Path, default=DEFAULT_LABELS_DIR, help="Path to YOLO labels directory.")
    args = parser.parse_args()

    counts, file_count = count_classes(args.labels)
    total_boxes = sum(counts.values())

    print(f"Labels directory: {args.labels} ({file_count} label files)\n")
    print("| Class ID | Label | Number of Annotations |")
    print("| :--- | :--- | ---: |")
    for cls_id, name in CLASS_NAMES.items():
        print(f"| {cls_id} | {name.title()} | {counts.get(cls_id, 0)} |")
    print(f"| Total | All Annotations | {total_boxes} |")


if __name__ == "__main__":
    main()
