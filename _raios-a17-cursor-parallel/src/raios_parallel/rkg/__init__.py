"""Minimal controlled RKG."""
from __future__ import annotations

from typing import Any

from ..identity import canonical_json, deterministic_id, utc_now

NODE_KINDS = {
    "ENTITY", "CLAIM", "CAPABILITY", "EXPERIENCE", "SKILL", "FAILURE",
    "EVIDENCE", "SOURCE", "TOOL", "POLICY", "MODEL", "TASK",
}
RELATIONS = {
    "SUPPORTS", "CONTRADICTS", "REQUIRES", "ENABLES", "CAUSES", "OBSERVED_IN",
    "LEARNED_FROM", "VALIDATED_BY", "FAILED_IN", "RECOVERED_BY", "COMPILED_TO",
    "DEPENDS_ON", "SUPERSEDES",
}


class CognitiveGraph:
    def __init__(self, store: Any) -> None:
        self.store = store

    def add_node(self, kind: str, node_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        from ..identity import FailClosed

        if kind not in NODE_KINDS:
            raise FailClosed(f"UNCONTROLLED_GRAPH_KIND:{kind}")
        body = {"node_id": node_id, "kind": kind, "payload": payload or {}, "created_at": utc_now()}
        self.store.conn.execute(
            "INSERT OR IGNORE INTO rkg_nodes(node_id, kind, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (node_id, kind, canonical_json(body), body["created_at"]),
        )
        return body

    def add_edge(self, src: str, dst: str, relation: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        from ..identity import FailClosed

        if relation not in RELATIONS:
            raise FailClosed(f"UNCONTROLLED_GRAPH_RELATION:{relation}")
        edge_id = deterministic_id("edge", src, dst, relation)
        body = {"edge_id": edge_id, "src": src, "dst": dst, "relation": relation, "payload": payload or {}, "created_at": utc_now()}
        self.store.conn.execute(
            "INSERT OR IGNORE INTO rkg_edges(edge_id, src, dst, relation, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (edge_id, src, dst, relation, canonical_json(body), body["created_at"]),
        )
        self.store.append_event("RKG_EDGE_ADDED", edge_id, {"relation": relation})
        return body
