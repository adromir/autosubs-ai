import os
import subprocess
import logging
from typing import List, Optional, Dict
from pathlib import Path

# Subliminal 2.6.0+ uses babelfish for language management
from babelfish import Language
import subliminal
from subliminal.video import Video, Movie, Episode

import re

# Setup basic logging for subliminal
logging.basicConfig(level=logging.INFO)

import xml.etree.ElementTree as ET
import charset_normalizer

def sanitize_srt(filepath: str):
    """
    Ensures the SRT file is UTF-8 encoded with Unix line endings (\n).
    Useful for preventing decode errors in translation/sync phases.
    """
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Detect encoding using charset_normalizer for high accuracy
        results = charset_normalizer.from_bytes(content)
        best_match = results.best()
        
        if best_match:
            text = str(best_match)
        else:
            # Fallback to latin-1 which is common for legacy subtitles
            text = content.decode('latin-1', errors='replace')
        
        # Security Check: Ensure we don't overwrite if the result is suspiciously small/empty
        if not text.strip() or len(text) < 10:
            print(f"[Sanitize] Warning: Refusing to sanitize suspiciously small file {filepath}")
            return

        # Normalize line endings to \n
        lines = text.splitlines()
        
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
            
        print(f"[Sanitize] Normalized {os.path.basename(filepath)} to UTF-8 (LF)")
    except Exception as e:
        print(f"[Sanitize] Error normalizing {filepath}: {e}")

def _get_imdb_id_from_nfo(video_path: str) -> Optional[str]:
    """
    Precisely extracts the Movie IMDb ID from a .nfo file using an XML parser.
    Fallows a prioritized search: <uniqueid type="imdb"> -> <imdbid> -> Regex fallback.
    """
    try:
        nfo_path = Path(video_path).with_suffix('.nfo')
        print(f"[Fetcher] Checking for NFO at: {nfo_path}")
        
        if not nfo_path.exists():
            # Check for movie.nfo in the same folder as a fallback
            movie_nfo = Path(video_path).parent / "movie.nfo"
            print(f"[Fetcher] NFO not found. Checking fallback: {movie_nfo}")
            if movie_nfo.exists():
                nfo_path = movie_nfo
            else:
                return None
        
        print(f"[Fetcher] Found NFO file. Parsing...")
        # 1. Attempt structured XML parsing for maximum precision
        try:
            tree = ET.parse(str(nfo_path))
            root = tree.getroot()
            
            # Standard: <uniqueid type="imdb" default="true">tt12345</uniqueid>
            # Some NFOs have multiple uniqueids, we find the one with type='imdb'
            unique_ids = root.findall('.//uniqueid')
            for uid in unique_ids:
                if uid.get('type') == 'imdb' and uid.text:
                    imdb_val = uid.text.strip()
                    if imdb_val.startswith('tt'):
                        print(f"[Fetcher] Success: Found <uniqueid type='imdb'>: {imdb_val}")
                        return imdb_val

            # Legacy/Classic: <imdbid>tt12345</imdbid>
            imdbid_tag = root.find('.//imdbid')
            if imdbid_tag is not None and imdbid_tag.text:
                imdb_val = imdbid_tag.text.strip()
                if imdb_val.startswith('tt'):
                    print(f"[Fetcher] Success: Found <imdbid>: {imdb_val}")
                    return imdb_val
                    
        except ET.ParseError as pe:
            # Fallback for malformed XML NFOs (common in some sources)
            print(f"[Fetcher] XML Parse Error ({pe}), falling back to regex...")
            
        # 2. Resilient Regex Fallback
        content = nfo_path.read_text(encoding='utf-8', errors='ignore')
        # We look for the tags specifically to avoid catching actor IDs by accident
        match = re.search(r'<(?:uniqueid|imdbid)[^>]*>(tt\d+)</(?:uniqueid|imdbid)>', content, re.IGNORECASE)
        if match:
            imdb_val = match.group(1)
            print(f"[Fetcher] Success: Found IMDb ID via regex fallback: {imdb_val}")
            return imdb_val

        print(f"[Fetcher] Warning: No IMDb ID found inside NFO content.")
    except Exception as e:
        print(f"[Fetcher] Error reading NFO: {e}")
    return None

