"""Regression / forgetting lab. Foundation only."""
from __future__ import annotations

from typing import Any


def regress(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": "NO_MERGED_MODEL_TO_REGRESS",
        "before_id": before.get("id"),
        "after_id": after.get("id"),
        "forgetting": "NOT_MEASURED",
        "gl005_proven": False,
    }
