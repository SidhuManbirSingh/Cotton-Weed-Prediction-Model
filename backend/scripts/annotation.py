"""
annotation.py
-------------
Runs YOLOv8 inference (supporting OpenVINO GPU acceleration) on images.
Exports paired YOLO datasets (matching .jpg and .txt filenames).

Task 2: Hardware Acceleration (Intel Arc GPU)
- model = YOLO('best_openvino_model/', task='detect')
- results = model.predict(source=frame, device='GPU')
"""

import os
import argparse
import cv2
import threading
from pathlib import Path

_YOLO_AVAILABLE = False
_model_lock = threading.Lock()

try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False

# Search for OpenVINO model directory first, fallback to .pt
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_OV_MODEL = _PROJECT_ROOT / "best_openvino_model"
_PT_MODEL = _PROJECT_ROOT / "model.pt"

_DEFAULT_MODEL = str(_OV_MODEL) if _OV_MODEL.exists() else str(_PT_MODEL)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
_model_cache: dict = {}


def _get_model(model_path: str):
    """Return a cached YOLO model instance."""
    if not _YOLO_AVAILABLE:
        raise ImportError("ultralytics is not installed. Run: pip install ultralytics")
    
    if model_path not in _model_cache:
        print(f"[annotation] Loading model: {model_path}")
        # If it's a directory (OpenVINO), we specify the task
        if Path(model_path).is_dir():
            _model_cache[model_path] = YOLO(model_path, task='detect')
        else:
            _model_cache[model_path] = YOLO(model_path)
    return _model_cache[model_path]


def _save_yolo_labels(results, img_width: int, img_height: int, label_path: Path):
    """Save YOLO-format detection labels to a .txt file."""
    lines = []
    for r in results:
        if r.boxes is None or len(r.boxes) == 0:
            continue
        for box in r.boxes:
            cls  = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            x_center = ((x1 + x2) / 2) / img_width
            y_center = ((y1 + y2) / 2) / img_height
            w = (x2 - x1) / img_width
            h = (y2 - y1) / img_height
            lines.append(f"{cls} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f} {conf:.4f}")

    label_path.write_text("\n".join(lines) + ("\n" if lines else ""))


def annotate_frames(
    input_dir: str,
    output_dir: str,
    model_path: str = _DEFAULT_MODEL,
    conf: float = 0.25,
    progress_callback=None,
    dataset_dir: str = None,
) -> int:
    """
    Run inference on all images in *input_dir*.
    Uses hardware acceleration (GPU) if an OpenVINO model is detected.
    """
    input_dir  = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ds_dir = Path(dataset_dir) if dataset_dir else None
    if ds_dir: ds_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not image_files:
        raise FileNotFoundError(f"No images found in: {input_dir}")

    model = _get_model(model_path)
    # Use Intel GPU if it's an OpenVINO model or if GPU is available
    device = 'GPU' if 'openvino' in model_path.lower() or Path(model_path).is_dir() else None
    
    total = len(image_files)
    print(f"[annotation] Model: {model_path} | Device: {device or 'CPU'}")

    count = 0
    for idx, img_path in enumerate(image_files):
        with _model_lock:
            # Task 2: Explicitly use GPU device
            results = model.predict(source=str(img_path), conf=conf, verbose=False, device=device)

        annotated = results[0].plot()
        out_path = output_dir / img_path.name
        cv2.imwrite(str(out_path), annotated)

        if ds_dir:
            # Matching filenames: frame_0001.jpg and frame_0001.txt
            base_name = f"frame_{idx:04d}"
            ds_img_path = ds_dir / f"{base_name}.jpg"
            ds_lbl_path = ds_dir / f"{base_name}.txt"
            cv2.imwrite(str(ds_img_path), annotated)
            h, w = annotated.shape[:2]
            _save_yolo_labels(results, w, h, ds_lbl_path)

        count += 1
        if progress_callback: progress_callback(count, total)
        if count % 50 == 0: print(f"[annotation] {count}/{total} frames…")

    return count


def annotate_single_image(
    input_path: str,
    output_path: str,
    model_path: str = _DEFAULT_MODEL,
    conf: float = 0.25,
) -> dict:
    """Run single inference using hardware acceleration where available."""
    input_path  = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = _get_model(model_path)
    device = 'GPU' if 'openvino' in model_path.lower() or Path(model_path).is_dir() else None

    with _model_lock:
        results = model.predict(source=str(input_path), conf=conf, verbose=False, device=device)

    annotated = results[0].plot()
    cv2.imwrite(str(output_path), annotated)

    label_path = output_path.with_suffix(".txt")
    h, w = annotated.shape[:2]
    _save_yolo_labels(results, w, h, label_path)

    return {
        "image_path": str(output_path.resolve()),
        "label_path": str(label_path.resolve()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  "-i", required=True)
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--model",  "-m", default=_DEFAULT_MODEL)
    parser.add_argument("--conf",   "-c", type=float, default=0.25)
    parser.add_argument("--dataset", "-d", default=None)
    args = parser.parse_args()
    annotate_frames(args.input, args.output, args.model, args.conf, dataset_dir=args.dataset)
