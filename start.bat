@echo off
setlocal

echo.
echo ==========================================
echo     AutoSubs AI - Automated Launcher
echo ==========================================
echo.

:: ─── Auto-Detection ──────────────────────────────────────────────────────────
if exist "venv\Scripts\activate.bat" (
    echo [DETECTED] Windows Native Installation.
    goto start_windows
)
if exist "scripts\Start-WSL-Backend.ps1" (
    echo [DETECTED] WSL Backend Service.
    goto start_wsl
)

echo [ERROR] No valid installation found! 
echo Please ensure you have run the installer first.
pause
exit /b

:: ─── Option 1: Native Windows Backend ──────────────────────────────────────
:start_windows
echo Activating Virtual Environment...
call "venv\Scripts\activate.bat"

echo Checking if frontend is built...
if not exist "frontend\dist" (
    echo Frontend not found. Building now...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo.
echo ==========================================
echo     AutoSubs AI is now starting!
echo     (Native Windows Backend)
echo ==========================================
echo.

:: ─── Auto-Browser Launch ───
:: Starts a background process that polls port 8000 and opens the browser when ready.
start /b powershell -WindowStyle Hidden -Command "while (!(Test-NetConnection localhost -Port 8000 -WarningAction SilentlyContinue).TcpTestSucceeded) { Start-Sleep 1 }; start http://localhost:8000"

cd backend
set PYTHONUNBUFFERED=1
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set HF_HUB_DISABLE_TELEMETRY=1
set HF_HUB_ENABLE_HF_TRANSFER=1
set TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1

:: Load ROCm/GPU env vars from .env for HIP initialization
for /f "usebackq tokens=1,* delims==" %%a in (`findstr /r "HSA_OVERRIDE_GFX_VERSION AMDGPU_TARGETS" .env 2^>nul`) do set "%%a=%%b"
if defined HSA_OVERRIDE_GFX_VERSION echo   [ROCm] HSA_OVERRIDE_GFX_VERSION=%HSA_OVERRIDE_GFX_VERSION%

python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
goto end

:: ─── Option 2: WSL ROCm Backend (Advanced) ───────────────────────────────────
:start_wsl
echo Checking if frontend is built...
if not exist "frontend\dist" (
    echo Frontend not found. Building now...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo.
echo ==========================================
echo     AutoSubs AI is now starting!
echo     (Backend: WSL ROCm)
echo ==========================================
echo.

:: ─── Auto-Browser Launch ───
start /b powershell -WindowStyle Hidden -Command "while (!(Test-NetConnection localhost -Port 8000 -WarningAction SilentlyContinue).TcpTestSucceeded) { Start-Sleep 2 }; start http://localhost:8000"

powershell -ExecutionPolicy Bypass -File "%~dp0scripts\Start-WSL-Backend.ps1"
pause
goto end

:end
endlocal
