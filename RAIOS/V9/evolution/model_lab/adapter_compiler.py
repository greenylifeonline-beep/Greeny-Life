"""Distillation / adapter compiler. Declaration only."""
from __future__ import annotations

from typing import Any


def compile_adapter(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "compiled": False,
        "reason": "ADAPTER_COMPILE_FORBIDDEN_UNTIL_LAB_EVAL",
        "plan_id": plan.get("id"),
        "peft_installed": False,
        "gl005_proven": False,
    }
