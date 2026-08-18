"""Selective replay scheduler. Not everything is replayed."""
from __future__ import annotations

from typing import Any, Literal

from .config import EPSILON, deterministic_id, utc_now

Kind = Literal["immediate", "spaced", "failure", "high-value", "teacher-differential", "contradiction"]
SPACING = {"seconds": 30, "minutes": 15 * 60, "hours": 6 * 3600, "days": 24 * 3600}


class ReplayEngine:
    def __init__(self) -> None:
        self.schedule: list[dict[str, Any]] = []

    def plan(self, item: dict[str, Any], kind: Kind, gain: float, cost: float, spacing: str = "minutes") -> dict[str, Any] | None:
        if cost <= 0:
            cost = EPSILON
        ratio = gain / cost
        if ratio < 0.5 and kind not in {"failure", "contradiction"}:
            return None
        rec = {
            "replay_id": deterministic_id("rep", kind, str(item.get("id") or item)),
            "kind": kind,
            "item": item,
            "due_in_seconds": SPACING.get(spacing, SPACING["minutes"]),
            "spacing": spacing,
            "gain_per_cost": ratio,
            "created_at": utc_now(),
        }
        self.schedule.append(rec)
        return rec

    def due(self) -> list[dict[str, Any]]:
        return list(self.schedule)
