import os
import subprocess
import platform
from typing import Optional

# Fix #3: Detect hardware encoder ONCE at module load time — these are constant for the server lifetime.
# Running ffmpeg -encoders + PowerShell Get-CimInstance on every burn call was needlessly expensive.

def _detect_hw_encoder() -> str:
    """Probe available hardware encoders once at startup and return the best available one."""
    available_encoders = []
    try:
        enc_out = subprocess.check_output(
            ['ffmpeg', '-encoders'], stderr=subprocess.STDOUT, text=True
        ).lower()
        for enc in ('h264_nvenc', 'h264_amf', 'h264_qsv', 'h264_videotoolbox'):
            if enc in enc_out:
                available_encoders.append(enc)
    except Exception as e:
        print(f"[HW Detect] Could not query FFmpeg encoders: {e}")

    opt_system = platform.system()
    try:
        if opt_system == "Windows":
            out = subprocess.check_output(
                ['powershell', '-NoProfile', '-Command',
                 'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name'],
                stderr=subprocess.STDOUT, text=True
            ).lower()
        elif opt_system == "Linux":
            out = subprocess.check_output(
                "lspci | grep -i vga", shell=True, stderr=subprocess.STDOUT, text=True
            ).lower()
        else:
            out = ""

        if "nvidia" in out and 'h264_nvenc' in available_encoders:
            encoder = 'h264_nvenc'
        elif ("amd" in out or "radeon" in out) and 'h264_amf' in available_encoders:
            encoder = 'h264_amf'
        elif "intel" in out and 'h264_qsv' in available_encoders:
            encoder = 'h264_qsv'
        else:
            encoder = 'libx264'
    except Exception as e:
        # Fix #12: log the error instead of silently swallowing it
        print(f"[HW Detect] GPU vendor detection failed (falling back to libx264): {e}")
        encoder = 'libx264'

    if opt_system == "Darwin" and 'h264_videotoolbox' in available_encoders:
        encoder = 'h264_videotoolbox'

    print(f"[HW Detect] Selected video encoder: {encoder}")
    return encoder


# Private cache result — lazily populated on first burn call
_BURN_ENCODER_CACHE: Optional[str] = None

def burn_subtitles(video_path: str, srt_path: str):
    global _BURN_ENCODER_CACHE
    if _BURN_ENCODER_CACHE is None:
        _BURN_ENCODER_CACHE = _detect_hw_encoder()
    
    encoder = _BURN_ENCODER_CACHE
    """
    Burns the SRT subtitles natively into a cloned MP4 file using Hardware Encoders.
    Encoder is detected once at server startup and reused for all subsequent burns.
    """
    if not os.path.exists(video_path) or not os.path.exists(srt_path):
        raise FileNotFoundError("Video or SRT file not found for burning.")
        
    output_path = f"{os.path.splitext(video_path)[0]}_hardsubbed.mp4"
    # We must escape the SRT path formatting for FFmpeg filters on Windows and Unix
    escaped_srt = srt_path.replace('\\', '/').replace(':', '\\\\:').replace("'", r"\'")
    
    encoder = _BURN_ENCODER  # Use the pre-detected cached encoder

    # Build FFmpeg command dynamically off Hardware Context
    cmd = [
        'ffmpeg', '-y',
        '-hwaccel', 'auto',
        '-i', video_path,
        '-vf', f"subtitles='{escaped_srt}'",
        '-c:v', encoder,
    ]
    
    # Map encoder-specific presets to prevent FFmpeg crashes
    if encoder == 'libx264':
        cmd.extend(['-preset', 'fast'])
    elif encoder == 'h264_nvenc':
        cmd.extend(['-preset', 'p6'])
    elif encoder == 'h264_amf':
        cmd.extend(['-quality', 'quality'])
    elif encoder == 'h264_qsv':
        cmd.extend(['-preset', 'veryfast'])
    elif encoder == 'h264_videotoolbox':
        cmd.extend(['-b:v', '5M'])  # macOS native bitrate anchor
        
    # Force audio copy seamlessly
    cmd.extend(['-c:a', 'copy', output_path])
    
    print(f"\n[FFMPEG] Burning Subtitles using Native Video Encoder: {encoder}")
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Read stdout to prevent blocking buffer and permit potential debugging
    for line in process.stdout:
        if "Error" in line:
            print(f"[FFMPEG] {line.strip()}")
            
    process.wait()
    
    if process.returncode != 0:
        raise RuntimeError("FFmpeg failed to burn subtitles natively.")
        
    print(f" -> [FFMPEG] Subtitle burned successfully to: {output_path}")
