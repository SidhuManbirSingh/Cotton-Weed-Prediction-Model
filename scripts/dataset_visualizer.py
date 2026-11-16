"""Render ground-truth YOLO bounding boxes onto sampled dataset images."""

import argparse
import random
from pathlib import Path

import cv2

from _dataset_io import (
    CLASS_NAMES,
    DEFAULT_IMAGES_DIR,
    DEFAULT_LABELS_DIR,
    PROJECT_ROOT,
    list_images,
    parse_yolo_labels,
    resolve_label_path,
)

BOX_COLORS = {
    0: (94, 118, 242),   # Weed (#F2765E in BGR)
    1: (255, 91, 46),    # Cotton (#2E5BFF in BGR)
}


def visualize_dataset(
    images_dir: Path,
    labels_dir: Path | None,
    output_dir: Path,
    num_samples: int = 4,
    seed: int = 42,
) -> list[Path]:
    """Draw YOLO boxes for up to *num_samples* random images and save to *output_dir*."""
    all_images = list_images(images_dir)
    if not all_images:
        raise FileNotFoundError(f"No images found in {images_dir}")

    rng = random.Random(seed)
    sampled = rng.sample(all_images, min(num_samples, len(all_images)))
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    for img_path in sampled:
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        boxes = parse_yolo_labels(resolve_label_path(img_path, labels_dir))
        for cls_id, cx, cy, bw, bh in boxes:
            x1 = max(0, int((cx - bw / 2) * w))
            y1 = max(0, int((cy - bh / 2) * h))
            x2 = min(w - 1, int((cx + bw / 2) * w))
            y2 = min(h - 1, int((cy + bh / 2) * h))
            color = BOX_COLORS.get(cls_id, (200, 200, 200))
            label = CLASS_NAMES.get(cls_id, f"class_{cls_id}")
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, label, (x1, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        out_path = output_dir / img_path.name
        cv2.imwrite(str(out_path), img)
        saved.append(out_path)
    return saved


def main() -> None:
    """Parse arguments and write ground-truth annotated preview images."""
    parser = argparse.ArgumentParser(description="Visualize YOLO ground-truth labels on sample images.")
    parser.add_argument("--images", "-i", type=Path, default=DEFAULT_IMAGES_DIR, help="Images directory.")
    parser.add_argument("--labels", "-l", type=Path, default=DEFAULT_LABELS_DIR, help="Labels directory.")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "output" / "dataset_preview",
        help="Output folder for rendered preview images.",
    )
    parser.add_argument("--samples", "-n", type=int, default=4, help="Number of images to sample.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    args = parser.parse_args()

    saved = visualize_dataset(args.images, args.labels, args.output, args.samples, args.seed)
    print(f"[dataset_visualizer] Wrote {len(saved)} annotated preview(s) to {args.output}")


if __name__ == "__main__":
    main()
