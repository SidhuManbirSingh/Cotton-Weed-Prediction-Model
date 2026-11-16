"""Shared path resolution and YOLO label parsing helpers for CLI scripts."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IMAGES_DIR = PROJECT_ROOT / "datasets" / "test" / "images"
DEFAULT_LABELS_DIR = PROJECT_ROOT / "datasets" / "test" / "labels"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
CLASS_NAMES = {0: "weed", 1: "cotton"}


def list_images(images_dir: Path) -> list[Path]:
    """Return sorted image files inside *images_dir*."""
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    return sorted(
        p for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def resolve_label_path(image_path: Path, labels_dir: Path | None = None) -> Path:
    """Resolve matching .txt label file in *labels_dir* or beside *image_path*."""
    if labels_dir is not None:
        candidate = labels_dir / f"{image_path.stem}.txt"
        if candidate.exists():
            return candidate
    return image_path.with_suffix(".txt")


def parse_yolo_labels(txt_path: Path) -> list[tuple[int, float, float, float, float]]:
    """Parse normalized YOLO bounding boxes (class_id, cx, cy, w, h) from *txt_path*."""
    if not txt_path.exists():
        return []
    entries: list[tuple[int, float, float, float, float]] = []
    for raw_line in txt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = raw_line.strip().split()
        if len(parts) < 5:
            continue
        entries.append((
            int(float(parts[0])),
            float(parts[1]),
            float(parts[2]),
            float(parts[3]),
            float(parts[4]),
        ))
    return entries
