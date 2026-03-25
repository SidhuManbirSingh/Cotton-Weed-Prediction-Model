#!/usr/bin/env bash
# Quick sanity check: verify model.pt resolves correctly from annotation.py's perspective
set -e
PROJECT="/mnt/c/Users/manbi/OneDrive/Desktop/comp-440-website-1/Cotton-Weed-Prediction-Model"
cd "$PROJECT"

echo "=== Verifying model.pt path resolution ==="
python3 - <<'EOF'
from pathlib import Path

# Mirrors the logic in annotation.py
script_path = Path("/mnt/c/Users/manbi/OneDrive/Desktop/comp-440-website-1/Cotton-Weed-Prediction-Model/backend/scripts/annotation.py")
model_path = script_path.parent.parent.parent / "model.pt"
print(f"Resolved model path: {model_path}")
print(f"Exists: {model_path.exists()}")
EOF
