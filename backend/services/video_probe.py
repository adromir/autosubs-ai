import time
import ffmpeg
from pydantic import BaseModel
from typing import List, Optional
from collections import OrderedDict

class TrackInfo(BaseModel):
    index: int
    codec_name: str
    language: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[float] = None

class MediaInfo(BaseModel):
    filepath: str
    duration: float
    audio_tracks: List[TrackInfo]
    subtitle_tracks: List[TrackInfo]

ISO639_MAP = {
    "eng": "en", "en": "en",
    "ger": "de", "deu": "de", "de": "de",
    "spa": "es", "es": "es",
    "fra": "fr", "fre": "fr", "fr": "fr",
    "ita": "it", "it": "it",
    "por": "pt", "pt": "pt",
    "nld": "nl", "dut": "nl", "nl": "nl",
    "rus": "ru", "ru": "ru",
    "jpn": "ja", "ja": "ja",
    "zho": "zh", "chi": "zh", "zh": "zh",
    "kor": "ko", "ko": "ko",
    "pol": "pl", "pl": "pl",
    "tur": "tr", "tr": "tr",
    "ind": "id", "id": "id",
    "hin": "hi", "hi": "hi",
    "ara": "ar", "ar": "ar",
    "swe": "sv", "sv": "sv",
    "dan": "da", "da": "da",
    "fin": "fi", "fi": "fi",
    "nor": "no", "no": "no",
    "ces": "cs", "cze": "cs", "cs": "cs",
    "ell": "el", "gre": "el", "el": "el",
    "hun": "hu", "hu": "hu",
    "ron": "ro", "rum": "ro", "ro": "ro"
}

# Fix #9: Capped LRU probe cache — prevents unbounded memory growth on long-running servers.
# Oldest entries are evicted when the cap is reached; stale entries expire after 1 hour on read.
_PROBE_CACHE_MAX = 256
_probe_cache: OrderedDict = OrderedDict()

def probe_video(filepath: str, ignore_forced_subs: bool = True) -> MediaInfo:
    cache_key = (filepath, ignore_forced_subs)
    
    if cache_key in _probe_cache:
        entry_time, data = _probe_cache[cache_key]
        if time.time() - entry_time < 3600:  # 1 hour TTL
            # Move to end to mark as recently used (LRU order)
            _probe_cache.move_to_end(cache_key)
            print(f"[Efficiency] FFprobe Memory Cache HIT for: {filepath.split('/')[-1].split(chr(92))[-1]}")
            return data
        else:
            # TTL expired — remove stale entry
            del _probe_cache[cache_key]
            
    print(f"[Efficiency] FFprobe Network/Disk Scanning: {filepath.split('/')[-1].split(chr(92))[-1]}")
    try:
        probe = ffmpeg.probe(filepath)
    except ffmpeg.Error as e:
        print(f"ffprobe error: {e.stderr.decode('utf8') if e.stderr else str(e)}")
        raise RuntimeError(f"Failed to probe {filepath}")

    audio_tracks = []
    subtitle_tracks = []

    for stream in probe.get('streams', []):
        codec_type = stream.get('codec_type')
        if codec_type not in ['audio', 'subtitle']:
            continue
            
        tags = stream.get('tags', {})
        raw_lang = tags.get('language')
        mapped_lang = ISO639_MAP.get(raw_lang.lower(), raw_lang) if raw_lang else None

        track = TrackInfo(
            index=stream.get('index'),
            codec_name=stream.get('codec_name', 'unknown'),
            language=mapped_lang,
            title=tags.get('title')
        )
        
        if codec_type == 'audio':
            audio_tracks.append(track)
        elif codec_type == 'subtitle':
            if track.codec_name.lower() in ['hdmv_pgs_subtitle', 'dvd_subtitle', 'dvdsub', 'pgssub', 'dvbsub']:
                continue
                
            disposition = stream.get('disposition', {})
            tags = stream.get('tags', {})
            title = tags.get('title', '').lower()
            
            if ignore_forced_subs:
                is_explicitly_forced = disposition.get('forced', 0) == 1
                has_forced_in_title = 'forced' in title
                
                if is_explicitly_forced or has_forced_in_title:
                    print(f"Skipping native subtitle track {track.index} ({track.language}) because it is 'Forced'.")
                    continue
                
            subtitle_tracks.append(track)

    # Get global duration
    try:
        duration = float(probe.get('format', {}).get('duration', 0.0))
    except (ValueError, TypeError):
        duration = 0.0
        
    media_info = MediaInfo(
        filepath=filepath,
        duration=duration,
        audio_tracks=audio_tracks,
        subtitle_tracks=subtitle_tracks
    )
    
    # Evict oldest entry if cache is full
    if len(_probe_cache) >= _PROBE_CACHE_MAX:
        _probe_cache.popitem(last=False)
    
    _probe_cache[cache_key] = (time.time(), media_info)
    return media_info
