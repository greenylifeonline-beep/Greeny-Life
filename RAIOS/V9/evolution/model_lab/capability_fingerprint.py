"""Capability fingerprints. Unknown until measured. Never invent scores."""
from __future__ import annotations

from typing import Any

from .model_registry import AXES


def fingerprint(model_id: str, *, measured: dict[str, Any] | None = None) -> dict[str, Any]:
    measured = measured or {}
    axes = {}
    for axis in AXES:
        axes[axis] = measured.get(axis, "UNKNOWN")
    return {
        "model_id": model_id,
        "axes": axes,
        "winner": False,
        "evidence": measured.get("evidence") or [],
        "gl005_proven": False,
    }


def catalog(model_ids: list[str], live_generate: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    live_generate = live_generate or {}
    out = []
    for mid in model_ids:
        measured = {}
        gen = live_generate.get(mid)
        if gen:
            measured = {
                "latency": gen.get("latency_class") or "UNKNOWN",
                "evidence": [f"generate_code={gen.get('code')}"],
            }
            if gen.get("ok"):
                measured["reasoning"] = "UNSCORED_GENERATE_OK"
        out.append(fingerprint(mid, measured=measured))
    return out
