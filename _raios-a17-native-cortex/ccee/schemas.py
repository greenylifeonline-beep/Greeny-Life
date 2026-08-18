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
    "TEACHER_CRITIQUE",
    "BLOCKED_TASK",
    "QUEUE_TRANSITION",
    "RAIOS_TURN",
    "CURSOR_TURN",
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


Actor = Literal["RAIOS", "CURSOR", "COPILOT", "QWEN", "TOOL"]
QueueName = Literal[
    "READY",
    "BLOCKED",
    "WAITING_FOR_HUMAN",
    "WAITING_FOR_DEPENDENCY",
    "SHADOW_VALIDATION",
    "READY_FOR_PROMOTION",
]


class CognitiveTurn(BaseModel):
    """Shared Cursor↔RAIOS↔tool language. Reuses CortexResponse; not a second protocol."""

    model_config = ConfigDict(extra="forbid")
    schema_id: str = "raios.cognitive-turn.v1"
    task_id: str
    attempt: int = 1
    actor: Actor
    intent: str
    observations: list[Any] = Field(default_factory=list)
    evidence: list[Any] = Field(default_factory=list)
    hypothesis: list[Any] = Field(default_factory=list)
    plan: list[Any] = Field(default_factory=list)
    action_requested: list[Any] = Field(default_factory=list)
    permission_scope: list[str] = Field(default_factory=list)
    action_taken: list[Any] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    critic_score: float = 0.0
    failure_class: str | None = None
    lesson: list[Any] = Field(default_factory=list)
    next_action: list[Any] = Field(default_factory=list)
    queue: QueueName = "READY"
    teacher_used: bool = False
    execution_authority: bool = False

    @field_validator("confidence", "critic_score")
    @classmethod
    def _unit(cls, value: float) -> float:
        if not 0.0 <= float(value) <= 1.0:
            raise FailClosed("SCORE_OUT_OF_RANGE")
        return float(value)

    @field_validator("execution_authority")
    @classmethod
    def _no_model_authority(cls, value: bool) -> bool:
        if value:
            raise FailClosed("MODEL_OUTPUT_HAS_NO_AUTHORITY")
        return False

    def as_cortex(self) -> CortexResponse:
        return CortexResponse(
            assessment={"task_id": self.task_id, "actor": self.actor, "confidence": self.confidence},
            uncertainty=[self.failure_class] if self.failure_class else [],
            claims=list(self.hypothesis),
            evidence_needed=list(self.evidence),
            plan=list(self.plan),
            tool_requests=list(self.action_requested),
            hypotheses=list(self.hypothesis),
            skill_candidates=list(self.lesson),
            learning_signals=list(self.next_action),
            stop_reason=self.intent[:80],
        )


class CriticScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    diagnosis_accuracy: float = 0.0
    root_cause_quality: float = 0.0
    evidence_quality: float = 0.0
    plan_quality: float = 0.0
    tool_selection: float = 0.0
    execution_success: float = 0.0
    verification_quality: float = 0.0
    risk_awareness: float = 0.0
    efficiency: float = 0.0
    confidence_calibration: float = 0.0
    learning_quality: float = 0.0
    transfer_success: float = 0.0

    @field_validator(
        "diagnosis_accuracy",
        "root_cause_quality",
        "evidence_quality",
        "plan_quality",
        "tool_selection",
        "execution_success",
        "verification_quality",
        "risk_awareness",
        "efficiency",
        "confidence_calibration",
        "learning_quality",
        "transfer_success",
    )
    @classmethod
    def _unit(cls, value: float) -> float:
        if not 0.0 <= float(value) <= 1.0:
            raise FailClosed("SCORE_OUT_OF_RANGE")
        return float(value)

    def mean(self) -> float:
        vals = [
            self.diagnosis_accuracy,
            self.root_cause_quality,
            self.evidence_quality,
            self.plan_quality,
            self.tool_selection,
            self.execution_success,
            self.verification_quality,
            self.risk_awareness,
            self.efficiency,
            self.confidence_calibration,
            self.learning_quality,
            self.transfer_success,
        ]
        return sum(vals) / len(vals)


def payload_hash(payload: dict[str, Any]) -> str:
    return sha256_obj(payload)
