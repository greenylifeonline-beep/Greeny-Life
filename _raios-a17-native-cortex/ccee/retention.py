"""Retention tests. Passing the original example is not mastery."""
from __future__ import annotations

from typing import Any

from .event_bus import EventBus


class RetentionEngine:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    def evaluate(self, capability: str, original_pass: bool, delayed_pass: bool, delay_seconds: int) -> dict[str, Any]:
        rec = {
            "capability": capability,
            "original_pass": original_pass,
            "delayed_pass": delayed_pass,
            "delay_seconds": delay_seconds,
            "retention": "RETAINED" if original_pass and delayed_pass and delay_seconds > 0 else "LOST",
            "mastery_claimed": False,
        }
        self.bus.emit("RETENTION_RESULT", "retention", rec)
        return rec
