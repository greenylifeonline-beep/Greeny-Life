"""Evolution arena. Candidates compete. No auto canonical promotion."""
from __future__ import annotations

from typing import Any

from .config import FailClosed, deterministic_id, utc_now

LIFECYCLE = ("EXPERIMENTAL", "BENCHMARKED", "SHADOW", "CANARY_ELIGIBLE", "PROMOTION_REQUESTED")


class Arena:
    def __init__(self) -> None:
        self.candidates: dict[str, dict[str, Any]] = {}

    def compete(self, current: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        metrics = ("accuracy", "completion", "latency", "compute", "llm_calls", "failure_rate", "transfer", "robustness")
        score = {}
        for m in metrics:
            score[m] = {"current": float(current.get(m) or 0), "candidate": float(candidate.get(m) or 0)}
        cid = deterministic_id("arena", str(candidate.get("id") or candidate))
        rec = {
            "candidate_id": cid,
            "lifecycle": "EXPERIMENTAL",
            "score": score,
            "canonical": False,
            "created_at": utc_now(),
        }
        self.candidates[cid] = rec
        return rec

    def advance(self, candidate_id: str, nxt: str, *, governed: bool = False) -> dict[str, Any]:
        rec = self.candidates[candidate_id]
        if nxt not in LIFECYCLE:
            raise FailClosed(f"UNKNOWN_ARENA_STATE:{nxt}")
        if nxt == "PROMOTION_REQUESTED" and not governed:
            rec["lifecycle"] = "CANARY_ELIGIBLE"
            raise FailClosed("NO_CANONICAL_AUTO_PROMOTION")
        rec["lifecycle"] = nxt
        return rec
