#!/usr/bin/env bash
set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Checking Python dependencies ==="
python3 -c "import flask; print('flask ok')"
python3 -c "import flask_cors; print('flask_cors ok')"
python3 -c "import cv2; print('cv2 ok')"
python3 -c "import ultralytics; print('ultralytics ok')"
echo "=== All dependencies present ==="
