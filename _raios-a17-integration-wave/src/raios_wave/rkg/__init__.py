"""Minimal controlled RKG primitives with deterministic IDs and provenance."""
from __future__ import annotations

from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import EventType, RkgNodeKind, RkgRelation


class CognitiveGraph:
    def __init__(self, store: Any) -> None:
        self.store = store

    def add_node(self, kind: RkgNodeKind | str, node_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        kind = RkgNodeKind(kind)
        body = {
            "node_id": node_id,
            "kind": kind.value,
            "payload": payload or {},
            "created_at": utc_now(),
        }
        self.store.conn.execute(
            "INSERT OR IGNORE INTO rkg_nodes(node_id, kind, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (node_id, kind.value, canonical_json(body), body["created_at"]),
        )
        return body

    def add_edge(self, src: str, dst: str, relation: RkgRelation | str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        relation = RkgRelation(relation)
        edge_id = deterministic_id("edge", src, dst, relation.value)
        body = {
            "edge_id": edge_id,
            "src": src,
            "dst": dst,
            "relation": relation.value,
            "payload": payload or {},
            "created_at": utc_now(),
        }
        self.store.conn.execute(
            """
            INSERT OR IGNORE INTO rkg_edges(edge_id, src, dst, relation, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (edge_id, src, dst, relation.value, canonical_json(body), body["created_at"]),
        )
        self.store.append_event(EventType.RKG_EDGE_ADDED, edge_id, {"src": src, "dst": dst, "relation": relation.value})
        return body

    def neighbors(self, node_id: str) -> list[dict[str, Any]]:
        rows = self.store.conn.execute(
            "SELECT * FROM rkg_edges WHERE src = ? OR dst = ?",
            (node_id, node_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def assert_controlled(self) -> None:
        kinds = {row["kind"] for row in self.store.conn.execute("SELECT DISTINCT kind FROM rkg_nodes")}
        unknown = kinds - {item.value for item in RkgNodeKind}
        if unknown:
            raise FailClosed("UNCONTROLLED_GRAPH_KIND:" + ",".join(sorted(unknown)))
