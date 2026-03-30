import os
import shutil
from pathlib import Path
from typing import List, Dict

class ModelManager:
    def __init__(self, model_dir: str, nllb_dir: str):
        self.model_dir = Path(model_dir)
        self.nllb_dir = Path(nllb_dir)

    def _get_dir_size(self, path: Path) -> int:
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_dir_size(Path(entry.path))
        except Exception:
            pass
        return total

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes == 0: return "0 B"
        s = ("B", "KB", "MB", "GB", "TB")
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        r = round(size_bytes / p, 2)
        return f"{r} {s[i]}"

    def list_models(self) -> List[Dict]:
        models = []
        
        # 1. Scan Main Model Dir (Faster-Whisper, GGUFs, HF Cache)
        if self.model_dir.exists():
            for item in self.model_dir.iterdir():
                # Ignore hidden files/folders
                if item.name.startswith("."): continue
                
                # Check for GGUF files
                if item.is_file() and item.suffix.lower() == ".gguf":
                    models.append({
                        "id": item.name,
                        "name": item.name,
                        "type": "LLM (GGUF)",
                        "size": self._format_size(item.stat().st_size),
                        "size_bytes": item.stat().st_size,
                        "path": str(item),
                        "is_dir": False
                    })
                
                # Check for HF Hub model directories (models--*)
                elif item.is_dir() and item.name.startswith("models--"):
                    size = self._get_dir_size(item)
                    # Clean up name: models--Systran--faster-whisper-medium -> Systran/faster-whisper-medium
                    display_name = item.name.replace("models--", "").replace("--", "/")
                    
                    m_type = "Whisper/STT"
                    if "nllb" in item.name.lower(): m_type = "Translation (NLLB)"
                    
                    models.append({
                        "id": item.name,
                        "name": display_name,
                        "type": m_type,
                        "size": self._format_size(size),
                        "size_bytes": size,
                        "path": str(item),
                        "is_dir": True
                    })
                
                # Check for other significant directories (like 'hub' or 'snapshots' if exposed directly)
                elif item.is_dir() and item.name in ["hub", "assets"]:
                    # Usually we want to look INSIDE hub
                    hub_path = item / "models"
                    if hub_path.exists():
                        for sub in hub_path.iterdir():
                            if sub.is_dir():
                                size = self._get_dir_size(sub)
                                models.append({
                                    "id": f"{item.name}/{sub.name}",
                                    "name": sub.name.replace("--", "/"),
                                    "type": "AI Weights",
                                    "size": self._format_size(size),
                                    "size_bytes": size,
                                    "path": str(sub),
                                    "is_dir": True
                                })

        # 2. Scan Dedicated NLLB Dir
        if self.nllb_dir.exists() and self.nllb_dir != self.model_dir:
             for item in self.nllb_dir.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    size = self._get_dir_size(item)
                    models.append({
                        "id": f"nllb-{item.name}",
                        "name": f"NLLB: {item.name}",
                        "type": "Translation",
                        "size": self._format_size(size),
                        "size_bytes": size,
                        "path": str(item),
                        "is_dir": True
                    })

        # Sort by size descending
        return sorted(models, key=lambda x: x["size_bytes"], reverse=True)

    def delete_model(self, path: str) -> bool:
        p = Path(path)
        # Security check: Ensure the path is within our allowed directories
        if not (str(p).startswith(str(self.model_dir)) or str(p).startswith(str(self.nllb_dir))):
            print(f"[ModelManager] Security Alert: Attempted to delete outside allowed path: {path}")
            return False
            
        try:
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(p)
            return True
        except Exception as e:
            print(f"[ModelManager] Deletion failed for {path}: {e}")
            return False

    def wipe_all(self) -> Dict:
        results = {"deleted": [], "failed": []}
        all_models = self.list_models()
        for m in all_models:
            if self.delete_model(m["path"]):
                results["deleted"].append(m["name"])
            else:
                results["failed"].append(m["name"])
        return results
