"""Causal experience graph. Correlation is not claimed as true causality."""
from __future__ import annotations

from typing import Any

from .config import FailClosed, deterministic_id
from .event_bus import EventBus

NODES = ("CONTEXT", "DECISION", "ACTION", "OBSERVATION", "OUTCOME", "CORRECTION", "TRANSFER")


class CausalLearning:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []

    def add(self, kind: str, payload: dict[str, Any], parent: str | None = None) -> dict[str, Any]:
        if kind not in NODES:
            raise FailClosed(f"UNKNOWN_CAUSAL_NODE:{kind}")
        node_id = deterministic_id("cau", kind, str(payload.get("id") or payload))
        node = {
            "node_id": node_id,
            "kind": kind,
            "payload": payload,
            "status": "CAUSAL_HYPOTHESIS",
            "confidence": float(payload.get("confidence") or 0.3),
            "supporting_evidence": list(payload.get("supporting_evidence") or []),
            "contradicting_evidence": list(payload.get("contradicting_evidence") or []),
            "tested": False,
        }
        self.nodes[node_id] = node
        if parent:
            self.edges.append({"src": parent, "dst": node_id, "relation": "causal_parent", "status": "CAUSAL_HYPOTHESIS"})
        self.bus.emit("HYPOTHESIS", "causal", {"node_id": node_id, "kind": kind, "tested": False})
        return node

    def claim_true_causality(self, node_id: str) -> None:
        node = self.nodes[node_id]
        if not node.get("tested"):
            raise FailClosed("CORRELATION_IS_NOT_CAUSALITY")
