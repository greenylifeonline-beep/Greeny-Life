"""Learning-gap classifier. Feeds Evolution Brain. Does not start training."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from raios.events import Event, EventSink


class LearningGap(str, Enum):
    LANGUAGE_GAP = "LANGUAGE_GAP"
    DIALECT_GAP = "DIALECT_GAP"
    SEMANTIC_GAP = "SEMANTIC_GAP"
    DOMAIN_KNOWLEDGE_GAP = "DOMAIN_KNOWLEDGE_GAP"
    TERMINOLOGY_GAP = "TERMINOLOGY_GAP"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    REASONING_FAILURE = "REASONING_FAILURE"
    CONTEXT_FAILURE = "CONTEXT_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    PROMPT_FAILURE = "PROMPT_FAILURE"
    ROUTING_FAILURE = "ROUTING_FAILURE"
    MODEL_CAPACITY_LIMIT = "MODEL_CAPACITY_LIMIT"


@dataclass
class FailureRecord:
    stage: str
    message: str
    code: str | None = None
    detection_locale: str | None = None
    detection_language: str | None = None
    dialect_confidence: float | None = None
    language_confidence: float | None = None
    unbound_terms: list[str] = field(default_factory=list)
    domain: str | None = None
    provider_error: str | None = None
    capability: str | None = None
    used_llm: bool = False
    unparseable_llm: bool = False
    retrieval_attempted: bool = False
    missing_context: list[str] = field(default_factory=list)
    capacity: bool = False
    verification_failed: bool = False


@dataclass
class GapClassification:
    gap: LearningGap
    confidence: float
    evidence: list[str]
    eligible_for_evolution: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap": self.gap.value,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "eligible_for_evolution": self.eligible_for_evolution,
        }


class LearningGapClassifier:
    def classify(self, failure: FailureRecord) -> GapClassification:
        evidence: list[str] = [failure.stage, failure.message]
        if failure.code:
            evidence.append(failure.code)

        if failure.capacity:
            return GapClassification(LearningGap.MODEL_CAPACITY_LIMIT, 1.0, evidence + ["capacity"])
        if failure.code in {"CAPABILITY_NOT_REGISTERED", "NO_CAPABLE_PROVIDER"} or (
            failure.capability and "routing" in (failure.code or "").lower()
        ):
            return GapClassification(LearningGap.ROUTING_FAILURE, 1.0, evidence + ["routing"])
        if failure.provider_error and not failure.used_llm:
            return GapClassification(LearningGap.TOOL_FAILURE, 1.0, evidence + [failure.provider_error])
        if failure.unparseable_llm and failure.used_llm:
            return GapClassification(LearningGap.PROMPT_FAILURE, 1.0, evidence + ["unparseable_llm"])
        if failure.provider_error and failure.used_llm:
            return GapClassification(LearningGap.TOOL_FAILURE, 0.8, evidence + [failure.provider_error])
        if failure.retrieval_attempted:
            return GapClassification(LearningGap.RETRIEVAL_FAILURE, 1.0, evidence + ["retrieval"])
        if failure.missing_context:
            return GapClassification(
                LearningGap.CONTEXT_FAILURE,
                1.0,
                evidence + failure.missing_context,
            )
        if failure.verification_failed:
            return GapClassification(LearningGap.REASONING_FAILURE, 0.7, evidence + ["verification"])
        if failure.unbound_terms:
            return GapClassification(
                LearningGap.TERMINOLOGY_GAP,
                0.8,
                evidence + failure.unbound_terms,
            )
        if failure.domain and "unknown domain" in failure.message.lower():
            return GapClassification(LearningGap.DOMAIN_KNOWLEDGE_GAP, 0.7, evidence)
        if (
            failure.detection_language == "ar"
            and (failure.dialect_confidence is None or failure.dialect_confidence == 0.0)
            and failure.detection_locale is None
        ):
            return GapClassification(LearningGap.DIALECT_GAP, 0.9, evidence + ["arabic_unresolved_dialect"])
        if failure.language_confidence is not None and failure.language_confidence == 0.0:
            return GapClassification(LearningGap.LANGUAGE_GAP, 1.0, evidence + ["zero_language_confidence"])
        if (
            failure.stage in {"lid", "language_identification", "detect"}
            and failure.detection_locale is None
            and failure.detection_language is None
        ):
            return GapClassification(LearningGap.LANGUAGE_GAP, 0.8, evidence + ["unidentified"])
        return GapClassification(LearningGap.SEMANTIC_GAP, 0.5, evidence + ["default_semantic"])


class EvolutionInbox:
    """Write-only feed for the Evolution Brain. Never starts training."""

    def __init__(self, sink: EventSink) -> None:
        self.sink = sink

    def submit(self, classification: GapClassification, *, event_id: str, payload: dict[str, Any]) -> bool:
        return self.sink.emit(
            Event(
                event_id=event_id,
                event_type="learning_gap",
                payload={"gap": classification.to_dict(), **payload},
            )
        )
