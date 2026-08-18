"""Evidence-native confidence. Model score alone never yields VERIFIED."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def band(score: float) -> str:
    if score < 0.40:
        return "ABSTAIN"
    if score < 0.60:
        return "LOW"
    if score < 0.80:
        return "PROVISIONAL"
    if score < 0.95:
        return "STRONG"
    return "DETERMINISTIC_REQUIRED"


@dataclass
class EvidenceConfidence:
    score: float
    band: str
    supporting_signals: list[str] = field(default_factory=list)
    contradicting_signals: list[str] = field(default_factory=list)
    signal_diversity: int = 0
    deterministic_evidence: list[str] = field(default_factory=list)
    semantic_evidence: list[str] = field(default_factory=list)
    model_evidence: list[str] = field(default_factory=list)
    teacher_evidence: list[str] = field(default_factory=list)
    verification_eligible: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_confidence(
    *,
    supporting: list[str] | None = None,
    contradicting: list[str] | None = None,
    deterministic: list[str] | None = None,
    semantic: list[str] | None = None,
    model: list[str] | None = None,
    teacher: list[str] | None = None,
    base: float = 0.0,
) -> EvidenceConfidence:
    supporting = list(supporting or [])
    contradicting = list(contradicting or [])
    deterministic = list(deterministic or [])
    semantic = list(semantic or [])
    model = list(model or [])
    teacher = list(teacher or [])
    score = base
    score += 0.15 * min(len(deterministic), 4)
    score += 0.08 * min(len(supporting), 4)
    score += 0.05 * min(len(semantic), 3)
    score -= 0.20 * min(len(contradicting), 3)
    # Model/teacher may raise score but never unlock VERIFIED.
    score += 0.03 * min(len(model) + len(teacher), 3)
    score = max(0.0, min(score, 0.99))
    families = [
        bool(deterministic),
        bool(supporting),
        bool(semantic),
        bool(model),
        bool(teacher),
    ]
    diversity = sum(families)
    eligible = bool(deterministic) and not contradicting and not model and score >= 0.95
    if model or teacher:
        eligible = False
    return EvidenceConfidence(
        score=round(score, 3),
        band=band(score),
        supporting_signals=supporting,
        contradicting_signals=contradicting,
        signal_diversity=diversity,
        deterministic_evidence=deterministic,
        semantic_evidence=semantic,
        model_evidence=model,
        teacher_evidence=teacher,
        verification_eligible=eligible,
    )


def verification_from_confidence(conf: EvidenceConfidence, *, contradicted: bool = False) -> str:
    if contradicted or conf.contradicting_signals:
        return "CONTRADICTED"
    if conf.model_evidence or conf.teacher_evidence:
        if conf.band in {"STRONG", "DETERMINISTIC_REQUIRED"}:
            return "PARTIALLY_VERIFIED"
        return "UNVERIFIED"
    if conf.verification_eligible and conf.deterministic_evidence:
        return "VERIFIED"
    if conf.deterministic_evidence and conf.score >= 0.60:
        return "PARTIALLY_VERIFIED"
    if conf.band == "ABSTAIN":
        return "UNVERIFIED"
    return "UNVERIFIED"
