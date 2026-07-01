import os
import sys
import gc
import time
import threading
import builtins
import re
import textwrap

# ── Global Print Flush Monkey-Patch ──
# Forces all prints to flush immediately, ensuring progress logs (even from sub-libraries like WhisperX)
# are visible in real-time when running under uvicorn/buffering.
_orig_print = builtins.print
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    _orig_print(*args, **kwargs)
builtins.print = print

# ── ROCm/HIP environment setup (must happen before any HIP library imports) ──
# HSA_OVERRIDE_GFX_VERSION tells the ROCm runtime which GPU architecture to use.
# Without this, ctranslate2 ROCm on Windows fails with:
#   "CUDA driver version is insufficient for CUDA runtime version"
# because HIP cannot identify newer GPUs (e.g. gfx1200 / RX 9060 XT) automatically.
# The value is written to .env by install_deps.py when the user selects ROCm + GPU model.
# transcriber.py lives in backend/services/, but .env is in backend/
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(_backend_dir, ".env")
_config_path = os.path.join(_backend_dir, "config.json")

# 1. Load ROCm/HIP environment variables
if os.path.exists(_env_path):
    with open(_env_path) as _ef:
        for _line in _ef:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _k = _k.strip()
                if _k in ("HSA_OVERRIDE_GFX_VERSION", "AMDGPU_TARGETS", "HF_TOKEN", "HF_HUB_TOKEN") and _k not in os.environ:
                    os.environ[_k] = _v.strip()
                    if _k == "HF_TOKEN":
                        os.environ["HF_HUB_TOKEN"] = _v.strip()

# 2. Setup Model Cache Directory (HF_HOME, TORCH_HOME)
import json
_model_cache_dir = os.path.join(_backend_dir, "models")
try:
    if os.path.exists(_config_path):
        with open(_config_path, "r") as _cf:
            _conf = json.load(_cf)
            if _conf.get("model_cache_dir"):
                _model_cache_dir = _conf["model_cache_dir"]
except Exception:
    pass

# Ensure directory exists
os.makedirs(_model_cache_dir, exist_ok=True)

# Set global environment variables BEFORE any model-related imports
os.environ["HF_HOME"] = _model_cache_dir
os.environ["TORCH_HOME"] = _model_cache_dir
os.environ["XDG_CACHE_HOME"] = _model_cache_dir

# Fix OpenMP duplicate library error on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from typing import Optional, NamedTuple
import torchaudio
import torch
import copy
import warnings
import traceback
import sys

# Silence noisy AI library version mismatches and environment noise
warnings.filterwarnings("ignore", message="Environment variable TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD detected")
warnings.filterwarnings("ignore", message="Model was trained with pyannote.audio")
warnings.filterwarnings("ignore", category=UserWarning, module="whisperx")
import ffmpeg
import numpy as np
import pysubs2
from pathlib import Path

# ── torchaudio Legacy Compatibility Shim (Global) ──
# WhisperX and Pyannote expect symbols removed in torchaudio 2.0+ (specifically AudioMetaData).
# We inject these globally BEFORE importing any sub-libraries to prevent import-time AttributeErrors.
if not hasattr(torchaudio, "AudioMetaData"):
    class AudioMetaData(NamedTuple):
        sample_rate: int
        num_frames: int
        num_channels: int
        bits_per_sample: int
        encoding: str
    torchaudio.AudioMetaData = AudioMetaData
if not hasattr(torchaudio, "AudioMetadata"):
    torchaudio.AudioMetadata = torchaudio.AudioMetaData

if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["ffmpeg"]
if not hasattr(torchaudio, "get_audio_backend"):
    torchaudio.get_audio_backend = lambda: "ffmpeg"
if not hasattr(torchaudio, "set_audio_backend"):
    torchaudio.set_audio_backend = lambda x: None

