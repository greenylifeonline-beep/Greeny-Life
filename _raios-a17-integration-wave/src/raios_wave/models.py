"""Shared entities and fail-closed enumerations for the A17 X1–X3 wave."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .identity import SCHEMA_VERSION, clamp_unit, sha256_obj, utc_now


class EvidenceState(str, Enum):
    ABSENT = "ABSENT"
    PRESENT = "PRESENT"
    QUARANTINED = "QUARANTINED"
    HASH_BOUND = "HASH_BOUND"


class VerificationState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    EMPIRICALLY_OBSERVED = "EMPIRICALLY_OBSERVED"
    INDEPENDENTLY_VERIFIED = "INDEPENDENTLY_VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    REJECTED = "REJECTED"


class AuthorityState(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    CANONICAL = "CANONICAL"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


class LearningStage(str, Enum):
    ATTENDANCE_REQUIRED = "ATTENDANCE_REQUIRED"
    READ = "READ"
    PARSED = "PARSED"
    UNDERSTANDING_CHECKED = "UNDERSTANDING_CHECKED"
    LINKED = "LINKED"
    PRACTICED = "PRACTICED"
    TRANSFER_TESTED = "TRANSFER_TESTED"
    VALIDATED = "VALIDATED"


class KnowledgeState(str, Enum):
    DISCOVERED = "DISCOVERED"
    UNDERSTOOD = "UNDERSTOOD"
    LINKED = "LINKED"
    PRACTICED = "PRACTICED"
    TRANSFER_TESTED = "TRANSFER_TESTED"
    VALIDATED = "VALIDATED"
    CANONICAL = "CANONICAL"


class DifferentialOutcome(str, Enum):
    STUDENT_WRONG_TEACHER_RIGHT = "STUDENT_WRONG_TEACHER_RIGHT"
    STUDENT_RIGHT_TEACHER_WRONG = "STUDENT_RIGHT_TEACHER_WRONG"
    BOTH_PARTIAL = "BOTH_PARTIAL"
    BOTH_CORRECT_DIFFERENT = "BOTH_CORRECT_DIFFERENT"
    BOTH_WRONG = "BOTH_WRONG"
    UNRESOLVED = "UNRESOLVED"


class TeacherLifecycle(str, Enum):
    ACTIVE_TEACHER = "ACTIVE_TEACHER"
    CAPABILITY_INVENTORIED = "CAPABILITY_INVENTORIED"
    TEACHING = "TEACHING"
    TRANSFER_VALIDATING = "TRANSFER_VALIDATING"
    SAMPLED_AUDIT = "SAMPLED_AUDIT"
    RETIRED_FOR_CAPABILITY = "RETIRED_FOR_CAPABILITY"
    RETIRED_MODEL = "RETIRED_MODEL"


class RetirementDecision(str, Enum):
    RETIREMENT_ELIGIBLE = "RETIREMENT_ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    BLOCKED_BY_UNIQUE_CAPABILITY = "BLOCKED_BY_UNIQUE_CAPABILITY"
    BLOCKED_BY_TRANSFER = "BLOCKED_BY_TRANSFER"
    BLOCKED_BY_RETENTION = "BLOCKED_BY_RETENTION"
    BLOCKED_BY_REGRESSION = "BLOCKED_BY_REGRESSION"
    BLOCKED_BY_EVIDENCE = "BLOCKED_BY_EVIDENCE"
    BLOCKED_BY_GOVERNANCE = "BLOCKED_BY_GOVERNANCE"


class TrainingKind(str, Enum):
    SFT = "SFT"
    PREFERENCE = "PREFERENCE"
    DISTILLATION = "DISTILLATION"
    TOOL_USE = "TOOL_USE"
    FAILURE_RECOVERY = "FAILURE_RECOVERY"
    ARCHITECTURE_DECISION = "ARCHITECTURE_DECISION"
    TRANSFER = "TRANSFER"
    REPOSITORY_REASONING = "REPOSITORY_REASONING"
    CODE_REPAIR = "CODE_REPAIR"


class TrainingState(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


class DebtStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    STUDYING = "STUDYING"
    PRACTICING = "PRACTICING"
    TRANSFER_PENDING = "TRANSFER_PENDING"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    PAID = "PAID"
    DEFERRED = "DEFERRED"
    INVALIDATED = "INVALIDATED"


class KnowledgeDebtStatus(str, Enum):
    OPEN = "OPEN"
    SCHEDULED = "SCHEDULED"
    STUDYING = "STUDYING"
    PRACTICING = "PRACTICING"
    TRANSFER_PENDING = "TRANSFER_PENDING"
    RESOLVED = "RESOLVED"
    DEFERRED = "DEFERRED"


class RkgNodeKind(str, Enum):
    ENTITY = "ENTITY"
    CLAIM = "CLAIM"
    CAPABILITY = "CAPABILITY"
    EXPERIENCE = "EXPERIENCE"
    SKILL = "SKILL"
    FAILURE = "FAILURE"
    EVIDENCE = "EVIDENCE"
    SOURCE = "SOURCE"
    TOOL = "TOOL"
    POLICY = "POLICY"
    MODEL = "MODEL"
    TASK = "TASK"


class RkgRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    REQUIRES = "REQUIRES"
    ENABLES = "ENABLES"
    CAUSES = "CAUSES"
    OBSERVED_IN = "OBSERVED_IN"
    LEARNED_FROM = "LEARNED_FROM"
    VALIDATED_BY = "VALIDATED_BY"
    FAILED_IN = "FAILED_IN"
    RECOVERED_BY = "RECOVERED_BY"
    COMPILED_TO = "COMPILED_TO"
    DEPENDS_ON = "DEPENDS_ON"
    SUPERSEDES = "SUPERSEDES"


class CortexProviderKind(str, Enum):
    LOCAL_OLLAMA = "LOCAL_OLLAMA"
    REMOTE_OPENAI_COMPATIBLE = "REMOTE_OPENAI_COMPATIBLE"
    KAGGLE_REMOTE = "KAGGLE_REMOTE"
    FUTURE_LOCAL_RUNTIME = "FUTURE_LOCAL_RUNTIME"
    STUB = "STUB"


class LoopStage(str, Enum):
    TASK = "TASK"
    STRUCTURAL_OBSERVATION = "STRUCTURAL_OBSERVATION"
    CAPABILITY_REQUIREMENT = "CAPABILITY_REQUIREMENT"
    MEMORY_RETRIEVAL = "MEMORY_RETRIEVAL"
    RKG_RETRIEVAL = "RKG_RETRIEVAL"
    SKILL_RETRIEVAL = "SKILL_RETRIEVAL"
    POLICY_CHECK = "POLICY_CHECK"
    CONTEXT_COMPILER = "CONTEXT_COMPILER"
    MAIN_CORTEX = "MAIN_CORTEX"
    TOOL_AUTHORITY = "TOOL_AUTHORITY"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    EXPERIENCE_RECORD = "EXPERIENCE_RECORD"
    LEARNING_OBLIGATION = "LEARNING_OBLIGATION"
    ASSIMILATION = "ASSIMILATION"


class EventType(str, Enum):
    OBJECT_INGESTED = "OBJECT_INGESTED"
    ARTIFACT_QUARANTINED = "ARTIFACT_QUARANTINED"
    OBSERVATION_NORMALIZED = "OBSERVATION_NORMALIZED"
    OBSERVATION_IDEMPOTENT_HIT = "OBSERVATION_IDEMPOTENT_HIT"
    DIFFERENTIAL_COMPUTED = "DIFFERENTIAL_COMPUTED"
    CANDIDATE_CREATED = "CANDIDATE_CREATED"
    COMPETENCY_UPDATED = "COMPETENCY_UPDATED"
    RETIREMENT_EVALUATED = "RETIREMENT_EVALUATED"
    TRAINING_CANDIDATE_CREATED = "TRAINING_CANDIDATE_CREATED"
    LOOP_STAGE = "LOOP_STAGE"
    EXPERIENCE_RECORDED = "EXPERIENCE_RECORDED"
    KNOWLEDGE_INGESTED = "KNOWLEDGE_INGESTED"
    KNOWLEDGE_STATE_CHANGED = "KNOWLEDGE_STATE_CHANGED"
    KNOWLEDGE_DEBT_CREATED = "KNOWLEDGE_DEBT_CREATED"
    RKG_EDGE_ADDED = "RKG_EDGE_ADDED"
    GOVERNANCE_REJECTED = "GOVERNANCE_REJECTED"
    CORTEX_REPLACED = "CORTEX_REPLACED"
    IDENTITY_BOUND = "IDENTITY_BOUND"


DEFAULT_MASTERY_THRESHOLDS = {
    "unseen_transfer": 0.80,
    "independent_success": 0.85,
    "teacher_intervention": 0.10,
    "verifier_failure": 0.05,
    "distinct_transfer_domains": 3,
    "repeated_validations": 5,
}


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


@dataclass(frozen=True)
class TeacherObservation:
    observation_id: str
    teacher_id: str
    model: str
    task_id: str
    capability: str
    source_artifact: str
    source_sha256: str
    raw_text_ref: str
    observed_at: str
    claims: tuple[str, ...] = ()
    procedures: tuple[str, ...] = ()
    heuristics: tuple[str, ...] = ()
    failure_patterns: tuple[str, ...] = ()
    recovery_patterns: tuple[str, ...] = ()
    tool_strategies: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    counterexamples: tuple[str, ...] = ()
    transfer_test_candidates: tuple[str, ...] = ()
    skill_candidates: tuple[str, ...] = ()
    training_candidates: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    self_reported_claims: tuple[str, ...] = ()
    evidence_state: EvidenceState = EvidenceState.HASH_BOUND
    verification_state: VerificationState = VerificationState.UNVERIFIED
    canonical: bool = False
    schema_version: str = SCHEMA_VERSION
    content_sha256: str = ""

    def stable_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("content_sha256", None)
        return to_jsonable(data)

    def sealed(self) -> "TeacherObservation":
        if self.canonical:
            from .identity import FailClosed

            raise FailClosed("TEACHER_OBSERVATION_CANNOT_BE_CANONICAL")
        digest = sha256_obj(self.stable_payload())
        payload = {k: v for k, v in self.__dict__.items() if k != "content_sha256"}
        return TeacherObservation(**{**payload, "content_sha256": digest})


@dataclass(frozen=True)
class DifferentialRecord:
    differential_id: str
    task_id: str
    capability: str
    student_observation_id: str | None
    teacher_observation_id: str | None
    outcome: DifferentialOutcome
    student_missed: tuple[str, ...]
    teacher_added: tuple[str, ...]
    teacher_missed: tuple[str, ...]
    missing_concepts: tuple[str, ...]
    bad_assumptions: tuple[str, ...]
    ignored_evidence: tuple[str, ...]
    wrong_tool_selection: tuple[str, ...]
    better_tool_sequence: tuple[str, ...]
    superior_strategy: tuple[str, ...]
    weaker_teacher_strategy: tuple[str, ...]
    teacher_error_possibility: tuple[str, ...]
    missing_prerequisites: tuple[str, ...]
    reusable_patterns: tuple[str, ...]
    skill_candidates: tuple[str, ...]
    policy_candidates: tuple[str, ...]
    failure_recovery_candidates: tuple[str, ...]
    open_uncertainty: tuple[str, ...]
    teacher_assumed_correct: bool = False
    created_at: str = field(default_factory=utc_now)
    schema_version: str = SCHEMA_VERSION


@dataclass
class CompetencyRecord:
    capability_id: str
    knowledge_score: float = 0.0
    execution_score: float = 0.0
    transfer_score: float = 0.0
    reliability_score: float = 0.0
    independence_score: float = 0.0
    retention_score: float = 0.0
    teacher_intervention_rate: float = 1.0
    verifier_failure_rate: float = 1.0
    repeated_validations: int = 0
    distinct_transfer_domains: int = 0
    last_validation: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    failure_refs: list[str] = field(default_factory=list)
    skill_refs: list[str] = field(default_factory=list)
    learning_debt_refs: list[str] = field(default_factory=list)
    regression_gate: str = "UNKNOWN"
    retention_gate: str = "UNKNOWN"
    updated_at: str = field(default_factory=utc_now)

    def clamped(self) -> "CompetencyRecord":
        for name in (
            "knowledge_score",
            "execution_score",
            "transfer_score",
            "reliability_score",
            "independence_score",
            "retention_score",
            "teacher_intervention_rate",
            "verifier_failure_rate",
        ):
            setattr(self, name, clamp_unit(getattr(self, name), name.upper()))
        return self

    def as_dict(self) -> dict[str, Any]:
        return to_jsonable(asdict(self))


@dataclass(frozen=True)
class CortexProposal:
    """Cortex output is always a proposal. It has no execution authority."""

    proposal_id: str
    provider_kind: str
    model_name: str
    text: str
    structured: dict[str, Any]
    tool_plan: tuple[dict[str, Any], ...]
    execution_authority: bool = False
    mutates_canonical: bool = False
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.execution_authority or self.mutates_canonical:
            from .identity import FailClosed

            raise FailClosed("CORTEX_OUTPUT_CANNOT_HOLD_EXECUTION_AUTHORITY")
