"""Evaluation lab. Declares required axes. Does not run harness here."""
from __future__ import annotations

from typing import Any

from .model_registry import AXES


def evaluate(model_id: str) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "harness": "NOT_RUN",
        "axes": {axis: "UNKNOWN" for axis in AXES},
        "lm_eval": False,
        "gl005_proven": False,
    }
