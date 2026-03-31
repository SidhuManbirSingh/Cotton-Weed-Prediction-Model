#!/bin/bash
# Deployment script for Inference of ML for Cotton-Weed Prediction

# Source bashrc to ensure nvm/npm is available
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Resolve the absolute path of the directory containing this script
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

echo "=== Deployment Starting ==="
echo "Project path: $PROJECT"

# Function to clean up background processes on exit
cleanup() {
    echo "Stopping background processes..."
    kill $(jobs -p) 2>/dev/null
    exit
}
trap cleanup SIGINT SIGTERM

# Start Backend
echo "Starting Flask Backend on port 5000..."
cd "$PROJECT"
export PYTHONPATH="$PROJECT"
# Start the python backend in the background
python3 -m backend.server.server &

# Wait a few seconds to let backend initialize
sleep 3

# Start Frontend
echo "Starting Vite Frontend..."
cd "$PROJECT/frontend"
# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Run the frontend server directly
npm run dev
