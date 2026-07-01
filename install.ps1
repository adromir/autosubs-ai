#requires -version 5.0
$ErrorActionPreference = "Stop"

# Force current directory to the script's directory
Set-Location $PSScriptRoot

function Kill-Locks {
    # Try to gently kill any processes running inside the venv or node_modules that might lock files
    Get-Process -ErrorAction SilentlyContinue | Where-Object { 
        $_.Path -ne $null -and ($_.Path.StartsWith((Join-Path $PSScriptRoot "venv")) -or $_.Path.StartsWith((Join-Path $PSScriptRoot "frontend\node_modules")))
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

function Install-Standard {
    Write-Host "`n[INFO] Checking Prerequisites..." -ForegroundColor Cyan

    # Check Python
    if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Check Node
    if (-not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] Node.js / NPM is not installed or not in PATH." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "`n[INFO] Launching AI Dependency Setup..." -ForegroundColor Cyan
    python backend\install_deps.py
    $installExit = $LASTEXITCODE

    if ($installExit -ne 0) {
        Write-Host "[ERROR] Backend installation failed." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "`n[INFO] Installing Frontend UI Dependencies..." -ForegroundColor Cyan
    Push-Location frontend
    npm install
    $npmExit = $LASTEXITCODE
    Pop-Location

    if ($npmExit -ne 0) {
        Write-Host "[ERROR] Frontend npm install failed." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "`n==============================================" -ForegroundColor Green
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host "  Run 'AutoSubsLauncher.ps1' to start." -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    Read-Host "Press Enter to return to menu"
}

function Update-Repo {
    Write-Host "`n[INFO] Updating Repository..." -ForegroundColor Cyan
    if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] Git is not installed or not in PATH." -ForegroundColor Red
        Read-Host "Press Enter to return to menu"
        return
    }
    git pull
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n[SUCCESS] Repository updated." -ForegroundColor Green
    }
    else {
        Write-Host "`n[ERROR] Failed to update repository." -ForegroundColor Red
    }
    Read-Host "Press Enter to return to menu"
}

function Reinstall-Deps {
    Write-Host "`n[WARNING] This will delete your virtual environment and frontend modules." -ForegroundColor Yellow
    $confirm = Read-Host "Are you sure? (Y/N)"
    if ($confirm -match "^[yY]") {
        Kill-Locks
        
        try {
            Write-Host "`n[INFO] Removing Python Virtual Environment..." -ForegroundColor Cyan
            if (Test-Path "venv") { Remove-Item -Recurse -Force "venv" }
            
            Write-Host "[INFO] Removing Frontend Node Modules..." -ForegroundColor Cyan
            if (Test-Path "frontend\node_modules") { Remove-Item -Recurse -Force "frontend\node_modules" }
            
            Install-Standard
        }
        catch {
            Write-Host "`n[ERROR] Could not delete directories. Please ensure AutoSubs AI is completely closed and no other programs are using these folders." -ForegroundColor Red
            Read-Host "Press Enter to return to menu"
        }
    }
}

function Factory-Reset {
    Write-Host "`n[WARNING] This will WIPE ALL SETTINGS, PROFILES, and DEPENDENCIES." -ForegroundColor Red
    Write-Host "It will NOT delete downloaded AI models." -ForegroundColor Yellow
    $confirm = Read-Host "Are you absolutely sure you want to factory reset? (Y/N)"
    if ($confirm -match "^[yY]") {
        Kill-Locks
        
        try {
            Write-Host "`n[INFO] Deleting configurations and environments..." -ForegroundColor Cyan
            
            $pathsToDelete = @(
                "venv",
                "frontend\node_modules",
                "backend\profiles",
                "backend\.env",
                "backend\mount_cache.json",
                "installer_config.json"
            )

            foreach ($path in $pathsToDelete) {
                if (Test-Path $path) {
                    Write-Host " -> Deleting $path" -ForegroundColor Gray
                    Remove-Item -Recurse -Force $path
                }
            }
            
            Write-Host "`n[INFO] Re-initializing repository..." -ForegroundColor Cyan
            git reset --hard
            git clean -fd

            Install-Standard
        }
        catch {
            Write-Host "`n[ERROR] Could not complete Factory Reset because some files are in use. Please ensure AutoSubs AI is completely closed." -ForegroundColor Red
            Read-Host "Press Enter to return to menu"
        }
    }
}

while ($true) {
    Clear-Host
    Write-Host "==============================================" -ForegroundColor Magenta
    Write-Host "   AutoSubs AI - Installation & Maintenance   " -ForegroundColor Cyan
    Write-Host "==============================================" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "[1] Standard Installation"
    Write-Host "[2] Update Repository (git pull)"
    Write-Host "[3] Reinstall Dependencies"
    Write-Host "[4] Factory Reset"
    Write-Host "[5] Exit"
    Write-Host ""
    
    $choice = Read-Host "Select an option"

    switch ($choice) {
        "1" { Install-Standard }
        "2" { Update-Repo }
        "3" { Reinstall-Deps }
        "4" { Factory-Reset }
        "5" { exit }
        default { 
            Write-Host "Invalid option. Please try again." -ForegroundColor Yellow
            Start-Sleep -Seconds 1
        }
    }
}
