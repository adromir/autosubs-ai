import os

# Clear environment variables so PyTorch can see all physical devices
os.environ.pop("HIP_VISIBLE_DEVICES", None)
os.environ.pop("CUDA_VISIBLE_DEVICES", None)

import torch
from pathlib import Path

def update_env_file(key, value):
    env_path = Path(__file__).parent.parent / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            updated = True
            break
            
    if not updated:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append(f"{key}={value}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def main():
    print("\n\033[1;36m[INFO] Detecting available GPU devices...\033[0m")
    
    if not torch.cuda.is_available():
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print("Apple Silicon (MPS) detected. GPU configuration not required.")
            return
        print("No CUDA/ROCm compatible GPUs detected by PyTorch.")
        return
        
    count = torch.cuda.device_count()
    print("\nAvailable GPUs:")
    for i in range(count):
        print(f"  [{i}] {torch.cuda.get_device_name(i)}")
        
    print("\nEnter the ID(s) of the GPU(s) you want to use.")
    print("For multiple GPUs, separate IDs with commas (e.g., '0,1').")
    print("\033[1;33mWarning: If you have an integrated GPU (like AMD Radeon Graphics), do NOT select it unless it is your only GPU.\033[0m")
    
    while True:
        selection = input("\nSelected GPU IDs (default: 0): ").strip()
        
        if not selection:
            selection = "0"
            
        # Validate
        parts = [p.strip() for p in selection.split(",")]
        valid = True
        for p in parts:
            if not p.isdigit() or int(p) < 0 or int(p) >= count:
                print(f"[ERROR] Invalid GPU ID: '{p}'. Must be a number between 0 and {count-1}.")
                valid = False
                break
                
        if valid:
            update_env_file("HIP_VISIBLE_DEVICES", selection)
            update_env_file("CUDA_VISIBLE_DEVICES", selection)
            print(f"\n\033[1;32m[SUCCESS] GPU configuration saved! (Devices: {selection})\033[0m")
            break

if __name__ == "__main__":
    main()
