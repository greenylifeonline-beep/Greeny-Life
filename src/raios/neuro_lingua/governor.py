from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    reason: str
    ram_free_gb: float | None
    fallback: str | None


def _windows_memory() -> dict[str, float] | None:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)) == 0:
            return None
        return {
            "total_gb": stat.ullTotalPhys / (1024 ** 3),
            "free_gb": stat.ullAvailPhys / (1024 ** 3),
            "load": float(stat.dwMemoryLoad),
        }
    except Exception:
        return None


class CognitiveResourceGovernor:
    """Admission control wrapping observed RAM/A17 snapshots. Does not redefine Main Cortex."""

    def __init__(self, min_free_gb_for_cortex: float = 3.0):
        self.min_free_gb_for_cortex = min_free_gb_for_cortex
        self.main_cortex_identity = "RAIOS_MAIN_CORTEX"

    def snapshot(self) -> dict[str, Any]:
        mem = _windows_memory() if os.name == "nt" else None
        return {
            "memory": mem,
            "ollama_num_parallel": os.environ.get("OLLAMA_NUM_PARALLEL"),
            "ollama_max_loaded_models": os.environ.get("OLLAMA_MAX_LOADED_MODELS"),
            "keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE"),
        }

    def admit(self, capability: str, offline_ok: bool = True) -> AdmissionDecision:
        snap = self.snapshot()
        mem = snap.get("memory") or {}
        free_gb = mem.get("free_gb")
        cortex_caps = {
            "SEMANTIC_INTERPRETATION",
            "SEMANTIC_REALIZATION",
            "SEMANTIC_VERIFICATION",
            "PRAGMATIC_INTERPRETATION",
        }
        if capability not in cortex_caps:
            return AdmissionDecision(True, "DETERMINISTIC_OR_LOCAL", free_gb, None)
        if free_gb is None:
            return AdmissionDecision(False, "MEMORY_TELEMETRY_UNKNOWN", None, "deterministic_pipeline")
        if free_gb < self.min_free_gb_for_cortex:
            return AdmissionDecision(
                False,
                "MEMORY_CAPACITY_DENIED",
                float(free_gb),
                "deterministic_pipeline",
            )
        return AdmissionDecision(True, "CORTEX_ADMITTED", float(free_gb), None)
