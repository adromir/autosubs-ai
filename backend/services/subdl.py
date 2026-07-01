import requests
import os
import time
import zipfile
import logging
import shutil
from typing import List, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

class SubDLClient:
    # Migrated to v2 API for subtitles search
    API_URL = "https://api.subdl.com/api/v2/subtitles/search"
    DOWNLOAD_BASE = "https://dl.subdl.com"
    # Same safety throttle as SubSource
    MIN_REQUEST_INTERVAL = 1.2

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.last_request_time = 0

    def _throttle(self):
        """Ensures a minimum interval between requests (throttling)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def search_subtitles(self, title: str, languages: str, year: Optional[int] = None, imdb_id: Optional[str] = None) -> List[Dict]:
        """Searches for subtitles using the SubDL API."""
        self._throttle()
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        params = {
            "languages": languages,
            "type": "movie",
            "unpack": 1
        }
        if imdb_id:
            params["imdb_id"] = imdb_id
        else:
            params["film_name"] = title
            if year:
                params["year"] = year

        try:
            # Construct full URL for debugging/logging
            query_url = f"{self.API_URL}?" + "&".join([f"{k}={v}" for k,v in params.items()])
            print(f"[SubDL] Search Query: {query_url}")
            
            resp = requests.get(self.API_URL, params=params, headers=headers, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            if "results" in data and data["results"]:
                return data["results"]
            elif data.get("status") and data.get("subtitles"):
                return data["subtitles"]
            return []
        except Exception as e:
            logger.error(f"[SubDL] Search failed: {e}")
            return []

    def download_and_extract(self, download_url: str, output_path: str) -> bool:
        """Downloads the file and extracts the first .srt if it's a ZIP."""
        self._throttle()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # SubDL v2 returns nId which must be used for downloads, or relative URLs.
        full_url = str(download_url)
        if not full_url.startswith("http") and not full_url.startswith("/"):
            # Treat as v2 nId
            full_url = f"https://api.subdl.com/api/v2/subtitles/{full_url}/download"
        elif full_url.startswith('/'):
            # Legacy fallback
            full_url = f"{self.DOWNLOAD_BASE}{full_url}"
            
        print(f"[SubDL] Final Download URL: {full_url}")
        temp_file = f"{output_path}.tmp"
        try:
            # Download the file
            resp = requests.get(full_url, headers=headers, timeout=25, stream=True)
            resp.raise_for_status()
            with open(temp_file, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Check if it's a zip file
            if zipfile.is_zipfile(temp_file):
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    # Find the first .srt file or .ass file
                    srt_files = [f for f in zip_ref.namelist() if f.lower().endswith('.srt') or f.lower().endswith('.ass')]
                    if not srt_files:
                        logger.error("[SubDL] No .srt/.ass files found in the ZIP")
                        return False
                    
                    # Extract the first one
                    best_match = srt_files[0]
                    with zip_ref.open(best_match) as source, open(output_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
            else:
                # Direct move if it's already an srt
                os.replace(temp_file, output_path)
            
            return True
        except Exception as e:
            logger.error(f"[SubDL] Download/Extract failed: {e}")
            return False
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