def fetch_subtitle(
    video_path: str, 
    language_code: str, 
    providers: List[str], 
    provider_configs: Dict[str, Dict[str, str]],
    allow_title_match: bool = False,
    use_nfo: bool = False
) -> Optional[Dict]:
    """
    Downloads a subtitle for the given video path using Subliminal 2.6.0.
    Returns metadata about the download if successful, else None.
    """
    print(f"[Fetcher] fetch_subtitle called for {os.path.basename(video_path)}. use_nfo={use_nfo}")
    try:
        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            print(f"[Fetcher] Error: Video file not found at {video_path}")
            return None

        # 1. Scan the video file to extract metadata (including hash/checksum)
        # We also attempt NFO extraction if enabled
        imdb_id = _get_imdb_id_from_nfo(video_path) if use_nfo else None
        
        video = subliminal.scan_video(str(video_path_obj))
        if imdb_id:
            # Inject IMDb ID into video object metadata so subliminal providers can use it
            if isinstance(video, Movie):
                video.imdb_id = imdb_id
            elif isinstance(video, Episode):
                # Episodes usually use show IMDB ID, or we keep it as a fallback
                video.series_imdb_id = imdb_id
        
        # 2. Convert language code to Babelfish Language
        target_lang = Language.fromalpha2(language_code)
        
        # 3. Filter providers to only those currently supported by the installed subliminal version
        available_names = set(subliminal.provider_manager.names())
        
        # Identify custom providers (not in subliminal)
        custom_providers = []
        subliminal_providers = []
        custom_registry = {"subsource", "subdl"}
        
        for p in providers:
            if p in custom_registry:
                custom_providers.append(p)
            elif p in available_names:
                subliminal_providers.append(p)
            else:
                print(f"[Fetcher] Skipping completely unknown provider: {p}")

        # Try to extract the best possible "clean" title for custom providers
        # If subliminal already identified a title (Movie/Show), use that.
        # Otherwise fallback to filename manipulation.
        movie_title = getattr(video, 'title', None)
        if not movie_title:
             # Fallback if title is missing from subliminal scan: try to strip (year) or [extra]
             movie_title = os.path.basename(video_path).split(' (')[0].split(' [')[0]
             # For MKV/MP4 files, remove the extension if it's still there
             movie_title = os.path.splitext(movie_title)[0]
        
        # Sanitize for Custom Providers (Remove special chars that might cause 400/Bad Request)
        import re
        search_title = re.sub(r'[^a-zA-Z0-9\s]', ' ', movie_title)
        search_title = ' '.join(search_title.split()) # Collapse extra spaces
        
        movie_year = getattr(video, 'year', None)

        # 4. Handle custom providers FIRST if they are prioritized
        # (This follows the user's ordered list)
        for p_id in providers:
            if p_id == "subsource" and p_id in custom_providers:
                config = provider_configs.get("subsource", {})
                api_key = config.get("api_key")
                if not api_key:
                    print("[Fetcher] Skipping SubSource: No API Key provided")
                    continue
                
                print(f"[Fetcher] Searching SubSource for {language_code} (IMDb: {imdb_id})...")
                from services.subsource import SubSourceClient
                ss_client = SubSourceClient(api_key)
                
                ss_movie_id = ss_client.search_movie(search_title, year=movie_year, imdb_id=imdb_id)
                if ss_movie_id:
                    ss_subs = ss_client.get_subtitles(ss_movie_id, language_code)
                    if ss_subs:
                        best_ss = ss_subs[0]
                        # Use new naming convention: moviename.langCODE.srt
                        full_lang = f"{language_code}_{language_code.upper()}"
                        video_stem = Path(video_path).stem
                        output_path = str(Path(video_path).parent / f"{video_stem}.{full_lang}.srt")
                        
                        if ss_client.download_subtitle(best_ss['subtitleId'], output_path):
                            print(f"[Fetcher] SubSource download successful: {best_ss['subtitleId']}")
                            # Sanitize to UTF-8
                            sanitize_srt(output_path)
                            return {
                                "path": output_path,
                                "provider": "subsource",
                                "score": 100,
                                "is_hash_match": False
                            }
                print("[Fetcher] SubSource search returned no results.")

            elif p_id == "subdl" and p_id in custom_providers:
                config = provider_configs.get("subdl", {})
                api_key = config.get("api_key")
                if not api_key:
                    print("[Fetcher] Skipping SubDL: No API Key provided")
                    continue
                
                print(f"[Fetcher] Searching SubDL for {language_code} (IMDb: {imdb_id})...")
                from services.subdl import SubDLClient
                subdl_client = SubDLClient(api_key)
                
                subdl_list = subdl_client.search_subtitles(search_title, languages=language_code, year=movie_year, imdb_id=imdb_id)
                if subdl_list:
                    # Best match from the list
                    # SubDL gives us a relative or full download URL in the 'url' field.
                    best_subdl = subdl_list[0]
                    dl_url = best_subdl.get('url')
                    if dl_url:
                        full_lang = f"{language_code}_{language_code.upper()}"
                        video_stem = Path(video_path).stem
                        output_path = str(Path(video_path).parent / f"{video_stem}.{full_lang}.srt")
                        
                        if subdl_client.download_and_extract(dl_url, output_path):
                            print(f"[Fetcher] SubDL download + extraction successful")
                            # Sanitize to UTF-8
                            sanitize_srt(output_path)
                            return {
                                "path": output_path,
                                "provider": "subdl",
                                "score": 100,
                                "is_hash_match": False
                            }
                print("[Fetcher] SubDL search returned no results.")

        # 5. Attempt to download the single best subtitle from Subliminal-supported providers
        if not subliminal_providers:
            print("[Fetcher] No valid Subliminal providers left to search.")
            return None

        print(f"[Fetcher] Searching Subliminal for {language_code} via {len(subliminal_providers)} providers...")
        downloaded = subliminal.download_best_subtitles(
            [video], 
            {target_lang}, 
            providers=subliminal_providers,
            provider_configs=provider_configs,
            only_one=True,
            min_score=video.hashes.get('opensubtitles', 0) if not allow_title_match else 0
        )

        if downloaded and video in downloaded and downloaded[video]:
            sub = downloaded[video][0]
            
            full_lang = f"{language_code}_{language_code.upper()}"
            video_stem = Path(video_path).stem
            output_path = str(Path(video_path).parent / f"{video_stem}.{full_lang}.srt")
            
            # Subliminal downloads the content into the Subtitle object. We need to save it.
            # Usually download_best_subtitles saves them if we don't handle it.
            # We want to force the specific name.
            with open(output_path, 'wb') as f:
                f.write(sub.content)
            
            # Sanitize to UTF-8
            sanitize_srt(output_path)
            
            return {
                "path": output_path,
                "provider": sub.provider_name,
                "score": sub.compute_score(video),
                "is_hash_match": sub.compute_score(video) >= video.scores['hash']
            }
            
        print(f"[Fetcher] No subtitle found for {video_path}")
        return None
        
    except Exception as e:
        print(f"[Fetcher] Unexpected exception: {e}")
        import traceback
        traceback.print_exc()
        return None

