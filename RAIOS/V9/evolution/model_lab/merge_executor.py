"""Governed Model Lab executor; defaults to refusal and dry-run."""
from __future__ import annotations

from typing import Any


def execute(plan: dict[str, Any]) -> dict[str, Any]:
    strategy = str(plan.get("strategy") or "").upper()
    if strategy == "LINEAR" and plan.get("inputs"):
        from .weight_merge_runtime import execute_cpu_linear

        result = execute_cpu_linear(plan)
        return {"plan_id": plan.get("id"), "strategy": strategy, **result}
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
            "EXPLICIT_AUTHORITY_REQUIRED",
        ],
    }
