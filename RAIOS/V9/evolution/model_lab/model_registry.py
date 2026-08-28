"""Model registry. Discover candidates. Do not crown a winner."""
from __future__ import annotations

from typing import Any

# Families are scouting labels, not selected backbones.
FAMILIES = (
    "qwen",
    "deepseek",
    "granite",
    "llama",
    "mistral",
    "gemma",
    "phi",
    "yi",
    "command-r",
    "eurollm",
    "silma",
    "jais",
    "viking",
    "norwai",
    "unknown-open",
)

AXES = (
    "reasoning",
    "coding",
    "tool_use",
    "multilingual",
    "arabic",
    "norwegian_scandinavian",
    "long_context",
    "domain_performance",
    "latency",
    "ram",
    "vram",
    "storage",
    "license",
    "quantization",
    "parallelism",
    "safety",
    "regression",
)


def registry(*, live_local: list[str], named_hold: list[str], founder_claimed: list[str]) -> dict[str, Any]:
    rows = []
    for name in live_local:
        rows.append({"id": name, "source": "LIVE_LOCAL_THIS_HOST", "winner": False, "status": "MEASURED"})
    for name in named_hold:
        rows.append({"id": name, "source": "NAMED_HOLD", "winner": False, "status": "NOT_LOADED"})
    for name in founder_claimed:
        rows.append({"id": name, "source": "FOUNDER_CLAIMED_LAPTOP", "winner": False, "status": "UNVERIFIED_HERE"})
    return {
        "schema": "raios.model-registry.v1",
        "families_scouted": list(FAMILIES),
        "axes": list(AXES),
        "models": rows,
        "winner": None,
        "selection_blocked_until_hardware": True,
        "hardcoded_qwen_winner": False,
        "hardcoded_deepseek_winner": False,
        "hardcoded_granite_winner": False,
        "gl005_proven": False,
    }
