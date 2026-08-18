"""Forgetting is deprioritization. Evidence remains auditable."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import FailClosed
from .event_bus import EventBus
from .ledger import Ledger


class Forgetting:
    def __init__(self, ledger: Ledger, bus: EventBus) -> None:
        self.ledger = ledger
        self.bus = bus

    def candidate(self, knowledge_id: str, reason: str) -> dict[str, Any]:
        rec = self.ledger.get("knowledge", knowledge_id) or {"knowledge_id": knowledge_id}
        rec["state"] = "FORGET_CANDIDATE"
        rec["forget_reason"] = reason
        rec["destroyed"] = False
        rec["active_retrieval"] = False
        self.ledger.put("knowledge", "knowledge_id", knowledge_id, rec, extra={"state": "FORGET_CANDIDATE", "kind": rec.get("kind") or "claim"})
        self.bus.emit("FORGET_CANDIDATE", "forgetting", {"knowledge_id": knowledge_id, "destroyed": False})
        return rec

    def destroy(self, path: Path) -> None:
        raise FailClosed("EVIDENCE_DESTRUCTION_FORBIDDEN")
