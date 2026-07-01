from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import os
import json
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import BaseModel
import sys
import threading
import asyncio
import re
from services.job_manager import job_manager, JobStatus

from services.model_manager import ModelManager


# Absolute config path — independent of CWD
_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

router = APIRouter()

def natural_sort_key(s):
    import re
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

class FileItem(BaseModel):
    name: str
    path: str
    is_dir: bool

@router.get("/browser", response_model=List[FileItem])
def browse_directory(path: Optional[str] = None):
    try:
        items = []
        if not path:
            # On Windows, return a list of drives if no path is provided
            if os.name == 'nt':
                import string
                drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:")]
                for d in drives:
                    items.append(FileItem(name=d, path=d, is_dir=True))
                return items
            else:
                path = "/"
        
        target_dir = Path(path)
        if not target_dir.exists() or not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="Invalid directory path")

        for entry in os.scandir(target_dir):
            items.append(FileItem(
                name=entry.name,
                path=entry.path,
                is_dir=entry.is_dir()
            ))
            
        # Sort directories first, then alphabetically
        items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
        return items
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied to access this directory")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/models")
def get_models():
    models_file = Path(__file__).parent.parent / "data" / "available_models.json"
    default_models = ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large", "large-v2", "large-v3", "large-v3-turbo"]
    try:
        if models_file.exists():
            with open(models_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {"models": data.get("whisper_models", default_models)}
    except Exception as e:
        print(f"Error reading available_models.json: {e}")
    return {"models": default_models}

@router.get("/config/hardware")
def get_hardware():
    import torch
    import sys
    
    cuda_av = torch.cuda.is_available()
    rocm_av = hasattr(torch.version, 'hip') and torch.version.hip is not None
    if cuda_av and rocm_av:
        cuda_av = False 
    
    try:
        import torch_directml
        dml_av = torch_directml.is_available()
    except Exception:
        dml_av = False
        
    return {
        "os": sys.platform,
        "providers": [
            {"id": "auto", "name": "Auto (Default)", "available": True},
            {"id": "nvidia", "name": "NVIDIA CUDA", "available": cuda_av},
            {"id": "amd", "name": "AMD ROCm", "available": rocm_av},
            {"id": "directml", "name": "DirectML (Windows)", "available": dml_av},
            {"id": "cpu", "name": "CPU Only", "available": True}
        ]
    }

@router.get("/config/engines")
def get_engines():
    engines = []
    
    try:
        import faster_whisper
        engines.append({"id": "faster-whisper", "name": "Faster-Whisper", "available": True})
    except ImportError:
        engines.append({"id": "faster-whisper", "name": "Faster-Whisper", "available": False})
        
    try:
        import transformers
        engines.append({"id": "whisper", "name": "Whisper (Transformers)", "available": True})
    except ImportError:
        engines.append({"id": "whisper", "name": "Whisper (Transformers)", "available": False})
        
    try:
        import whisperx
        engines.append({"id": "whisperx", "name": "WhisperX", "available": True})
    except ImportError:
        engines.append({"id": "whisperx", "name": "WhisperX", "available": False})
        
    return {
        "engines": engines
    }

@router.get("/config/languages")
def get_languages():
    return {
        "languages": [
            {"code": "en", "name": "🇬🇧 English"},
            {"code": "de", "name": "🇩🇪 German"},
            {"code": "es", "name": "🇪🇸 Spanish"},
            {"code": "fr", "name": "🇫🇷 French"},
            {"code": "it", "name": "🇮🇹 Italian"},
            {"code": "pt", "name": "🇵🇹 Portuguese"},
            {"code": "nl", "name": "🇳🇱 Dutch"},
            {"code": "ru", "name": "🇷🇺 Russian"},
            {"code": "ja", "name": "🇯🇵 Japanese"},
            {"code": "zh", "name": "🇨🇳 Chinese"},
            {"code": "ko", "name": "🇰🇷 Korean"},
            {"code": "pl", "name": "🇵🇱 Polish"},
            {"code": "tr", "name": "🇹🇷 Turkish"},
            {"code": "id", "name": "🇮🇩 Indonesian"},
            {"code": "hi", "name": "🇮🇳 Hindi"},
            {"code": "ar", "name": "🇸🇦 Arabic"},
            {"code": "sv", "name": "🇸🇪 Swedish"},
            {"code": "da", "name": "🇩🇰 Danish"},
            {"code": "fi", "name": "🇫🇮 Finnish"},
            {"code": "no", "name": "🇳🇴 Norwegian"},
            {"code": "cs", "name": "🇨🇿 Czech"},
            {"code": "el", "name": "🇬🇷 Greek"},
            {"code": "hu", "name": "🇭🇺 Hungarian"},
            {"code": "ro", "name": "🇷🇴 Romanian"}
        ]
    }

class JobCreateRequest(BaseModel):
    model_config = {'protected_namespaces': ()}
    path: str
    target_languages: List[str]
    base_language: str = "en"
    model_size: str
    provider: str = "auto"
    engine: str = "faster-whisper"
    ignore_forced_subs: bool = True
    custom_prompt: str = ""
    use_vad: bool = True
    translation_engine: str = "nllb"
    llm_model: str = ""
    llm_model_path: str = ""
    hardcode_subs: bool = False
    fetch_internet_subs: bool = False
    allow_title_match: bool = False
    use_nfo: bool = False
    auto_sync: bool = False
    fallback_to_targets: bool = False
    fetch_all_available: bool = False
    vad_onset: float = 0.500
    vad_offset: float = 0.363
    vad_model: str = "pyannote"
    cleaning_method: str = "none"
    enable_extraction: bool = True
    enable_transcription: bool = True
    emby_naming: bool = False
    auto_janitor: bool = True

def is_video_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']

@router.post("/jobs", response_model=List[JobStatus])
def create_jobs(request: JobCreateRequest):
    raw_path = request.path
    print(f"\n[API] Received Batch Processing Request for path: {raw_path}")
    local_path_str = raw_path
    target_dir = Path(local_path_str)

    if not target_dir.exists():
        print(f"[API] Error: Path not found -> {local_path_str}")
        raise HTTPException(status_code=404, detail=f"Path not found: {local_path_str}")

    created_jobs = []

    if target_dir.is_file() and is_video_file(target_dir.name):
        print(f"[API] Found a direct video file target: {target_dir.name}")
        job = job_manager.create_job(
            str(target_dir), 
            request.target_languages, 
            request.base_language, 
            request.model_size, 
            request.provider, 
            request.engine, 
            request.ignore_forced_subs, 
            request.custom_prompt, 
            request.use_vad, 
            request.translation_engine, 
            request.llm_model, 
            request.hardcode_subs,
            fetch_internet_subs=request.fetch_internet_subs,
            allow_title_match=request.allow_title_match,
            use_nfo=request.use_nfo,
            auto_sync=request.auto_sync,
            fallback_to_targets=request.fallback_to_targets,
            vad_onset=request.vad_onset,
            vad_offset=request.vad_offset,
            vad_model=request.vad_model,
            cleaning_method=request.cleaning_method,
            fetch_all_available=request.fetch_all_available,
            llm_model_path=request.llm_model_path,
            enable_extraction=request.enable_extraction,
            enable_transcription=request.enable_transcription,
            emby_naming=request.emby_naming,
            auto_janitor=request.auto_janitor
        )
        created_jobs.append(job)
    elif target_dir.is_dir():
        print(f"[API] Scanning directory for video files: {target_dir}")
        collected_files = []
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if is_video_file(file):
                    collected_files.append(os.path.join(root, file))

        # Sort files via natural order so S01E02 comes after S01E01
        collected_files.sort(key=natural_sort_key)

        for file_path in collected_files:
            print(f"  -> Discovered video: {os.path.basename(file_path)}")
            job = job_manager.create_job(
                file_path, 
                request.target_languages, 
                request.base_language, 
                request.model_size, 
                request.provider, 
                request.engine, 
                request.ignore_forced_subs, 
                request.custom_prompt, 
                request.use_vad, 
                request.translation_engine, 
                request.llm_model, 
                request.hardcode_subs,
                fetch_internet_subs=request.fetch_internet_subs,
                allow_title_match=request.allow_title_match,
                use_nfo=request.use_nfo,
                auto_sync=request.auto_sync,
                fallback_to_targets=request.fallback_to_targets,
                vad_onset=request.vad_onset,
                vad_offset=request.vad_offset,
                vad_model=request.vad_model,
                cleaning_method=request.cleaning_method,
                fetch_all_available=request.fetch_all_available,
                llm_model_path=request.llm_model_path,
                enable_extraction=request.enable_extraction,
                enable_transcription=request.enable_transcription,
                emby_naming=request.emby_naming,
                auto_janitor=request.auto_janitor
            )
            created_jobs.append(job)
    else:
        print(f"[API] Error: Target is not a valid component -> {target_dir}")
        raise HTTPException(status_code=400, detail="Path is not a valid directory or video file")

    print(f"[API] Successfully queued {len(created_jobs)} distinct jobs.")
    return created_jobs

@router.get("/jobs", response_model=List[JobStatus])
def get_jobs():
    return job_manager.get_all_jobs()

@router.get("/jobs/stream")
async def stream_jobs():
    queue = asyncio.Queue()
    await job_manager.add_listener(queue)
    
    async def event_generator():
        try:
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            await job_manager.remove_listener(queue)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

def get_model_manager():
    """Dynamically get ModelManager based on current config."""
    # Default paths
    base_dir = Path(__file__).parent.parent
    model_dir = base_dir / "models"
    nllb_dir = base_dir / "model_cache" / "nllb"
    
    # Check config for overrides
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r") as f:
                data = json.load(f)
                custom_path = data.get("model_cache_dir")
                if custom_path and os.path.exists(custom_path):
                    model_dir = Path(custom_path)
                    # For NLLB, check if the folder exists inside the custom path or nearby
                    # Or just keep it as is if NLLB isn't redirected.
                    # Currently, we look for 'nllb' within the cache or parallel.
                    nllb_dir = model_dir / "nllb" 
                    if not nllb_dir.exists():
                        # Fallback to the standard cache loc if not in custom dir
                        nllb_dir = base_dir / "model_cache" / "nllb"
        except:
            pass
            
    return ModelManager(str(model_dir), str(nllb_dir))

@router.get("/models")
def list_models():
    return get_model_manager().list_models()

@router.delete("/models")
def delete_model(path: str):
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")
    success = get_model_manager().delete_model(path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete model")
    return {"status": "success"}

@router.post("/models/wipe")
def wipe_models():
    # Final safety check handled by frontend, but we could add more here
    results = get_model_manager().wipe_all()
    return results

@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    success = await job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job not found or already ended")
    return {"status": "cancelled", "id": job_id}

@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await job_manager.update_job(job_id, status="pending", progress=0.0, message="Retrying job...")
    return {"status": "retrying", "id": job_id}

_DEFAULT_PROVIDERS = [
    {"id": "subdl", "active": True, "api_key": ""},
    {"id": "subsource", "active": True, "api_key": ""},
    {"id": "opensubtitlescom", "active": True, "api_key": "", "user": "", "pass": ""},
    {"id": "opensubtitles", "active": True, "user": "", "pass": ""},
    {"id": "podnapisi", "active": True},
    {"id": "addic7ed", "active": False},
    {"id": "tvsubtitles", "active": False},
    {"id": "napiprojekt", "active": False},
    {"id": "gestdown", "active": False}
]

@router.get("/config/settings")
def get_settings():
    # Dynamically verify against subliminal's actual providers + our custom ones
    try:
        import subliminal
        valid_ids = set(subliminal.provider_manager.names()) | {"subsource", "subdl"}
    except Exception:
        valid_ids = {p["id"] for p in _DEFAULT_PROVIDERS}

    try:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, "r") as f:
                data = json.load(f)
                # Ensure new keys are present and not empty
                if not data.get("model_cache_dir"):
                    data["model_cache_dir"] = ""
                
                if not data.get("subliminal_providers"):
                    data["subliminal_providers"] = [p for p in _DEFAULT_PROVIDERS if p["id"] in valid_ids]
                else:
                    # Filter out any currently invalid providers to avoid KeyErrors
                    data["subliminal_providers"] = [p for p in data["subliminal_providers"] if p.get("id") in valid_ids]
                    # Optionally, ensure new defaults from our list are present if they are valid
                    existing_ids = {p["id"] for p in data["subliminal_providers"]}
                    for d_p in _DEFAULT_PROVIDERS:
                        if d_p["id"] not in existing_ids and d_p["id"] in valid_ids:
                            data["subliminal_providers"].append(d_p)
                        elif d_p["id"] in existing_ids:
                            # Update existing with new keys like api_key if missing
                            for p in data["subliminal_providers"]:
                                if p["id"] == d_p["id"]:
                                    for k, v in d_p.items():
                                        if k not in p:
                                            p[k] = v
                return data
    except Exception as e:
        print(f"[Config] Could not read config: {e}")
    
    return {
        "discord_webhook": "", 
        "telegram_bot_token": "", 
        "telegram_chat_id": "", 
        "model_cache_dir": "",
        "subliminal_providers": _DEFAULT_PROVIDERS
    }

class SettingsUpdate(BaseModel):
    model_config = {'protected_namespaces': ()}
    discord_webhook: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    model_cache_dir: str = ""
    subliminal_providers: List[Dict] = []

@router.post("/config/settings")
def update_settings(settings: SettingsUpdate):
    with open(_CONFIG_PATH, "w") as f:
        json.dump(settings.model_dump(), f)
    return {"status": "success"}

class CleanupRequest(BaseModel):
    path: str

@router.post("/cleanup")
def cleanup_temp_files(req: CleanupRequest):
    target_dir = Path(req.path)
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Invalid directory path")
        
    deleted_count = 0
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".tmp.wav"):
                try:
                    os.remove(os.path.join(root, file))
                    deleted_count += 1
                except Exception as e:
                    print(f"[Janitor] Failed to delete {file}: {e}")
                    
    return {"status": "success", "deleted_count": deleted_count}

@router.post("/shutdown")
def shutdown_server():
    import os
    print("\n[API] Fast Shutdown requested! Instantly terminating process tree...")
    # os._exit kills the process immediately, bypassing python ThreadPool graceful exits
    os._exit(0)

