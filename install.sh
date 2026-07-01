#!/bin/bash

# Force current directory to script's directory
cd "$(dirname "$0")"

kill_locks() {
    # Attempt to gently kill python/node processes running in our directories
    pkill -f "$(pwd)/venv/bin/python" || true
    pkill -f "$(pwd)/frontend/node_modules" || true
    sleep 1
}

install_standard() {
    echo -e "\n\033[1;36m[INFO] Checking Prerequisites...\033[0m"

    if ! command -v python3 &> /dev/null; then
        echo -e "\033[1;31m[ERROR] Python3 is not installed or not in PATH.\033[0m"
        read -p "Press Enter to return to menu"
        return
    fi

    if command -v dpkg &> /dev/null; then
        if ! dpkg -l | grep -q python3-venv; then
            echo -e "\033[1;33m[WARNING] python3-venv might be missing. You may need: sudo apt install python3-venv\033[0m"
        fi
    fi

    if ! command -v ffmpeg &> /dev/null; then
        echo -e "\033[1;31m[ERROR] ffmpeg is not installed. Subtitle extraction will fail.\033[0m"
        echo "        Please install it: sudo apt install ffmpeg"
        read -p "Press Enter to return to menu"
        return
    fi

    if ! command -v npm &> /dev/null; then
        echo -e "\033[1;31m[ERROR] Node.js / NPM is not installed or not in PATH.\033[0m"
        read -p "Press Enter to return to menu"
        return
    fi

    echo -e "\n\033[1;36m[INFO] Launching AI Dependency Setup...\033[0m"
    python3 backend/install_deps.py
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m[ERROR] Backend installation failed.\033[0m"
        read -p "Press Enter to return to menu"
        return
    fi

    echo -e "\n\033[1;36m[INFO] Installing Frontend UI Dependencies...\033[0m"
    cd frontend
    npm install
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m[ERROR] Frontend npm install failed.\033[0m"
        cd ..
        read -p "Press Enter to return to menu"
        return
    fi
    cd ..

    echo -e "\n\033[1;32m==============================================\033[0m"
    echo -e "\033[1;32m  Installation Complete!\033[0m"
    echo -e "\033[1;32m  Run './start.sh' to start.\033[0m"
    echo -e "\033[1;32m==============================================\033[0m"
    read -p "Press Enter to return to menu"
}

update_repo() {
    echo -e "\n\033[1;36m[INFO] Updating Repository...\033[0m"
    if ! command -v git &> /dev/null; then
        echo -e "\033[1;31m[ERROR] Git is not installed.\033[0m"
        read -p "Press Enter to return to menu"
        return
    fi
    git pull
    if [ $? -eq 0 ]; then
        echo -e "\n\033[1;32m[SUCCESS] Repository updated.\033[0m"
    else
        echo -e "\n\033[1;31m[ERROR] Failed to update repository.\033[0m"
    fi
    read -p "Press Enter to return to menu"
}

reinstall_deps() {
    echo -e "\n\033[1;33m[WARNING] This will delete your virtual environment and frontend modules.\033[0m"
    read -p "Are you sure? (Y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        kill_locks
        
        echo -e "\n\033[1;36m[INFO] Removing Python Virtual Environment...\033[0m"
        rm -rf venv
        
        echo -e "\033[1;36m[INFO] Removing Frontend Node Modules...\033[0m"
        rm -rf frontend/node_modules
        
        install_standard
    fi
}

factory_reset() {
    echo -e "\n\033[1;31m[WARNING] This will WIPE ALL SETTINGS, PROFILES, and DEPENDENCIES.\033[0m"
    echo -e "\033[1;33mIt will NOT delete downloaded AI models.\033[0m"
    read -p "Are you absolutely sure you want to factory reset? (Y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        kill_locks
        
        echo -e "\n\033[1;36m[INFO] Deleting configurations and environments...\033[0m"
        
        for p in venv frontend/node_modules backend/profiles backend/.env backend/mount_cache.json installer_config.json; do
            if [ -e "$p" ]; then
                echo -e "\033[1;30m -> Deleting $p\033[0m"
                rm -rf "$p"
            fi
        done
        
        echo -e "\n\033[1;36m[INFO] Re-initializing repository...\033[0m"
        git reset --hard
        git clean -fd

        install_standard
    fi
}

while true; do
    clear
    echo -e "\033[1;35m==============================================\033[0m"
    echo -e "\033[1;36m   AutoSubs AI - Installation & Maintenance   \033[0m"
    echo -e "\033[1;35m==============================================\033[0m"
    echo ""
    echo "[1] Standard Installation"
    echo "[2] Update Repository (git pull)"
    echo "[3] Reinstall Dependencies"
    echo "[4] Factory Reset"
    echo "[5] Exit"
    echo ""
    
    read -p "Select an option: " choice

    case $choice in
        1) install_standard ;;
        2) update_repo ;;
        3) reinstall_deps ;;
        4) factory_reset ;;
        5) exit 0 ;;
        *) 
            echo -e "\033[1;33mInvalid option. Please try again.\033[0m"
            sleep 1
            ;;
    esac
done
