"""Pydantic contracts for CCEE. Invalid structure fails closed."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import FailClosed, sha256_obj

EVENT_TYPES = (
    "TASK_RECEIVED",
    "TASK_COMPLETED",
    "TASK_FAILED",
    "MODEL_CALL",
    "TOOL_CALL",
    "TOOL_FAILURE",
    "OBSERVATION",
    "CLAIM_DISCOVERED",
    "CONTRADICTION",
    "HYPOTHESIS",
    "EXPERIMENT",
    "EXPERIMENT_RESULT",
    "LESSON",
    "SKILL_CANDIDATE",
    "SKILL_VALIDATED",
    "TRANSFER_RESULT",
    "RETENTION_RESULT",
    "TEACHER_OBSERVATION",
    "CURRICULUM_MISSION",
    "BENCHMARK",
    "SELF_CRITIQUE",
    "RECOVERY",
    "FORGET_CANDIDATE",
    "KNOWLEDGE_PROMOTION_REQUEST",
    "OLLAMA_SERVER_ERROR",
    "CERTIFICATION_GATE",
    "FALSE_PASS_BLOCKED",
)

KnowledgeState = Literal[
    "DISCOVERED",
    "VALIDATED",
    "CANONICAL",
    "CONTRADICTED",
    "STALE",
    "DEPRECATED",
    "FORGET_CANDIDATE",
]

MissionState = Literal[
    "DISCOVERED",
    "QUEUED",
    "ACTIVE",
    "PRACTICING",
    "TRANSFER_TESTING",
    "RETENTION_TESTING",
    "MASTERED",
    "FAILED",
    "DEFERRED",
    "OBSOLETE",
]


class CognitiveEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    timestamp: str
    monotonic_sequence: int
    run_id: str
    source: str
    event_type: str
    risk_class: str = "LOW"
    payload_hash: str
    payload: dict[str, Any]
    parent_event_ids: list[str] = Field(default_factory=list)
    causal_parent_ids: list[str] = Field(default_factory=list)
    knowledge_state: KnowledgeState = "DISCOVERED"
    confidence: float = 0.0
    novelty: float = 0.0
    contradiction_score: float = 0.0
    utility_estimate: float = 0.0
    cost_estimate: float = 0.0
    canonical: bool = False
    previous_hash: str | None = None
    event_hash: str | None = None
    idempotency_key: str | None = None

    @field_validator("event_type")
    @classmethod
    def _type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise FailClosed(f"UNKNOWN_EVENT_TYPE:{value}")
        return value

    @field_validator("canonical")
    @classmethod
    def _canonical(cls, value: bool) -> bool:
        if value:
            raise FailClosed("EVENT_CANONICAL_FORBIDDEN")
        return False

    @field_validator("confidence", "novelty", "contradiction_score", "utility_estimate")
    @classmethod
    def _unit(cls, value: float) -> float:
        if not 0.0 <= float(value) <= 1.0:
            raise FailClosed("SCORE_OUT_OF_RANGE")
        return float(value)


class CortexResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment: dict[str, Any] = Field(default_factory=dict)
    uncertainty: list[Any] = Field(default_factory=list)
    claims: list[Any] = Field(default_factory=list)
    evidence_needed: list[Any] = Field(default_factory=list)
    plan: list[Any] = Field(default_factory=list)
    tool_requests: list[Any] = Field(default_factory=list)
    hypotheses: list[Any] = Field(default_factory=list)
    skill_candidates: list[Any] = Field(default_factory=list)
    learning_signals: list[Any] = Field(default_factory=list)
    stop_reason: str = ""
    execution_authority: bool = False
    canonical_authority: bool = False

    @field_validator("execution_authority", "canonical_authority")
    @classmethod
    def _no_authority(cls, value: bool) -> bool:
        if value:
            raise FailClosed("MODEL_OUTPUT_HAS_NO_AUTHORITY")
        return False


class ExperienceEpisode(BaseModel):
    model_config = ConfigDict(extra="allow")
    episode_id: str
    input: Any
    context: Any
    intent: Any
    plan: Any
    actions: list[Any] = Field(default_factory=list)
    tool_calls: list[Any] = Field(default_factory=list)
    model_calls: list[Any] = Field(default_factory=list)
    observations: list[Any] = Field(default_factory=list)
    decisions: list[Any] = Field(default_factory=list)
    result: Any
    success_score: float = 0.0
    failure_score: float = 0.0
    latency: float = 0.0
    compute_cost: float = 0.0
    teacher_used: bool = False
    recovery_used: bool = False
    uncertainty: float = 0.0
    lessons: list[Any] = Field(default_factory=list)
    candidate_skills: list[Any] = Field(default_factory=list)
    counterfactuals: list[Any] = Field(default_factory=list)


class SkillRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    skill_id: str
    interface: str
    preconditions: list[str]
    inputs: list[str]
    outputs: list[str]
    procedure: list[str]
    invariants: list[str]
    negative_controls: list[str]
    tests: list[str]
    rollback: dict[str, Any]
    failure_modes: list[str]
    provenance: dict[str, Any]
    version: str
    confidence: float
    transfer_evidence: list[str]
    kind: str = "MICRO_SKILL"
    prompt_template_is_skill: bool = False
    zero_llm: bool = False
    active: bool = False

    @field_validator("prompt_template_is_skill")
    @classmethod
    def _not_prompt(cls, value: bool) -> bool:
        if value:
            raise FailClosed("PROMPT_TEMPLATE_IS_NOT_A_SKILL")
        return False


def payload_hash(payload: dict[str, Any]) -> str:
    return sha256_obj(payload)
