#!/bin/bash

# Exit on error
set -e

echo "Checking for Virtual Environment..."
if [ -f "venv/bin/activate" ]; then
    echo "Activating Virtual Environment (venv)..."
    source venv/bin/activate
fi

echo "Checking if frontend is built..."
if [ ! -d "frontend/dist" ]; then
    echo "Frontend build not found. Building it now..."
    cd frontend
    npm install
    npm run build
    cd ..
else
    echo "Frontend is already built."
fi

echo ""
echo ""
echo "=============================================="
echo "    AutoSubs AI is now running!"
echo "    Access the Dashboard at:"
echo "    http://localhost:8000/"
echo "=============================================="
echo ""

echo "Starting FastAPI backend..."
cd backend
export HF_HUB_DISABLE_SYMLINKS_WARNING=1
export HF_HUB_DISABLE_TELEMETRY=1
uvicorn main:app --host 0.0.0.0 --port 8000
