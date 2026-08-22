"""Merge executor. Refuses weight merge on this host."""
from __future__ import annotations

from typing import Any


def execute(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "executed": False,
        "reason": "MERGE_FORBIDDEN_HERE",
        "plan_id": plan.get("id"),
        "strategy": plan.get("strategy"),
        "weights_touched": False,
        "downloaded": False,
        "gl005_proven": False,
        "law": [
            "NO_NEW_LOCAL_MODEL_DOWNLOADS",
            "MERGE_DECLARATION_NE_MERGE_EXECUTION",
            "DESTRUCTIVE_MERGE_FORBIDDEN",
        ],
    }
