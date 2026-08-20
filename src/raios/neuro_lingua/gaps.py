from __future__ import annotations

from enum import Enum
from typing import Any


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
    UNKNOWN = "UNKNOWN"


def classify_gap(signals: dict[str, Any]) -> dict[str, Any]:
    if not signals:
        return {
            "status": "OK",
            "gap": LearningGap.UNKNOWN.value,
            "confidence": None,
            "evidence": ["no_signals"],
            "forced": False,
        }
    if signals.get("memory_denied") or signals.get("http_status") == 500:
        gap = LearningGap.MODEL_CAPACITY_LIMIT
    elif signals.get("language_unknown"):
        gap = LearningGap.LANGUAGE_GAP
    elif signals.get("dialect_unspecified"):
        gap = LearningGap.DIALECT_GAP
    elif signals.get("terminology_miss"):
        gap = LearningGap.TERMINOLOGY_GAP
    elif signals.get("retrieval_empty"):
        gap = LearningGap.RETRIEVAL_FAILURE
    elif signals.get("provider_unavailable"):
        gap = LearningGap.ROUTING_FAILURE
    elif signals.get("intent_mismatch"):
        gap = LearningGap.SEMANTIC_GAP
    else:
        gap = LearningGap.UNKNOWN
    return {
        "status": "OK",
        "gap": gap.value,
        "confidence": 0.7 if gap is not LearningGap.UNKNOWN else None,
        "evidence": [f"signals:{sorted(signals)}"],
        "forced": False,
        "feeds": "evolution_brain",
        "automatic_training": False,
    }
