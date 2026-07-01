#requires -version 5.0
$ErrorActionPreference = "Stop"

# Force current directory to the script's directory
Set-Location $PSScriptRoot

Write-Host "`n==========================================" -ForegroundColor Magenta
Write-Host "     AutoSubs AI - Automated Launcher     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host ""

if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[DETECTED] Windows Native Installation." -ForegroundColor Green
    $mode = "windows"
} else {
    Write-Host "[ERROR] No valid installation found!" -ForegroundColor Red
    Write-Host "Please ensure you have run 'AutoSubs Setup.bat' first." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path "frontend\dist")) {
    Write-Host "`n[INFO] Frontend not found. Building now..." -ForegroundColor Cyan
    Push-Location frontend
    npm install
    npm run build
    Pop-Location
}


    Write-Host "`n==========================================" -ForegroundColor Green
    Write-Host "     AutoSubs AI is now starting!         " -ForegroundColor White
    Write-Host "     (Native Windows Backend)             " -ForegroundColor Gray
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "`n[INFO] Activating Virtual Environment..." -ForegroundColor Cyan

    . ".\venv\Scripts\Activate.ps1"

    # Background browser polling
    Start-Job -ScriptBlock {
        while (-not (Test-NetConnection localhost -Port 8000 -WarningAction SilentlyContinue).TcpTestSucceeded) {
            Start-Sleep -Seconds 1
        }
        Start-Process "http://localhost:8000"
    } | Out-Null

    $env:PYTHONUNBUFFERED = "1"
    $env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
    $env:HF_HUB_DISABLE_TELEMETRY = "1"
    $env:HF_XET_HIGH_PERFORMANCE = "1"
    $env:TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD = "1"

    # Load from .env if exists
    if (Test-Path ".env") {
        $envContent = Get-Content ".env"
        foreach ($line in $envContent) {
            if ($line -match "^HSA_OVERRIDE_GFX_VERSION=(.*)") {
                $env:HSA_OVERRIDE_GFX_VERSION = $matches[1]
                Write-Host "  [ROCm] HSA_OVERRIDE_GFX_VERSION=$($env:HSA_OVERRIDE_GFX_VERSION)" -ForegroundColor DarkCyan
            }
            if ($line -match "^AMDGPU_TARGETS=(.*)") {
                $env:AMDGPU_TARGETS = $matches[1]
            }
        }
    }

    Push-Location backend
    try {
        python -m uvicorn main:app --host 0.0.0.0 --port 8000
    } finally {
        Pop-Location
        Read-Host "`nPress Enter to exit"
    }

