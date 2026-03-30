import os
import subprocess
import sys
import platform
import shutil
import importlib.util
import pathlib
import re

def colored_print(text, color_num):
    print(f"\033[38;5;{color_num}m{text}\033[0m")

def _write_env_var(env_path, key, value):
    """Write or update an environment variable in the .env file."""
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated = False
    new_line = f"{key}={value}\n"
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = new_line
            updated = True
            break
    if not updated:
        lines.append(new_line)

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def patch_whisperx_metadata(pip_exe):
    """
    Surgically relax WhisperX 3.8.4 strict metadata version pins to satisfy the pip resolver.
    Changes 'Requires-Dist: torch (~=2.8.0)' to 'Requires-Dist: torch (>=2.8.0)'.
    This is necessary for ROCm 2.9.1 compatibility on Windows/AMD hardware.
    """
    print("\n[Surgery] Patching WhisperX metadata to satisfy the pip resolver...")
    try:
        # Get site-packages directory from the environment
        script = "import site; print(site.getsitepackages()[0])"
        output = subprocess.check_output([pip_exe.replace("pip", "python"), "-c", script], text=True).strip()
        site_packages = pathlib.Path(output)

        # Locate whisperx dist-info
        dist_infos = list(site_packages.glob("whisperx-*.dist-info"))
        if not dist_infos:
            print("  [Notice] WhisperX metadata not found (is it installed?). Skipping patch.")
            return

        for dist_info in dist_infos:
            metadata_file = dist_info / "METADATA"
            if metadata_file.exists():
                text = metadata_file.read_text(encoding="utf-8")
                
                # Perform the relaxing replacements
                original_text = text
                text = re.sub(r'Requires-Dist: torch \(~=2\.8\.0\)', 'Requires-Dist: torch (>=2.8.0)', text)
                text = re.sub(r'Requires-Dist: torchaudio \(~=2\.8\.0\)', 'Requires-Dist: torchaudio (>=2.8.0)', text)
                
                if text != original_text:
                    metadata_file.write_text(text, encoding="utf-8")
                    print(f"  [Fix] Successfully relaxed WhisperX metadata in {dist_info.name}")
                else:
                    print(f"  [Notice] WhisperX metadata already compatible or previously patched in {dist_info.name}")
    except Exception as e:
        print(f"  [Warning] Metadata surgery failed: {e}")

def autodetect_hardware():
    has_amd = False
    has_nvidia = False
    opt_system = platform.system()
    try:
        if opt_system == "Windows":
            out = subprocess.check_output(
                ['powershell', '-NoProfile', '-Command',
                 'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name'],
                stderr=subprocess.STDOUT, text=True
            ).lower()
            if "nvidia" in out:
                has_nvidia = True
            if "amd" in out or "radeon" in out:
                has_amd = True
        elif opt_system == "Linux":
            out = subprocess.check_output(
                "lspci | grep -i vga",
                shell=True, stderr=subprocess.STDOUT, text=True
            ).lower()
            if "nvidia" in out:
                has_nvidia = True
            if "amd" in out or "radeon" in out:
                has_amd = True
    except Exception:
        pass
    return has_amd, has_nvidia

def autodetect_rocm_gfx():
    """Attempt to detect all unique GFX architectures using ROCm tools."""
    rocm_bin = r"C:\Program Files\AMD\ROCm\7.1\bin"
    amdgpu_arch = os.path.join(rocm_bin, "amdgpu-arch.exe")
    
    if os.path.exists(amdgpu_arch):
        try:
            # amdgpu-arch can output multiple lines if multiple GPUs are present
            raw_output = subprocess.check_output([amdgpu_arch], text=True).splitlines()
            gfx_targets = sorted(list(set([line.strip() for line in raw_output if line.strip().startswith("gfx")])))
            
            if gfx_targets:
                # AMDGPU_TARGETS expects a semicolon-separated list: "gfx1200;gfx1030"
                full_targets = ";".join(gfx_targets)
                
                # Pick the first one for the HSA_OVERRIDE (usually the primary)
                # Map gfx1200 -> 12.0.0
                primary = gfx_targets[0]
                major = primary[3:5]
                minor = primary[5:6]
                patch = primary[6:7] or "0"
                hsa_version = f"{int(major)}.{int(minor)}.{int(patch)}"
                
                return full_targets, hsa_version
        except Exception:
            pass
    return None, None

