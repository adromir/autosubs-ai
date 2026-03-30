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
        self.custom_models = self._load_custom_models()
        self.api = HfApi()
        
        # Curated list of recommended translation models (GGUF)
        self.RECOMMENDED_MODELS = [
            {
                "id": "llama-3-8b-instruct",
                "name": "Meta Llama 3 (8B Instruct)",
                "repo": "MaziyarPanahi/Meta-Llama-3-8B-Instruct-GGUF",
                "file": "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
                "size": "4.9 GB",
                "description": "State-of-the-art general purpose model. Excellent for translation."
            },
            {
                "id": "phi-3-mini-4k",
                "name": "Phi-3 Mini (3.8B)",
                "repo": "microsoft/Phi-3-mini-4k-instruct-gguf",
                "file": "Phi-3-mini-4k-instruct-q4.gguf",
                "size": "2.4 GB",
                "description": "Fast and efficient. Ideal for lower VRAM cards."
            },
            {
                "id": "gemma-2-9b",
                "name": "Google Gemma 2 (9B)",
                "repo": "google/gemma-2-9b-it-GGUF",
                "file": "gemma-2-9b-it-Q4_K_M.gguf",
                "size": "5.4 GB",
                "description": "Latest Google model. Very high translation quality."
            },
            {
                "id": "qwen-3.5-9b",
                "name": "Alibaba Qwen 3.5 (9B)",
                "repo": "bartowski/Qwen_Qwen3.5-9B-GGUF",
                "file": "Qwen_Qwen3.5-9B-Q4_K_M.gguf",
                "size": "5.6 GB",
                "description": "Superior translation for Qwen series, high-performance 9B model."
            }
        ]

    def _load_custom_models(self) -> List[Dict]:
        if not self.config_path.exists():
            return []
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                return config.get("custom_llm_models", [])
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
        all_models = self.RECOMMENDED_MODELS + self.custom_models
        for model in all_models:
            m = model.copy()
            m["is_downloaded"] = m["file"] in local_files
            m["progress"] = self.downloads.get(m["id"], 100.0 if m["is_downloaded"] else 0.0)
            results.append(m)
        return results

    def start_download(self, model_id: str):
        """Start a background thread to download a model from HuggingFace."""
        all_models = self.RECOMMENDED_MODELS + self.custom_models
        model = next((m for m in all_models if m["id"] == model_id), None)
        if not model or model["id"] in self.downloads:
            return False

        def download_worker():
            try:
                self.downloads[model_id] = 0.1
                # Use HF-Transfer if available (set by env in install_deps)
                hf_hub_download(
                    repo_id=model["repo"],
                    filename=model["file"],
                    local_dir=str(self.cache_dir),
                    local_dir_use_symlinks=False
                )
                self.downloads[model_id] = 100.0
            except Exception as e:
                print(f"Download failed for {model_id}: {e}")
                self.downloads.pop(model_id, None)

        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()
        return True

    def get_download_status(self, model_id: str) -> float:
        return self.downloads.get(model_id, 0.0)

# Instantiate as singleton for the backend
llm_manager = None

def init_llm_manager(cache_dir: str):
    global llm_manager
    llm_manager = LLMManager(cache_dir)
