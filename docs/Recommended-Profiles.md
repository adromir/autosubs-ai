# Recommended Profiles & Settings

When setting up AutoSubs AI, you have a vast array of models, hardware providers, and parameters to choose from. To make things easy, we have compiled the optimal settings for three major use cases: **Fastest**, **Balanced**, and **Most Accurate**.

You can set these up as different [Job Profiles](Configuration-and-Parameters.md) in your GUI!

---

## ⚡ 1. The "Fastest" Profile (Speed over Perfection)

**Best for:** Processing massive backlogs of media where you just need *passable* subtitles as quickly as possible. Ideal for older hardware or CPU-only servers.

### Recommended Settings:
* **Whisper Engine**: `Faster-Whisper`
* **Whisper Model**: `tiny` (or `tiny.en` if the source is English)
* **Compute Type**: `int8` (Extremely fast, lowest VRAM footprint)
* **VAD (Voice Activity Detection)**: `Silero` (Faster than WhisperX's VAD)
* **Translation Model**: `NLLB-200`
* **Hardware Provider**: `CPU` (if no GPU is available) or `CUDA/ROCm`

**Pros**: Blistering fast processing times. Will chew through a standard 20-minute TV episode in less than a minute on most modern hardware.
**Cons**: Fails on strong accents, background noise, or highly technical jargon.

---

## ⚖️ 2. The "Balanced" Profile (The Sweet Spot)

**Best for:** The average user running AutoSubs AI on a standard desktop PC with a mid-range GPU (e.g., RTX 3060, RX 6700 XT). This provides an excellent compromise between processing time and highly accurate results.

### Recommended Settings:
* **Whisper Engine**: `Faster-Whisper`
* **Whisper Model**: `large-v3-turbo` 
* **Compute Type**: `float16` 
* **VAD (Voice Activity Detection)**: `WhisperX` (Better word-level timestamps)
* **Translation Model**: `llama-3-8b-instruct` (or `NLLB-200` if you don't have enough VRAM for an LLM)
* **Hardware Provider**: `CUDA` or `ROCm` (GPU required)

**Pros**: `large-v3-turbo` offers nearly identical accuracy to the massive `large-v3` model, but is significantly faster and uses less VRAM.
**Cons**: Requires a dedicated GPU with at least 6GB-8GB of VRAM.

---

## 🎯 3. The "Most Accurate" Profile (No Compromises)

**Best for:** Archival quality subtitles. Use this when the accuracy of every single word and timestamp matters, such as for Foreign Cinema, anime, or difficult audio with heavy background noise.

### Recommended Settings:
* **Whisper Engine**: `WhisperX`
* **Whisper Model**: `large-v3`
* **Compute Type**: `float16`
* **VAD (Voice Activity Detection)**: `WhisperX`
* **Translation Model**: `Qwen 3.6` or `Gemma 4` (Large LLMs for nuanced, context-aware translation)
* **Hardware Provider**: `CUDA` or `ROCm` (High-end GPU required)

**Pros**: Perfect word-level synchronization, robust against background noise, catches whispers and thick accents. 
**Cons**: Very slow. Demands significant hardware resources (12GB+ VRAM recommended for running both `large-v3` and a large Translation LLM simultaneously).

---

## Pro-Tips

> [!TIP]
> **Always use embedded extraction first!** 
> Regardless of which profile you choose, always make sure the "Extract Embedded Subtitles" feature is turned on. It takes 0 seconds and saves the AI from having to do any work if the subtitle already exists in the file.

> [!WARNING]
> **A Note on Translation:** If you use LLMs for translation, keep in mind they require significant VRAM and take longer to load than sequence-to-sequence models like NLLB-200. Only use LLMs for translation if you have the hardware to support it.
