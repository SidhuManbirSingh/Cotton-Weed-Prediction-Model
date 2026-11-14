#!/usr/bin/env bash
# Starts the Flask backend server.
# Run from repository root: bash start_backend.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Starting Flask backend on port 5000 ==="
export PYTHONPATH="$SCRIPT_DIR"
python3 -m backend.server.server
