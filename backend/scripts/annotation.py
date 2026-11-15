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
import time
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


def _resolve_device_label(model_path: str, explicit_device: str | None) -> str:
    """Return human-readable runtime backend label used for prediction."""
    if explicit_device == 'GPU':
        return "OpenVINO GPU"
    if explicit_device == 'CPU':
        return "OpenVINO CPU"
    try:
        import torch
        if torch.cuda.is_available():
            return "CUDA GPU"
    except Exception:
        pass
    return "CPU"


def _predict_with_fallback(model, source: str, conf: float, device: str | None):
    """Run YOLO inference with OpenVINO GPU-to-CPU fallback if GPU plugin fails."""
    try:
        return model.predict(source=source, conf=conf, verbose=False, device=device), device
    except Exception:
        if device == 'GPU':
            return model.predict(source=source, conf=conf, verbose=False, device='CPU'), 'CPU'
        raise


def _collect_box_stats(results, model_names: dict, counts: dict, conf_sums: dict):
    """Accumulate detection counts and confidence sums across prediction results."""
    for r in results:
        if r.boxes is None or len(r.boxes) == 0:
            continue
        names = getattr(r, "names", None) or model_names or {}
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf_val = float(box.conf[0])
            cls_name = str(names.get(cls_id, f"class_{cls_id}")).lower()
            counts[cls_name] = counts.get(cls_name, 0) + 1
            conf_sums[cls_name] = conf_sums.get(cls_name, 0.0) + conf_val


def _build_summary(
    counts: dict,
    conf_sums: dict,
    elapsed_ms: int,
    model_path: str,
    device_label: str,
    frame_count: int = 1,
) -> dict:
    """Format class counts and mean confidences into an API-ready summary dict."""
    weed_count = int(counts.get("weed", 0))
    cotton_count = int(counts.get("cotton", 0))
    weed_conf = round(conf_sums["weed"] / weed_count, 2) if weed_count else None
    cotton_conf = round(conf_sums["cotton"] / cotton_count, 2) if cotton_count else None
    total = int(sum(counts.values()))
    return {
        "weed_count": weed_count,
        "weed_conf": weed_conf,
        "cotton_count": cotton_count,
        "cotton_conf": cotton_conf,
        "total_detections": total,
        "inference_ms": int(elapsed_ms),
        "frames_processed": int(frame_count),
        "model": Path(model_path).name,
        "device": device_label,
    }


def annotate_frames(
    input_dir: str,
    output_dir: str,
    model_path: str = _DEFAULT_MODEL,
    conf: float = 0.25,
    progress_callback=None,
    dataset_dir: str = None,
    summary_out: dict = None,
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
    used_device = device

    total = len(image_files)
    print(f"[annotation] Model: {model_path} | Device: {device or 'Auto'}")

    counts: dict = {}
    conf_sums: dict = {}
    t0 = time.perf_counter()
    count = 0
    for idx, img_path in enumerate(image_files):
        with _model_lock:
            results, used_device = _predict_with_fallback(model, str(img_path), conf, device)
            device = used_device

        _collect_box_stats(results, getattr(model, "names", {}), counts, conf_sums)
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

    if isinstance(summary_out, dict):
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        summary_out.update(_build_summary(
            counts,
            conf_sums,
            elapsed_ms,
            model_path,
            _resolve_device_label(model_path, used_device),
            frame_count=count,
        ))

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

    t0 = time.perf_counter()
    with _model_lock:
        results, used_device = _predict_with_fallback(model, str(input_path), conf, device)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    counts: dict = {}
    conf_sums: dict = {}
    _collect_box_stats(results, getattr(model, "names", {}), counts, conf_sums)

    annotated = results[0].plot()
    cv2.imwrite(str(output_path), annotated)

    label_path = output_path.with_suffix(".txt")
    h, w = annotated.shape[:2]
    _save_yolo_labels(results, w, h, label_path)

    return {
        "image_path": str(output_path.resolve()),
        "label_path": str(label_path.resolve()),
        "summary": _build_summary(
            counts,
            conf_sums,
            elapsed_ms,
            model_path,
            _resolve_device_label(model_path, used_device),
            frame_count=1,
        ),
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
