# AutoSubs AI: ToDo & Roadmap

## 🟢 Phase 1: High Sensibility, Quick Wins (High Priority, Low-Medium Complexity)

These items provide massive value to the user experience and are relatively straightforward to implement within our current architectural paradigm.

### 1. Support More Recent AI Models for Translation

* **Sensibility**: Very High. The LLM space evolves rapidly. Newer models (like Qwen 3.6, Gemma 4) provide significantly better translation nuance and context awareness.
* **Complexity**: Low. Our GGUF/llama-cpp-python pipeline is already robust.
* **Subtasks**:
  * `[x]` Test and benchmark new models (e.g., Qwen 3.6, Gemma 4) for translation speed and quality.
  * `[x]` Update the frontend Model Manager dropdowns to include these new models.
  * `[x]` Optimize system prompts specifically for these newer architectures.

### 2. Clean Downloaded Subtitles with AI

* **Sensibility**: High. Internet subtitles are notorious for gambling ads, synchronization credits, and URL spam.
* **Complexity**: Medium. Requires a pre-processing LLM pass.
* **Subtasks**:
  * `[x]` Create a new prompt template designed specifically for identifying and stripping promotional/spam lines without altering standard dialogue.
  * `[x]` Add a toggle in the UI: `Clean downloaded subtitles via AI`.
  * `[x]` Implement logic in `subtitle_cleaner.py` to route fetched SRTs through the local LLM or VAD if the toggle is active.

### 3. Secure Backend

* **Sensibility**: High. If users expose this to their local network or via a reverse proxy, the API needs strict protection.
* **Complexity**: Medium.
* **Subtasks**:
  * `[x]` Implement a persistent API Token architecture generated at installation.
  * `[x]` Protect all FastAPI endpoints (`/jobs`, `/config`, `/models`) with a dependency (`Depends(verify_token)`).
  * `[x]` Add a login screen to the React frontend that appears if the user is unauthenticated.

### 4. Docker Volume Mounting (Browse Local Folders)

* **Sensibility**: High. Docker is the primary deployment method for home lab servers (Unraid, Proxmox). Users must be able to map `/movies` or `/tv` into the container. Also add Folder Mappings for persistence (Models and Setting files)
* **Complexity**: Low.
* **Subtasks**:
  * `[x]` Update `docker-compose.yml` template to include volume mapping examples and auth variables.
  * `[x]` Update `docker-compose.yml` template to include volume mappings for persistence (Downloaded Models and Configuration files).  
  * `[x]` Ensure the `FolderBrowser` component can gracefully navigate from the Docker root `/` to mapped media folders.

### 4.5. Expose Advanced Configuration Parameters

* **Sensibility**: Medium. Power users might want deeper control over AI execution parameters.
* **Complexity**: Low. Just adding fields to the Profile schema and UI, passing them down to the backend processors.
* **Subtasks**:
  * `[ ]` Add `Beam Size` setting for Whisper inference (tradeoff between speed and accuracy).
  * `[ ]` Add `Compute Type` toggle for fine-tuning precision (e.g. force `int8` on low VRAM GPUs, or default to `float16`).
  * `[ ]` Add `Translation Batch Mode` vs `Sequential Mode` for native LLM translation.

---

## 🟡 Phase 2: Core Enhancements (Medium Priority, High Complexity)

These features push the application from "great" to "cutting-edge", introducing advanced AI capabilities.

### 5. Speaker Detection & Styling (Diarization)

* **Sensibility**: High. Massive accessibility win. Color-coding or prefixing subtitles by speaker `[Speaker 1: Hello]` drastically improves readability.
* **Complexity**: High. Requires integrating a Diarization model (like Pyannote.Diarization) alongside Whisper.
* **Subtasks**:
  * `[ ]` Integrate `pyannote/speaker-diarization-3.1` into the backend environment.
  * `[ ]` Modify the transcription pipeline to align Whisper timestamps with Diarization timestamps.
  * `[ ]` Add UI styling options (e.g., prefix `[Speaker X]:` or export to `.ASS` with colors).

### 6. Detection of Onscreen Text (OCR)

* **Sensibility**: Medium. Excellent for Anime or foreign films with localized signs, but niche.
* **Complexity**: High. Requires frame extraction and OCR.
* **Subtasks**:
  * `[ ]` Integrate `EasyOCR` or `Tesseract` for text detection.
  * `[ ]` Extract keyframes from the video file via `ffmpeg` where motion/scene changes occur.
  * `[ ]` Run OCR on keyframes, translate the text, and insert it as an overlapping subtitle (preferably in `.ASS` format to position it top-screen).

### 7. Translation Memory & Cache (New Idea)

