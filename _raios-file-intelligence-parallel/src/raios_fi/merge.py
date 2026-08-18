"""Merge intelligence. newer != better. larger != better. different != conflicting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from raios_fi.compare import ComparisonEngine
from raios_fi.versions import VersionDifferential

Decision = Literal["KEEP_A", "KEEP_B", "MERGE", "REIMPLEMENT", "ARCHIVE", "REJECT", "REVIEW_REQUIRED"]


@dataclass(frozen=True)
class MergeCandidate:
    path_key: str
    decision: Decision
    reason: str
    evidence: tuple[str, ...]
    confidence: float
    assumed_newer_is_better: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MergeIntelligence:
    def decide(self, diff: VersionDifferential) -> list[MergeCandidate]:
        out: list[MergeCandidate] = []
        for p in diff.only_in_a:
            out.append(
                MergeCandidate(
                    p,
                    "REVIEW_REQUIRED",
                    "present_only_in_a; not automatically discarded",
                    ("only_in_a",),
                    0.55,
                )
            )
        for p in diff.only_in_b:
            out.append(
                MergeCandidate(
                    p,
                    "REVIEW_REQUIRED",
                    "present_only_in_b; not automatically adopted",
                    ("only_in_b",),
                    0.55,
                )
            )
        for p in diff.same_hash:
            out.append(MergeCandidate(p, "KEEP_A", "identical_content", ("same_hash",), 1.0))
        for p in diff.modified:
            out.append(
                MergeCandidate(
                    p,
                    "REVIEW_REQUIRED",
                    "content_diff; merge requires symbol+test evidence; newer is not automatically better",
                    ("modified",),
                    0.4,
                )
            )
        # Cap + force REVIEW when confidence low.
        for i, c in enumerate(out):
            if c.confidence < 0.7 and c.decision == "MERGE":
                out[i] = MergeCandidate(c.path_key, "REVIEW_REQUIRED", c.reason, c.evidence, c.confidence)
        return out[:500]

    def feature_completeness(self, a_features: set[str], b_features: set[str]) -> dict[str, Any]:
        return {
            "only_a": sorted(a_features - b_features),
            "only_b": sorted(b_features - a_features),
            "shared": sorted(a_features & b_features),
            "winner_assumed": None,
            "note": "completeness != quality; no automatic keep",
        }
