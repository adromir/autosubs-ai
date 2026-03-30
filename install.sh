#!/bin/bash

echo "=============================================="
echo "  AutoSubs AI - Full Installation Setup"
echo "=============================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed or not in PATH."
    exit 1
fi

# Check for python3-venv (Ubuntu/Debian)
if ! dpkg -l | grep -q python3-venv; then
    echo "[WARNING] python3-venv might be missing. You may need: sudo apt install python3-venv"
fi

# Check for FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "[ERROR] ffmpeg is not installed. Subtitle extraction and alignment will fail."
    echo "        Please install it: sudo apt install ffmpeg"
    exit 1
fi

# Check NPM
if ! command -v npm &> /dev/null; then
    echo "[ERROR] Node.js / NPM is not installed or not in PATH."
    exit 1
fi

read -p "Do you want to create and use a Python Virtual Environment (venv)? (Y/N): " use_venv
if [[ "$use_venv" == "Y" || "$use_venv" == "y" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Virtual environment activated!"
fi

echo ""
read -p "Do you want to secure the Web GUI with a Username and Password? (Y/N): " use_auth
if [[ "$use_auth" == "Y" || "$use_auth" == "y" ]]; then
    read -p "Enter Username: " auth_user
    read -s -p "Enter Password: " auth_pass
    echo ""
    echo "AUTH_USERNAME=$auth_user" > backend/.env
    echo "AUTH_PASSWORD=$auth_pass" >> backend/.env
    echo "Credentials saved securely to backend/.env!"
fi

echo ""
echo "Launching AI Dependency Setup..."
python3 backend/install_deps.py
if [ $? -ne 0 ]; then
    echo "[ERROR] Backend installation failed."
    exit 1
fi

echo ""
echo "Installing Frontend UI Dependencies..."
cd frontend
npm install
if [ $? -ne 0 ]; then
    echo "[ERROR] Frontend npm install failed."
fi
cd ..

echo ""
echo ""

echo ""
echo "=============================================="
echo "  Installation Complete!"
echo "  Run ./start.sh to launch AutoSubs AI."
echo "=============================================="