* **Sensibility**: High. If a user processes multiple episodes of the same TV show, the AI should remember how it translated character names or fictional terms.
* **Complexity**: Medium.
* **Subtasks**:
  * `[ ]` Create a local SQLite database or JSON dictionary to store high-confidence translated terms.
  * `[ ]` Feed previous translations as a dynamic glossary into the LLM system prompt.
  * `[ ]` Add a UI dashboard to view/edit the Translation Dictionary.

### 8. GPU-Accelerated Audio Extraction (New Idea)

* **Sensibility**: Medium. Currently, audio extraction relies on CPU via FFmpeg. GPUs can do this significantly faster.
* **Complexity**: Medium.
* **Subtasks**:
  * `[x]` Update `orchestrator.py` to detect if Nvidia/AMD hardware encoders are available (`h264_nvenc`, `hevc_amf`).
  * `[x]` Modify the FFmpeg extraction command to utilize hardware decoding.

---

## 🔴 Phase 3: Ecosystem Integrations (Low Priority, High Complexity)

These are entirely separate codebases that require managing external lifecycles, outside the scope of our core transcription loop.

### 9. Emby Integration / Plugin

* **Sensibility**: Medium. Automatically triggering AutoSubs AI when a new movie is added to Emby.
* **Complexity**: High. Emby plugins are written in C# (.NET).
* **Subtasks**:
  * `[ ]` Create a C# Emby Plugin repository.
  * `[ ]` Setup Emby Webhook/Library Monitor to detect missing subtitles.
  * `[ ]` Send an HTTP POST request to AutoSubs AI's `/api/jobs` endpoint with the file path.

### 10. KODI Extension / Plugin

* **Sensibility**: Medium. Allows initiating downloads from the TV interface.
* **Complexity**: High. Kodi add-ons use Python 2/3 and a very specific XML UI framework.
* **Subtasks**:
  * `[ ]` Develop a Kodi Context Menu Add-on ("Generate Subtitles via AutoSubs AI").
  * `[ ]` Create a Kodi settings page to input the AutoSubs AI API IP/Port.
  * `[ ]` Send the current playing file path to the backend.

### 11. More Voice Detection Models

* **Sensibility**: Low. We currently use Pyannote and Silero-VAD, which are the industry standards. Newer models rarely offer enough of a leap to justify the integration overhead unless specifically requested.
* **Complexity**: Medium.
* **Subtasks**:
  * `[ ]` Wait for a significant breakthrough in VAD models before allocating resources here.
  * `[ ]` Monitor `webrtcvad` or Whisper's native VAD developments.

---

## 🟣 Phase 4: Experimental & Deep Automation (Future Roadmap)

### 12. Audio Source Separation (Vocal Isolation)

* **Idea**: Implement Demucs or MDX-Net to strip background music and SFX before passing the audio to VAD and Whisper.
* **Sensibility**: Medium-High. Greatly improves transcription accuracy and VAD precision on loud action movies.
* **Complexity**: High.
* **Subtasks**:
  * `[ ]` Evaluate lightweight source separation models that don't overwhelm VRAM.
  * `[ ]` Create a new distinct Orchestrator Phase (e.g., Phase 1.5) exclusively for Audio Separation to maintain strict model isolation.
  * `[ ]` Extract `.tmp.wav`, process to `.tmp.vocals.wav`, delete the original, and rename the vocals file back to `.tmp.wav` so downstream phases (VAD/Whisper) require zero code changes.
  * `[ ]` Add UI toggle (Warning: High Performance Cost).

### 13. Folder Watchdog (Background Runner)

* **Idea**: Monitor directories for new media files and automatically kick off subtitle generation.
* **Sensibility**: High. Brings AutoSubs AI closer to a fully autonomous homelab tool (like Radarr/Sonarr).
* **Complexity**: High.
* **Subtasks**:
  * `[ ]` Integrate `watchdog` library to monitor network shares or local paths.
  * `[ ]` Build UI to map specific folders to specific Processing Profiles.
  * `[ ]` Implement debounce/file-lock checks to avoid triggering while a file is actively being copied.

### 14. Translate via CTranslate2 (NLLB Optimization)

* **Idea**: Migrate NLLB translation from HuggingFace Transformers to CTranslate2.
* **Sensibility**: High. Since `ctranslate2` is already installed for `faster-whisper`, using it for NLLB would yield 2x-4x speedups and drastically lower VRAM usage via INT8 quantization.
* **Complexity**: Medium.
* **Subtasks**:
  * `[ ]` Refactor `translator.py` to use `ctranslate2.Translator`.
  * `[ ]` Handle automated downloading of CTranslate2-compatible NLLB models (or on-the-fly conversion).
