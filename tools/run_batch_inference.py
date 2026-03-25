import os
from pathlib import Path
from main import annotate_image, get_model

# Force model to load
get_model()

# Paths
source_dir = Path(r"C:\Users\manbi\OneDrive\Desktop\comp-440-website\img to vid\test\images")
output_dir = Path(r"C:\Users\manbi\OneDrive\Desktop\comp-440-website\outputs\inference_images")

# Create output dir if it doesn't exist
output_dir.mkdir(parents=True, exist_ok=True)

# Find all images
image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
image_files = [f for f in source_dir.iterdir() if f.is_file() and f.suffix.lower() in image_extensions]

print(f"Found {len(image_files)} images in {source_dir}")

for img_file in image_files:
    dst_file = output_dir / img_file.name
    print(f"Processing {img_file.name} -> {dst_file}")
    annotate_image(img_file, dst_file)

print("Inference completed successfully.")
