#!/usr/bin/env bash
# Smoke test: run live YOLOv8 image inference against /api/process-image
set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

SAMPLE_IMG="media/workbench_presets/uav_raw_field.png"
if [ ! -f "$SAMPLE_IMG" ]; then
  echo "Preset image not found: $SAMPLE_IMG"
  exit 1
fi

UPLOAD_JSON=$(curl -s -X POST http://localhost:5000/api/upload -F "file=@${SAMPLE_IMG}")
FILENAME=$(echo "$UPLOAD_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['filename'])")

echo "=== Running /api/process-image for $FILENAME ==="
curl -s -X POST http://localhost:5000/api/process-image \
  -H "Content-Type: application/json" \
  -d "{\"filename\": \"${FILENAME}\"}" | python3 -m json.tool
echo "=== Done ==="
