# AI Models & Engines Comparison

AutoSubs AI integrates several state-of-the-art AI engines to handle Transcription, Translation, and Synchronization. This page explains the differences so you can choose the optimal configuration for your hardware and needs.

---

## 🎙️ Transcription Engines (Whisper)

AutoSubs AI provides two different wrapper engines for OpenAI's Whisper model architecture.

### 1. Faster-Whisper (Default & Recommended)
*Faster-Whisper* is a heavily optimized reimplementation of OpenAI's Whisper using CTranslate2.
- **Speed**: Up to 4x faster than the original OpenAI implementation.
- **Memory**: Drastically reduced VRAM footprint (an 8GB GPU can comfortably run the `large-v3` model).
- **Stability**: Highly stable cross-platform support for CPU, CUDA, and ROCm.
- **Use Case**: This should be your go-to engine for almost all workloads.

### 2. Transformers Native (Fallback)
If `Faster-Whisper` encounters environmental errors or unsupported architectures, AutoSubs AI gracefully falls back to the native HuggingFace `transformers` implementation.
- **Speed**: Slower than Faster-Whisper.
- **Memory**: Consumes significantly more VRAM. Uses PyTorch SDPA (Scaled Dot-Product Attention) to accelerate where possible.
- **Use Case**: Used purely as an automatic fallback to guarantee a successful transcription.

### Whisper Model Sizes
When configuring your profile, you must pick a model size.
| Size | Parameters | VRAM Needed (float16) | Accuracy | Best For |
| :--- | :--- | :--- | :--- | :--- |
| **base / small** | 74M / 244M | ~1GB - 2GB | Moderate | CPU-only processing or extremely fast low-resource translation. |
| **medium** | 769M | ~3GB - 4GB | High | The sweet spot. Excellent accuracy for standard conversational dialogue. |
| **large-v3** | 1550M | ~4.5GB - 6GB | Elite | Best-in-class accuracy. Captures highly technical jargon, quiet whispers, and thick accents. Recommended if you have 8GB+ VRAM. |

---

## 🗣️ Translation Models

If the subtitle needs to be translated from its source language to your target language, AutoSubs AI utilizes one of two incredibly powerful translation paradigms.

### 1. Native LLM Translation (Premium)
Uses Large Language Models (LLMs) to perform contextual translation natively via `llama-cpp-python` (GGUF format). Supported models include **Llama-3 (8B)** and **Gemma-2 (9B)**.
- **The Pros**: LLMs don't just translate word-for-word; they understand *context*, slang, and idiomatic expressions. If a character makes a joke in Japanese, the LLM will provide the closest English equivalent rather than a literal, broken translation.
- **The Cons**: High hardware requirements. You need at least 8GB to 12GB of VRAM to comfortably load and infer the GGUF models rapidly. Inference is slower than NLLB.
- **Best For**: Anime, complex foreign cinema, or dialogue-heavy dramas where nuance matters.

### 2. NLLB-200 (No Language Left Behind)
Facebook's dedicated sequence-to-sequence translation model. AutoSubs AI uses the `nllb-200-distilled-600M` variant.
- **The Pros**: Blisteringly fast and extremely lightweight (~2GB VRAM). It supports direct translation across over 200 languages natively.
- **The Cons**: It translates line-by-line rather than contextually. It may stumble on heavy slang or untranslatable idioms.
- **Best For**: Documentaries, news footage, bulk processing, or running on low-end hardware / CPUs.

---

## ⏱️ Synchronization (VAD)

To ensure subtitles perfectly match the audio (especially when fetching from the internet), AutoSubs AI utilizes Voice Activity Detection (VAD).

### WebRTC VAD
- **What it is**: An algorithmic approach developed by Google for Real-Time Communications. 
- **The Pros**: Very fast, zero dependencies on neural network weights, and highly stable. It aggressively filters out pure silence and static noise.
- **How it's used in AutoSubs AI**: We rely on `webrtc` to locate human speech timestamps in the audio waveform and use FFsubsync to mathematically align the mismatched subtitle timestamps to these precise audio markers.
