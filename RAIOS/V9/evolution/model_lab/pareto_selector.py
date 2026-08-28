"""Pareto selector. Refuses to pick a winner without hardware + eval evidence."""
from __future__ import annotations

from typing import Any


def select(candidates: list[dict[str, Any]], hardware: dict[str, Any] | None = None) -> dict[str, Any]:
    hardware = hardware or {}
    gpu = hardware.get("gpu_capacity")
    return {
        "winner": None,
        "reason": "HARDWARE_OR_EVAL_INCOMPLETE" if gpu != "MEASURED" else "EVAL_AXES_UNKNOWN",
        "candidates": [c.get("id") or c.get("model_id") for c in candidates],
        "gpu_capacity": gpu,
        "gl005_proven": False,
    }
