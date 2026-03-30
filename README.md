# 🎬 AutoSubs AI

<p align="center">
  <a href="https://github.com/adromir">
    <img src="https://img.shields.io/badge/Creator-Adromir-blueviolet?style=for-the-badge&logo=github" alt="Creator Adromir">
  </a>
  <img src="https://img.shields.io/badge/Status-Stable-success?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AMD_ROCm-7.1-orange?style=for-the-badge&logo=amd" alt="AMD ROCm 7.1">
  <img src="https://img.shields.io/badge/NVIDIA_CUDA-12.1-green?style=for-the-badge&logo=nvidia" alt="NVIDIA CUDA 12.1">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
</p>

---

**AutoSubs AI** is a state-of-the-art subtitle orchestration pipeline designed for speed, precision, and hardware flexibility. Whether you are running an **AMD RX 9060XT**, an **NVIDIA RTX 4090**, or a **CPU-only server**, AutoSubs AI provides a stunning Glassmorphism GUI to extract, fetch, transcribe, sync, and translate subtitles with zero friction.

---

---

## 🚀 Key Features

### 🔍 Comprehensive Subtitle Discovery
Choose the best source for your media. AutoSubs AI automates the entire search:
*   **Internet Fetching (Subliminal)**: Access subtitle providers (OpenSubtitles, Podnapisi, Addic7ed, etc.) natively through **Subliminal 2.6.0** integration.
*   **Premium Providers**: Built-in high-speed REST clients for **SubSource.net** and **SubDL.com** with automatic **ZIP/Archive extraction**.
*   **Embedded Extraction**: Automatically scans and extracts existing text-based `.srt` tracks from `mkv` or `mp4` containers, avoiding redundant AI work.

### 🧠 Dual-Engine AI Translation
AutoSubs AI features a versatile, high-performance translation pipeline designed for precision and speed:

*   **Premium: Native LLM (GGUF)**: Powered by `llama-cpp-python`, utilizing state-of-the-art models like **Llama 3 (8B)** or **Gemma 2 (9B)** entirely in-process. 
    *   **Context Aware**: Best for capturing nuances, slang, and complex dialogue flow.
    *   **GPU Accelerated**: Full ROCm/HIP and CUDA offloading for lightning-fast inference.
    *   **Zero Dependencies**: Fully self-contained. No external software like Ollama is required.
*   **High-Speed: NLLB-200**: Based on Facebook's *No Language Left Behind* project.
    *   **Maximum Performance**: Optimized for rapid, sentence-level translation across 200+ languages.
    *   **Lightweight**: Minimal VRAM footprint, ideal for background processing while multi-tasking.
*   **VRAM Handover**: Automatically clears transcription memory before loading translation models to maximize stability on consumer-grade GPUs.

### 🔄 Automatic Audio Synchronization
Never deal with "out of sync" subtitles again:
*   **Smart Alignment**: Internet-fetched subtitles are automatically passed to **FFsubsync** to align them perfectly with the video's actual audio track.
*   **Resilient VAD**: Uses the stable `webrtc` voice activity detection engine to ensure alignment succeeds even in loud or musically intense scenes.

### 🎙️ Elite AI Transcription
When no subtitles exist, create your own with industry-leading accuracy:
*   **Whisper Engines**: Full support for `Faster-Whisper` and `WhisperX` (the gold standards of transcription).
*   **SRT Sanitization**: Every subtitle is automatically normalized to `UTF-8` with Unix line endings (`\n`) to ensure 100% downstream stability.

---

## 🛠️ Installation & Requirements

AutoSubs AI is optimized for high-performance hardware. Please ensure your system meets these prerequisites:

### 📋 Prerequisites

| Hardware | OS | Requirement & Download Links |
| :--- | :--- | :--- |
| **AMD GPU** | **Windows** | **[AMD ROCm 7.1 SDK (HIP SDK)](https://www.amd.com/en/developer/rocm-hub/hip-sdk.html)**<br>**[Visual Studio 2022 C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)** |
| **AMD GPU** | **Linux** | **ROCm 7.1+ Drivers** (`amdgpu-install`) |
| **NVIDIA GPU** | **Any** | **NVIDIA Drivers (535+)**, **[CUDA Toolkit 12.1](https://developer.nvidia.com/cuda-12-1-0-download-archive)** |
| **General** | **Any** | **Python 3.10+**, **FFmpeg** |

> [!IMPORTANT]
> **Windows ROCm Users**: To compile native LLM support, you MUST install **Visual Studio 2022 Build Tools** with the "Desktop development with C++" workload and have the **ROCm 7.1 SDK** installed. Our installer will handle the rest via the native Clang toolchain.

### 📦 Setup Methods

#### 1️⃣ Native Windows Installation
1. Install the **[AMD ROCm 7.1 SDK](https://www.amd.com/en/developer/rocm-hub/hip-sdk.html)** (or CUDA for NVIDIA).
2. Install **Visual Studio 2022 Build Tools** (Select "Desktop development with C++").
3. Run `install.bat`. It will autodetect your hardware (including GFX architecture) and configure your environment.

#### 2️⃣ Native Linux Installation (Debian/Ubuntu)
**For AMD ROCm (7.1+):**
```bash
# Install the AMDGPU-install tool (Ubuntu 24.04 example)
wget https://repo.radeon.com/amdgpu-install/7.0/ubuntu/noble/amdgpu-install_7.0.60000-1_all.deb
sudo apt install ./amdgpu-install_7.0.60000-1_all.deb
sudo amdgpu-install --usecase=rocm,hiplibsdk,dkms
```

**For NVIDIA CUDA:**
```bash
sudo apt update
sudo apt install nvidia-cuda-toolkit
```

4. Run `bash install.sh`.

#### 3️⃣ Docker Deployment
*   **ROCm 7.1 (AMD)**: `docker compose --profile rocm up -d --build`
*   **CUDA 12.1 (NVIDIA)**: `docker compose --profile cuda up -d --build`
*   **Standard CPU**: `docker compose --profile cpu up -d --build`

---

## 💡 Recommendations & Settings

For the best experience, we recommend the following model choices based on your hardware:

### **Transcription (Whisper)**
*   **High Performance (8GB+ VRAM)**: Use `large-v3` or `distil-large-v3`.
*   **Balanced**: Use `medium`. Excellent accuracy with much lower memory footprint.
*   **Fast/CPU**: Use `small` or `base` with `INT8` quantization.

### **Translation**
*   **Native LLM (Premium)**: **Llama-3-8B-Instruct**. Best for capturing nuances, slang, and context-aware translations.
*   **NLLB-200 (Standard)**: `facebook/nllb-200-distilled-600M`. Fast, reliable, and extremely lightweight.

### **Synchronization**
*   **VAD Engine**: Use `webrtc` for general synchronization. It is the most stable choice for background audio processing.

---

## ⚙️ Settings Overview
| Setting | Description | Recommended |
| :--- | :--- | :--- |
| **Beam Size** | Search depth for Whisper. | `5` |
| **VAD Filter** | Removes noise/silence. | `Enabled` |
| **Compute Type** | Precision mode. | `float16` (GPU) or `int8` (CPU) |
| **Translate Phase** | Sequential vs Batch. | `Batch` for NLLB, `Sequential` for Ollama |

---

## ⚖️ Disclaimer & License

> [!WARNING]
> This software is intended for personal and educational use. Always ensure you have the rights to the content you are processing.

**Creator**: [Adromir](https://github.com/adromir)  
**Webpage**: [https://github.com/adromir](https://github.com/adromir)  
**License**: Distributed under the **MIT License**.

---
*Powered by Deep Learning and a passion for automation.*
