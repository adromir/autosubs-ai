#!/bin/bash
# Author: Adromir
# Description: Automated interactive installation of ROCm in WSL, ctranslate2 with ROCm support,
#              faster-whisper, whisperX and the full AutoSubs AI backend stack.
# Distro: AutoSubsAI-Ubuntu (isolated from any other Ubuntu 24.04 installations)

set -e

GFX_ARCHITECTURE=""
HSA_OVERRIDE=""
UBUNTU_CODENAME=$(lsb_release -cs)
ENV_FILE="$HOME/whisper_wsl.env"
VENV_DIR="$HOME/whisper_wsl_env"

prompt_gpu_selection() {
    echo ""
    echo "=========================================="
    echo "  AutoSubs AI - WSL ROCm GPU Selector"
    echo "=========================================="
    echo "Please select your Graphics Card:"
    echo "  1) RX 9700 / 9070 (XT)"
    echo "  2) RX 9060 (XT)"
    echo "  3) RX 7900 XTX/XT"
    echo "  4) RX 7800/7700 XT"
    echo "  5) RX 7600"
    echo "  6) RX 6900/6800/6700"
    echo "  7) RX 6600"
    read -p "Enter the number of your GPU: " gpu_choice

    case $gpu_choice in
        1)
            GFX_ARCHITECTURE="gfx1201"
            HSA_OVERRIDE="12.0.1"
            ;;
        2)
            GFX_ARCHITECTURE="gfx1200"
            HSA_OVERRIDE="12.0.0"
            ;;
        3)
            GFX_ARCHITECTURE="gfx1100"
            HSA_OVERRIDE="11.0.0"
            ;;
        4)
            GFX_ARCHITECTURE="gfx1101"
            HSA_OVERRIDE="11.0.1"
            ;;
        5)
            GFX_ARCHITECTURE="gfx1102"
            HSA_OVERRIDE="11.0.2"
            ;;
        6)
            GFX_ARCHITECTURE="gfx1030"
            HSA_OVERRIDE="10.3.0"
            ;;
        7)
            GFX_ARCHITECTURE="gfx1032"
            HSA_OVERRIDE="10.3.2"
            ;;
        *)
            echo "Invalid selection. Exiting."
            exit 1
            ;;
    esac

    echo ""
    echo "  Selected Architecture : $GFX_ARCHITECTURE"
    echo "  HSA Override          : $HSA_OVERRIDE"
    echo ""
}

install_rocm() {
    echo "--- [1/5] Installing ROCm 7.2 for WSL ---"
    sudo apt-get update
    sudo apt-get install -y wget curl gnupg2 dkms lsb-release

    local deb_file="amdgpu-install_7.2.70200-1_all.deb"
    wget "https://repo.radeon.com/amdgpu-install/7.2/ubuntu/${UBUNTU_CODENAME}/${deb_file}"
    sudo apt-get install -y "./${deb_file}"
    rm "./${deb_file}"

    # --no-dkms is required in WSL (no kernel module compilation)
    sudo amdgpu-install -y --usecase=wsl,rocm --no-dkms
}

install_dependencies() {
    echo "--- [2/5] Installing Build Dependencies ---"
    sudo apt-get install -y \
        cmake build-essential libopenblas-dev git \
        python3-pip python3-venv python3-dev \
        ffmpeg \
        rocthrust-dev
    # rocthrust-dev provides the thrust:: namespace headers for ROCm
    # Without it, thrust::counting_iterator is not found (only rocprim:: is visible)
}

