"""Canary model registry. Empty until a merge/eval produces a candidate."""
from __future__ import annotations

from typing import Any


def snapshot() -> dict[str, Any]:
    return {
        "canaries": [],
        "promoted": [],
        "automatic_promotion": False,
        "gl005_proven": False,
        "law": ["NO_AUTO_CANONICAL_PROMOTION"],
    }


def register(model_id: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": "NO_EVALED_CANARY",
        "model_id": model_id,
        "automatic_promotion": False,
    }
