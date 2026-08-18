"""File knowledge graph. Edges only PROVEN/INFERRED/UNKNOWN with confidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from raios_fi.store import Store

NODE_KINDS = (
    "ROOT",
    "FILE",
    "SYMBOL",
    "MODULE",
    "ROUTE",
    "DATABASE",
    "TABLE",
    "EVENT",
    "API",
    "TEST",
    "CONFIG",
    "DOCUMENT",
    "EVIDENCE",
)

EDGE_KINDS = (
    "CONTAINS",
    "IMPORTS",
    "CALLS",
    "IMPLEMENTS",
    "READS",
    "WRITES",
    "EMITS",
    "CONSUMES",
    "TESTS",
    "CONFIGURES",
    "REFERENCES",
    "SUPERSEDES",
    "MOVED_FROM",
    "EQUIVALENT_TO",
    "CONTRADICTS",
)


@dataclass(frozen=True)
class GraphNode:
    kind: str
    node_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FileKnowledgeGraph:
    def __init__(self, store: Store) -> None:
        self.store = store

    def add_edge(
        self,
        src_kind: str,
        src: str,
        dst_kind: str,
        dst: str,
        kind: str,
        state: str,
        confidence: float,
        evidence: str,
    ) -> None:
        if kind not in EDGE_KINDS:
            raise ValueError(kind)
        if src_kind not in NODE_KINDS or dst_kind not in NODE_KINDS:
            raise ValueError("unknown_node_kind")
        if state not in {"PROVEN", "INFERRED", "UNKNOWN"}:
            raise ValueError(state)
        self.store.upsert_relation(src_kind, src, dst_kind, dst, kind, state, confidence, evidence)

    def neighbors(self, src: str) -> list[dict[str, Any]]:
        cur = self.store.conn.execute(
            "SELECT dst_kind, dst_id, kind, state, confidence FROM relations WHERE src_id=?",
            (src,),
        )
        return [dict(r) for r in cur.fetchall()]