def fetch_all_subtitles(
    video_path: str, 
    target_languages: List[str], 
    providers: List[str], 
    provider_configs: Dict[str, Dict[str, str]],
    allow_title_match: bool = False,
    use_nfo: bool = False,
    deep_cleanup: bool = True
) -> List[Dict]:
    """
    Attempts to download subtitles for EVERY target language in the list.
    Returns a list of metadata for all successfully downloaded subtitles.
    """
    from services.subtitle_processor import sanitize_and_refine
    results = []
    video_path_obj = Path(video_path)
    
    # 1. Prepare video metadata once
    imdb_id = _get_imdb_id_from_nfo(video_path) if use_nfo else None
    video = subliminal.scan_video(str(video_path_obj))
    if imdb_id:
        if isinstance(video, Movie): video.imdb_id = imdb_id
        elif isinstance(video, Episode): video.series_imdb_id = imdb_id

    movie_title = getattr(video, 'title', None)
    if not movie_title:
         movie_title = os.path.splitext(os.path.basename(video_path).split(' (')[0].split(' [')[0])[0]
    
    import re
    search_title = re.sub(r'[^a-zA-Z0-9\s]', ' ', movie_title)
    search_title = ' '.join(search_title.split())
    movie_year = getattr(video, 'year', None)

    # 2. Pre-search movie IDs for bulk-enabled providers
    movie_ids = {}
    if "subsource" in providers:
        config = provider_configs.get("subsource", {})
        if config.get("api_key"):
            from services.subsource import SubSourceClient
            ss_client = SubSourceClient(config["api_key"])
            movie_ids["subsource"] = ss_client.search_movie(search_title, year=movie_year, imdb_id=imdb_id)
            
    if "subdl" in providers:
        config = provider_configs.get("subdl", {})
        if config.get("api_key"):
            from services.subdl import SubDLClient
            subdl_client = SubDLClient(config["api_key"])
            # We search once with empty language to potentially get more results or verify movie existence
            # SubDL: fetch_all_subtitles can be optimized by fetching alllangs in one query if the API supports comma-sep
            # but we'll stick to our cached search for now.
            movie_ids["subdl"] = True # SubDL doesn't have a separate 'search_movie' ID step in our client, it's combined.

    # 3. Loop through each language
    for lang_code in target_languages:
        print(f"[Fetcher] Bulk-fetch attempting: {lang_code}")
        found = False
        target_lang = Language.fromalpha2(lang_code)

        for p_id in providers:
            if p_id == "subsource" and movie_ids.get("subsource"):
                from services.subsource import SubSourceClient
                ss_client = SubSourceClient(provider_configs["subsource"]["api_key"])
                ss_subs = ss_client.get_subtitles(movie_ids["subsource"], lang_code)
                if ss_subs:
                    output_path = _get_output_path(video_path, lang_code)
                    if ss_client.download_subtitle(ss_subs[0]['subtitleId'], output_path):
                        sanitize_and_refine(output_path, deep_cleanup=deep_cleanup)
                        results.append({"path": output_path, "provider": "subsource", "lang": lang_code})
                        found = True; break
            
            elif p_id == "subdl":
                from services.subdl import SubDLClient
                subdl_client = SubDLClient(provider_configs["subdl"]["api_key"])
                # Request specifically for this language
                subdl_list = subdl_client.search_subtitles(search_title, languages=lang_code, year=movie_year, imdb_id=imdb_id)
                if subdl_list:
                    dl_url = subdl_list[0].get('url')
                    if dl_url:
                        output_path = _get_output_path(video_path, lang_code)
                        if subdl_client.download_and_extract(dl_url, output_path):
                            sanitize_and_refine(output_path, deep_cleanup=deep_cleanup)
                            results.append({"path": output_path, "provider": "subdl", "lang": lang_code})
                            found = True; break
        
        if found: continue

        # Final fallback: Subliminal
        sub_providers = [p for p in providers if p not in ["subsource", "subdl"] and p in subliminal.provider_manager.names()]
        if sub_providers:
            downloaded = subliminal.download_best_subtitles([video], {target_lang}, providers=sub_providers, provider_configs=provider_configs, only_one=True)
            if downloaded and video in downloaded and downloaded[video]:
                sub = downloaded[video][0]
                output_path = _get_output_path(video_path, lang_code)
                with open(output_path, 'wb') as f: f.write(sub.content)
                sanitize_and_refine(output_path, deep_cleanup=deep_cleanup)
                results.append({"path": output_path, "provider": sub.provider_name, "lang": lang_code})

    return results

