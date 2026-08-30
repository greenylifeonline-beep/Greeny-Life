"""Merge strategies as canonical capability/ownership declarations.

This module declares which strategy owns each merge method. It does not
activate weight merging on the control-plane host; execution remains gated
by merge_executor.py.
"""
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

# Assimilated from the proven Weight-Merge-Lab registry (17 passing tests).
# One method -> one owner. LINEAR is intentionally not flattened into the
# generic MergeKit strategy even when MergeKit is the eventual backend.
STRATEGY_OWNERS = {
    "LINEAR": "LinearStrategy",
    "SLERP": "MergeKitStrategy",
    "NUSLERP": "MergeKitStrategy",
    "TIES": "MergeKitStrategy",
    "DARE_LINEAR": "MergeKitStrategy",
    "DARE_TIES": "MergeKitStrategy",
    "SCE": "MergeKitStrategy",
    "TASK_ARITHMETIC": "MergeKitStrategy",
}

REGISTRY_WIRING = {
    "product_registry": "StrategyRegistry.default",
    "build_default_registry": "StrategyRegistry.default",
    "linear_backend": "MergeKitStrategy",
    "backend_absent": "NOT_IMPLEMENTED",
    "false_success_forbidden": True,
    "duplicate_product_registry": False,
}

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


def owner_for(method: str) -> str | None:
    """Return the canonical strategy owner for a merge method."""
    return STRATEGY_OWNERS.get(str(method).upper())


def declarations() -> dict[str, Any]:
    return {
        "strategies": list(STRATEGIES),
        "owners": dict(STRATEGY_OWNERS),
        "registry_wiring": dict(REGISTRY_WIRING),
        "installed_blindly": False,
        "tools": list(TOOL_TOURNAMENT),
        "execution": "FORBIDDEN_HERE",
        "gl005_proven": False,
        "law": [
            "ONE_METHOD_ONE_STRATEGY_OWNER",
            "LINEAR_OWNER_NE_GENERIC_MERGEKIT_OWNER",
            "BACKEND_ABSENT_NE_SUCCESS",
            "BUILD_DEFAULT_REGISTRY_NE_SECOND_PRODUCT_REGISTRY",
            "MERGE_DECLARATION_NE_MERGE_EXECUTION",
        ],
    }
