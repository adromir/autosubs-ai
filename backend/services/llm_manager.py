import os
import json
import threading
from pathlib import Path
from typing import List, Dict, Optional
from huggingface_hub import hf_hub_download, HfApi

class LLMManager:
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.cache_dir.parent / "config.json"
        self.downloads = {}  # Track progress {model_id: progress_float}
        self.download_processes = {} # Track subprocesses {model_id: Popen}
        self.custom_models = self._load_custom_models()
        self.api = HfApi()
        

    def _load_available_models(self) -> Dict:
        models_file = Path(__file__).parent.parent / "data" / "available_models.json"
        
        if models_file.exists():
            try:
                with open(models_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[LLM Manager] Error reading {models_file}: {e}")
                return {"whisper_models": [], "llm_models": []}
        else:
            print(f"[LLM Manager] Warning: {models_file} not found.")
            return {"whisper_models": [], "llm_models": []}

    def _load_custom_models(self) -> List[Dict]:
        if not self.config_path.exists():
            return []
        try:
            with open(self.config_path, "r") as f:
                return json.load(f).get("custom_llm_models", [])
        except:
            return []

    def _save_custom_models(self):
        config = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    config = json.load(f)
            except:
                pass
        
        config["custom_llm_models"] = self.custom_models
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)

    def scan_remote_repo(self, repo_id: str) -> List[str]:
        """List all .gguf files in a HuggingFace repository."""
        try:
            files = self.api.list_repo_files(repo_id)
            return [f for f in files if f.endswith(".gguf")]
        except Exception as e:
            print(f"Error scanning repo {repo_id}: {e}")
            return []

    def register_custom_model(self, repo: str, file: str, name: Optional[str] = None):
        """Add a custom model repo/file pair to the persistent registry."""
        model_id = f"custom-{repo.replace('/', '-')}-{file}"
        # Check for existing
        if any(m["id"] == model_id for m in self.custom_models):
            return model_id
        
        new_model = {
            "id": model_id,
            "name": name or f"Custom: {file}",
            "repo": repo,
            "file": file,
            "size": "Unknown",
            "description": f"Custom model from {repo}",
            "is_custom": True
        }
        self.custom_models.append(new_model)
        self._save_custom_models()
        return model_id

    def get_local_models(self) -> List[str]:
        """Scan the cache directory for .gguf files."""
        if not self.cache_dir.exists():
            return []
        return [f.name for f in self.cache_dir.glob("*.gguf")]

    def get_recommended_models(self) -> List[Dict]:
        """Return both curated and custom lists with current status."""
        local_files = self.get_local_models()
        results = []
        # Merge Curated + Custom
        all_models = self._load_available_models().get("llm_models", []) + self.custom_models
        for model in all_models:
            m = model.copy()
            m["is_downloaded"] = m["file"] in local_files
            m["progress"] = self.downloads.get(m["id"], 100.0 if m["is_downloaded"] else 0.0)
            results.append(m)
        return results

    def start_download(self, model_id: str):
        """Start a background process to download a model from HuggingFace."""
        all_models = self._load_available_models().get("llm_models", []) + self.custom_models
        model = next((m for m in all_models if m["id"] == model_id), None)
        if not model or model["id"] in self.downloads:
            return False

        def download_worker():
            try:
                self.downloads[model_id] = 0.1
                import subprocess
                import sys
                
                env = os.environ.copy()
                env["HF_XET_HIGH_PERFORMANCE"] = "1"
                env["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
                env["HF_HUB_CACHE"] = str(os.path.join(self.cache_dir, ".cache"))
                
                # Clean up stale locks to prevent the downloader from deadlocking
                import glob
                lock_dir = os.path.join(self.cache_dir, ".cache", "huggingface", "download")
                if os.path.exists(lock_dir):
                    for lock_file in glob.glob(os.path.join(lock_dir, "*.lock")):
                        try: os.remove(lock_file)
                        except: pass
                
                hf_bin = os.path.join(os.path.dirname(sys.executable), "huggingface-cli")
                if os.name == "nt": hf_bin += ".exe"
                
                cmd = [
                    hf_bin, "download", model["repo"],
                    "--local-dir", str(self.cache_dir),
                    "--include", model["file"], "*mmproj-F16*", "mtp-*", "*UD-Q4_K_XL*"
                ]
                
                process = subprocess.Popen(cmd, env=env)
                self.download_processes[model_id] = process
                
                process.wait()
                if process.returncode == 0:
                    self.downloads[model_id] = 100.0
                else:
                    print(f"Download failed with exit code {process.returncode}")
                    self.downloads.pop(model_id, None)
                    
            except Exception as e:
                print(f"Download failed for {model_id}: {e}")
                self.downloads.pop(model_id, None)
            finally:
                self.download_processes.pop(model_id, None)

        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()
        return True

    def cancel_download(self, model_id: str):
        """Cancel an ongoing download."""
        if model_id in self.download_processes:
            try:
                self.download_processes[model_id].terminate()
            except:
                pass
            self.download_processes.pop(model_id, None)
        self.downloads.pop(model_id, None)
        return True

    def get_download_status(self, model_id: str) -> float:
        return self.downloads.get(model_id, 0.0)

# Instantiate as singleton for the backend
llm_manager = None

def init_llm_manager(cache_dir: str):
    global llm_manager
    llm_manager = LLMManager(cache_dir)
