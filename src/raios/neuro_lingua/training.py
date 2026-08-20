from __future__ import annotations

from enum import Enum
from typing import Any


class TrainingDecision(str, Enum):
    NO_TRAINING = "NO_TRAINING"
    RETRIEVAL = "RETRIEVAL"
    SEMANTIC_MEMORY = "SEMANTIC_MEMORY"
    COMPILED_SKILL = "COMPILED_SKILL"
    ADAPTER_CANDIDATE = "ADAPTER_CANDIDATE"
    LORA_QLORA_BENCHMARK = "LORA_QLORA_BENCHMARK"
    PEFT_ESCALATION = "PEFT_ESCALATION"
    CPT_ONLY_IF_JUSTIFIED = "CPT_ONLY_IF_JUSTIFIED"


def decide_training(kind: str, *, repeats: int = 1, persistent: bool = False) -> dict[str, Any]:
    if kind == "changing_fact":
        decision = TrainingDecision.RETRIEVAL
        escalation = TrainingDecision.NO_TRAINING
    elif kind == "stable_fact":
        decision = TrainingDecision.SEMANTIC_MEMORY
        escalation = TrainingDecision.NO_TRAINING
    elif kind == "repeated_procedure" and repeats >= 3:
        decision = TrainingDecision.COMPILED_SKILL
        escalation = TrainingDecision.NO_TRAINING
    elif kind == "persistent_behavior_gap" and persistent:
        decision = TrainingDecision.ADAPTER_CANDIDATE
        escalation = TrainingDecision.LORA_QLORA_BENCHMARK
    else:
        decision = TrainingDecision.NO_TRAINING
        escalation = TrainingDecision.NO_TRAINING
    return {
        "status": "OK",
        "decision": decision.value,
        "escalation": escalation.value,
        "install_mora": False,
        "install_moe_lora": False,
        "install_cpt": False,
        "evidence": [f"kind={kind}", f"repeats={repeats}", f"persistent={persistent}"],
        "confidence": 0.9,
        "warnings": [],
    }
