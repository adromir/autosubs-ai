import time
import requests
import os
import logging
import zipfile
import shutil
from typing import List, Optional, Dict
from pathlib import Path
from babelfish import Language

logger = logging.getLogger(__name__)

class SubSourceClient:
    BASE_URL = "https://api.subsource.net/api/v1"
    # Rate limits: 60/min, 1800/hour, 7200/day
    # Minimum delay between requests to stay safe (1.2s = ~50 requests/min)
    MIN_REQUEST_INTERVAL = 1.2 

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        self.last_request_time = 0

    def _throttle(self):
        """Ensures a minimum interval between requests (throttling)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def search_movie(self, title: str, year: Optional[int] = None, imdb_id: Optional[str] = None) -> Optional[str]:
        """Searches for a movie/show and returns the SubSource ID."""
        self._throttle()
        url = f"{self.BASE_URL}/movies/search"
        
        # Method: GET (as POST is not supported by the endpoint)
        # Observed Parameters: imdb (for ID), query (for title)
        params = {
            "api_key": self.api_key,
            "type": "movie"
        }
        
        if imdb_id:
            params["imdb"] = imdb_id
            params["searchType"] = "imdb"
        else:
            params["q"] = title
            params["searchType"] = "text"
            
        try:
            print(f"[SubSource] GET Search Request: {url} | Params: {params}")
            
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 429:
                logger.warning("[SubSource] Rate limited")
                return None
                
            resp.raise_for_status()
            data = resp.json()
            
            # SubSource returns a list of results under the 'data' key.
            results = data.get("data", [])
            if not results:
                return None
                
            # Try to find the best match. 
            for movie in results:
                m_id = str(movie.get("movieId") or movie.get("id") or "")
                if not m_id:
                    continue
                    
                # If a year was provided, try to match it
                m_year = movie.get("releaseYear") or movie.get("year")
                if year and m_year == year:
                    return m_id
                    
                # If no year was provided or it's the first result, return it as a fallback
                if not year:
                    return m_id
            
            # Fallback to first valid ID if no year match was found
            if results:
                return str(results[0].get("movieId") or results[0].get("id"))
            
            return None
            
        except Exception as e:
            logger.error(f"[SubSource] Search failed: {e}")
            return None

    def get_subtitles(self, movie_id: str, lang_code_alpha2: str) -> List[Dict]:
        """Lists available subtitles for a movie ID and language."""
        self._throttle()
        url = f"{self.BASE_URL}/subtitles"
        
        # SubSource requires the full language name (e.g., "english", "german")
        try:
            full_language_name = Language.fromalpha2(lang_code_alpha2).name.lower()
        except Exception:
            # Fallback if babelfish fails or code is non-standard
            mapping = {"en": "english", "de": "german", "es": "spanish", "fr": "french"}
            full_language_name = mapping.get(lang_code_alpha2, lang_code_alpha2)
            
        params = {"movieId": movie_id, "language": full_language_name, "api_key": self.api_key}
        
        try:
            query_url = f"{url}?" + "&".join([f"{k}={v}" for k,v in params.items()])
            print(f"[SubSource] Listing Query: {query_url}")
            
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            resp.raise_for_status()
            # SubSource returns subtitles under the 'data' key.
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"[SubSource] Listing subtitles failed: {e}")
            return []

    def download_subtitle(self, sub_id: str, output_path: str) -> bool:
        """Downloads the actual subtitle file, handling ZIP extraction if necessary."""
        self._throttle()
        url = f"{self.BASE_URL}/subtitles/{sub_id}/download"
        print(f"[SubSource] Final Download URL: {url}")
        
        temp_file = f"{output_path}.tmp"
        try:
            resp = requests.get(url, headers=self.headers, timeout=20, stream=True)
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
                        logger.error("[SubSource] No .srt/.ass files found in the ZIP")
                        return False
                    
                    # Extract the first one
                    best_match = srt_files[0]
                    with zip_ref.open(best_match) as source, open(output_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                        print(f"[SubSource] Extracted {best_match} from archive.")
            else:
                # Direct move if it's already an srt
                os.replace(temp_file, output_path)
            
            return True
        except Exception as e:
            logger.error(f"[SubSource] Download failed: {e}")
            return False
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
