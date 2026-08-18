"""Dynamically generated curriculum. Priority is not FIFO."""
from __future__ import annotations

from typing import Any

from .config import FailClosed
from .ledger import Ledger
from .schemas import MissionState

ORDER = [
    "DISCOVERED",
    "QUEUED",
    "ACTIVE",
    "PRACTICING",
    "TRANSFER_TESTING",
    "RETENTION_TESTING",
    "MASTERED",
    "FAILED",
    "DEFERRED",
    "OBSOLETE",
]


class Curriculum:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger

    def queue(self, mission: dict[str, Any], compute: dict[str, Any] | None = None) -> dict[str, Any]:
        compute = compute or {}
        if mission.get("high_risk") and not compute.get("allow_high_risk"):
            mission["state"] = "DEFERRED"
            mission["reason"] = "HIGH_RISK_NOT_AUTO"
        else:
            mission["state"] = "QUEUED"
        mission["priority"] = self._priority(mission, compute)
        self.ledger.put("missions", "mission_id", mission["mission_id"], mission, extra={"state": mission["state"], "score": mission.get("score") or 0})
        return mission

    def _priority(self, mission: dict[str, Any], compute: dict[str, Any]) -> float:
        return (
            0.25 * float(mission.get("expected_gain") or 0)
            + 0.20 * float(mission.get("leverage") or 0)
            + 0.20 * float(mission.get("failure_reduction") or 0)
            + 0.15 * float(mission.get("reuse_probability") or 0)
            + 0.10 * float(compute.get("teacher_availability") or 0.5)
            + 0.10 * float(compute.get("available_compute") or 0.5)
            - 0.20 * float(mission.get("compute_cost") or 0)
            - 0.30 * float(mission.get("risk") or 0)
        )

    def next_mission(self) -> dict[str, Any] | None:
        queued = [m for m in self.ledger.list("missions") if m.get("state") == "QUEUED"]
        if not queued:
            return None
        return sorted(queued, key=lambda m: float(m.get("priority") or 0), reverse=True)[0]

    def transition(self, mission_id: str, nxt: MissionState) -> dict[str, Any]:
        mission = self.ledger.get("missions", mission_id)
        if not mission:
            raise FailClosed("MISSION_UNKNOWN")
        if nxt == "MASTERED" and mission.get("state") != "RETENTION_TESTING":
            raise FailClosed("MASTERY_REQUIRES_RETENTION")
        mission["state"] = nxt
        self.ledger.put("missions", "mission_id", mission_id, mission, extra={"state": nxt, "score": mission.get("score") or 0})
        return mission
