import os
import subprocess
import sys
import platform
import shutil
import importlib.util
import pathlib
import re
import json

CONFIG_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "installer_config.json"))

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"  [Warning] Failed to save config: {e}")

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
        script = "import sysconfig; print(sysconfig.get_paths()['purelib'])"
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
                text = re.sub(r'Requires-Dist: ctranslate2\b.*', 'Requires-Dist: ctranslate2 (>=4.0.0)', text)
                
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


def prompt_provider_choice(has_amd, has_nvidia, config):
    """Ask the user which provider to install. Returns the raw choice string."""
    opt_sys = platform.system()

    if "provider_choice" in config:
        choice = config["provider_choice"]
        colored_print(f"\n[Auto-Config] Using saved Provider Choice: [{choice}]", 10)
        return choice

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
    else:
        colored_print("   --> No dedicated GPU detected.", 10)
        colored_print("       Recommended: [5] CPU  (Faster-Whisper INT8, no GPU required)", 14)
    print("------------------------------\n")

    print("Select your execution provider:")
    print("  [1]  AMD ROCm (Windows/Linux) - Full support: Faster-Whisper, WhisperX, Transformers")
    print("  [2]  NVIDIA CUDA 12.1         - Modern NVIDIA GPUs (all engines)")
    print("  [3]  NVIDIA CUDA 11.8         - Older NVIDIA GPUs (all engines)")
    print("  [4]  CPU Only                 - No GPU, universal fallback")
    print()

    try:
        choice = input("Enter your choice (1-4): ").strip()
    except KeyboardInterrupt:
        print("\nInstallation cancelled.")
        sys.exit(0)

    config["provider_choice"] = choice
    return choice


def prompt_venv_setup(config) -> str:
    """
    Ask whether to create a virtual environment.
    Returns the Python executable to use for subsequent pip calls
    (either the venv python or the current sys.executable).
    Does NOT restart the script.
    """
    print("\n--- Virtual Environment ---")
    if "use_venv" in config:
        use_venv = config["use_venv"]
        colored_print(f"  [Auto-Config] Using saved Venv setup preference: {'Yes' if use_venv else 'No'}", 10)
    else:
        print("It is recommended to install dependencies inside a virtual environment.")
        try:
            ans = input("Create and use a venv in './venv'? (Y/n): ").strip().lower()
        except KeyboardInterrupt:
            print("\nInstallation cancelled.")
            sys.exit(0)
        use_venv = ans in ("", "y", "yes")
        config["use_venv"] = use_venv

    if use_venv:
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


def prompt_auth_setup(config):
    """Optionally configure HTTP basic auth for the API."""
    print("\n--- API Authentication ---")
    if "enable_auth" in config:
        enable_auth = config["enable_auth"]
        colored_print(f"  [Auto-Config] Using saved Auth setup preference: {'Yes' if enable_auth else 'No'}", 10)
    else:
        print("You can protect the web interface with a username and password.")
        try:
            ans = input("Enable HTTP authentication? (y/N): ").strip().lower()
        except KeyboardInterrupt:
            print("\nInstallation cancelled.")
            sys.exit(0)
        enable_auth = ans in ("y", "yes")
        config["enable_auth"] = enable_auth

    if enable_auth:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "AUTH_USERNAME=" in content:
                print("  Auth credentials already exist in .env. Skipping prompt.")
                return

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





