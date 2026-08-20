from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from typing import Any

from .cortex import CORTEX_IDENTITY, gate_run, public_fields, status as cortex_status


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


def _linux_memory() -> dict[str, float] | None:
    try:
        info: dict[str, float] = {}
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                parts = rest.split()
                if not parts:
                    continue
                info[key] = float(parts[0]) / (1024 ** 2)
        free_gb = info.get("MemAvailable")
        if free_gb is None:
            free_gb = info.get("MemFree")
        if free_gb is None:
            return None
        return {
            "total_gb": info.get("MemTotal"),
            "free_gb": free_gb,
            "load": None,
        }
    except Exception:
        return None


def _host_memory() -> dict[str, float] | None:
    if os.name == "nt":
        return _windows_memory()
    return _linux_memory()


class CognitiveResourceGovernor:
    """Admission control. C1 owns treat/run/throw. Hold is not throw. Identity is not swapped."""

    def __init__(self, min_free_gb_for_cortex: float = 24.0):
        self.min_free_gb_for_cortex = min_free_gb_for_cortex
        self.main_cortex_identity = CORTEX_IDENTITY
        self.cortex_isolated = False

    def snapshot(self) -> dict[str, Any]:
        mem = _host_memory()
        st = cortex_status(min_free_gb=self.min_free_gb_for_cortex)
        return {
            "memory": mem,
            "cortex_identity": self.main_cortex_identity,
            "cortex_owner": "C1",
            "isolated_as_disposal": False,
            "cortex_hold": st["hold"],
            "cortex_isolated": False,
            "ollama_num_parallel": os.environ.get("OLLAMA_NUM_PARALLEL"),
            "ollama_max_loaded_models": os.environ.get("OLLAMA_MAX_LOADED_MODELS"),
            "keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE"),
            **public_fields(st),
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
        gate = gate_run(min_free_gb=self.min_free_gb_for_cortex)
        return AdmissionDecision(
            bool(gate["admitted"]),
            str(gate["reason"]),
            float(free_gb) if free_gb is not None else None,
            gate.get("fallback"),
        )
