"""Training decision policy. NL-0 never trains a model.

This module returns decision structures only. MoRA, MoE-LoRA and CPT are not
dependencies and are not default actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from raios.neuro_lingua.learning import GapClassification, LearningGap


class KnowledgeRoute(str, Enum):
    RETRIEVAL = "retrieval"
    SEMANTIC_MEMORY = "semantic_memory"
    COMPILED_SKILL = "compiled_skill"
    ADAPTER_CANDIDATE = "adapter_candidate"


class AdapterEscalation(str, Enum):
    NO_TRAINING = "no_training"
    LORA_QLORA_BENCHMARK = "lora_qlora_benchmark"
    OTHER_PEFT = "other_peft"
    TARGETED_CPT = "targeted_cpt"


class FactStability(str, Enum):
    CHANGING = "changing"
    STABLE = "stable"
    PROCEDURE = "procedure"
    BEHAVIORAL_GAP = "behavioral_gap"


@dataclass
class TrainingDecision:
    route: KnowledgeRoute
    escalation: AdapterEscalation
    train_now: bool
    reason: str
    gap: LearningGap | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route.value,
            "escalation": self.escalation.value,
            "train_now": self.train_now,
            "reason": self.reason,
            "gap": self.gap.value if self.gap else None,
            "notes": list(self.notes),
        }


_RETRIEVAL_GAPS = {
    LearningGap.RETRIEVAL_FAILURE,
    LearningGap.DOMAIN_KNOWLEDGE_GAP,
}
_MEMORY_GAPS = {
    LearningGap.TERMINOLOGY_GAP,
    LearningGap.DIALECT_GAP,
    LearningGap.LANGUAGE_GAP,
}
_SKILL_GAPS = {
    LearningGap.PROMPT_FAILURE,
    LearningGap.ROUTING_FAILURE,
}


def decide_knowledge_route(stability: FactStability) -> KnowledgeRoute:
    return {
        FactStability.CHANGING: KnowledgeRoute.RETRIEVAL,
        FactStability.STABLE: KnowledgeRoute.SEMANTIC_MEMORY,
        FactStability.PROCEDURE: KnowledgeRoute.COMPILED_SKILL,
        FactStability.BEHAVIORAL_GAP: KnowledgeRoute.ADAPTER_CANDIDATE,
    }[stability]


def decide_training(
    *,
    stability: FactStability,
    gap: GapClassification | None = None,
    recurrence: int = 1,
    evidence_justifies_peft: bool = False,
    evidence_justifies_cpt: bool = False,
) -> TrainingDecision:
    route = decide_knowledge_route(stability)
    notes = [
        "NL-0 never trains.",
        "MoRA/MoE-LoRA/CPT are not default dependencies.",
    ]
    if route is KnowledgeRoute.RETRIEVAL:
        return TrainingDecision(
            route=route,
            escalation=AdapterEscalation.NO_TRAINING,
            train_now=False,
            reason="Changing facts must be retrieved, not trained.",
            gap=gap.gap if gap else None,
            notes=notes,
        )
    if route is KnowledgeRoute.SEMANTIC_MEMORY:
        return TrainingDecision(
            route=route,
            escalation=AdapterEscalation.NO_TRAINING,
            train_now=False,
            reason="Stable facts belong in semantic memory / concept registry.",
            gap=gap.gap if gap else None,
            notes=notes,
        )
    if route is KnowledgeRoute.COMPILED_SKILL:
        return TrainingDecision(
            route=route,
            escalation=AdapterEscalation.NO_TRAINING,
            train_now=False,
            reason="Repeated procedures compile to skills; no weight update.",
            gap=gap.gap if gap else None,
            notes=notes,
        )

    # Persistent behavioral/capability gap → adapter *candidate* only.
    escalation = AdapterEscalation.NO_TRAINING
    reason = "Insufficient recurrence for adapter consideration."
    if recurrence >= 5:
        escalation = AdapterEscalation.LORA_QLORA_BENCHMARK
        reason = "Persistent gap: LoRA/QLoRA benchmark is the first adapter candidate."
        if evidence_justifies_peft:
            escalation = AdapterEscalation.OTHER_PEFT
            reason = "Evidence justified non-LoRA PEFT as a candidate (still not executed)."
        if evidence_justifies_cpt:
            escalation = AdapterEscalation.TARGETED_CPT
            reason = "Targeted continual pretraining is expensive escalation only (not executed)."
    notes.append(f"recurrence={recurrence}")
    if gap and gap.gap in _RETRIEVAL_GAPS:
        notes.append("Prefer retrieval over adapters for knowledge gaps.")
    if gap and gap.gap in _MEMORY_GAPS:
        notes.append("Prefer concept-registry / WAL DISCOVERED observations.")
    if gap and gap.gap in _SKILL_GAPS:
        notes.append("Prefer compiled skill / routing fix over training.")
    return TrainingDecision(
        route=route,
        escalation=escalation,
        train_now=False,
        reason=reason,
        gap=gap.gap if gap else None,
        notes=notes,
    )
