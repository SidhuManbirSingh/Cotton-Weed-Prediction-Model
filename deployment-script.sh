#!/usr/bin/env bash
# ==============================================================================
# CottonVision — Single-Command Deployment Script
# Starts the full application (Backend API + Interactive Workbench Landing Page)
# Usage:
#   bash deployment-script.sh
#   ./deployment-script.sh
# ==============================================================================

set -e

# Resolve absolute path of directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "🌱 CottonVision — UAV Cotton & Weed Detection System"
echo "=================================================================="
echo "Working directory: $SCRIPT_DIR"

# Clean up child processes on exit
cleanup() {
    echo ""
    echo "Shutting down CottonVision services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Detect Python binary (python3 or python)
if command -v python3 &>/dev/null; then
    PY_BIN="python3"
elif command -v python &>/dev/null; then
    PY_BIN="python"
else
    echo "❌ Error: Python is not installed or not in PATH."
    echo "Please install Python 3.10+ (https://www.python.org/downloads/)."
    exit 1
fi

echo "✓ Using Python: $($PY_BIN --version 2>&1)"

# 2. Check & Install Python Dependencies
echo "Checking Python backend dependencies..."
$PY_BIN -c "import flask, werkzeug, cv2, ultralytics" 2>/dev/null || {
    echo "Installing missing dependencies from requirements.txt..."
    $PY_BIN -m pip install -r requirements.txt
}
echo "✓ Python dependencies verified."

# 3. Start Backend & Unified Web Server on port 5000
echo "Starting Flask Backend & Web Application on port 5000..."
export PYTHONPATH="$SCRIPT_DIR"
$PY_BIN -m backend.server.server &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for server initialization..."
SERVER_READY=0
for i in {1..15}; do
    if $PY_BIN -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/')" &>/dev/null; then
        SERVER_READY=1
        break
    fi
    sleep 1
done

if [ $SERVER_READY -eq 1 ]; then
    echo "✓ CottonVision Server is live at: http://localhost:5000"
else
    echo "⚠️ Server started in background (PID: $BACKEND_PID). Continuing..."
fi

# 4. Check for Node.js / Vite Frontend (Optional enhancement)
if command -v npm &>/dev/null && [ -d "frontend" ]; then
    echo "Node.js detected. Starting Vite dev server proxy..."
    cd "$SCRIPT_DIR/frontend"
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend npm packages..."
        npm install
    fi
    npm run dev &
    cd "$SCRIPT_DIR"
    echo "✓ Vite frontend available at: http://localhost:3000"
else
    echo "ℹ️  Node.js not in PATH. Running in Unified Mode:"
    echo "   Complete interactive UI + Inference API served directly via http://localhost:5000"
fi

# 5. Open browser if supported
URL="http://localhost:5000"
echo ""
echo "=================================================================="
echo "🚀 Application is running!"
echo "   Open your browser to: $URL"
echo "   Press Ctrl+C to stop the server."
echo "=================================================================="

if command -v xdg-open &>/dev/null; then
    xdg-open "$URL" 2>/dev/null || true
elif command -v open &>/dev/null; then
    open "$URL" 2>/dev/null || true
elif command -v cmd.exe &>/dev/null; then
    cmd.exe /c start "$URL" 2>/dev/null || true
fi

# Keep script running to maintain background jobs
wait $BACKEND_PID
