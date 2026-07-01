import os
import subprocess
import json
import pysubs2
from pathlib import Path
from backend.services.translator import translate_with_llama

def clean_subtitles(srt_path: str, method: str, vad_model: str, audio_path: str, llm_model_path: str, vad_onset: float = 0.5, vad_offset: float = 0.363, job_id: str = None, job_manager = None) -> bool:
    """
    Cleans a subtitle file using the specified method ('ai' or 'vad').
    """
    if method == "none":
        return True
        
    print(f"[Cleaner] Starting {method.upper()} cleaning on {os.path.basename(srt_path)}")
    
    try:
        if method == "ai":
            return _clean_with_ai(srt_path, llm_model_path, job_id, job_manager)
        elif method == "vad":
            return _clean_with_vad(srt_path, audio_path, vad_model, vad_onset, vad_offset, job_id, job_manager)
        else:
            print(f"[Cleaner] Unknown method: {method}")
            return False
    except Exception as e:
        print(f"[Cleaner] Error during cleaning: {e}")
        return False
        
def _clean_with_ai(srt_path: str, llm_model_path: str, job_id: str, job_manager) -> bool:
    if not llm_model_path or not os.path.exists(llm_model_path):
        print("[Cleaner] Valid LLM model path required for AI cleaning.")
        return False
        
    # We can use the _llama_clean_subprocess or call native llama directly.
    # To keep isolation, we'll spawn a subprocess for LLM cleaning to prevent memory leaks.
    subprocess_script = os.path.join(os.path.dirname(__file__), "_llama_clean_subprocess.py")
    temp_out = srt_path + ".cleaned.srt"
    
    cmd = [
        "python", subprocess_script,
        srt_path,
        temp_out,
        llm_model_path
    ]
    
    print(f"[Cleaner] Spawning AI cleaning subprocess...")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line = line.strip()
            print(f"[Llama Clean Output] {line}")
            if line.startswith("PROGRESS:") and job_manager and job_id:
                try:
                    parts = line.split("PROGRESS:")[1].split("/")
                    processed = int(parts[0])
                    total = int(parts[1])
                    if total > 0:
                        progress = 24.0 + (processed / total) * 1.0  # Phase 2.5
                        import asyncio
                        asyncio.run(job_manager.update_job(job_id, progress=progress))
                except:
                    pass
                    
    stderr = process.stderr.read()
    if stderr:
        print(f"[Cleaner Subprocess Error] {stderr}")
        
    if process.returncode == 0 and os.path.exists(temp_out):
        os.replace(temp_out, srt_path)
        return True
    else:
        if os.path.exists(temp_out):
            os.remove(temp_out)
        return False

def _clean_with_vad(srt_path: str, audio_path: str, vad_model: str, vad_onset: float, vad_offset: float, job_id: str, job_manager) -> bool:
    if not audio_path or not os.path.exists(audio_path):
        print("[Cleaner] Audio path required for VAD cleaning.")
        return False
        
    subprocess_script = os.path.join(os.path.dirname(__file__), "_vad_clean_subprocess.py")
    temp_out = srt_path + ".cleaned.srt"
    
    cmd = [
        "python", subprocess_script,
        srt_path,
        audio_path,
        temp_out,
        vad_model,
        str(vad_onset),
        str(vad_offset)
    ]
    
    print(f"[Cleaner] Spawning VAD cleaning subprocess...")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line = line.strip()
            print(f"[VAD Clean Output] {line}")
            
    stderr = process.stderr.read()
    if stderr:
        print(f"[Cleaner Subprocess Error] {stderr}")
        
    if process.returncode == 0 and os.path.exists(temp_out):
        os.replace(temp_out, srt_path)
        return True
    else:
        if os.path.exists(temp_out):
            os.remove(temp_out)
        return False