def check_compiler_present():
    """Check if the ROCm HIP Clang compiler is available."""
    if platform.system() == "Windows":
        # Always use ROCm Clang, never MSVC as per user requirement
        rocm_clang = r"C:\Program Files\AMD\ROCm\7.1\bin\clang.exe"
        return os.path.exists(rocm_clang)
    else:
        # Check for g++ or clang++ on Linux
        return shutil.which("g++") is not None or shutil.which("clang++") is not None


def prompt_provider_choice(has_amd, has_nvidia):
    """Ask the user which provider to install. Returns the raw choice string."""
    opt_sys = platform.system()

    os.system('cls' if os.name == 'nt' else 'clear')
    colored_print("=========================================", 14)
    colored_print(" AutoSubs AI - Dependency Installer", 14)
    colored_print("=========================================\n", 14)

    print("--- Hardware Autodetection ---")
    if has_nvidia:
        colored_print("   --> Detected NVIDIA GPU.", 10)
        colored_print("       Recommended: [2] CUDA 12.1  (Faster-Whisper, WhisperX, Transformers)", 14)
    elif has_amd:
        if opt_sys == "Linux":
            colored_print("   --> Detected AMD GPU on Linux.", 10)
            colored_print("       Recommended: [1] ROCm  (Faster-Whisper & WhisperX with full ROCm support)", 14)
        else:
            colored_print("   --> Detected AMD GPU on Windows.", 10)
            colored_print("       Best options:", 14)
            colored_print("         [1] ROCm 7.2  -- RECOMMENDED  (Faster-Whisper & WhisperX, native Windows, ctranslate2 ROCm)", 10)
            colored_print("         [4] DirectML  -- Simpler setup, Transformers engine only", 14)
            colored_print("         [6] WSL ROCm  -- Advanced: runs backend inside WSL2 Ubuntu", 14)
    else:
        colored_print("   --> No dedicated GPU detected.", 10)
        colored_print("       Recommended: [5] CPU  (Faster-Whisper INT8, no GPU required)", 14)
    print("------------------------------\n")

    print("Select your execution provider:")
    print("  [1]  AMD ROCm (Windows/Linux) - Full support: Faster-Whisper, WhisperX, Transformers")
    print("  [2]  NVIDIA CUDA 12.1         - Modern NVIDIA GPUs (all engines)")
    print("  [3]  NVIDIA CUDA 11.8         - Older NVIDIA GPUs (all engines)")
    print("  [4]  DirectML                 - Windows AMD/Intel/NVIDIA (Transformers engine only)")
    print("  [5]  CPU Only                 - No GPU, universal fallback")
    if opt_sys == "Windows":
        print("  [6]  WSL ROCm [Advanced]     - Backend inside WSL2 Ubuntu (alternative, not needed)")
    print()

    try:
        choice = input("Enter your choice (1-6): ").strip()
    except KeyboardInterrupt:
        print("\nInstallation cancelled.")
        sys.exit(0)

    return choice


def prompt_venv_setup() -> str:
    """
    Ask whether to create a virtual environment.
    Returns the Python executable to use for subsequent pip calls
    (either the venv python or the current sys.executable).
    Does NOT restart the script.
    """
    print("\n--- Virtual Environment ---")
    print("It is recommended to install dependencies inside a virtual environment.")
    try:
        ans = input("Create and use a venv in './venv'? (Y/n): ").strip().lower()
    except KeyboardInterrupt:
        print("\nInstallation cancelled.")
        sys.exit(0)

    if ans in ("", "y", "yes"):
        venv_dir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "venv")
        )
        if os.path.exists(venv_dir):
            print(f"  [Notice] Virtual environment already exists at {venv_dir}. Skipping creation.")
        else:
            print(f"Creating venv at: {venv_dir}")
            subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        
        venv_python = os.path.join(
            venv_dir, "Scripts" if os.name == "nt" else "bin", "python"
        )
        colored_print(f"Venv created. Installing packages into: {venv_dir}", 10)
        return venv_python
    else:
        return sys.executable


