from fastapi import APIRouter, HTTPException, Query
from services import llm_manager as mgr
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class DownloadRequest(BaseModel):
    model_id: str

class RegisterRequest(BaseModel):
    repo: str
    file: str
    name: Optional[str] = None

@router.get("/models")
async def list_models():
    """List local, recommended, and custom LLM models."""
    if not mgr.llm_manager:
        return {"local": [], "recommended": []}
    return {
        "local": mgr.llm_manager.get_local_models(),
        "recommended": mgr.llm_manager.get_recommended_models()
    }

@router.get("/scan")
async def scan_repo(repo_id: str = Query(..., description="HF Repository ID")):
    """Scan a remote HF repo for .gguf files."""
    if not mgr.llm_manager:
        raise HTTPException(status_code=500, detail="LLM Manager not initialized")
    files = mgr.llm_manager.scan_remote_repo(repo_id)
    return {"repo": repo_id, "files": files}

@router.post("/register")
async def register_model(req: RegisterRequest):
    """Register a custom model for download."""
    if not mgr.llm_manager:
        raise HTTPException(status_code=500, detail="LLM Manager not initialized")
    model_id = mgr.llm_manager.register_custom_model(req.repo, req.file, req.name)
    return {"status": "registered", "model_id": model_id}

@router.post("/download")
async def download_model(req: DownloadRequest):
    """Start downloading a model from HuggingFace."""
    if not mgr.llm_manager:
        raise HTTPException(status_code=500, detail="LLM Manager not initialized")
    
    success = mgr.llm_manager.start_download(req.model_id)
    if not success:
        raise HTTPException(status_code=400, detail="Model already downloading or invalid ID")
    
    return {"status": "started", "model_id": req.model_id}

@router.get("/download/status/{model_id}")
async def get_status(model_id: str):
    """Check the download progress of a specific model."""
    if not mgr.llm_manager:
        return {"progress": 0.0}
    return {"progress": mgr.llm_manager.get_download_status(model_id)}
