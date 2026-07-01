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
- **Source Language**: The spoken language of the video file (e.g., `Japanese`). Set to `auto` to let Whisper detect the language automatically.
- **Target Language**: The language you want the final subtitle to be in (e.g., `English`). If this differs from the Source Language, the Translation phase is triggered.

### Advanced Parameters

#### Beam Size
*Affects: Transcription (Whisper)*
Beam Search is an algorithm Whisper uses to predict the next word. It explores multiple possible text paths simultaneously.
- **Default (`5`)**: Provides the best balance between accuracy and speed.
- **Lower (e.g., `1` or `2`)**: Faster inference, but the AI might misunderstand complex audio or mumble.
- **Higher (e.g., `10`)**: Extremely accurate, but linearly increases transcription time and VRAM usage. Use this for highly technical audio or thick accents.

#### Compute Type
*Affects: Transcription (Whisper)*
Determines the mathematical precision of the neural network weights.
- **`float16`**: Recommended for GPUs. Uses half-precision mathematics, cutting memory usage in half and significantly speeding up inference with zero noticeable accuracy loss.
- **`int8`**: Recommended for CPU-only execution. Heavily quantizes the model, trading a very minor amount of accuracy for a massive boost in CPU speed.
- **`float32`**: Full precision. Extremely slow and memory-heavy; generally not recommended unless debugging floating-point errors.

#### VAD Filter (Voice Activity Detection)
*Affects: Transcription (Whisper)*
- **Enabled (Recommended)**: Runs a highly efficient VAD pass over the audio to identify segments without human speech (e.g., long musical intro, silence). These segments are completely skipped by Whisper. This drastically reduces hallucination (where Whisper tries to translate music into random words) and speeds up transcription.
- **Disabled**: Whisper listens to every single second of audio.

#### Translate Phase Mode
*Affects: Native LLM Translation*
- **Sequential**: Translates the subtitle file one line at a time. It maintains absolute structural integrity but is extremely slow.
- **Batch (Recommended)**: Groups multiple lines of dialogue into chunks and translates them simultaneously. It utilizes the LLM's parallel processing capabilities, resulting in massive speedups (often 10x faster). The built-in prompt engineering ensures the SRT timestamps are preserved perfectly during the batch response.