def prompt_auth_setup():
    """Optionally configure HTTP basic auth for the API."""
    print("\n--- API Authentication ---")
    print("You can protect the web interface with a username and password.")
    try:
        ans = input("Enable HTTP authentication? (y/N): ").strip().lower()
    except KeyboardInterrupt:
        print("\nInstallation cancelled.")
        sys.exit(0)

    if ans in ("y", "yes"):
        try:
            username = input("  Username: ").strip()
            password = input("  Password: ").strip()
        except KeyboardInterrupt:
            print("\nSkipping auth setup.")
            return

        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        with open(env_path, "a") as f:
            f.write(f"\nAUTH_USERNAME={username}\nAUTH_PASSWORD={password}\n")
        colored_print(f"  Auth credentials saved to {env_path}", 10)
    else:
        print("  Skipping authentication setup.")


def install_wsl_option():
    """Handle option 6: launch the WSL ROCm installer via PowerShell."""
    if platform.system() != "Windows":
        colored_print("ERROR: WSL option is only available on Windows.", 9)
        sys.exit(1)

    # Check WSL availability by looking for wsl.exe — do NOT use 'wsl --status'
    # because it exits with code 1 if no distro is installed yet, even when WSL IS available.
    import shutil
    if shutil.which("wsl") is None:
        colored_print("ERROR: wsl.exe not found in PATH. Enable WSL via:", 9)
        colored_print("  Windows Settings -> Turn Windows features on -> Windows Subsystem for Linux", 14)
        sys.exit(1)

    ps_script = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "Install-WSL-Backend.ps1")
    )
    if not os.path.exists(ps_script):
        colored_print(f"ERROR: Installer script not found at: {ps_script}", 9)
        sys.exit(1)

    colored_print(f"Running: {ps_script}", 14)
    subprocess.call(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script])
    print("\n=========================================")
    colored_print("WSL ROCm setup complete.", 10)
    print("Start the backend via start.bat -> option [2]")


