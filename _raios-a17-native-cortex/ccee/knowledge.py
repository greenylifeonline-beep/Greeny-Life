"""Knowledge metabolism. Historical facts do not decay. No auto canonical."""
from __future__ import annotations

from typing import Any

from .config import FailClosed, deterministic_id, utc_now
from .event_bus import EventBus
from .ledger import Ledger

STATES = ("DISCOVERED", "VALIDATED", "CANONICAL", "CONTRADICTED", "STALE", "DEPRECATED", "FORGET_CANDIDATE")
KINDS = ("historical_fact", "operational_truth", "hypothesis", "policy", "skill", "preference", "observation")


class KnowledgeMetabolism:
    def __init__(self, ledger: Ledger, bus: EventBus) -> None:
        self.ledger = ledger
        self.bus = bus

    def ingest(self, kind: str, claim: str, *, historical: bool = False) -> dict[str, Any]:
        if kind not in KINDS:
            raise FailClosed(f"UNKNOWN_KNOWLEDGE_KIND:{kind}")
        kid = deterministic_id("know", kind, claim)
        rec = {
            "knowledge_id": kid,
            "kind": kind,
            "claim": claim,
            "state": "DISCOVERED",
            "confidence": 0.4,
            "historical": historical,
            "canonical": False,
            "created_at": utc_now(),
        }
        self.ledger.put("knowledge", "knowledge_id", kid, rec, extra={"state": "DISCOVERED", "kind": kind})
        self.bus.emit("CLAIM_DISCOVERED", "knowledge", rec)
        return rec

    def decay(self, knowledge_id: str, amount: float = 0.1) -> dict[str, Any]:
        rec = self.ledger.get("knowledge", knowledge_id)
        if not rec:
            raise FailClosed("KNOWLEDGE_UNKNOWN")
        if rec.get("historical") or rec.get("kind") == "historical_fact":
            return rec
        rec["confidence"] = max(0.0, float(rec.get("confidence") or 0) - amount)
        if rec["confidence"] < 0.2:
            rec["state"] = "STALE"
        self.ledger.put("knowledge", "knowledge_id", knowledge_id, rec, extra={"state": rec["state"], "kind": rec["kind"]})
        return rec

    def promote_canonical(self, knowledge_id: str, governed: bool = False) -> dict[str, Any]:
        rec = self.ledger.get("knowledge", knowledge_id)
        if not rec:
            raise FailClosed("KNOWLEDGE_UNKNOWN")
        if not governed:
            self.bus.emit("KNOWLEDGE_PROMOTION_REQUEST", "knowledge", {"knowledge_id": knowledge_id, "allowed": False})
            raise FailClosed("NO_CANONICAL_AUTO_PROMOTION")
        rec["state"] = "CANONICAL"
        rec["canonical"] = True
        self.ledger.put("knowledge", "knowledge_id", knowledge_id, rec, extra={"state": "CANONICAL", "kind": rec["kind"]})
        return rec
