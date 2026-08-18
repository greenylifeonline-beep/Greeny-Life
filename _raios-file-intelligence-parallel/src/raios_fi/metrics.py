"""Performance metrics required by the File Intelligence addendum."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PerformanceReport:
    total_files: int = 0
    incremental_files: int = 0
    cache_hit_ratio: float = 0.0
    classification_coverage: float = 0.0
    classification_abstention_ratio: float = 0.0
    structural_parse_coverage: float = 0.0
    symbol_coverage: float = 0.0
    graph_edges: int = 0
    proven_edges: int = 0
    inferred_edges: int = 0
    unknown_edges: int = 0
    version_matches: int = 0
    renames: int = 0
    moves: int = 0
    semantic_equivalents: int = 0
    duplicate_groups: int = 0
    dead_candidates: int = 0
    repair_candidates: int = 0
    model_escalations: int = 0
    teacher_escalations: int = 0
    average_query_latency: float = 0.0
    model_calls_per_query: float = 0.0
    files_read_per_query: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        extras = payload.pop("extras", {}) or {}
        payload.update(extras)
        return payload
