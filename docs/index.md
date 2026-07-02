# Welcome to the AutoSubs AI Wiki

![Dashboard](assets/dashboard.png)

AutoSubs AI is an intelligent, hardware-accelerated subtitle orchestration pipeline designed to solve every subtitle problem autonomously. This Wiki serves as the definitive guide to understanding what it does, how to use it, and how to fine-tune its capabilities.

## What Can It Do?

Managing subtitles for large media libraries (like Plex, Jellyfin, or Emby) can be incredibly tedious. Sometimes subtitles don't exist, sometimes they are out of sync, and sometimes they are in the wrong language. AutoSubs AI automates this entire process with a 5-phase pipeline.

### The 5-Phase Pipeline Explained

When you submit a video to AutoSubs AI, it intelligently runs through the following workflow:

#### 1. 📂 Extraction (Zero AI Overhead)
Before burning expensive GPU cycles on AI transcription, AutoSubs AI first checks if your video file (e.g., `.mkv` or `.mp4`) already contains embedded subtitles. 
- If it finds text-based subtitles (like SRT, SSA, or ASS) in your desired source language, it extracts them directly to the disk.
- **Why it matters:** This skips the transcription phase entirely, saving you time and power.

#### 2. 🌐 Fetching (The Internet Search)
If no subtitles are embedded, the app searches the internet.
- AutoSubs AI uses **Subliminal** to query top providers like *OpenSubtitles*, *Podnapisi*, and *Addic7ed*.
- It also uses built-in high-speed scrapers for *SubSource.net* and *SubDL.com*, capable of downloading and extracting ZIP archives automatically.
- **Why it matters:** Community-created subtitles are often highly accurate and formatted correctly. If a perfect match is found, transcription is skipped.

#### 3. 🎙️ Transcription (AI Generation)
If no subtitles exist in the file or on the internet, the AI takes over.
- AutoSubs AI extracts the audio track from your video and passes it into a state-of-the-art **Whisper** engine (`Faster-Whisper` or `WhisperX`).
- It generates a perfectly timed `.srt` file from scratch, recognizing speech, punctuation, and speaker cadence.
- **Why it matters:** This guarantees that *every* video you process will end up with a subtitle, regardless of how obscure the media is.

![Console Output](assets/console.png)

#### 4. ⏱️ Synchronization
Sometimes internet-fetched subtitles are out of sync by a few seconds (e.g., due to different video release versions like Web-DL vs BluRay).
- The fetched subtitle and the video's audio track are analyzed together using **FFsubsync** and Voice Activity Detection (VAD).
- The subtitle is mathematically shifted to align perfectly with the actual voices in the video.
- **Why it matters:** You'll never have to manually adjust subtitle offsets while watching a movie again.

#### 5. 🗣️ Translation (Dual-Engine AI)
If your target language differs from the video's language, the final subtitle is translated.
- You can choose between blazing-fast **NLLB-200** machine translation or premium context-aware **Native LLMs** (like Llama 3 or Gemma 2).
- **Why it matters:** You can turn raw, untranslated Japanese Anime or French Cinema into perfect English subtitles automatically.

---

## Example Use Cases

*   **The Foreign Cinema Fanatic:** Drop a folder of untranslated international films into the Web UI. AutoSubs AI will generate subtitles and natively translate them into your native language using advanced LLMs, maintaining the nuances of the original script.
*   **The Media Server Admin:** Your Plex library is missing subtitles. Run the directory through AutoSubs AI; it will fetch the best web-subtitles, sync them perfectly to the audio, and save them as `.en.srt` next to the media files so Plex picks them up automatically.
*   **The Content Creator / Editor:** You have raw podcast footage. Run the file through AutoSubs AI to generate a highly accurate base transcript using `Whisper large-v3`.
*   **Accessibility:** Easily generate closed captions for educational videos or family recordings that have no subtitles.

