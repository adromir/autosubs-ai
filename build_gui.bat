@echo off
setlocal

echo ==============================================
echo     AutoSubs AI - GUI Rebuilder (Windows)
echo ==============================================
echo.

echo Checking for Node.js (npm)...
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 'npm' is not installed or not in your PATH.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo [1/3] Navigating to frontend directory...
if not exist "frontend" (
    echo [ERROR] 'frontend' directory not found. Are you running this from the project root?
    pause
    exit /b 1
)
cd frontend

echo [2/3] Installing or verifying Node dependencies...
call npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm install failed!
    pause
    exit /b 1
)

echo [3/3] Building the production Vite app...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm run build failed!
    pause
    exit /b 1
)

echo.
echo ==============================================
echo [SUCCESS] GUI has been successfully rebuilt into /frontend/dist!
echo You can now run start.bat to serve the new UI natively via FastAPI.
echo ==============================================
echo.

pause
endlocal
