# AutoSubs AI - WSL ROCm Backend Installer
# Author: Adromir
# Creates an isolated "AutoSubsAI-Ubuntu" WSL2 distro (Ubuntu 24.04) and
# installs ROCm + ctranslate2 + faster-whisper for AMD GPU acceleration.
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts\Install-WSL-Backend.ps1

$ErrorActionPreference = "Stop"

# ── Constants ─────────────────────────────────────────────────────────────────
$DISTRO_NAME    = "AutoSubsAI-Ubuntu"
$INSTALL_DIR    = "$env:LOCALAPPDATA\AutoSubsAI-WSL"
$SCRIPT_SRC     = Join-Path $PSScriptRoot "..\wsl\setup_wsl_rocm.sh"
$SCRIPT_SRC     = [System.IO.Path]::GetFullPath($SCRIPT_SRC)

# ── Helper Functions ──────────────────────────────────────────────────────────
function Write-Header {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  AutoSubs AI - WSL ROCm Backend Installer" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-DistroInstalled {
    $list = wsl --list --quiet 2>&1
    # wsl --list returns UTF-16 on some systems; convert and compare
    $text = [string]$list
    return $text -match [regex]::Escape($DISTRO_NAME)
}

function Convert-ToWSLPath {
    param([string]$WinPath)
    # E:\foo\bar -> /mnt/e/foo/bar
    $drive = $WinPath.Substring(0,1).ToLower()
    $rest  = $WinPath.Substring(2).Replace("\", "/")
    return "/mnt/$drive$rest"
}

function Test-WSLExecutable {
    # Check for wsl.exe without requiring admin rights.
    # Get-WindowsOptionalFeature requires elevation and is unnecessary here.
    $wslPath = Get-Command "wsl.exe" -ErrorAction SilentlyContinue
    if ($null -eq $wslPath) {
        Write-Host "[ERROR] wsl.exe not found in PATH." -ForegroundColor Red
        Write-Host "        Enable WSL via: Windows Settings -> Turn Windows features on -> Windows Subsystem for Linux" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "[WSL] wsl.exe found: $($wslPath.Source)" -ForegroundColor Green
}

function Install-Ubuntu24Distro {
    Write-Host "[WSL] Installing isolated distro '$DISTRO_NAME' (Ubuntu 24.04)..." -ForegroundColor Yellow
    Write-Host "      Downloading Ubuntu 24.04 rootfs (~600 MB), please wait..." -ForegroundColor Gray

    if (-not (Test-Path $INSTALL_DIR)) {
        New-Item -ItemType Directory -Path $INSTALL_DIR | Out-Null
    }

    # Ubuntu uses the Noble codename for 24.04.
    # Primary URL: cloud-images WSL releases (noble = Ubuntu 24.04 LTS codename)
    # Fallback URL: generic releases path
    $rootfsUrls = @(
        "https://cloud-images.ubuntu.com/wsl/releases/noble/current/ubuntu-noble-wsl-amd64-wsl.rootfs.tar.gz",
        "https://cloud-images.ubuntu.com/releases/noble/release/ubuntu-noble-server-cloudimg-amd64-wsl.rootfs.tar.gz"
    )
    $rootfsTar = Join-Path $env:TEMP "autosubs-ubuntu-24.04.tar.gz"

    # Remove stale cache from any previous failed download
    if (Test-Path $rootfsTar) {
        $cached = Get-Item $rootfsTar
        if ($cached.Length -lt 100MB) {
            Write-Host "[WSL] Removing incomplete cached file ($([math]::Round($cached.Length/1MB))MB < 100MB threshold)..." -ForegroundColor Yellow
            Remove-Item $rootfsTar -Force
        } else {
            Write-Host "[WSL] Using cached rootfs at $rootfsTar ($([math]::Round($cached.Length/1MB))MB)" -ForegroundColor Gray
        }
    }

    if (-not (Test-Path $rootfsTar)) {
        $downloaded = $false
        foreach ($url in $rootfsUrls) {
            Write-Host "[WSL] Trying: $url" -ForegroundColor Yellow
            try {
                Invoke-WebRequest -Uri $url -OutFile $rootfsTar -UseBasicParsing
                $downloaded = $true
                Write-Host "[WSL] Download complete." -ForegroundColor Green
                break
            } catch {
                Write-Host "[WSL] Failed: $($_.Exception.Message)" -ForegroundColor Red
                if (Test-Path $rootfsTar) { Remove-Item $rootfsTar -Force }
            }
        }
        if (-not $downloaded) {
            Write-Host "[ERROR] Could not download Ubuntu 24.04 rootfs from any known URL." -ForegroundColor Red
            Write-Host "        Please download manually from: https://cloud-images.ubuntu.com/wsl/releases/" -ForegroundColor Yellow
            exit 1
        }
    }

    Write-Host "[WSL] Importing as '$DISTRO_NAME' into $INSTALL_DIR ..." -ForegroundColor Yellow
    wsl --import $DISTRO_NAME $INSTALL_DIR $rootfsTar --version 2

    Write-Host "[WSL] Bootstrapping default user (autosubs)..." -ForegroundColor Yellow
    # Use semicolons for bash command chaining — avoids PowerShell && parsing issues
    wsl -d $DISTRO_NAME -- bash -c "useradd -m -s /bin/bash -G sudo autosubs"
    wsl -d $DISTRO_NAME -- bash -c "echo 'autosubs ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers"
    wsl -d $DISTRO_NAME -- bash -c "printf '[user]\ndefault=autosubs\n' >> /etc/wsl.conf"

    Write-Host "[WSL] Distro '$DISTRO_NAME' created successfully." -ForegroundColor Green
}


function Copy-SetupScript {
    if (-not (Test-Path $SCRIPT_SRC)) {
        Write-Host "[ERROR] Setup script not found at: $SCRIPT_SRC" -ForegroundColor Red
        exit 1
    }

    Write-Host "[Setup] Copying ROCm setup script into '$DISTRO_NAME'..." -ForegroundColor Yellow

    # Convert Windows path to WSL /mnt/... path
    $wslSrc = Convert-ToWSLPath $SCRIPT_SRC

    # Copy into WSL home directory using semicolons (not &&)
    wsl -d $DISTRO_NAME -- bash -c "cp '$wslSrc' ~/setup_wsl_rocm.sh"
    wsl -d $DISTRO_NAME -- bash -c "chmod +x ~/setup_wsl_rocm.sh"
    Write-Host "[Setup] Script copied to ~/setup_wsl_rocm.sh in WSL." -ForegroundColor Green
}

function Run-SetupScript {
    Write-Host "" 
    Write-Host "[Setup] Running ROCm + ctranslate2 + whisper installer inside WSL..." -ForegroundColor Cyan
    Write-Host "        GPU selection prompt will appear below." -ForegroundColor Gray
    Write-Host "        Expected duration: 20-60 min depending on connection + CPU." -ForegroundColor Gray
    Write-Host ""

    # Run interactively — no -c flag so the user can answer the GPU prompt
    wsl -d $DISTRO_NAME -- bash --login -c "cd ~ ; ./setup_wsl_rocm.sh"
}

function Show-Done {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "  AutoSubs AI WSL Installation Complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Distro  : $DISTRO_NAME" -ForegroundColor White
    Write-Host "  Install : $INSTALL_DIR" -ForegroundColor White
    Write-Host ""
    Write-Host "  To start the WSL backend:" -ForegroundColor Cyan
    Write-Host "    Run start.bat and choose option [2]" -ForegroundColor White
    Write-Host "    Or run: scripts\Start-WSL-Backend.ps1" -ForegroundColor White
    Write-Host ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
Write-Header

# Verify wsl.exe is available (no admin required)
Test-WSLExecutable

if (Test-DistroInstalled) {
    Write-Host "[WSL] Distro '$DISTRO_NAME' already exists." -ForegroundColor Green
    $ans = Read-Host "Re-run the setup script to update/repair? (y/N)"
    if ($ans -notmatch "^[Yy]$") {
        Write-Host "Skipping setup. Exiting." -ForegroundColor Gray
        exit 0
    }
} else {
    Install-Ubuntu24Distro
}

Copy-SetupScript
Run-SetupScript
Show-Done