if not hasattr(torchaudio, "info"):
    def _global_mock_info(filepath, **kwargs):
        try:
            import subprocess
            import json
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', '-select_streams', 'a:0', str(filepath)]
            out = subprocess.check_output(cmd).decode('utf-8')
            data = json.loads(out)
            if 'streams' in data and len(data['streams']) > 0:
                s = data['streams'][0]
                return torchaudio.AudioMetaData(
                    sample_rate=int(s.get('sample_rate', 44100)),
                    num_frames=int(s.get('duration_ts', 0)),
                    num_channels=int(s.get('channels', 2)),
                    bits_per_sample=int(s.get('bits_per_sample', 16) or 16),
                    encoding=s.get('codec_name', 'audio')
                )
        except Exception: pass
        return torchaudio.AudioMetaData(44100, 0, 2, 16, 'unknown')
    torchaudio.info = _global_mock_info

# NOTE: 'import torch' is intentionally LOADED LAZILY inside transcribe_audio.
# This prevents ROCm/HIP initialization from hanging the uvicorn server startup.
# NOTE: 'from faster_whisper import WhisperModel' is intentionally NOT imported here at module level.
# ctranslate2 ROCm loads HIP DLLs at import time. If HIP can't init (GPU not recognized),
# that DLL load hangs — which would block uvicorn startup entirely.
# Instead we import lazily inside the engine block where it's wrapped in try/except.

# ── Post-Processing Utilities ──

