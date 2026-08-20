"""CognitiveMeaningPacket — the canonical Brain boundary.

Application code consumes meaning, not model output. Realization is a view
of this packet into a target locale.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from raios.knowledge_state import KnowledgeState
from raios.neuro_lingua.types import (
    BoundConcept,
    CodeSwitchSegment,
    Confidence,
    DetectionResult,
    ExecutionMetrics,
    PragmaticFrame,
    PreservedSpan,
    Register,
)
from raios.risk import RiskLevel


def _packet_id(source_text: str) -> str:
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()[:16]
    return f"cmp_{digest}"


@dataclass
class CognitiveMeaningPacket:
    source_text: str
    detection: DetectionResult
    segments: list[CodeSwitchSegment]
    concepts: list[BoundConcept]
    pragmatics: PragmaticFrame
    numbers: list[PreservedSpan]
    entities: list[PreservedSpan]
    identifiers: list[PreservedSpan]
    terminology: list[PreservedSpan]
    register: Register = Register.UNKNOWN
    intent: str | None = None
    knowledge_state: KnowledgeState = KnowledgeState.DISCOVERED
    risk_level: RiskLevel = RiskLevel.LOW
    evidence: list[str] = field(default_factory=list)
    provider_trace: list[str] = field(default_factory=list)
    packet_id: str = ""
    meaning_confidence: Confidence = field(
        default_factory=lambda: Confidence(value=0.0, method="unset")
    )

    def __post_init__(self) -> None:
        if not self.packet_id:
            self.packet_id = _packet_id(self.source_text)

    @property
    def source_locale(self) -> str | None:
        return self.detection.locale

    def preserved_surfaces(self, kind: str | None = None) -> list[str]:
        groups = {
            "number": self.numbers,
            "entity": self.entities,
            "identifier": self.identifiers,
            "terminology": self.terminology,
        }
        if kind:
            return [span.surface for span in groups[kind]]
        surfaces: list[str] = []
        for spans in groups.values():
            surfaces.extend(span.surface for span in spans)
        return surfaces

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "source_text": self.source_text,
            "source_locale": self.source_locale,
            "detection": self.detection.to_dict(),
            "segments": [segment.to_dict() for segment in self.segments],
            "concepts": [concept.to_dict() for concept in self.concepts],
            "pragmatics": self.pragmatics.to_dict(),
            "numbers": [span.to_dict() for span in self.numbers],
            "entities": [span.to_dict() for span in self.entities],
            "identifiers": [span.to_dict() for span in self.identifiers],
            "terminology": [span.to_dict() for span in self.terminology],
            "register": self.register.value,
            "intent": self.intent,
            "knowledge_state": self.knowledge_state.value,
            "risk_level": self.risk_level.value,
            "evidence": list(self.evidence),
            "provider_trace": list(self.provider_trace),
            "meaning_confidence": self.meaning_confidence.to_dict(),
        }

    def canonical_digest(self) -> str:
        payload = {
            "concepts": sorted(c.concept_id for c in self.concepts),
            "intent": self.intent,
            "pragmatics": {
                "action": self.pragmatics.action,
                "deadline": self.pragmatics.deadline,
                "politeness_marker": self.pragmatics.politeness_marker,
            },
            "identifiers": sorted(s.surface for s in self.identifiers),
            "numbers": sorted(s.surface for s in self.numbers),
        }
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class InterpretationResult:
    meaning: CognitiveMeaningPacket
    metrics: ExecutionMetrics
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meaning": self.meaning.to_dict(),
            "metrics": self.metrics.to_dict(),
            "warnings": list(self.warnings),
        }


@dataclass
class RenderedOutput:
    text: str
    target_locale: str
    meaning: CognitiveMeaningPacket
    realization_complete: bool
    verification: dict[str, Any]
    metrics: ExecutionMetrics
    warnings: list[str] = field(default_factory=list)
    leakage: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "target_locale": self.target_locale,
            "realization_complete": self.realization_complete,
            "verification": self.verification,
            "metrics": self.metrics.to_dict(),
            "warnings": list(self.warnings),
            "leakage": list(self.leakage),
            "packet_id": self.meaning.packet_id,
        }