def install():
    config = load_config()
    has_amd, has_nvidia = autodetect_hardware()

    # ── Step 1: choose provider ──────────────────────────────────────────────
    choice = prompt_provider_choice(has_amd, has_nvidia, config)

    # ── Step 2: venv and auth ──────────────────
    pip_exe = prompt_venv_setup(config)   # returns either venv python or sys.executable
    prompt_auth_setup(config)
    
    constraints_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "constraints.txt")

    # ── Step 4: install base backend packages ─────────────────────────────────
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")

    print("\n[1/2] Installing base dependencies...")
    subprocess.check_call([pip_exe, "-m", "pip", "install", "--upgrade", "-c", constraints_path, "-r", requirements_path])

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
                if "gpu_choice" in config:
                    gpu_choice = config["gpu_choice"]
                    colored_print(f"\n  [Auto-Config] Using saved GPU model choice: [{gpu_choice}]", 10)
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
                    config["gpu_choice"] = gpu_choice
                
                # We need GPU_MAP regardless of branch now to resolve the choice
                GPU_MAP = {
                    "1": ("RX 9070 / 9070 XT",  "gfx1201", "12.0.1"),
                    "2": ("RX 9060 (XT)",         "gfx1200", "12.0.0"),
                    "3": ("RX 7900 XTX/XT",       "gfx1100", "11.0.0"),
                    "4": ("RX 7800/7700 XT",       "gfx1101", "11.0.1"),
                    "5": ("RX 7600",               "gfx1102", "11.0.2"),
                    "6": ("RX 6900/6800/6700 XT",  "gfx1030", "10.3.0"),
                    "7": ("RX 6600",               "gfx1032", "10.3.2"),
                }
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
            colored_print(f"\n[ROCm] Installing official ctranslate2 4.8.0 ROCm wheel in final state...", 14)
            try:
                import urllib.request
                import zipfile
                zip_url = "https://github.com/OpenNMT/CTranslate2/releases/download/v4.8.0/rocm-python-wheels-Windows.zip"
                zip_path = os.path.join(os.path.dirname(pip_exe), "ct2_wheels.zip")
                urllib.request.urlretrieve(zip_url, zip_path)
                extract_dir = os.path.join(os.path.dirname(pip_exe), "ct2_wheels")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                import glob
                ct2_whl_list = glob.glob(os.path.join(extract_dir, "**", f"ctranslate2-4.8.0-{py_ver}-*.whl"), recursive=True)
                if not ct2_whl_list:
                    raise FileNotFoundError(f"Wheel not found for {py_ver}")
                ct2_whl = ct2_whl_list[0]
                
                subprocess.check_call([pip_exe, "-m", "pip", "install", "-c", constraints_path, "--no-cache-dir", ct2_whl])
                
                os.remove(zip_path)
                shutil.rmtree(extract_dir)
            except Exception as e:
                colored_print(f"[WARNING] ctranslate2 ROCm wheel download/install failed: {e} — will use default ctranslate2.", 9)
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
            
            subprocess.call([pip_exe, "-m", "pip", "uninstall", "-y", "ctranslate2"])
            colored_print(f"\n[ROCm] Installing official ctranslate2 4.8.0 ROCm wheel for Linux...", 14)
            try:
                import urllib.request
                import zipfile
                zip_url = "https://github.com/OpenNMT/CTranslate2/releases/download/v4.8.0/rocm-python-wheels-Linux.zip"
                zip_path = os.path.join(os.path.dirname(pip_exe), "ct2_wheels_linux.zip")
                urllib.request.urlretrieve(zip_url, zip_path)
                extract_dir = os.path.join(os.path.dirname(pip_exe), "ct2_wheels_linux")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                import glob
                ct2_whl_list = glob.glob(os.path.join(extract_dir, "**", f"ctranslate2-4.8.0-{py_ver}-*.whl"), recursive=True)
                if not ct2_whl_list:
                    raise FileNotFoundError(f"Wheel not found for {py_ver}")
                ct2_whl = ct2_whl_list[0]
                
                subprocess.check_call([pip_exe, "-m", "pip", "install", "-c", constraints_path, "--no-cache-dir", ct2_whl])
                
                os.remove(zip_path)
                shutil.rmtree(extract_dir)
            except Exception as e:
                colored_print(f"[WARNING] ctranslate2 ROCm wheel download/install failed: {e} — will use default ctranslate2.", 9)
                colored_print("  Faster-Whisper will still work but without ROCm GPU acceleration.", 9)
                subprocess.check_call([pip_exe, "-m", "pip", "install", "ctranslate2"])

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
        colored_print("\n>>> Installing PyTorch for CPU...", 10)
        subprocess.check_call([
            pip_exe, "-m", "pip", "install",
            "torch", "torchaudio"
        ])
    else:
        colored_print("\n>>> Installing PyTorch for CPU...", 10)
        subprocess.check_call([
            pip_exe, "-m", "pip", "install",
            "torch", "torchaudio"
        ])

    # ── Step 6: Install Native LLM (llama-cpp-python) ────────────────────────
    print("\n[3/3] Installing Native LLM Support (llama-cpp-python)...")
    
    if choice == "1":
        colored_print("   --> Installing llama-cpp-python official ROCm wheel...", 14)
        try:
            if platform.system() == "Windows":
                llama_whl = "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.32-hip-radeon/llama_cpp_python-0.3.32-py3-none-win_amd64.whl"
            else:
                llama_whl = "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.32-hip-radeon/llama_cpp_python-0.3.32-py3-none-manylinux_2_35_x86_64.whl"
            
            subprocess.check_call([
                pip_exe, "-m", "pip", "install", llama_whl, 
                "--no-cache-dir", "--force-reinstall", "--upgrade"
            ])
            colored_print("   --> Native LLM support installed successfully!", 10)
        except Exception as e:
            colored_print(f"\n[WARNING] Native LLM wheel installation failed: {e}", 9)
            colored_print("   AutoSubs AI will fall back to CPU-only NLLB for translations.", 14)
            subprocess.check_call([pip_exe, "-m", "pip", "install", "llama-cpp-python", "--no-cache-dir"])
    else:
        # Check for build tools on Windows before attempt
        if choice in ["2", "3"] and os.name == 'nt' and not check_compiler_present():
            colored_print("\n[CRITICAL ERROR] Compiler NOT found!", 9)
            print("To compile 'llama-cpp-python' with GPU support, you MUST have the correct compiler installed.")
            # Proceed to install CPU-only regardless to allow the app to boot
            subprocess.check_call([pip_exe, "-m", "pip", "install", "llama-cpp-python", "--no-cache-dir"])
            return 

        # Environment variables for compilation
        env = os.environ.copy()
        
        if choice in ["2", "3"]:
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
    save_config(config)
    print("\n=========================================")
    colored_print("Installation Complete!", 10)
    print("Start the app with: AutoSubsLauncher.bat or AutoSubsLauncher.sh")


if __name__ == "__main__":
    install()
