"""Merge strategies as capability declarations. Not an installed toolkit."""
from __future__ import annotations

from typing import Any

STRATEGIES = (
    "LINEAR",
    "SLERP",
    "TIES",
    "DARE",
    "SCE",
    "TASK_ARITHMETIC",
    "LAYER_BLOCK_MERGE",
    "LORA_MERGE",
    "ADAPTER_FUSION",
    "CUSTOM",
)

TOOL_TOURNAMENT = (
    {"id": "mergekit", "install": False, "justified": False, "role": "CANDIDATE"},
    {"id": "peft", "install": False, "justified": False, "role": "CANDIDATE"},
    {"id": "safetensors", "install": False, "justified": False, "role": "CANDIDATE"},
    {"id": "transformers", "install": False, "justified": False, "role": "CANDIDATE"},
    {"id": "accelerate", "install": False, "justified": False, "role": "CANDIDATE"},
    {"id": "optuna", "install": False, "justified": False, "role": "CANDIDATE"},
    {"id": "lm-evaluation-harness", "install": False, "justified": False, "role": "CANDIDATE"},
    {"id": "ray-tune", "install": False, "justified": False, "role": "NOT_JUSTIFIED_AT_THIS_SCALE"},
)


def declarations() -> dict[str, Any]:
    return {
        "strategies": list(STRATEGIES),
        "installed_blindly": False,
        "tools": list(TOOL_TOURNAMENT),
        "execution": "FORBIDDEN_HERE",
        "gl005_proven": False,
    }
