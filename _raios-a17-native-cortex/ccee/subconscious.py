"""Subconscious (background) brain. Consumes WAL; never merely rereads lessons."""
from __future__ import annotations

from typing import Any

from .curiosity import CuriosityEngine
from .event_bus import EventBus
from .resource_governor import ResourceGovernor
from .wal import CognitiveWAL


class SubconsciousBrain:
    SIGNALS = (
        "failures",
        "uncertainty",
        "repetition",
        "contradictions",
        "expensive_reasoning",
        "teacher_superiority",
        "skill_opportunities",
        "missing_evidence",
        "stale_knowledge",
        "unresolved_hypotheses",
        "transfer_failures",
    )

    def __init__(self, wal: CognitiveWAL, bus: EventBus, curiosity: CuriosityEngine, governor: ResourceGovernor) -> None:
        self.wal = wal
        self.bus = bus
        self.curiosity = curiosity
        self.governor = governor
        self.last_offset = 0

    def cycle(self) -> dict[str, Any]:
        if self.governor.mode == "FOREGROUND_PRIORITY":
            return {"skipped": True, "reason": "FOREGROUND_PRIORITY"}
        found: dict[str, list[str]] = {k: [] for k in self.SIGNALS}
        for event in self.wal.replay():
            if event.monotonic_sequence <= self.last_offset:
                continue
            payload = event.payload
            if event.event_type in {"TASK_FAILED", "TOOL_FAILURE", "OLLAMA_SERVER_ERROR"}:
                found["failures"].append(event.event_id)
            if event.event_type == "CONTRADICTION":
                found["contradictions"].append(event.event_id)
            if payload.get("uncertainty") or event.confidence < 0.4:
                found["uncertainty"].append(event.event_id)
            if payload.get("teacher_used"):
                found["teacher_superiority"].append(event.event_id)
            if event.event_type == "TRANSFER_RESULT" and not payload.get("passed"):
                found["transfer_failures"].append(event.event_id)
            if event.event_type == "HYPOTHESIS" and not payload.get("tested"):
                found["unresolved_hypotheses"].append(event.event_id)
            if event.event_type == "SKILL_CANDIDATE":
                found["skill_opportunities"].append(event.event_id)
            if event.cost_estimate > 0.7:
                found["expensive_reasoning"].append(event.event_id)
            self.last_offset = event.monotonic_sequence
        missions = self.curiosity.ingest_signals(found)
        return {"skipped": False, "signals": {k: len(v) for k, v in found.items()}, "missions": len(missions)}
