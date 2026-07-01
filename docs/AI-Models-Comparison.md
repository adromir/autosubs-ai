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

### Included Whisper Models

AutoSubs AI supports the full standard Whisper model fleet. 
*Note: `*.en` variants are English-only models. They perform marginally better for English-to-English transcription but cannot handle foreign languages.*

| Model | Parameters | VRAM (fp16) | Recommendation / Use Case |
| :--- | :--- | :--- | :--- |
| **tiny** / **tiny.en** | 39M | ~1 GB | **Ultra-Low End:** Good for embedded devices or CPUs where speed is the only concern. Poor accuracy on complex audio. |
| **base** / **base.en** | 74M | ~1 GB | **Low End:** Use on low-end CPUs. Generally not recommended unless absolutely necessary. |
| **small** / **small.en** | 244M | ~2 GB | **Balanced CPU:** The best choice for CPU-only execution. Decent accuracy, acceptable speed. |
| **medium** / **medium.en** | 769M | ~4 GB | **The Sweet Spot:** Highly accurate for standard conversational dialogue. Great for mid-tier GPUs (6GB VRAM). |
| **large-v2** | 1550M | ~6 GB | **Legacy High-End:** Excellent accuracy, but generally superseded by large-v3. |
| **large-v3** | 1550M | ~6 GB | **Elite / The Gold Standard:** Best-in-class accuracy. Captures highly technical jargon, quiet whispers, and thick accents perfectly. **Recommended if you have an 8GB+ GPU.** |
| **large-v3-turbo**| 809M | ~4 GB | **Speed & Quality:** A heavily pruned version of large-v3. Nearly identical accuracy but much faster inference. **Highly Recommended for most GPU users.** |

---

## 🗣️ Translation Models

If the subtitle needs to be translated from its source language to your target language, AutoSubs AI utilizes one of two incredibly powerful translation paradigms.

### 1. NLLB-200 (No Language Left Behind)
Facebook's dedicated sequence-to-sequence translation model. AutoSubs AI uses the `nllb-200-distilled-600M` variant.
- **The Pros**: Blisteringly fast and extremely lightweight (~2GB VRAM). It supports direct translation across over 200 languages natively.
- **The Cons**: It translates line-by-line rather than contextually. It may stumble on heavy slang or untranslatable idioms.
- **Recommendation**: Best for Documentaries, news footage, bulk processing, or running on low-end hardware / CPUs.

### 2. Native LLM Translation (Premium via Llama.cpp)
Uses Large Language Models (LLMs) to perform contextual translation natively via `llama-cpp-python` (GGUF format). LLMs translate contextually, understanding slang, jokes, and idioms. AutoSubs AI comes pre-configured to download the following top-tier open-weight models:

| Model | Size | VRAM Needed | Recommendation / Use Case |
| :--- | :--- | :--- | :--- |
| **Qwen 3 (0.6B)** | 1.2 GB | ~2 GB | **Potato PC / Extreme Speed:** Tiny but surprisingly capable. Best if you have almost no VRAM but still want contextual translation. |
| **Phi-3 Mini (3.8B)** | 2.4 GB | ~4 GB | **Low-End GPUs:** Fast and highly efficient. A great entry point for LLM translation on 4GB-6GB graphics cards. |
| **Qwen 2.5 (7B)** | 4.5 GB | ~6 GB | **Mid-Tier (Asian Languages):** Qwen models excel significantly at Asian languages (Japanese, Chinese, Korean). Highly recommended for Anime translation. |
| **Meta Llama 3 (8B)** | 4.9 GB | ~8 GB | **Solid All-Rounder:** Excellent translation quality, though slightly older than 3.1. |
| **Meta Llama 3.1 (8B)** | 8.5 GB | ~10 GB | **High-End Default:** Flawless prompt adherence and incredible nuance. **Highly recommended for 10GB+ VRAM users translating European languages.** |
| **Gemma 2 (9B)** | 5.4 GB | ~8 GB | **The Challenger:** Google's latest model. Rivals Llama 3.1 in quality but is slightly smaller. Excellent general-purpose translator. |
| **Mistral NeMo (12B)** | 10.5 GB | ~12 GB | **Multilingual Master:** Built specifically with massive multilingual tokenizers. Exceptional at handling obscure languages perfectly. |
| **Gemma 4 Family (12B)** | 4.5 - 12.8 GB| Variable | **Cutting Edge:** Unsloth-optimized variants of Gemma 4. Use `E4B IT` for speed, or the massive `12B IT` if you have 16GB+ VRAM for flawless, elite translation. |

---

## ⏱️ Synchronization (VAD Models)

To ensure subtitles perfectly match the audio (especially when fetching from the internet), AutoSubs AI utilizes Voice Activity Detection (VAD). We utilize VAD in two places: to filter out silence during Whisper transcription, and to sync fetched subtitles to the audio waveform.

### 1. WebRTC VAD
- **What it is**: An algorithmic approach developed by Google for Real-Time Communications. 
- **The Pros**: Lightning fast, zero dependencies on neural network weights, and highly stable. It aggressively filters out pure silence and static noise.
- **Use Case / Recommendation**: This is our primary engine for **Subtitle Synchronization (FFsubsync)**. Because it's algorithmic, it runs instantly on CPU and perfectly detects the mathematical starts and stops of speech.

### 2. Pyannote / Silero VAD (Whisper Pre-filtering)
- **What it is**: Deep-learning based VAD models.
- **The Pros**: Extremely accurate at distinguishing between human speech and non-speech sounds (like a dog barking or a car engine, which WebRTC might mistake for speech).
- **Use Case / Recommendation**: Used during the **Whisper Transcription phase**. By running the audio through Pyannote/Silero first, we tell Whisper to completely ignore sections without human speech. This completely prevents Whisper from hallucinating subtitles during long musical intros or action scenes.
