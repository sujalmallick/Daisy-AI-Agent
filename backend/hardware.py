import os
import shutil
import subprocess

def detect_hardware_tier() -> dict:
    """
    Auto-detects the host system hardware capabilities to configure optimal STT & compute:
      - Tier 1: NVIDIA GPU with CUDA (fastest, float16, 0% CPU load)
      - Tier 2: DirectML (AMD / Intel dedicated or integrated GPUs)
      - Tier 3: CPU-Only (8-bit quantized whisper, 4 threads, <250MB RAM)
    """
    # 1. Check for NVIDIA CUDA
    try:
        smi = shutil.which("nvidia-smi")
        if smi:
            res = subprocess.run([smi, "--query-gpu=name,driver_version", "--format=csv,noheader"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                gpu_name = res.stdout.strip().split(",")[0].strip()
                return {
                    "tier": 1,
                    "tier_name": "CUDA_GPU",
                    "device": "cuda",
                    "compute_type": "float16",
                    "description": f"NVIDIA GPU detected: {gpu_name}",
                    "gpu_name": gpu_name
                }
    except Exception:
        pass

    # 2. Check for DirectML / Windows graphics
    if os.name == "nt":
        try:
            import onnxruntime as ort
            if "DmlExecutionProvider" in ort.get_available_providers():
                return {
                    "tier": 2,
                    "tier_name": "DIRECTML",
                    "device": "directml",
                    "compute_type": "float16",
                    "description": "Windows DirectML GPU acceleration active (AMD/Intel)",
                    "gpu_name": "DirectML Adapter"
                }
        except Exception:
            pass

    # 3. Fallback to CPU-Only
    return {
        "tier": 3,
        "tier_name": "CPU_QUANTIZED",
        "device": "cpu",
        "compute_type": "int8",
        "description": "CPU multi-threaded 8-bit quantized execution",
        "gpu_name": None
    }

if __name__ == "__main__":
    hw = detect_hardware_tier()
    print(f"Hardware Tier: {hw['tier_name']} | Device: {hw['device']} ({hw['compute_type']}) | {hw['description']}")
