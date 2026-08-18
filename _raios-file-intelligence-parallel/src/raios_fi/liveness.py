"""Active/dead safety. One heuristic never proves DEAD or triggers archive."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

LIVE_STATES = (
    "ACTIVE_PROVEN",
    "ACTIVE_INFERRED",
    "ORPHAN_CANDIDATE",
    "DEAD_CANDIDATE",
    "DEAD_PROVEN",
    "DYNAMIC_REFERENCE_POSSIBLE",
    "UNKNOWN",
)


@dataclass(frozen=True)
class Liveness:
    active_state: str
    archive_allowed: bool
    delete_allowed: bool
    heuristics: tuple[str, ...]
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_liveness(path: Path, *, imported_by: int = 0, referenced: bool | None = None) -> Liveness:
    rel = str(path).replace("\\", "/").lower()
    heuristics: list[str] = []
    state = "UNKNOWN"
    if imported_by > 0:
        state = "ACTIVE_PROVEN"
        heuristics.append("imported_by>0")
    elif "/tests/" in rel or rel.endswith((".test.ts", ".spec.ts", "_test.py")):
        state = "ACTIVE_INFERRED"
        heuristics.append("test_path")
    elif "node_modules" in rel.split("/"):
        state = "DYNAMIC_REFERENCE_POSSIBLE"
        heuristics.append("vendor_path_not_dead")
    elif "/archive/" in rel:
        # Historical material is not dead code.
        state = "UNKNOWN"
        heuristics.append("archive_is_not_dead_code")
    elif referenced is False:
        state = "ORPHAN_CANDIDATE"
        heuristics.append("unref_single_heuristic")
    elif referenced is None:
        state = "UNKNOWN"
        heuristics.append("no_reference_graph")

    # Never promote to DEAD_PROVEN from a single heuristic.
    if state == "DEAD_CANDIDATE" and len(heuristics) < 2:
        state = "ORPHAN_CANDIDATE"
    if state == "DEAD_PROVEN":
        state = "DEAD_CANDIDATE"
        heuristics.append("dead_proven_rejected_single_pass")

    if state not in LIVE_STATES:
        state = "UNKNOWN"
    return Liveness(
        active_state=state,
        archive_allowed=False,
        delete_allowed=False,
        heuristics=tuple(heuristics),
        evidence=tuple(heuristics),
    )
