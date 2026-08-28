"""Experiment generator. Plans only. Does not download or merge."""
from __future__ import annotations

from typing import Any

from .merge_strategy import STRATEGIES


def generate(candidates: list[str], strategies: tuple[str, ...] = STRATEGIES) -> dict[str, Any]:
    plans = []
    if len(candidates) >= 2:
        a, b = candidates[0], candidates[1]
        for strat in strategies:
            plans.append(
                {
                    "id": f"exp-{strat.lower()}-{a}-x-{b}",
                    "strategy": strat,
                    "parents": [a, b],
                    "execute": False,
                    "blocked": "NO_WEIGHT_DOWNLOAD_AND_NO_MERGE_HERE",
                }
            )
    return {
        "plans": plans,
        "executed": 0,
        "winner": None,
        "gl005_proven": False,
    }
