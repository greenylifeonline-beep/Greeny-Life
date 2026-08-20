"""Main Cortex belongs to C1: treat, run, or throw.

Executor isolation is not disposal. Executor never throws. Identity is not swapped
to a tiny student. This host does not load cortex weights.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

CORTEX_IDENTITY = "qwen3.6:35b-a3b"
OWNER = "C1"
VERBS = ("treat", "run", "throw")
MIN_RAM_GB_FOR_CORTEX = 24.0

LAWS = (
    "C1_OWNS_CORTEX_TREAT_RUN_THROW",
    "EXECUTOR_NE_THROW_CORTEX",
    "EXECUTOR_NE_ISOLATE_AS_DISPOSAL",
    "HOLD_NE_THROW",
    "CORTEX_RUN_REQUIRES_C1",
    "STUDENT_NE_MAIN_CORTEX",
    "TINY_QWEN_NE_CORTEX_IDENTITY",
    "CUSTOMER_LANGUAGE_NE_CORTEX",
    "HF_WEIGHTS_NE_IN_SECRET_REPO",
)

_TRUE = {"1", "true", "yes", "on"}


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUE


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
        total = info.get("MemTotal")
        free_gb = info.get("MemAvailable")
        if free_gb is None:
            free_gb = info.get("MemFree")
        if total is None and free_gb is None:
            return None
        return {"total_gb": total, "free_gb": free_gb}
    except OSError:
        return None


def _gpu_present() -> bool:
    nvidia = Path("/proc/driver/nvidia/gpus")
    if nvidia.is_dir() and any(nvidia.iterdir()):
        return True
    return shutil.which("nvidia-smi") is not None


def host_can_run(*, min_free_gb: float = MIN_RAM_GB_FOR_CORTEX) -> tuple[bool, str]:
    if not _gpu_present():
        return False, "HOST_NO_GPU"
    mem = _linux_memory()
    free_gb = None if mem is None else mem.get("free_gb")
    if free_gb is None:
        return False, "HOST_RAM_UNKNOWN"
    if float(free_gb) < float(min_free_gb):
        return False, "HOST_RAM_INSUFFICIENT"
    return True, "HOST_CAN_RUN_CORTEX"


def status(*, min_free_gb: float = MIN_RAM_GB_FOR_CORTEX) -> dict[str, Any]:
    thrown = _flag("C1_CORTEX_THROW")
    run_granted = _flag("C1_CORTEX_RUN")
    can, host_reason = host_can_run(min_free_gb=min_free_gb)
    hold = (not thrown) and not (run_granted and can)
    mem = _linux_memory()
    return {
        "schema": "raios.cortex.v1",
        "owner": OWNER,
        "verbs": list(VERBS),
        "identity": CORTEX_IDENTITY,
        "isolated_as_disposal": False,
        "hold": hold,
        "thrown": thrown,
        "run_granted": run_granted,
        "host_can_run": can,
        "host_reason": host_reason,
        "ram_total_gb": None if mem is None else mem.get("total_gb"),
        "ram_free_gb": None if mem is None else mem.get("free_gb"),
        "gpu": _gpu_present(),
        "law": list(LAWS),
        "gl005_proven": False,
    }


def gate_run(*, min_free_gb: float = MIN_RAM_GB_FOR_CORTEX) -> dict[str, Any]:
    st = status(min_free_gb=min_free_gb)
    if st["thrown"]:
        reason = "CORTEX_THROWN_BY_C1"
        admitted = False
    elif not st["run_granted"]:
        reason = "CORTEX_HOLD_AWAITING_C1_RUN"
        admitted = False
    elif not st["host_can_run"]:
        reason = "HOST_CANNOT_RUN_CORTEX"
        admitted = False
    else:
        reason = "C1_CORTEX_RUN"
        admitted = True
    return {
        "admitted": admitted,
        "reason": reason,
        "fallback": None if admitted else "deterministic_pipeline",
        **st,
    }


def treat() -> dict[str, Any]:
    """C1 treat path: diagnose weakness. Does not load weights, run, or throw."""
    st = status()
    gate = gate_run()
    return {
        "schema": "raios.cortex-treat.v1",
        "ok": True,
        "verb": "treat",
        "owner": OWNER,
        "identity": CORTEX_IDENTITY,
        "loaded": False,
        "thrown": False,
        "run": False,
        "isolated_as_disposal": False,
        "weakness": [
            "used_as_silent_live_spine_without_c1_run",
            "identity_swap_temptation_tiny_qwen",
            "this_host_cannot_load_35b",
        ],
        "repair": [
            "c1_owns_treat_run_throw",
            "hold_is_not_throw",
            "deterministic_neurolingua_until_c1_run",
            "student_ne_cortex_identity",
        ],
        "status": st,
        "gate": {k: gate[k] for k in ("admitted", "reason", "fallback")},
        "law": list(LAWS),
        "gl005_proven": False,
    }


def refuse_throw() -> dict[str, Any]:
    return {
        "ok": False,
        "verb": "throw",
        "error": "EXECUTOR_NE_THROW_CORTEX",
        "owner": OWNER,
        "identity": CORTEX_IDENTITY,
        "isolated_as_disposal": False,
        "law": list(LAWS),
        "gl005_proven": False,
    }


def public_fields(st: dict[str, Any] | None = None) -> dict[str, Any]:
    row = st or status()
    return {
        "cortex_identity": CORTEX_IDENTITY,
        "cortex_owner": OWNER,
        "cortex_verbs": list(VERBS),
        "isolated_as_disposal": False,
        "cortex_hold": bool(row.get("hold")),
        "cortex_thrown": bool(row.get("thrown")),
        "cortex_isolated": False,
        "run_granted": bool(row.get("run_granted")),
        "host_can_run": bool(row.get("host_can_run")),
        "host_reason": row.get("host_reason"),
    }
