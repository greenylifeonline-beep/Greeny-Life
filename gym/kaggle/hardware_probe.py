#!/usr/bin/env python3
"""Hardware probe for Kaggle A/B and any other host.

GPU is measured, never inferred from account capability.
If no GPU: HARDWARE_STATE=CPU_ONLY and GPU_CAPACITY=NOT_PROVEN.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run(cmd: list[str], timeout: float = 3.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:
        return 1, type(exc).__name__


def _cpu() -> dict[str, Any]:
    model = platform.processor() or platform.machine()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                model = line.split(":", 1)[-1].strip()
                break
    count = os.cpu_count() or 0
    return {"cpu_model": model, "cpu_count": count}


def _ram() -> dict[str, Any]:
    meminfo = Path("/proc/meminfo")
    total = None
    free = None
    if meminfo.is_file():
        data = {}
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, _, rest = line.partition(":")
            parts = rest.split()
            if parts:
                data[key] = int(parts[0]) * 1024
        total = data.get("MemTotal")
        free = data.get("MemAvailable") or data.get("MemFree")
    return {"ram_total_bytes": total, "ram_free_bytes": free}


def _disk(path: str) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {"disk_total_bytes": usage.total, "disk_free_bytes": usage.free, "path": path}


def _gpu() -> dict[str, Any]:
    nvidia_dir = Path("/proc/driver/nvidia/gpus")
    nvidia_smi = shutil.which("nvidia-smi")
    gpu_count = 0
    names: list[str] = []
    vram_total: list[int | None] = []
    vram_free: list[int | None] = []
    if nvidia_dir.is_dir():
        gpu_count = sum(1 for _ in nvidia_dir.iterdir())
    if nvidia_smi:
        code, out = _run(
            [
                nvidia_smi,
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ]
        )
        if code == 0:
            rows = [ln.strip() for ln in out.splitlines() if ln.strip()]
            gpu_count = len(rows)
            for row in rows:
                parts = [p.strip() for p in row.split(",")]
                names.append(parts[0] if parts else "unknown")
                try:
                    vram_total.append(int(float(parts[1]) * 1024 * 1024) if len(parts) > 1 else None)
                except ValueError:
                    vram_total.append(None)
                try:
                    vram_free.append(int(float(parts[2]) * 1024 * 1024) if len(parts) > 2 else None)
                except ValueError:
                    vram_free.append(None)
    cuda = False
    torch_version = None
    try:
        import torch  # type: ignore

        torch_version = str(torch.__version__)
        cuda = bool(torch.cuda.is_available())
        if cuda and not names:
            gpu_count = int(torch.cuda.device_count())
            names = [torch.cuda.get_device_name(i) for i in range(gpu_count)]
    except Exception:
        pass
    has_gpu = gpu_count > 0 or cuda
    return {
        "accelerator_type": "GPU" if has_gpu else "CPU",
        "gpu_count": gpu_count,
        "gpu_name": names,
        "vram_total_per_gpu": vram_total,
        "vram_free_per_gpu": vram_free,
        "cuda_available": cuda,
        "torch_version": torch_version,
        "hardware_state": "GPU_PRESENT" if has_gpu else "CPU_ONLY",
        "gpu_capacity": "MEASURED" if has_gpu else "NOT_PROVEN",
    }


def _kaggle_fs() -> dict[str, Any]:
    working = Path("/kaggle/working")
    inp = Path("/kaggle/input")
    mounted = []
    if inp.is_dir():
        mounted = sorted(p.name for p in inp.iterdir())
    cap = _disk(str(working)) if working.exists() else {"disk_total_bytes": None, "disk_free_bytes": None, "path": "/kaggle/working"}
    return {
        "kaggle_working_exists": working.exists(),
        "kaggle_input_exists": inp.exists(),
        "kaggle_working_capacity": cap,
        "kaggle_input_mounted_assets": mounted,
        "kaggle_kernel_run_type": os.environ.get("KAGGLE_KERNEL_RUN_TYPE"),
        "kaggle_kernel_id": os.environ.get("KAGGLE_KERNEL_ID") or os.environ.get("KAGGLE_DATASET_ID"),
    }


def probe(worker_id: str = "UNKNOWN") -> dict[str, Any]:
    cpu = _cpu()
    ram = _ram()
    gpu = _gpu()
    kaggle = _kaggle_fs()
    root_disk = _disk("/")
    rec = {
        "schema": "raios.kaggle-hardware-probe.v1",
        "worker_id": worker_id,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu_model": cpu["cpu_model"],
        "cpu_count": cpu["cpu_count"],
        "ram_total": ram["ram_total_bytes"],
        "ram_free": ram["ram_free_bytes"],
        "accelerator_type": gpu["accelerator_type"],
        "gpu_count": gpu["gpu_count"],
        "gpu_name": gpu["gpu_name"],
        "vram_total_per_gpu": gpu["vram_total_per_gpu"],
        "vram_free_per_gpu": gpu["vram_free_per_gpu"],
        "cuda_availability": gpu["cuda_available"],
        "torch_version": gpu["torch_version"],
        "disk_total": root_disk["disk_total_bytes"],
        "disk_free": root_disk["disk_free_bytes"],
        "/kaggle/working_capacity": kaggle["kaggle_working_capacity"],
        "/kaggle/input_mounted_assets": kaggle["kaggle_input_mounted_assets"],
        "session_runtime_identity": {
            "hostname": socket.gethostname(),
            "kaggle_kernel_run_type": kaggle["kaggle_kernel_run_type"],
            "kaggle_kernel_id": kaggle["kaggle_kernel_id"],
            "cwd": str(Path.cwd()),
        },
        "hardware_state": gpu["hardware_state"],
        "gpu_capacity": gpu["gpu_capacity"],
        "on_kaggle": bool(kaggle["kaggle_working_exists"] or kaggle["kaggle_kernel_run_type"]),
        "is_c5": False,
        "gl005_proven": False,
        "law": [
            "ACCOUNT_CAPABILITY_NE_SESSION_GPU",
            "NO_GPU_MEANS_CPU_ONLY",
            "WORKER_NE_C5",
        ],
    }
    return rec


def main() -> int:
    worker = os.environ.get("RAIOS_KAGGLE_WORKER") or (sys.argv[1] if len(sys.argv) > 1 else "UNKNOWN")
    rec = probe(worker)
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
