#!/bin/bash

echo "=============================================="
echo "    AutoSubs AI - GUI Rebuilder (Linux)"
echo "=============================================="
echo ""

if ! command -v npm &> /dev/null; then
    echo "[ERROR] 'npm' is not installed or not in your PATH."
    echo "Please install Node.js (e.g. sudo apt install npm or nvm)"
    exit 1
fi

echo "[1/3] Navigating to frontend directory..."
if [ ! -d "frontend" ]; then
    echo "[ERROR] 'frontend' directory not found. Are you running this from the project root?"
    exit 1
fi
cd frontend

echo "[2/3] Installing or verifying Node dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo "[ERROR] npm install failed!"
    exit 1
fi

echo "[3/3] Building the production Vite app..."
npm run build
if [ $? -ne 0 ]; then
    echo "[ERROR] npm run build failed!"
    exit 1
fi

echo ""
echo "=============================================="
echo "[SUCCESS] GUI has been successfully rebuilt into /frontend/dist!"
echo "You can now run start.sh to serve the new UI natively via FastAPI."
echo "=============================================="
echo ""
