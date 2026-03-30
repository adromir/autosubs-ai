@echo off
setlocal enabledelayedexpansion

echo ==============================================
echo   AutoSubs AI - Full Installation Setup
echo ==============================================
echo.

:: ── Prerequisite checks ──────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

call npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / NPM is not installed or not in PATH.
    pause
    exit /b 1
)

:: ── Run the backend installer (handles provider choice, venv, auth internally) ─
echo Launching AI Dependency Setup...
python backend\install_deps.py
set INSTALL_EXIT=%errorlevel%

if %INSTALL_EXIT% neq 0 (
    echo [ERROR] Backend installation failed.
    pause
    exit /b 1
)

:: ── Exit code 2 means WSL mode was chosen — skip Windows frontend/backend deps ─
if %INSTALL_EXIT%==2 (
    echo.
    echo [WSL Mode] Skipping Windows-side frontend install.
    echo Use start.bat ^> option [2] to launch the WSL backend.
    pause
    exit /b 0
)

:: ── Install frontend dependencies (Windows mode only) ────────────────────────
echo.
echo Installing Frontend UI Dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Frontend npm install failed.
    pause
    exit /b 1
)
cd ..

echo.
echo.

echo.
echo ==============================================
echo   Installation Complete!
echo   Run start.bat to launch AutoSubs AI.
echo ==============================================
pause
