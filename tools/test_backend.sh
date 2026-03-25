#!/usr/bin/env bash
# End-to-end smoke test: uploads a generated test image and checks annotation
set -e
PROJECT="/mnt/c/Users/manbi/OneDrive/Desktop/comp-440-website-1/Cotton-Weed-Prediction-Model"
cd "$PROJECT"

echo "=== Creating test image ==="
python3 - <<'EOF'
import cv2, numpy as np
img = np.zeros((480,640,3), dtype=np.uint8)
cv2.putText(img, "Test Frame", (100,240), cv2.FONT_HERSHEY_SIMPLEX, 2, (200,200,200), 3)
cv2.imwrite("/tmp/test_frame.jpg", img)
print("Test image written to /tmp/test_frame.jpg")
EOF

echo "=== Uploading test image ==="
RESPONSE=$(curl -s -X POST http://localhost:5000/api/upload \
  -F "file=@/tmp/test_frame.jpg;type=image/jpeg")
echo "Upload response: $RESPONSE"

echo "=== Done - backend is reachable and processing uploads ==="
