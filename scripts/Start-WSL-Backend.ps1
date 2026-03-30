# AutoSubs AI — WSL ROCm Backend Launcher
# Author: Adromir
# Starts the FastAPI backend inside the AutoSubsAI-Ubuntu WSL distro.
# Called by start.bat when the user picks option [2].
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts\Start-WSL-Backend.ps1

$DISTRO_NAME = "AutoSubsAI-Ubuntu"
$PORT        = 8000

function Write-Header {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  AutoSubs AI - Starting WSL ROCm Backend" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-DistroInstalled {
    $list = wsl --list --quiet 2>&1
    return ($list -match $DISTRO_NAME)
}

function Get-WSLProjectPath {
    # Convert the Windows project root (parent of this scripts/ folder) to a WSL /mnt/ path.
    # PSScriptRoot is scripts/, so go one level up -> project root.
    $winPath = (Get-Item "$PSScriptRoot\..").FullName
    $drive   = $winPath.Substring(0,1).ToLower()
    $rest    = $winPath.Substring(2).Replace("\", "/")
    return "/mnt/${drive}${rest}"
}

function Stop-ExistingBackend {
    # Kill any process already occupying port 8000 on the host side
    $proc = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "[Launcher] Port $PORT is in use — killing existing process..." -ForegroundColor Yellow
        Stop-Process -Id $proc.OwningProcess -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }

    # Also kill any stale uvicorn in WSL
    wsl -d $DISTRO_NAME -- bash -c "pkill -f 'uvicorn main:app' 2>/dev/null || true"
}

function Start-WSLBackend {
    $wslProject = Get-WSLProjectPath

    # The startup command sources the saved GPU env and launches uvicorn
    $startCmd = @"
set -a
if [ -f ~/whisper_wsl.env ]; then source ~/whisper_wsl.env; fi
set +a
source "\${VENV_DIR:-\$HOME/whisper_wsl_env}/bin/activate"
export HF_HUB_DISABLE_SYMLINKS_WARNING=1
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=1
export TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1
echo ""
echo "  ROCm Architecture : \$GFX_ARCHITECTURE"
echo "  HSA Override      : \$HSA_OVERRIDE_GFX_VERSION"
echo "  Backend Path      : ${wslProject}/backend"
echo ""
cd "${wslProject}/backend"
exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1
"@

    Write-Host "[Launcher] Starting backend in '$DISTRO_NAME' on port $PORT..." -ForegroundColor Green
    Write-Host "  Access at: http://localhost:$PORT/" -ForegroundColor Cyan
    Write-Host ""

    # Run in the foreground so the console shows uvicorn output
    wsl -d $DISTRO_NAME -- bash -c $startCmd
}

# ── Main ──────────────────────────────────────────────────────────────────────
Write-Header

if (-not (Test-DistroInstalled)) {
    Write-Host "[ERROR] WSL distro '$DISTRO_NAME' is not installed." -ForegroundColor Red
    Write-Host "        Run: scripts\Install-WSL-Backend.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Verify the env file exists (setup completed)
$envCheck = wsl -d $DISTRO_NAME -- bash -c "test -f ~/whisper_wsl.env && echo found || echo missing"
if ($envCheck -match "missing") {
    Write-Host "[ERROR] WSL environment not configured. Please run Install-WSL-Backend.ps1 first." -ForegroundColor Red
    exit 1
}

Stop-ExistingBackend
Start-WSLBackend
