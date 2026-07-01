#!/bin/bash
set -e

cd "$(dirname "$0")"

echo -e "\n\033[1;35m==========================================\033[0m"
echo -e "\033[1;36m     AutoSubs AI - Automated Launcher     \033[0m"
echo -e "\033[1;35m==========================================\033[0m\n"

if [ -f "venv/bin/activate" ]; then
    echo -e "\033[1;32m[DETECTED] Linux Native Installation.\033[0m"
else
    echo -e "\033[1;31m[ERROR] No valid installation found!\033[0m"
    echo -e "\033[1;33mPlease ensure you have run './install.sh' first.\033[0m"
    read -p "Press Enter to exit"
    exit 1
fi

if [ ! -d "frontend/dist" ]; then
    echo -e "\n\033[1;36m[INFO] Frontend not found. Building now...\033[0m"
    cd frontend
    npm install
    npm run build
    cd ..
fi

echo -e "\n\033[1;32m==========================================\033[0m"
echo -e "\033[1;37m     AutoSubs AI is now starting!         \033[0m"
echo -e "\033[1;30m     (Native Linux Backend)               \033[0m"
echo -e "\033[1;32m==========================================\033[0m"
echo -e "\n\033[1;36m[INFO] Activating Virtual Environment...\033[0m"

source venv/bin/activate

# Background browser polling
(
    while ! python3 -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('localhost', 8000))" 2>/dev/null; do
        sleep 1
    done
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:8000" &> /dev/null
    fi
) &

export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_SYMLINKS_WARNING=1
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=1
export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1

# Load overrides from .env if present
if [ -f ".env" ]; then
    while IFS='=' read -r key value; do
        if [ "$key" == "HSA_OVERRIDE_GFX_VERSION" ]; then
            export HSA_OVERRIDE_GFX_VERSION="$value"
            echo -e "  \033[1;36m[ROCm] HSA_OVERRIDE_GFX_VERSION=$HSA_OVERRIDE_GFX_VERSION\033[0m"
        elif [ "$key" == "AMDGPU_TARGETS" ]; then
            export AMDGPU_TARGETS="$value"
        fi
    done < ".env"
fi

cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

read -p $'\nPress Enter to exit'
