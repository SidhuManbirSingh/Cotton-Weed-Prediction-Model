#!/usr/bin/env bash
# Starts the Flask backend server.
# Run from WSL: bash start_backend.sh
set -e
PROJECT="/mnt/c/Users/manbi/OneDrive/Desktop/comp-440-website-1/Cotton-Weed-Prediction-Model"
cd "$PROJECT"

echo "=== Starting Flask backend on port 5000 ==="
export PYTHONPATH="$PROJECT"
python3 -m backend.server.server
