#!/usr/bin/env bash
set -e
PROJECT="/mnt/c/Users/manbi/OneDrive/Desktop/comp-440-website-1/Cotton-Weed-Prediction-Model"
cd "$PROJECT"

echo "=== Checking Python deps ==="
python3 -c "import flask; print('flask ok')"
python3 -c "import flask_cors; print('flask_cors ok')"
python3 -c "import cv2; print('cv2 ok')"
python3 -c "import ultralytics; print('ultralytics ok')"
echo "=== All deps present ==="