patch_sources() {
    echo "  [Patch] Applying ROCm 7.x compatibility patches..."
    local SRC="$HOME/CTranslate2-rocm"

    # ── Patch 1: ALL source files — thrust::counting_iterator → rocprim:: ────
    # thrust::counting_iterator is NOT in rocThrust for ROCm 7.x.
    # rocprim::counting_iterator IS the correct drop-in (same template interface).
    #
    # IMPORTANT: thrust::make_transform_iterator MUST stay as thrust::
    # rocprim::make_transform_iterator requires __device__ annotated functors,
    # but ctranslate2 functors (e.g. exp_minus_max_func) are not annotated.
    echo "  [Patch 1/4] Replacing thrust::counting_iterator in all sources..."
    find "${SRC}/src" \( -name "*.cu" -o -name "*.h" \) | while read -r f; do
        # Revert any previous wrong make_transform_iterator replacement
        if grep -q "rocprim::make_transform_iterator" "${f}" 2>/dev/null; then
            sed -i 's/rocprim::make_transform_iterator/thrust::make_transform_iterator/g' "${f}"
            echo "    reverted make_transform_iterator in: $(basename ${f})"
        fi
        # Replace ONLY counting_iterator
        if grep -q "thrust::counting_iterator" "${f}" 2>/dev/null; then
            if ! grep -q "rocprim/rocprim.hpp" "${f}"; then
                sed -i '1s|^|#include <rocprim/rocprim.hpp>\n|' "${f}"
            fi
            sed -i 's/thrust::counting_iterator/rocprim::counting_iterator/g' "${f}"
            echo "    patched: $(basename ${f})"
        fi
    done
    echo "  [Patch 1/4] counting_iterator -> rocprim:: OK"

    # ── Patch 2: primitives.cu — fix counting_iterator + add thrust headers ─
    # IMPORTANT: thrust::reduce and thrust::max_element MUST stay as thrust::
    # because they use the THRUST_CALL execution-policy API.  rocprim::reduce
    # has a completely different signature (storage, size, stream, ...).
    # We only need to add missing #includes so rocThrust resolves them.
    local PRIM="${SRC}/src/cuda/primitives.cu"
    # Revert any wrong rocprim::reduce/max_element replacements from previous runs
    sed -i 's/rocprim::reduce\b/thrust::reduce/g'       "${PRIM}" 2>/dev/null || true
    sed -i 's/rocprim::max_element\b/thrust::max_element/g' "${PRIM}" 2>/dev/null || true
    # Fix counting_iterator (this one IS correct as rocprim::)
    if grep -q "thrust::counting_iterator" "${PRIM}" 2>/dev/null; then
        sed -i 's/thrust::counting_iterator/rocprim::counting_iterator/g' "${PRIM}"
    fi
    # Add explicit thrust headers if missing
    if ! grep -q "thrust/reduce.h" "${PRIM}"; then
        sed -i '1s|^|#include <thrust/reduce.h>\n#include <thrust/extrema.h>\n#include <rocprim/rocprim.hpp>\n|' "${PRIM}"
    fi
    echo "  [Patch 2/4] primitives.cu: headers + iterators OK"

    # ── Patch 3: utils.h — hipBLAS API renames in ROCm 7.x ──────────────────
    # hipblasGemmEx_v2           → hipblasGemmEx_64
    # hipblasGemmStridedBatchedEx_v2 → hipblasGemmStridedBatchedEx_64
    local UTILS="${SRC}/src/cuda/utils.h"
    local patched=0
    if grep -q "hipblasGemmEx_v2" "${UTILS}" 2>/dev/null; then
        sed -i 's/hipblasGemmEx_v2/hipblasGemmEx_64/g' "${UTILS}"
        patched=1
    fi
    if grep -q "hipblasGemmStridedBatchedEx_v2" "${UTILS}" 2>/dev/null; then
        sed -i 's/hipblasGemmStridedBatchedEx_v2/hipblasGemmStridedBatchedEx_64/g' "${UTILS}"
        patched=1
    fi
    if [ $patched -eq 1 ]; then
        echo "  [Patch 3/4] utils.h: hipblas *_v2 -> *_64 OK"
    else
        echo "  [Patch 3/4] utils.h: already patched, skipping"
    fi

    # ── Patch 4: primitives.cu — hipBLAS _v2 renames (also in .cu) ──────────
    if grep -q "hipblasGemmEx_v2\|hipblasGemmStridedBatchedEx_v2" "${PRIM}" 2>/dev/null; then
        sed -i 's/hipblasGemmEx_v2/hipblasGemmEx_64/g' "${PRIM}"
        sed -i 's/hipblasGemmStridedBatchedEx_v2/hipblasGemmStridedBatchedEx_64/g' "${PRIM}"
        echo "  [Patch 4/4] primitives.cu: hipblas *_v2 -> *_64 OK"
    else
        echo "  [Patch 4/4] primitives.cu: already patched, skipping"
    fi

    echo "  [Patch] All ROCm 7.x patches applied."
}