def _get_output_path(video_path: str, lang_code: str) -> str:
    full_lang = f"{lang_code}_{lang_code.upper()}"
    video_stem = Path(video_path).stem
    return str(Path(video_path).parent / f"{video_stem}.{full_lang}.srt")

def sync_subtitle(video_path: str, subtitle_path: str, audio_stream_index: Optional[int] = None, vad_engine: str = "silero") -> bool:
    """
    Syncs a subtitle file to a video file using ffsubsync.
    Overwrites the subtitle_path with the synced version.
    """
    try:
        from services.subtitle_processor import sanitize_and_refine
        # ffsubsync has its own specific list of supported VADs
        supported_vads = {"subs_then_webrtc", "webrtc", "subs_then_auditok", "auditok", "subs_then_silero", "silero"}
        ff_vad = vad_engine if vad_engine in supported_vads else "subs_then_webrtc"
        
        if ff_vad == "silero" or ff_vad == "subs_then_silero":
            ff_vad = "subs_then_webrtc"

        print(f"[Sync] Attempting FFsubsync for {os.path.basename(subtitle_path)} (Using VAD: {ff_vad})...")
        temp_out = f"{subtitle_path}.synced.srt"
        
        cmd = [
            "ffsubsync", 
            video_path, 
            "-i", subtitle_path, 
            "-o", temp_out,
            "--encoding", "utf-8",
            "--vad", ff_vad
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(temp_out):
            os.replace(temp_out, subtitle_path)
            print(f"[Sync] FFsubsync successful for {os.path.basename(subtitle_path)}")
            # Refine again after sync to be safe
            sanitize_and_refine(subtitle_path)
            return True
        else:
            print(f"[Sync] FFsubsync failed: {result.stderr}")
            if os.path.exists(temp_out):
                os.remove(temp_out)
            return False
            
    except Exception as e:
        print(f"[Sync] Error running ffsubsync: {e}")
        return False
