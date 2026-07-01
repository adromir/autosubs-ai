# Configuration & Settings Guide

AutoSubs AI provides a highly customizable Web GUI. You can tailor exactly how the pipeline operates by adjusting parameters in the **Settings** menu and your **Job Profiles**.

## Global Settings Overview

### Hardware Providers (`Hardware` tab)
Here you can manually override the execution engine AutoSubs AI uses for inference.
- **Auto (Default)**: Highly recommended. It dynamically chooses the best available hardware (e.g., CUDA if NVIDIA is detected, ROCm if AMD is detected, or CPU if neither exist).
- **NVIDIA CUDA**: Forces the use of CUDA.
- **AMD ROCm**: Forces the use of ROCm.
- **CPU Only**: Disables GPU acceleration. This will severely impact performance but guarantees stability if you are experiencing GPU driver crashes.

### Language & Engine Limits (`Limits` tab)
If you only ever process certain languages, you can constrain the UI dropdown menus here.
- **Enabled Languages**: Unchecking languages removes them from the Job Profiles dropdown, keeping your UI clean.
- **Enabled Models**: Disable models you never intend to use (e.g., if you only have 8GB of VRAM, you might want to disable `large-v3` to prevent accidental Out-Of-Memory crashes).

---

## Job Profiles & Parameters

A **Job Profile** defines the exact parameters for a given folder. When you submit a job from the `Dashboard`, you select a Profile.

### Core Parameters
- **Source Language**: The spoken language of the video file.
- **Target Language**: The language you want the final subtitle to be in. If this differs from the Source Language, the Translation phase is triggered.
- **Transcription Model**: The Whisper model size to use (`base`, `small`, `medium`, `large-v3`).
- **Translation Engine**: The engine used if translation is needed (`Native LLM` vs `NLLB`).

### Pipeline Toggles
These settings dictate which steps of the 5-phase pipeline are permitted to run:
- **Enable Extraction**: Allows AutoSubs AI to check the video file (e.g., MKV) and extract pre-existing embedded subtitle tracks.
- **Fetch Internet Subs**: Allows searching external databases (SubSource, SubDL, etc.) for existing subtitles to save time.
  - *Allow Title Match*: If an exact hash match fails, allows matching purely based on the movie/episode title.
  - *Use NFO*: Reads local `.nfo` files created by media managers (like Sonarr/Radarr) to improve fetching accuracy.
  - *Fetch All Available*: Downloads all matches found rather than just the top result.
- **Enable Transcription**: If no subtitle is found via Extraction or Fetching, this allows the Whisper AI to generate one from scratch.

### Subtitle Processing & Synchronization
- **Auto Sync**: Automatically runs fetched or extracted subtitles through FFsubsync and VAD to fix timing offsets against the audio track.
- **Use VAD**: Voice Activity Detection. Helps identify human speech timestamps to ensure silent parts aren't hallucinated by Whisper.
  - *VAD Onset / Offset*: Advanced threshold tuning for when speech is considered to have started or stopped.
- **Deep Cleanup & Cleaning Method**: Instructs the system to scrub downloaded subtitles of spam, URLs, and ads. The `LLM` cleaning method uses Native LLM models for highly intelligent context-aware stripping.
- **Hardcode**: Burns the final subtitle directly into the video file (requires re-encoding).

### File Management
- **Emby Naming**: Forces output subtitles to follow strict Jellyfin/Emby naming conventions (e.g., adding explicit ISO codes to the filename).
- **Auto Janitor**: Automatically deletes intermediate audio extractions and temporary subtitle files after the job completes, saving disk space.
