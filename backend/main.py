import os
import sys
from dotenv import load_dotenv
load_dotenv()

# --- OFFLINE-FIRST & LOG HARDENING ---
import logging
# Stop verbose HTTP diagnostics from huggingface_hub/transformers/httpx
for logger_name in ["httpx", "huggingface_hub", "transformers", "filelock"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# --------------------------------------

from api.routes import router as api_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Proactive HF Authentication on startup
hf_token = os.getenv("HF_TOKEN")

# Fix user environment variable conflicts
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("HF_HUB_ENABLE_HF_TRANSFER", None)

if hf_token:
    try:
        # Re-set environment variables explicitly to ensure priority over stale system vars
        os.environ["HF_TOKEN"] = hf_token
        os.environ["HF_HUB_TOKEN"] = hf_token
        from huggingface_hub import login
        login(token=hf_token)
        print(f"[BOOT] HuggingFace Authenticated via HF_TOKEN.")
    except Exception as e:
        print(f"[BOOT WARNING] HuggingFace Login failed: {e}")
from services.video_probe import probe_video
print("   --> Loading Transcriber Service...")
from services.transcriber import extract_audio, extract_audio_array, transcribe_audio
print("   --> Loading Extractor Service...")
from services.subtitle_extractor import extract_subtitle
print("   --> Loading Translator Service...")
from services.translator import translate_srt
from services.llm_manager import init_llm_manager
from services.subtitle_burner import burn_subtitles
from contextlib import asynccontextmanager
import asyncio
print("[BOOT] Loading Orchestrator...")
from services.orchestrator import background_worker
print("[BOOT] Loading Network Manager...")
from services.network_manager import network_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Restore persistent network shares prior to allowing traffic
    await asyncio.to_thread(network_manager.restore_mounts)
    
    # Initialize LLM Manager with configured cache directory
    # Default to 'backend/models' if not set
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(backend_dir, "config.json")
    cache_dir = os.path.join(backend_dir, "models")
    if os.path.exists(config_path):
        import json
        try:
            with open(config_path, "r") as f:
                conf = json.load(f)
                if conf.get("model_cache_dir"):
                    cache_dir = conf["model_cache_dir"]
        except: pass
    
    init_llm_manager(cache_dir)
    
    task = asyncio.create_task(background_worker())
    yield
    task.cancel()

app = FastAPI(title="Subtitle Generator API", lifespan=lifespan)

import base64
from fastapi import Request
from fastapi.responses import Response
# Basic Auth Middleware Removed - Using Bearer Token Dependency

# Configure CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Depends
from api.auth import router as auth_router, verify_token

app.include_router(auth_router, prefix="/api/auth")
app.include_router(api_router, prefix="/api", dependencies=[Depends(verify_token)])

def health_check():
    return {"status": "ok"}

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse



from api.settings import router as settings_router
app.include_router(settings_router, prefix="/api/settings", dependencies=[Depends(verify_token)])

from api.console import router as console_router
app.include_router(console_router, prefix="/api/console", dependencies=[Depends(verify_token)])

from api.profiles import router as profiles_router
app.include_router(profiles_router, prefix="/api/profiles", dependencies=[Depends(verify_token)])

from api.llm import router as llm_router
app.include_router(llm_router, prefix="/api/llm", dependencies=[Depends(verify_token)])

# Serve the frontend statically
# The Dockerfile will copy the built frontend to /app/frontend/dist
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    # Catch-all route to serve index.html for React Router (if using client-side routing)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # We only catch-all if it doesn't start with /api
        if full_path.startswith("api/"):
            return Response("Not Found", status_code=404)
            
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.exists(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