def post_process_text(text: str) -> str:
    """
    Cleans up hallucinations, noise markers, and internal repetitions.
    """
    if not text:
        return ""
        
    # 1. Strip special hallucination characters (¶, etc.)
    text = re.sub(r'[¶\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # 2. Strip common Whisper noise markers like [MUSIC], (Laughter), [inaudible]
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    
    # 3. Handle internal deduplication of phrases or words
    # Example: "and caused damage and caused damage" -> "and caused damage"
    # This regex catches repeated groups of words (1 or more) separated by spaces.
    # We use a backreference \1 to find the repeated part.
    # \b matches word boundaries to ensure we don't break words like 'ber-berry'.
    # Note: We only collapse if it repeats at least once. 
    # We do multiple passes to catch nested or consecutive different repetitions.
    for _ in range(2):
        text = re.sub(r'\b(.+?)(?:\s+\1\b)+', r'\1', text, flags=re.IGNORECASE).strip()
    
    # 4. Final cleanup of double spaces/trimming
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def wrap_text(text: str, width: int = 42) -> str:
    """
    Wraps text to a maximum line length while respecting word boundaries.
    """
    if not text:
        return ""
    # textwrap.fill handles the newline insertion automatically
    return textwrap.fill(text, width=width, break_long_words=False, replace_whitespace=True)

# ── Self-Healing Checkpoint Utilities ──

def ensure_whisperx_checkpoint_upgraded():
    """
    Automatically detects and upgrades the WhisperX pytorch_model.bin
    if it is an older version (1.5.4) that causes Lightning warnings.
    """
    try:
        import whisperx
        import torch
        from packaging import version
        from pytorch_lightning.utilities.upgrade_checkpoint import main as upgrade_main
        
        wx_dir = os.path.dirname(whisperx.__file__)
        bin_path = os.path.join(wx_dir, "assets", "pytorch_model.bin")
        
        if not os.path.exists(bin_path):
            return

        # Use CPU to avoid VRAM overhead during version check
        # and ignore security warnings since this is a known asset.
        os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
        
        # We only need metadata, but torch.load reads the header.
        ckpt = torch.load(bin_path, map_location="cpu", weights_only=False)
        pl_version = ckpt.get("pytorch-lightning_version", "0.0.0")
        
        if version.parse(pl_version) < version.parse("2.0.0"):
            print(f"[Self-Healing] Detected legacy WhisperX checkpoint (v{pl_version}). Upgrading to v2.x...")
            # Shim sys.argv for the upgrade utility
            orig_argv = sys.argv
            sys.argv = ["upgrade_checkpoint", bin_path]
            try:
                upgrade_main()
                print("[Self-Healing] WhisperX checkpoint successfully upgraded!")
            finally:
                sys.argv = orig_argv
        else:
            # Already up to date
            pass
            
    except Exception as e:
        print(f"[Self-Healing] Checkpoint maintenance skipped: {e}")

_transcription_cache = {
    "engine": None,
    "model_size": None,
    "device": None,
    "compute_type": None,
    "model": None,
    "align_model": None,
    "align_metadata": None,
    "align_lang": None
}

def clear_transcription_cache():
    global _transcription_cache
    if _transcription_cache["model"] is not None:
        del _transcription_cache["model"]
    if _transcription_cache["align_model"] is not None:
        del _transcription_cache["align_model"]
        
    _transcription_cache.update({
        "engine": None,
        "model_size": None,
        "device": None,
        "compute_type": None,
        "model": None,
        "align_model": None,
        "align_metadata": None,
        "align_lang": None
    })
    gc.collect()
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def extract_audio(video_path: str, output_audio_path: str, track_index: Optional[int] = None):
    try:
        duration = 0.0
        try:
            probe = ffmpeg.probe(video_path)
            duration = float(probe['format']['duration'])
        except Exception:
            pass

        print(f"Extracting audio track from: {os.path.basename(video_path)}")
        
        stream = ffmpeg.input(video_path, hwaccel='auto')
        if track_index is not None:
            stream = stream[str(track_index)]
        else:
            stream = stream.audio
            
        stream = ffmpeg.output(stream, output_audio_path, acodec='pcm_s16le', ac=1, ar='16k')
        args = ffmpeg.compile(stream, overwrite_output=True)
        
        import subprocess
        process = subprocess.Popen(
            args, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True, 
            bufsize=1,
            encoding='utf-8', 
            errors='replace'
        )
        
        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        
        if duration > 0:
            try:
                from tqdm import tqdm
                pbar = tqdm(total=100, desc="Extracting Audio", unit="%", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}% [{elapsed}<{remaining}]")
                last_progress = 0
                for line in process.stderr:
                    match = time_pattern.search(line)
                    if match:
                        h, m, s = match.groups()
                        current_time = int(h) * 3600 + int(m) * 60 + float(s)
                        progress = min(100, int((current_time / duration) * 100))
                        if progress > last_progress:
                            pbar.update(progress - last_progress)
                            last_progress = progress
                pbar.update(100 - last_progress)
                pbar.close()
                process.wait()
            except ImportError:
                last_progress = -1
                for line in process.stderr:
                    match = time_pattern.search(line)
                    if match:
                        h, m, s = match.groups()
                        current_time = int(h) * 3600 + int(m) * 60 + float(s)
                        progress = min(100, int((current_time / duration) * 100))
                        if progress > last_progress and progress % 10 == 0:
                            print(f"Extracting Audio... {progress}%", end='\r', flush=True)
                            last_progress = progress
                process.wait()
                print("Extracting Audio... 100%")
        else:
            print("Extracting Audio (duration unknown)...", end="", flush=True)
            for _ in process.stderr:
                pass
            process.wait()
            print(" Done!")
            
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg process returned non-zero exit status {process.returncode}")
        
        # Verification: Ensure file was actually created and has content
        if not os.path.exists(output_audio_path) or os.path.getsize(output_audio_path) == 0:
            raise RuntimeError(f"FFmpeg produced an empty or missing audio file: {output_audio_path}")
            
    except Exception as e:
        print(f"\nFailed to extract audio: {str(e)}")
        raise RuntimeError(f"Audio extraction failed for {video_path}")

def extract_audio_array(video_path: str, track_index: Optional[int] = None) -> np.ndarray:
    try:
        stream = ffmpeg.input(video_path)
        if track_index is not None:
            stream = stream[str(track_index)]
        else:
            stream = stream.audio
            
        out, _ = (
            ffmpeg.output(stream, 'pipe:', format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
        return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
    except ffmpeg.Error as e:
        print(f"Failed to extract audio Array inside RAM: {e.stderr.decode('utf8') if e.stderr else str(e)}")
        raise RuntimeError(f"Audio RAM extraction failed for {video_path}")

def format_timestamp(seconds: float):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds_remainder:06.3f}".replace('.', ',')

def transcribe_audio(audio_input, model_size: str, output_srt_path: str, language: str = None, provider: str = "auto", engine: str = "faster-whisper", cancel_check = None, custom_prompt: str = "", use_vad: bool = True, progress_callback = None, total_duration: float = 0.0, deep_cleanup: bool = True, vad_onset: float = 0.500, vad_offset: float = 0.363, vad_model: str = "pyannote") -> str:
    global _transcription_cache
    import torch
    
    device = "cpu"
    compute_type = "float32"
    
    if provider in ["cuda", "nvidia"] or (provider == "auto" and torch.cuda.is_available() and getattr(torch.version, 'hip', None) is None):
        device = "cuda"
        compute_type = "float16"
    elif provider in ["rocm", "amd"] or (provider == "auto" and torch.cuda.is_available() and getattr(torch.version, 'hip', None) is not None):
        device = "cuda"
        compute_type = "float16"
    elif provider == "cpu" or provider == "auto":
        device = "cpu"
        compute_type = "int8"

    if provider == "directml" or (provider == "auto" and device == "cpu"):
        try:
            import torch_directml
            if torch_directml.is_available():
                device = "privateuseone"
                engine = "whisper"
        except ImportError:
            pass
            
    print(f"Executing Transcription with engine={engine}, provider={provider}, assigned_device={device}")

    # ===== ENGINE: FASTER-WHISPER =====
    if engine == "faster-whisper":
        try:
            from faster_whisper import WhisperModel  # lazy import — avoids HIP DLL hang at server start
            try:
                from faster_whisper import BatchedInferencePipeline
                has_batched = True
            except ImportError:
                has_batched = False
                
            if _transcription_cache["engine"] != "faster-whisper" or _transcription_cache["model_size"] != model_size or _transcription_cache["device"] != device:
                print(f"Loading faster-whisper {model_size} on {device}...")
                clear_transcription_cache()
                try:
                    # Respect custom model cache directory
                    base_model = WhisperModel(model_size, device=device, compute_type=compute_type, download_root=_model_cache_dir)
                    if has_batched:
                        model = BatchedInferencePipeline(model=base_model)
                    else:
                        model = base_model
                except RuntimeError as e:
                    if "CUDA failed with error CUDA driver version is insufficient" in str(e) or "HIP error" in str(e):
                        print(f"\n[Hardware Alert] ROCm/CUDA initialization failed on {device}. Falling back to CPU for stability.")
                        device = "cpu"
                        compute_type = "int8"
                        base_model = WhisperModel(model_size, device="cpu", compute_type="int8", download_root=_model_cache_dir)
                        if has_batched:
                            model = BatchedInferencePipeline(model=base_model)
                        else:
                            model = base_model
                    else:
                        raise e
                _transcription_cache.update({"engine": "faster-whisper", "model_size": model_size, "device": device, "compute_type": compute_type, "model": model, "has_batched": has_batched})
            else:
                model = _transcription_cache["model"]
                has_batched = _transcription_cache.get("has_batched", False)
            
            kwargs = {
                "language": language,
                "beam_size": 5,
                "vad_filter": use_vad,
                # Fix: Propagate VAD tuning to faster-whisper's built-in Silero-VAD
                "vad_parameters": dict(
                    threshold=vad_onset,
                    min_speech_duration_ms=250,
                    max_speech_duration_s=float('inf'),
                    min_silence_duration_ms=int(vad_offset * 1000),
                    speech_pad_ms=400
                ) if use_vad else None,
                "temperature": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            }
            
            if has_batched:
                kwargs["batch_size"] = 16
                print("Using BatchedInferencePipeline (batch_size=16) for accelerated transcription.")
            else:
                # Add arguments that are unused by BatchedInferencePipeline
                kwargs["condition_on_previous_text"] = False
                kwargs["compression_ratio_threshold"] = 2.4
                kwargs["log_prob_threshold"] = -1.0
                kwargs["no_speech_threshold"] = 0.6

            if custom_prompt and custom_prompt.strip():
                kwargs["initial_prompt"] = custom_prompt.strip()
            
            segments, info = model.transcribe(audio_input, **kwargs)
            
            print(f"faster-whisper detected language '{info.language}' with probability {info.language_probability}")
            
            subs = pysubs2.SSAFile()
            last_text = None
            for segment in segments:
                if cancel_check and cancel_check():
                    print("faster-whisper: Cancellation requested!")
                    raise InterruptedError("Cancelled by user")
                
                # ── Apply Post-Processing ──
                raw_text = segment.text.strip()
                
                if deep_cleanup:
                    cleaned_text = post_process_text(raw_text)
                    # Skip if empty after cleaning or if it's an exact duplicate of the last segment
                    if not cleaned_text or cleaned_text == last_text:
                        continue
                    # Apply line wrapping for 42 chars
                    final_text = wrap_text(cleaned_text)
                    print(f"[{format_timestamp(segment.start)} -> {format_timestamp(segment.end)}] {final_text}")
                    last_text = cleaned_text
                else:
                    final_text = raw_text
                    print(f"[{format_timestamp(segment.start)} -> {format_timestamp(segment.end)}] {final_text}")
                
                # Update progress
                if progress_callback and total_duration > 0:
                    progress = min(1.0, segment.end / total_duration)
                    progress_callback(progress)
                    
                event = pysubs2.SSAEvent(
                    start=int(segment.start * 1000), 
                    end=int(segment.end * 1000), 
                    text=final_text
                )
                subs.events.append(event)
            
            # Enforce UTF-8 and LF (Unix) line endings
            with open(output_srt_path, "w", encoding="utf-8", newline="\n") as f:
                subs.to_file(f, format_="srt")
                
            return info.language
        except Exception as e:
            print(f"faster-whisper failed ({e}). Traceback:")
            traceback.print_exc()
            print("Falling back to HuggingFace Transformers...")
            engine = "whisper"

    # ===== ENGINE: WHISPERX =====
    if engine == "whisperx":
        try:
            import whisperx
            from whisperx.vads import Pyannote

            # 4. PyTorch 2.6+ Security Patch: Global Monkey-Patch for trusted models
            try:
                # Surgical silent monkey-patch: Force weights_only=False globally for this process
                # since we trust our model weights (WhisperX/Pyannote).
                # This resolves the noisy "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD" warning by doing it internally.
                _orig_torch_load = torch.load
                def _patched_torch_load(*args, **kwargs):
                    if "weights_only" not in kwargs:
                        kwargs["weights_only"] = False
                    return _orig_torch_load(*args, **kwargs)
                torch.load = _patched_torch_load
            except Exception:
                pass

            print("[Patch] Applied torchaudio legacy shim and global torch.load security bypass.")
            wx_device = "cuda" if device in ["cuda", "privateuseone"] else "cpu" 
            
            # ── Automated Checkpoint Maintenance ──
            # Replaced manual upgrade commands with automated self-healing.
            ensure_whisperx_checkpoint_upgraded()

            if _transcription_cache["engine"] != "whisperx" or _transcription_cache["model_size"] != model_size or _transcription_cache["device"] != wx_device:
                print(f"Loading whisperx {model_size} on {wx_device}...")
                clear_transcription_cache()
                
                # Fix: Support selectable VAD models.
                # Pyannote (Precision) is pinned to CPU for AMD ROCm stability.
                # Silero (Speed) uses WhisperX's native method which is highly efficient.
                if vad_model == "silero":
                    print("WhisperX: Using Silero-VAD (Speed Optimized)")
                    v_model = None # whisperx.load_model will use vad_method="silero" if vad_model is None
                else:
                    print("WhisperX: Using Pyannote-VAD (Precision Optimized) pinned to CPU")
                    v_model = Pyannote(torch.device("cpu"), vad_onset=vad_onset, vad_offset=vad_offset)
                
                # Anti-hallucination: Use standard robustness thresholds
                asr_options = {
                    "beam_size": 5,
                    "condition_on_previous_text": False,
                    "compression_ratio_threshold": 2.4,
                    "log_prob_threshold": -1.0,
                    "no_speech_threshold": 0.6,
                    "temperatures": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                }
                if custom_prompt and custom_prompt.strip():
                    asr_options["initial_prompt"] = custom_prompt.strip()

                try:
                    model = whisperx.load_model(
                        model_size, wx_device, 
                        compute_type=compute_type, 
                        vad_model=v_model, 
                        vad_method="silero" if vad_model == "silero" else "pyannote",
                        language=language, 
                        asr_options=asr_options,
                        download_root=_model_cache_dir
                    )
                except RuntimeError as e:
                    if "CUDA failed with error CUDA driver version is insufficient" in str(e) or "HIP error" in str(e):
                        print(f"\n[Hardware Alert] WhisperX ROCm initialization failed on {wx_device}. Falling back to CPU.")
                        wx_device = "cpu"
                        compute_type = "float32"
                        if v_model: # Re-init Pyannote for CPU just in case
                            v_model = Pyannote(torch.device("cpu"), vad_onset=vad_onset, vad_offset=vad_offset)
                        model = whisperx.load_model(
                            model_size, "cpu", 
                            compute_type="float32", 
                            vad_model=v_model, 
                            vad_method="silero" if vad_model == "silero" else "pyannote",
                            language=language, 
                            asr_options=asr_options,
                            download_root=_model_cache_dir
                        )
                    else:
                        raise e
                _transcription_cache.update({"engine": "whisperx", "model_size": model_size, "device": wx_device, "compute_type": compute_type, "model": model})
            else:
                model = _transcription_cache["model"]
                
            if cancel_check and cancel_check(): raise InterruptedError("Cancelled by user")
            if isinstance(audio_input, np.ndarray):
                audio = audio_input
            else:
                audio = whisperx.load_audio(audio_input)
            
            if progress_callback: progress_callback(0.1)
            # Scaling: 16 batch_size leverages 16GB VRAM on RX 9060 XT (gfx1200) efficiently.
            print(f"WhisperX: Starting transcription [batch_size=16]...")
            result = model.transcribe(audio, batch_size=16, language=language, print_progress=True)
            
            # Fix: Save detected language BEFORE align results overwrite the 'result' dict
            detected_lang = result.get("language", language or "en")
            
            if progress_callback: progress_callback(0.5)
            if cancel_check and cancel_check(): raise InterruptedError("Cancelled by user")
            
            try:
                # Performance Optimization: Cache alignment model by language to avoid 1GB+ VRAM load per file.
                if _transcription_cache["align_lang"] != detected_lang or _transcription_cache["align_model"] is None:
                    print(f"WhisperX: Loading alignment model for '{detected_lang}' on {wx_device}...")
                    try:
                        # Attempt strict offline load
                        model_a, metadata = whisperx.load_align_model(language_code=detected_lang, device=wx_device, download_root=_model_cache_dir)
                    except Exception:
                        print(f" -> WhisperX align model for '{detected_lang}' not found locally. Initializing download...")
                        # Temporarily enable network
                        os.environ["HF_HUB_OFFLINE"] = "0"
                        try:
                            model_a, metadata = whisperx.load_align_model(language_code=detected_lang, device=wx_device, download_root=_model_cache_dir)
                        finally:
                            os.environ["HF_HUB_OFFLINE"] = "1"
                    _transcription_cache.update({
                        "align_model": model_a,
                        "align_metadata": metadata,
                        "align_lang": detected_lang
                    })
                else:
                    print(f"WhisperX: Using cached alignment model for '{detected_lang}'...")
                    model_a = _transcription_cache["align_model"]
                    metadata = _transcription_cache["align_metadata"]

                result = whisperx.align(result["segments"], model_a, metadata, audio, wx_device, return_char_alignments=False, print_progress=True)
                
                print(f"WhisperX: Finalizing aligned segments and result merging...")
                if progress_callback: progress_callback(0.9)
            except Exception as e:
                print(f"WhisperX alignment skipped: {e}")
                
            print(f"WhisperX: Post-processing {len(result['segments'])} transcribed segments...")
            subs = pysubs2.SSAFile()
            last_text = None
            for segment in result["segments"]:
                # ── Apply Post-Processing ──
                raw_text = segment["text"].strip()
                if deep_cleanup:
                    cleaned_text = post_process_text(raw_text)
                    if not cleaned_text or cleaned_text == last_text: 
                        continue
                    final_text = wrap_text(cleaned_text)
                    last_text = cleaned_text
                else:
                    final_text = raw_text
                
                print(f"[{format_timestamp(segment['start'])} -> {format_timestamp(segment['end'])}] {final_text}")
                event = pysubs2.SSAEvent(
                    start=int(segment["start"] * 1000), 
                    end=int(segment["end"] * 1000), 
                    text=final_text
                )
                subs.events.append(event)
            
            # Enforce UTF-8 and LF (Unix) line endings
            with open(output_srt_path, "w", encoding="utf-8", newline="\n") as f:
                subs.to_file(f, format_="srt")
            
            # NOTE: We no longer delete model_a here, as it's cached globally for the next file.
            # Only VRAM-intensive main model caches are force-purged if needed.
            
            # Proactive VRAM cleanup for Windows ROCm
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            return detected_lang
        except Exception as e:
            print(f"whisperx failed ({e}). Traceback:")
            traceback.print_exc()
            print("Falling back to HuggingFace Transformers...")
            engine = "whisper"

    # ===== ENGINE: WHISPER (Transformers native) =====
    if engine == "whisper":
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
        
        hf_device = "cpu"
        if device == "privateuseone":
            import torch_directml
            hf_device = torch_directml.device()
        elif device == "cuda":
            hf_device = "cuda:0"
            
        if _transcription_cache["engine"] != "whisper" or _transcription_cache["model_size"] != model_size or _transcription_cache["device"] != hf_device:
            print(f"Loading transformers Whisper {model_size} on {hf_device} [float16, SDPA]...")
            clear_transcription_cache()
            # Use float16 on GPU for ~2x speedup vs float32; cpu stays float32 natively
            dtype = torch.float16 if hf_device != "cpu" else torch.float32
            
            # Strict Offline-First Loading for Whisper
            repo_id = f"openai/whisper-{model_size}"
            try:
                processor = AutoProcessor.from_pretrained(repo_id, local_files_only=True)
                model = AutoModelForSpeechSeq2Seq.from_pretrained(
                    repo_id, 
                    dtype=dtype, 
                    low_cpu_mem_usage=True, 
                    use_safetensors=True,
                    attn_implementation="sdpa",
                    local_files_only=True
                ).to(hf_device)
            except Exception:
                print(f" -> Whisper {model_size} not found locally. Initializing download...")
                os.environ["HF_HUB_OFFLINE"] = "0"
                os.environ["TRANSFORMERS_OFFLINE"] = "0"
                try:
                    processor = AutoProcessor.from_pretrained(repo_id)
                    model = AutoModelForSpeechSeq2Seq.from_pretrained(
                        repo_id, 
                        dtype=dtype, 
                        low_cpu_mem_usage=True, 
                        use_safetensors=True,
                        attn_implementation="sdpa"
                    ).to(hf_device)
                finally:
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    os.environ["TRANSFORMERS_OFFLINE"] = "1"
            
            _transcription_cache.update({"engine": "whisper", "model_size": model_size, "device": hf_device, "compute_type": "float16", "model": model, "processor": processor})
        else:
            model = _transcription_cache["model"]
            processor = _transcription_cache["processor"]
        
        if cancel_check and cancel_check(): raise InterruptedError("Cancelled by user")
        
        if isinstance(audio_input, np.ndarray):
            audio_data = audio_input
        else:
            # Load audio for transformers if not already np.ndarray
            import whisperx
            audio_data = whisperx.load_audio(audio_input)
            
        print("Transcribing via Transformers generate() [Long-form mode]...", flush=True)

        stop_event = threading.Event()
        def progress_logger():
            start_time = time.time()
            while not stop_event.wait(timeout=5):
                elapsed = int(time.time() - start_time)
                print(f"   --> [Transformers] Generating... ({elapsed}s elapsed)", flush=True)

        prog_thread = threading.Thread(target=progress_logger, daemon=True)
        prog_thread.start()
        
        try:
            print("Transcribing via Transformers Native Generate() [Long-form stable mode]...", flush=True)

            stop_event = threading.Event()
            def progress_logger():
                start_time = time.time()
                while not stop_event.wait(timeout=5):
                    elapsed = int(time.time() - start_time)
                    print(f"   --> [Transformers] Generating... ({elapsed}s elapsed)", flush=True)

            prog_thread = threading.Thread(target=progress_logger, daemon=True)
            prog_thread.start()
            
            try:
                # --- Native Whisper Long-Form Generation (Transformers 4.36+) ---
                # This path avoids the 'experimental pipeline' warnings by using the model's 
                # own internal chunking and cross-attention mechanisms directly.
                
                # Prepare inputs - Whisper expects 80 mel-frequency components (input_features)
                inputs = processor(audio_data, return_tensors="pt", sampling_rate=16000)
                input_features = inputs.input_features.to(hf_device).to(dtype)
                
                # generation_config explicitly prevents several deprecation warnings about parameter mixing
                from transformers import GenerationConfig
                gen_config = GenerationConfig.from_pretrained(
                    f"openai/whisper-{model_size}",
                    max_new_tokens=448,
                    do_sample=True,
                    return_timestamps=True,
                    language=language if language else None,
                    task="transcribe"
                )
                
                with torch.no_grad():
                    generated_ids = model.generate(input_features, generation_config=gen_config)
                    
                    # Use the processor to decode with timestamps - produces a transcription with <|0.00|> tags
                    result_chunks = processor.batch_decode(generated_ids, skip_special_tokens=False, decode_with_timestamps=True)
                    
                    # --- PARSING Native Chunks ---
                    # Native generate returns a single long string with timestamp tokens.
                    # We need to parse this back into segments for SRT production.
                    # Format is typically: <|0.00|> Text here <|5.00|> Next text...
                    raw_text = result_chunks[0]
                    
                    # Regex to find all timestamp patterns: <|0.00|>
                    import re
                    ts_regex = re.compile(r"<\|(\d+\.\d+)\|>(.*?)<\|(\d+\.\d+)\|>", re.DOTALL)
                    parsed_chunks = []
                    
                    # The structure from batch_decode with timestamps is a sequence of <|ts|> TEXT <|ts|>
                    # We can also use processor.tokenizer.decode() more granularly, 
                    # but regex is robust for the final string.
                    for match in ts_regex.finditer(raw_text):
                        st_val = float(match.group(1))
                        txt_val = match.group(2).strip()
                        et_val = float(match.group(3))
                        if txt_val:
                            parsed_chunks.append({"timestamp": (st_val, et_val), "text": txt_val})
                    
                    # Fallback if regex missed segments (legacy format)
                    if not parsed_chunks:
                        print("   [Warning] Native parser found no segments. Falling back to simple string split.")
                        parsed_chunks = [{"timestamp": (0, total_duration), "text": processor.batch_decode(generated_ids, skip_special_tokens=True)[0]}]
                    
                    result_chunks = parsed_chunks
            finally:
                stop_event.set()
                prog_thread.join(timeout=1.0)
        except Exception as e:
            print(f"Native Generate failed: {e}")
            import traceback
            traceback.print_exc()
            result_chunks = []
            
        if cancel_check and cancel_check(): raise InterruptedError("Cancelled by user")
        
        subs = pysubs2.SSAFile()
        last_text = None
        for chunk in result_chunks:
            st = chunk["timestamp"][0]
            et = chunk["timestamp"][1] if len(chunk["timestamp"]) > 1 and chunk["timestamp"][1] is not None else st + 5.0
            
            # ── Apply Post-Processing ──
            raw_text = chunk["text"].strip()
            if deep_cleanup:
                cleaned_text = post_process_text(raw_text)
                if not cleaned_text or cleaned_text == last_text:
                    continue
                final_text = wrap_text(cleaned_text)
                last_text = cleaned_text
            else:
                final_text = raw_text
            
            print(f"[{format_timestamp(st)} -> {format_timestamp(et)}] {final_text}")
            event = pysubs2.SSAEvent(
                start=int(st * 1000), 
                end=int(et * 1000), 
                text=final_text
            )
            subs.append(event)
            
        # Enforce UTF-8 and LF (Unix) line endings
        with open(output_srt_path, "w", encoding="utf-8", newline="\n") as f:
            subs.to_file(f, format_="srt")
            
        return language or "en"
