"""
path_bridge.py — Windows ↔ WSL path translation utility
=========================================================
When the FastAPI backend runs inside WSL2, it receives Windows-style paths from
the frontend (e.g. E:\\Movies\\film.mkv) but needs Linux paths (/mnt/e/Movies/film.mkv).

This module auto-detects WSL at import time and provides transparent conversion.
"""

import os
import re
from pathlib import PurePosixPath, PureWindowsPath

# ── WSL Detection ─────────────────────────────────────────────────────────────
def _detect_wsl() -> bool:
    """Return True if this Python process is running inside WSL."""
    # Method 1: environment variable set by all WSL sessions
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    # Method 2: /proc/version contains "microsoft" on WSL kernels
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False

IS_WSL: bool = _detect_wsl()

# ── Path Conversion ────────────────────────────────────────────────────────────
_WIN_PATH_RE = re.compile(r"^([A-Za-z]):[/\\](.*)", re.DOTALL)


def to_local_path(path: str) -> str:
    """
    Convert a path to the format appropriate for this process's filesystem.

    - In WSL: converts Windows paths (C:\\foo) to /mnt/c/foo
    - On Windows/Linux (native): returns path unchanged
    """
    if not IS_WSL:
        return path

    m = _WIN_PATH_RE.match(path)
    if m:
        drive = m.group(1).lower()
        rest  = m.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{rest}"

    # Already a POSIX path — pass through
    return path


def to_windows_path(path: str) -> str:
    """
    Convert a WSL /mnt/X/... path back to a Windows X:\\... path.
    No-op when not in WSL or when path is already Windows-style.
    """
    if not IS_WSL:
        return path

    posix = PurePosixPath(path)
    parts = posix.parts  # ('/', 'mnt', 'e', 'foo', 'bar.mkv')
    if len(parts) >= 3 and parts[1] == "mnt" and len(parts[2]) == 1:
        drive  = parts[2].upper()
        rest   = "\\".join(parts[3:])
        return f"{drive}:\\{rest}"

    return path
