#!/usr/bin/env bash
# Smoke test: upload a generated JPEG to /api/upload and verify Flask health
set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

TMP_IMG=$(python3 - <<'EOF'
import tempfile, cv2, numpy as np
from pathlib import Path

out = Path(tempfile.gettempdir()) / "cottonvision_test_frame.jpg"
img = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.putText(img, "Test Frame", (120, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (200, 200, 200), 3)
cv2.imwrite(str(out), img)
print(out)
EOF
)

echo "=== Uploading $TMP_IMG ==="
RESPONSE=$(curl -s -X POST http://localhost:5000/api/upload \
  -F "file=@${TMP_IMG};type=image/jpeg")
echo "Upload response: $RESPONSE"
rm -f "$TMP_IMG"
echo "=== Done ==="
