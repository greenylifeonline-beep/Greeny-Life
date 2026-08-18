"""Cognitive query compiler: plan JSON before expensive stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class QueryPlan:
    natural: str
    root_scope: list[str]
    file_filters: dict[str, Any]
    lexical_queries: list[str]
    symbol_queries: list[str]
    graph_traversal: list[str]
    version_comparison: bool
    evidence_selection: list[str]
    expensive_stages_allowed: list[str]
    model_synthesis: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compile_query(natural: str, roots: list[str] | None = None) -> QueryPlan:
    n = natural.lower()
    lex: list[str] = []
    symbols: list[str] = []
    graph: list[str] = []
    compare = "compare" in n or "both versions" in n or "two version" in n
    if "shipped" in n or "order" in n:
        lex.extend(["shipped", "order", "status"])
        symbols.extend(["ship", "order", "fulfill"])
        graph.append("state_transition:order->shipped")
    if "import" in n:
        graph.append("IMPORTS")
    expensive = ["STAGE_1", "STAGE_2", "STAGE_3"]
    if compare:
        expensive.append("STAGE_5")
    # Never enable STAGE_8 unless evidence exists later.
    return QueryPlan(
        natural=natural,
        root_scope=list(roots or []),
        file_filters={"is_binary": False},
        lexical_queries=lex,
        symbol_queries=symbols,
        graph_traversal=graph,
        version_comparison=compare,
        evidence_selection=["why_selected", "provider", "score", "source_hash"],
        expensive_stages_allowed=expensive,
        model_synthesis=False,
    )