def install():
    has_amd, has_nvidia = autodetect_hardware()

    # ── Step 1: choose provider ──────────────────────────────────────────────
    choice = prompt_provider_choice(has_amd, has_nvidia)

    # ── Step 2: WSL — skip ALL Windows-side installation entirely ────────────
    if choice == "6":
        colored_print("\n>>> Launching WSL ROCm Backend Installer...", 10)
        print("\nAll dependencies will be installed inside WSL. Nothing will be installed in Windows Python.")
        install_wsl_option()
        # Exit with code 2 so install.bat knows to skip frontend/Windows-side steps
        sys.exit(2)


    # ── Step 3: venv and auth (after choice, never for WSL) ──────────────────
    pip_exe = prompt_venv_setup()   # returns either venv python or sys.executable
    prompt_auth_setup()
    
    constraints_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "constraints.txt")

    # ── Step 4: install base backend packages ─────────────────────────────────
    base_deps = [
        "fastapi>=0.110.0", "uvicorn>=0.31.1", "ffmpeg-python==0.2.0",
        "transformers>=4.40.0", "accelerate>=0.28.0", "pysubs2>=1.7.0",
        "sse-starlette>=2.0.0", "pydantic>=2.7.0", "python-multipart>=0.0.9",
        "python-dotenv>=1.0.1", "hf-transfer>=0.1.9", "huggingface_hub",
        "requests", "plyer", "pandas==2.2.3", "nltk>=3.8.1", "av==15.1.0", "tokenizers", "onnxruntime",
        "subliminal==2.6.0", "babelfish", "ffsubsync", "charset-normalizer", "silero-vad", "ninja",
        "omegaconf>=2.3.0", "pyannote-audio>=4.0.0"
    ]

    print("\n[1/2] Installing base dependencies...")
    subprocess.check_call([pip_exe, "-m", "pip", "install", "--upgrade", "-c", constraints_path] + base_deps)

    print("\nRemoving old torch installations to prevent conflicts...")
    subprocess.call([pip_exe, "-m", "pip", "uninstall", "-y",
                     "torch", "torchvision", "torchaudio", "torch-directml"])

    # ── Step 5: install PyTorch for selected provider ─────────────────────────
    print("\n[2/2] Installing PyTorch environment...")

    if choice == "1":
        colored_print("\n>>> Installing ROCm 7.2.1 Environment...", 10)
        is_windows = os.name == 'nt'
        py_ver = f"cp{sys.version_info.major}{sys.version_info.minor}"

        if is_windows:
            # ── Select GPU architecture → write HSA_OVERRIDE_GFX_VERSION to .env ──
            # Without this, the ROCm HIP runtime on Windows cannot identify the GPU
            # and fails with "CUDA driver version is insufficient" at runtime.
            # ── Autodetect GPU architecture for HSA_OVERRIDE_GFX_VERSION ──
            gfx_arch, hsa_override = autodetect_rocm_gfx()
            
            if gfx_arch and hsa_override:
                colored_print(f"\n  [Auto] Detected GPU Architecture: {gfx_arch} (HSA Override: {hsa_override})", 10)
            else:
                GPU_MAP = {
                    "1": ("RX 9070 / 9070 XT",  "gfx1201", "12.0.1"),
                    "2": ("RX 9060 (XT)",         "gfx1200", "12.0.0"),
                    "3": ("RX 7900 XTX/XT",       "gfx1100", "11.0.0"),
                    "4": ("RX 7800/7700 XT",       "gfx1101", "11.0.1"),
                    "5": ("RX 7600",               "gfx1102", "11.0.2"),
                    "6": ("RX 6900/6800/6700 XT",  "gfx1030", "10.3.0"),
                    "7": ("RX 6600",               "gfx1032", "10.3.2"),
                }
                print("\n  Select your AMD GPU model:")
                for k, (name, gfx, hsa) in GPU_MAP.items():
                    print(f"    [{k}] {name}  ({gfx})")
                try:
                    gpu_choice = input("  Enter number: ").strip()
                except KeyboardInterrupt:
                    gpu_choice = "2"  # default to RX 9060 XT
                gpu_name, gfx_arch, hsa_override = GPU_MAP.get(gpu_choice, ("RX 9060 XT", "gfx1200", "12.0.0"))
                colored_print(f"  Selected: {gpu_name} → HSA_OVERRIDE_GFX_VERSION={hsa_override}", 10)

            # Write to .env so transcriber.py picks it up at startup
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
            _write_env_var(env_path, "HSA_OVERRIDE_GFX_VERSION", hsa_override)
            _write_env_var(env_path, "AMDGPU_TARGETS", gfx_arch)

            rocm_sdk_urls = [
                "https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/rocm_sdk_core-7.2.1-py3-none-win_amd64.whl",
                "https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/rocm_sdk_devel-7.2.1-py3-none-win_amd64.whl",
                "https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/rocm_sdk_libraries_custom-7.2.1-py3-none-win_amd64.whl",
                "https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/rocm-7.2.1.tar.gz"
            ]
            colored_print("\n[ROCm 7.2.1 Windows] Installing SDK...", 14)
            subprocess.check_call([pip_exe, "-m", "pip", "install", "-c", constraints_path,
                                    "--no-cache-dir", "--no-deps"] + rocm_sdk_urls)

            pytorch_rocm_urls = [
                f"https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/torch-2.9.1%2Brocm7.2.1-{py_ver}-{py_ver}-win_amd64.whl",
                f"https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/torchaudio-2.9.1%2Brocm7.2.1-{py_ver}-{py_ver}-win_amd64.whl",
                f"https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/torchvision-0.24.1%2Brocm7.2.1-{py_ver}-{py_ver}-win_amd64.whl"
            ]
            colored_print(f"\n[ROCm 7.2.1 Windows] Installing PyTorch (Python {sys.version_info.major}.{sys.version_info.minor})...", 14)
            try:
                subprocess.check_call([pip_exe, "-m", "pip", "install", "-c", constraints_path,
                                        "--no-cache-dir", "--no-deps"] + pytorch_rocm_urls)
            except subprocess.CalledProcessError:
                print("\n[WARNING] Exact wheel not found, falling back to find-links...")
                subprocess.check_call([pip_exe, "-m", "pip", "install", "-c", constraints_path,
                                        "--no-cache-dir", "--no-deps",
                                        "--find-links", "https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/",
                                        "torch", "torchaudio"])

            # ── [CRITICAL] ROCm ctranslate2 (Windows native, Python 3.x) ──────────
            # Re-installed LAST to ensure it is not overwritten by standard dependencies.
            # Pre-built by sssshhhhhh: https://github.com/sssshhhhhh/CTranslate2/releases
            print("\nEnsuring ROCm ctranslate2 is installed last to prevent CUDA-overwrites...")
            
            # --- Resolve WhisperX/Faster-Whisper Version Conflicts ---
            # We install these with --no-deps so they don't overwrite our ROCm Torch (2.9.1)
            # with their pinned standard torch (2.8.0).
            print("\nInstalling WhisperX/Faster-Whisper with constraints to preserve ROCm environment...")
            subprocess.check_call([pip_exe, "-m", "pip", "install", "-c", constraints_path, "--no-deps", "whisperx", "faster-whisper"])

            # ── [CRITICAL SURGERY] Satisfy the resolver ──
            # Run the metadata patch before ctranslate2 so subsequent checks pass.
            patch_whisperx_metadata(pip_exe)

            subprocess.call([pip_exe, "-m", "pip", "uninstall", "-y", "ctranslate2"])
            ct2_whl = f"https://github.com/sssshhhhhh/CTranslate2/releases/download/v4.7.1-rocm/ctranslate2-4.7.1-{py_ver}-{py_ver}-win_amd64.whl"
            colored_print(f"\n[ROCm] Installing verified ctranslate2 4.7.1 ROCm wheel in final state...", 14)
            try:
                subprocess.check_call([pip_exe, "-m", "pip", "install", "-c", constraints_path, "--no-cache-dir", ct2_whl])
            except subprocess.CalledProcessError:
                colored_print("[WARNING] ctranslate2 ROCm wheel download failed — will use default ctranslate2.", 9)
                colored_print("  Faster-Whisper will still work but without ROCm GPU acceleration.", 9)
                subprocess.check_call([pip_exe, "-m", "pip", "install", "ctranslate2"])
        else:
            colored_print(f"\n[ROCm 7.2 Linux] Installing PyTorch via AMD manylinux repo...", 14)
            try:
                subprocess.check_call([
                    pip_exe, "-m", "pip", "install", "--no-cache-dir", "--no-deps",
                    "--find-links", "https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2/",
                    "torch", "torchaudio"
                ])
            except Exception as e:
                print(f"AMD repo failed ({e}), falling back to PyTorch ROCm 6.2 index...")
                subprocess.check_call([
                    pip_exe, "-m", "pip", "install", "--no-deps",
                    "torch", "torchaudio",
                    "--index-url", "https://download.pytorch.org/whl/rocm6.2"
                ])

    elif choice == "2":
        colored_print("\n>>> Installing PyTorch for CUDA 12.1...", 10)
        subprocess.check_call([
            pip_exe, "-m", "pip", "install",
            "torch", "torchaudio",
            "--index-url", "https://download.pytorch.org/whl/cu121"
        ])
    elif choice == "3":
        colored_print("\n>>> Installing PyTorch for CUDA 11.8...", 10)
        subprocess.check_call([
            pip_exe, "-m", "pip", "install",
            "torch", "torchaudio",
            "--index-url", "https://download.pytorch.org/whl/cu118"
        ])
    elif choice == "4":
        colored_print("\n>>> Installing PyTorch CPU + torch-directml...", 10)
        subprocess.check_call([
            pip_exe, "-m", "pip", "install",
            "torch", "torchaudio", "torch-directml"
        ])
    else:
        colored_print("\n>>> Installing PyTorch for CPU...", 10)
        subprocess.check_call([
            pip_exe, "-m", "pip", "install",
            "torch", "torchaudio"
        ])

    # ── Step 6: Install Native LLM (llama-cpp-python) ────────────────────────
    print("\n[3/3] Installing Native LLM Support (llama-cpp-python)...")
    
    # Check for build tools on Windows before attempt
    if os.name == 'nt' and not check_compiler_present():
        colored_print("\n[CRITICAL ERROR] ROCm HIP SDK 7.1 NOT found!", 9)
        print("To compile 'llama-cpp-python' with ROCm (HIP) support, you MUST have")
        print("the AMD ROCm 7.1 SDK installed at C:\\Program Files\\AMD\\ROCm\\7.1")
        print("\nDownload Link:")
        colored_print("  https://visualstudio.microsoft.com/visual-cpp-build-tools/", 14)
        print("\nInstructions:")
        print("  1. Download and run the 'Visual Studio Installer'")
        print("  2. Select 'Desktop development with C++'")
        print("  3. Ensure 'MSVC v143' and 'C++ CMake tools for Windows' are checked")
        print("  4. Restart this installer after installation completes.")
        print("\nAutoSubs AI will continue, but Native LLM translation will NOT work until this is fixed.")
        # Proceed to install CPU-only regardless to allow the app to boot
        subprocess.check_call([pip_exe, "-m", "pip", "install", "llama-cpp-python", "--no-cache-dir"])
        return 

    # Environment variables for compilation
    env = os.environ.copy()
    
    if choice == "1":
        colored_print("   --> Compiling llama-cpp-python with ROCm (HIPBlast) support (Native Clang)...", 14)
        
        # Explicitly inject ROCm 7.1 Binaries into PATH for compilation discovery
        rocm_root = r"C:\Program Files\AMD\ROCm\7.1"
        rocm_bin = os.path.join(rocm_root, "bin")
        
        # Only inject if path exists (installer-side check)
        if os.path.exists(rocm_bin):
            env["PATH"] = rocm_bin + os.pathsep + env.get("PATH", "")
            colored_print(f"   --> Injected {rocm_bin} into PATH for build step.", 10)
        else:
            colored_print(f"\n[CRITICAL ERROR] ROCm 7.1 Binaries NOT found at {rocm_bin}!", 9)
            return
        
        gfx_arch, hsa_override = autodetect_rocm_gfx()
        if not gfx_arch:
            gfx_arch = "gfx1200" # fallback if autodetection fails entirely
        
        if "AMDGPU_TARGETS" in os.environ:
            gfx_arch = os.environ["AMDGPU_TARGETS"]
        
        # Explicitly point to ROCm Clang to bypass MSVC for .cu/.cpp files
        c_compiler = os.path.join(rocm_bin, "clang.exe").replace("\\", "/")
        cxx_compiler = os.path.join(rocm_bin, "clang++.exe").replace("\\", "/")
        
        # Use modern GGML flags for 0.3.x builds with Ninja generator
        env["CMAKE_GENERATOR"] = "Ninja"
        env["HIP_PATH"] = rocm_root
        env["CMAKE_ARGS"] = (
            f"-DGGML_HIPBLAS=ON -DGGML_HIP=ON "
            f"-DCMAKE_C_COMPILER=\"{c_compiler}\" "
            f"-DCMAKE_CXX_COMPILER=\"{cxx_compiler}\" "
            f"-DAMDGPU_TARGETS={gfx_arch}"
        )
    elif choice in ["2", "3"]:
        colored_print("   --> Compiling llama-cpp-python with CUDA support...", 14)
        env["CMAKE_ARGS"] = "-DLLAMA_CUDA=ON"
    
    try:
        # Install llama-cpp-python. We use --verbose to show compilation progress.
        # We don't use -c constraints here because llama-cpp-python compilation can be sensitive.
        subprocess.check_call([
            pip_exe, "-m", "pip", "install", "llama-cpp-python", 
            "--no-cache-dir", "--force-reinstall", "--upgrade"
        ], env=env)
        colored_print("   --> Native LLM support installed successfully!", 10)
    except Exception as e:
        colored_print(f"\n[WARNING] Native LLM compilation failed: {e}", 9)
        colored_print("   AutoSubs AI will fall back to CPU-only NLLB for translations.", 14)
        subprocess.check_call([pip_exe, "-m", "pip", "install", "llama-cpp-python", "--no-cache-dir"])

    # ── Step 7: done ─────────────────────────────────────────────────────────
    print("\n=========================================")
    colored_print("Installation Complete!", 10)
    print("Start the app with: start.bat")


if __name__ == "__main__":
    install()