compile_ctranslate2() {
    echo "--- [3/5] Cloning and Compiling CTranslate2 (arlo-phoenix ROCm fork) ---"
    # Use an absolute path variable to avoid fragile relative-cd chains.
    local CT2_DIR="$HOME/CTranslate2-rocm"

    if [ ! -d "${CT2_DIR}/.git" ]; then
        # Directory missing OR exists but isn't a git repo — (re)clone it.
        echo "  Cloning arlo-phoenix/CTranslate2-rocm..."
        rm -rf "${CT2_DIR}"
        git clone --recurse-submodules \
            https://github.com/arlo-phoenix/CTranslate2-rocm.git "${CT2_DIR}"
    else
        echo "  Repo already exists, pulling latest..."
        git -C "${CT2_DIR}" pull
        git -C "${CT2_DIR}" submodule update --init --recursive
    fi

    # Apply ROCm 7.x compatibility patches BEFORE cmake
    patch_sources

    # Always start from a clean build dir to avoid stale CMakeCache
    rm -rf "${CT2_DIR}/build"
    mkdir -p "${CT2_DIR}/build"
    cd "${CT2_DIR}/build"

    export HSA_OVERRIDE_GFX_VERSION="${HSA_OVERRIDE}"
    export AMDGPU_TARGETS="${GFX_ARCHITECTURE}"
    export ROCM_AMDGPU_TARGETS="${GFX_ARCHITECTURE}"
    export ROCM_PATH="/opt/rocm"

    cmake .. \
        -DWITH_HIP=ON \
        -DWITH_MKL=OFF \
        -DWITH_OPENBLAS=ON \
        -DCMAKE_HIP_ARCHITECTURES="${GFX_ARCHITECTURE}" \
        -DCMAKE_BUILD_TYPE=Release \
        -DOPENMP_RUNTIME=COMP \
        -DCMAKE_CXX_STANDARD=17 \
        -DCMAKE_CXX_FLAGS="-I/opt/rocm/include" \
        -DCMAKE_HIP_FLAGS="-I/opt/rocm/include" \
        -DCMAKE_HIP_COMPILER="/opt/rocm/lib/llvm/bin/clang++" \
        -DCMAKE_CXX_COMPILER="/opt/rocm/lib/llvm/bin/clang++" \
        -DCMAKE_C_COMPILER="/opt/rocm/lib/llvm/bin/clang" \
        -DCMAKE_PREFIX_PATH="/opt/rocm" \
        -DBUILD_CLI=OFF

    make -j$(nproc)
    sudo make install
}

setup_python_environment() {
    echo "--- [4/5] Setting Up Python Environment ---"
    cd "$HOME"

    python3 -m venv "${VENV_DIR}"
    source "${VENV_DIR}/bin/activate"

    export CTRANSLATE2_ROOT="/usr/local"
    export LD_LIBRARY_PATH="/usr/local/lib:$LD_LIBRARY_PATH"

    pip install --upgrade pip wheel setuptools
    pip install pybind11 pybind11-global
    # --no-build-isolation: use venv's pybind11 instead of an isolated build env
    # that doesn't have access to the already-installed pybind11 package.
    CTRANSLATE2_ROOT=/usr/local \
    pip install --no-build-isolation "$HOME/CTranslate2-rocm/python"

    # Install ROCm PyTorch (Linux/manylinux wheels from AMD)
    pip install --no-cache-dir --no-deps \
        --find-links "https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2/" \
        torch torchaudio || \
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/rocm6.2

    # Install Whisper engines WITHOUT letting pip replace our custom ctranslate2.
    # faster-whisper and whisperx both require ctranslate2>=4.5.0 from PyPI, but
    # our ROCm build is 4.1.0. The API is compatible — we just skip their ctranslate2 dep.
    pip install --no-deps faster-whisper
    pip install --no-deps whisperx

    # Install pyannote.audio (whisperx diarization dependency) and its deps
    pip install pyannote.audio onnxruntime

    # Install AutoSubs AI backend dependencies (updated versions to avoid conflicts)
    pip install \
        "fastapi>=0.110.0" "uvicorn>=0.31.1" ffmpeg-python==0.2.0 \
        "transformers>=4.40.0" "accelerate>=0.28.0" "pysubs2>=1.7.0" \
        "sse-starlette>=2.0.0" "pydantic>=2.7.0" "python-multipart>=0.0.9" \
        python-dotenv==1.0.1 "hf-transfer>=0.1.9" requests plyer \
        charset-normalizer silero-vad

    # Verify ctranslate2 is still our ROCm build (not overwritten by PyPI)
    echo "  CTranslate2 installed: $(pip show ctranslate2 | grep Version)"

    echo "  Python environment ready at: ${VENV_DIR}"
}

save_env_config() {
    echo "--- [5/5] Saving GPU Configuration ---"
    cat > "${ENV_FILE}" <<EOF
# AutoSubs AI WSL Environment Configuration
# Generated by setup_wsl_rocm.sh — do not edit manually
GFX_ARCHITECTURE=${GFX_ARCHITECTURE}
HSA_OVERRIDE_GFX_VERSION=${HSA_OVERRIDE}
ROCM_PATH=/opt/rocm
CTRANSLATE2_ROOT=/usr/local
LD_LIBRARY_PATH=/usr/local/lib:/opt/rocm/lib:/opt/rocm/lib/llvm/lib
VENV_DIR=${VENV_DIR}
EOF
    echo "  Configuration saved to: ${ENV_FILE}"
}

main() {
    prompt_gpu_selection
    install_rocm
    install_dependencies
    compile_ctranslate2
    setup_python_environment
    save_env_config

    echo ""
    echo "=========================================="
    echo "  AutoSubs AI WSL Setup Complete!"
    echo "=========================================="
    echo "  Venv     : ${VENV_DIR}"
    echo "  Env File : ${ENV_FILE}"
    echo ""
    echo "  Run the backend from Windows using:"
    echo "  scripts\\Start-WSL-Backend.ps1"
    echo ""
}

main
