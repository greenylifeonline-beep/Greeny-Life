"""Economic query compiler: minimum sufficient stages, never all stages by default."""
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
    selected_stages: list[str]
    skipped_stages: list[str]
    estimated_cost: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ALL_STAGES = (
    "STAGE_0_METADATA",
    "STAGE_1_FILENAME",
    "STAGE_2_RIPGREP",
    "STAGE_3_SYMBOL",
    "STAGE_4_AST",
    "STAGE_5_DEPENDENCY",
    "STAGE_6_FTS5",
    "STAGE_7_SEMANTIC",
    "STAGE_8_QWEN",
)

STAGE_COST = {
    "STAGE_0_METADATA": 0.01,
    "STAGE_1_FILENAME": 0.02,
    "STAGE_2_RIPGREP": 0.2,
    "STAGE_3_SYMBOL": 0.08,
    "STAGE_4_AST": 0.4,
    "STAGE_5_DEPENDENCY": 0.3,
    "STAGE_6_FTS5": 0.1,
    "STAGE_7_SEMANTIC": 0.8,
    "STAGE_8_QWEN": 5.0,
}


def compile_query(natural: str, roots: list[str] | None = None) -> QueryPlan:
    n = natural.lower()
    lex: list[str] = []
    symbols: list[str] = []
    graph: list[str] = []
    compare = "compare" in n or "both versions" in n or "two version" in n
    selected = ["STAGE_0_METADATA", "STAGE_1_FILENAME"]
    reasons = ["metadata_always"]

    if "shipped" in n or "order" in n:
        lex.extend(["shipped", "order", "status"])
        symbols.extend(["ship", "order", "fulfill"])
        graph.append("state_transition:order->shipped")
        selected.extend(["STAGE_2_RIPGREP", "STAGE_3_SYMBOL"])
        reasons.append("lexical+symbol for order/shipped")
    if "import" in n or "depend" in n:
        graph.append("IMPORTS")
        if "STAGE_5_DEPENDENCY" not in selected:
            selected.append("STAGE_5_DEPENDENCY")
        reasons.append("dependency asked")
    if compare:
        if "STAGE_5_DEPENDENCY" not in selected:
            selected.append("STAGE_5_DEPENDENCY")
        reasons.append("version comparison")
    if "function" in n or "class" in n or "symbol" in n:
        if "STAGE_3_SYMBOL" not in selected:
            selected.append("STAGE_3_SYMBOL")
        reasons.append("symbol asked")
    if "full text" in n or "contains" in n or (lex and "STAGE_6_FTS5" not in selected):
        if lex or "contains" in n or "full text" in n:
            selected.append("STAGE_6_FTS5")
            reasons.append("text contains")
    if "ast" in n or "structural" in n:
        selected.append("STAGE_4_AST")
        reasons.append("structural asked")

    # Never enable STAGE_7/8 unless explicitly requested AND later evidence exists.
    if "semantic" in n:
        selected.append("STAGE_7_SEMANTIC")
        reasons.append("semantic asked; still no vectors unless available")
    skipped = [s for s in ALL_STAGES if s not in selected]
    # STAGE_8 always skipped at plan time.
    if "STAGE_8_QWEN" not in skipped:
        skipped.append("STAGE_8_QWEN")
    selected = [s for s in selected if s != "STAGE_8_QWEN"]
    cost = sum(STAGE_COST[s] for s in selected)
    return QueryPlan(
        natural=natural,
        root_scope=list(roots or []),
        file_filters={"is_binary": False},
        lexical_queries=lex,
        symbol_queries=symbols,
        graph_traversal=graph,
        version_comparison=compare,
        evidence_selection=["why_selected", "provider", "score", "source_hash"],
        expensive_stages_allowed=selected,
        model_synthesis=False,
        selected_stages=selected,
        skipped_stages=skipped,
        estimated_cost=round(cost, 3),
        reason="; ".join(reasons),
    )
