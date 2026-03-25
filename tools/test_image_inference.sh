#!/usr/bin/env bash
set -e
echo "=== Testing /api/process-image endpoint ==="
curl -s -X POST http://localhost:5000/api/process-image \
  -H 'Content-Type: application/json' \
  -d '{"filename": "test_frame.jpg"}' | python3 -m json.tool
echo ""
echo "=== Done ==="
