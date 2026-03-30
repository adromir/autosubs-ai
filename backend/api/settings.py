from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from dotenv import set_key, find_dotenv
from services.network_manager import network_manager

router = APIRouter()

class HFTokenRequest(BaseModel):
    token: str

@router.post("/hf-token")
def set_hf_token(request: HFTokenRequest):
    token = request.token.strip()
    
    # 1. Clear existing environment variables to force the new token's use
    os.environ.pop("HF_TOKEN", None)
    os.environ.pop("HF_HUB_TOKEN", None)

    try:
        from huggingface_hub import login, HfApi
        
        print(f"[HF-Auth] Verifying token: {token[:4]}...{token[-4:] if len(token) > 8 else ''}")
        
        # 2. Manual verification via HfApi to get detailed failure info
        api = HfApi()
        try:
            user_info = api.whoami(token=token)
            print(f"[HF-Auth] Success! Logged in as: {user_info.get('name')} ({user_info.get('type')})")
        except Exception as api_err:
            print(f"[HF-Auth] HfApi.whoami failed: {api_err}")
            raise HTTPException(status_code=400, detail=f"Invalid Token: {str(api_err)}")

        # 3. Synchronize with the official login utility
        login(token=token)
        
        # 4. Persist
        dotenv_file = find_dotenv()
        if not dotenv_file:
            dotenv_file = os.path.join(os.path.dirname(__file__), "..", ".env")
            if not os.path.exists(dotenv_file):
                with open(dotenv_file, "w") as f:
                    f.write("")

        set_key(dotenv_file, "HF_TOKEN", token)
        os.environ["HF_TOKEN"] = token
        os.environ["HF_HUB_TOKEN"] = token
        
        return {
            "status": "success", 
            "message": f"Successfully authenticated as {user_info.get('name') or 'User'}!"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[HF-Auth] Unexpected Error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication Error: {str(e)}")

@router.get("/hf-token")
def get_hf_token():
    token = os.getenv("HF_TOKEN", "")
    return {"token": token, "is_set": bool(token)}


class NetworkMountRequest(BaseModel):
    share_path: str
    username: str = ""
    password: str = ""


@router.get("/network-mount")
def get_network_mounts():
    return network_manager.get_mounts()

@router.post("/network-mount")
def mount_network(request: NetworkMountRequest):
    try:
        result = network_manager.mount_share(request.share_path, request.username, request.password)
        if isinstance(result, str):
            return {"status": "success", "message": f"Mounted securely to {result}! You can now browse via this path."}
        return {"status": "success", "message": "Windows Session explicitly authenticated! You can now browse your mapped network drives securely."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/network-mount")
def unmount_network(share_path: str):
    if not share_path:
        raise HTTPException(status_code=400, detail="Share path is required")
    network_manager.unmount_share(share_path)
    return {"status": "success"}

import sys
import subprocess
import threading
import time

def restart_server():
    # Allow the HTTP response to reach the frontend before we die
    time.sleep(1.0)
    print("RESTARTING SERVER INITIATED BY GUI...", flush=True)

    # Build the restart command using `python -m uvicorn` so it works correctly
    # inside a virtualenv on Windows (os.execv fails because the venv uvicorn
    # launcher is a script wrapper, not a .py file that Python can exec directly).
    # Re-use the same arguments that were originally passed (host, port, app, etc.)
    cmd = [sys.executable, "-m", "uvicorn"] + sys.argv[1:]
    print(f"Launch command: {' '.join(cmd)}", flush=True)

    # Spawn the new server process detached before this one exits
    subprocess.Popen(cmd, cwd=os.getcwd())

    # Terminate the current process after the new one is spawned
    os._exit(0)

@router.post("/restart")
def restart_application():
    threading.Thread(target=restart_server, daemon=True).start()
    return {"status": "success", "message": "Rebooting the internal API natively..."}
