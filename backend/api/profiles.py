from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os
from typing import List, Optional

router = APIRouter()

PROFILES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "profiles.json")

class ProfileData(BaseModel):
    name: str
    model: str
    provider: str
    engine: str
    base_lang: str
    target_langs: List[str]
    ignore_forced: bool
    use_vad: bool
    prompt: str
    trans_engine: str
    llm_model: str
    hardcode: bool
    deep_cleanup: bool = True
    vad_onset: float = 0.500
    vad_offset: float = 0.363
    vad_model: str = "pyannote"
    fetch_internet_subs: bool = False
    allow_title_match: bool = False
    use_nfo: bool = False
    auto_sync: bool = False
    fallback_to_targets: bool = False
    fetch_all_available: bool = False
    is_default: bool = False
    llm_model_path: str = ""

class RenameRequest(BaseModel):
    old_name: str
    new_name: str

class DefaultRequest(BaseModel):
    name: str

def load_profiles():
    if not os.path.exists(PROFILES_FILE):
        return {"profiles": [], "default": None}
    try:
        with open(PROFILES_FILE, "r") as f:
            content = f.read()
            if not content:
                return {"profiles": [], "default": None}
            return json.loads(content)
    except Exception as e:
        print(f"Error loading profiles: {e}")
        return {"profiles": [], "default": None}

def save_profiles(data):
    os.makedirs(os.path.dirname(PROFILES_FILE), exist_ok=True)
    with open(PROFILES_FILE, "w") as f:
        json.dump(data, f, indent=4)

@router.get("/")
def get_profiles():
    return load_profiles()

@router.post("/")
def save_profile(profile: ProfileData):
    data = load_profiles()
    profiles = data.get("profiles", [])
    
    # Remove existing with same name if updating
    profiles = [p for p in profiles if p["name"] != profile.name]
    
    new_profile = profile.model_dump()
    profiles.append(new_profile)
    
    # If this is set as default, or if it's the first profile, set it as default
    if profile.is_default or not data.get("default"):
        for p in profiles:
            p["is_default"] = (p["name"] == profile.name)
        data["default"] = profile.name
        
    data["profiles"] = profiles
    save_profiles(data)
    return {"status": "success", "message": f"Profile '{profile.name}' saved!"}

@router.post("/rename")
def rename_profile(req: RenameRequest):
    data = load_profiles()
    profiles = data.get("profiles", [])
    
    found = False
    for p in profiles:
        if p["name"] == req.old_name:
            p["name"] = req.new_name
            found = True
            break
            
    if not found:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    if data.get("default") == req.old_name:
        data["default"] = req.new_name
        
    data["profiles"] = profiles
    save_profiles(data)
    return {"status": "success", "message": f"Profile renamed to '{req.new_name}'"}

@router.post("/set-default")
def set_default_profile(req: DefaultRequest):
    data = load_profiles()
    profiles = data.get("profiles", [])
    
    found = False
    for p in profiles:
        p["is_default"] = (p["name"] == req.name)
        if p.get("is_default"):
            found = True
            
    if not found:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    data["default"] = req.name
    data["profiles"] = profiles
    save_profiles(data)
    return {"status": "success", "message": f"'{req.name}' is now the default profile"}

@router.delete("/{name}")
def delete_profile(name: str):
    data = load_profiles()
    profiles = data.get("profiles", [])
    
    new_profiles = [p for p in profiles if p["name"] != name]
    if len(new_profiles) == len(profiles):
        raise HTTPException(status_code=404, detail="Profile not found")
        
    if data.get("default") == name:
        if new_profiles:
            data["default"] = new_profiles[0]["name"]
            new_profiles[0]["is_default"] = True
        else:
            data["default"] = None
        
    data["profiles"] = new_profiles
    save_profiles(data)
    return {"status": "success", "message": f"Profile '{name}' deleted"}
