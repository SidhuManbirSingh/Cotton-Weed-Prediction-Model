#!/usr/bin/env bash
# Verify model.pt resolves cleanly from annotation.py
set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Verifying model.pt path resolution ==="
python3 - <<'EOF'
from pathlib import Path
from backend.scripts.annotation import _DEFAULT_MODEL

model_path = Path(_DEFAULT_MODEL)
print(f"Resolved model path: {model_path}")
print(f"Exists: {model_path.exists()}")
EOF
