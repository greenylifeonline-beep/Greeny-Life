"""Contradiction engine. Historical evidence is never destroyed."""
from __future__ import annotations

from typing import Any

from .event_bus import EventBus
from .ledger import Ledger


class ContradictionEngine:
    def __init__(self, ledger: Ledger, bus: EventBus) -> None:
        self.ledger = ledger
        self.bus = bus

    def note(self, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        rec = {
            "left": left,
            "right": right,
            "score": 1.0 if left.get("claim") != right.get("claim") else 0.0,
            "state": "CONTRADICTED" if left.get("claim") != right.get("claim") else "CONSISTENT",
        }
        if rec["state"] == "CONTRADICTED":
            self.bus.emit("CONTRADICTION", "contradiction", rec, contradiction_score=1.0)
            kid = f"contra:{left.get('id')}:{right.get('id')}"
            self.ledger.put("knowledge", "knowledge_id", kid, rec, extra={"state": "CONTRADICTED", "kind": "contradiction"})
        return rec
