from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .identity import SCHEMA_VERSION, sha256_obj, utc_now
from .refs import validate_refs


class FabricError(RuntimeError):
    pass


class FailClosed(FabricError):
    pass


class DebtState(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    STUDYING = "STUDYING"
    PRACTICING = "PRACTICING"
    REPLAY_PENDING = "REPLAY_PENDING"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    PAID = "PAID"
    DEFERRED = "DEFERRED"
    INVALIDATED = "INVALIDATED"


class KnowledgeMaturity(str, Enum):
    SEEN = "SEEN"
    UNDERSTOOD = "UNDERSTOOD"
    CONNECTED = "CONNECTED"
    PRACTICED = "PRACTICED"
    VALIDATED = "VALIDATED"
    TRANSFERABLE = "TRANSFERABLE"
    MASTERED = "MASTERED"


class EpistemicState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    EVIDENCE_BOUNDED = "EVIDENCE_BOUNDED"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    DEPRECATED = "DEPRECATED"
    QUARANTINED = "QUARANTINED"


class OriginClass(str, Enum):
    REAL = "REAL"
    SYNTHETIC = "SYNTHETIC"
    DERIVED = "DERIVED"


class TeacherDependencyState(str, Enum):
    TEACHER_SOLVES = "TEACHER_SOLVES"
    STUDENT_CO_SOLVES = "STUDENT_CO_SOLVES"
    STUDENT_SOLVES_TEACHER_VERIFIES = "STUDENT_SOLVES_TEACHER_VERIFIES"
    STUDENT_INDEPENDENT = "STUDENT_INDEPENDENT"
    TEACHER_AUDIT_ONLY = "TEACHER_AUDIT_ONLY"
    RETIRED = "RETIRED"


class TrainingKind(str, Enum):
    SFT = "SFT"
    PREFERENCE = "PREFERENCE"
    DISTILLATION = "DISTILLATION"
    TOOL_USE = "TOOL_USE"
    FAILURE_RECOVERY = "FAILURE_RECOVERY"
    ARCHITECTURE_DECISION = "ARCHITECTURE_DECISION"
    TRANSFER = "TRANSFER"


class TrainingState(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


class HarvestKind(str, Enum):
    OBSERVED_FACT = "OBSERVED_FACT"
    DERIVED_INFERENCE = "DERIVED_INFERENCE"
    UNVERIFIED_HYPOTHESIS = "UNVERIFIED_HYPOTHESIS"


class CompressionLayer(str, Enum):
    RAW_EXPERIENCE = "RAW_EXPERIENCE"
    PATTERN = "PATTERN"
    ABSTRACTION = "ABSTRACTION"
    KNOWLEDGE_SKILL = "KNOWLEDGE_SKILL"
    COLD_ARCHIVE = "COLD_ARCHIVE"


class ParticipationMode(str, Enum):
    OBSERVE = "OBSERVE"
    PREDICT = "PREDICT"
    ASSISTED_SOLVE = "ASSISTED_SOLVE"
    CO_SOLVE = "CO_SOLVE"
    STUDENT_FIRST = "STUDENT_FIRST"
    STUDENT_EXECUTE_TEACHER_VERIFY = "STUDENT_EXECUTE_TEACHER_VERIFY"
    INDEPENDENT = "INDEPENDENT"


class TeacherVerificationStatus(str, Enum):
    UNTRUSTED = "UNTRUSTED"
    UNVERIFIED = "UNVERIFIED"
    INDEPENDENTLY_VERIFIED = "INDEPENDENTLY_VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    ERROR_DETECTED = "ERROR_DETECTED"


class DifferentialOutcome(str, Enum):
    TEACHER_WRONG_STUDENT_RIGHT = "TEACHER_WRONG_STUDENT_RIGHT"
    TEACHER_RIGHT_STUDENT_WRONG = "TEACHER_RIGHT_STUDENT_WRONG"
    BOTH_WRONG = "BOTH_WRONG"
    BOTH_RIGHT = "BOTH_RIGHT"
    TEACHER_DISAGREEMENT = "TEACHER_DISAGREEMENT"


class EventType(str, Enum):
    TRACE_CREATED = "TRACE_CREATED"
    DEBT_CREATED = "DEBT_CREATED"
    DEBT_STATE_CHANGED = "DEBT_STATE_CHANGED"
    KNOWLEDGE_CREATED = "KNOWLEDGE_CREATED"
    KNOWLEDGE_MATURITY_CHANGED = "KNOWLEDGE_MATURITY_CHANGED"
    COMPETENCY_UPDATE_PROPOSED = "COMPETENCY_UPDATE_PROPOSED"
    COMPETENCY_UPDATE_ACCEPTED = "COMPETENCY_UPDATE_ACCEPTED"
    COMPETENCY_UPDATE_REJECTED = "COMPETENCY_UPDATE_REJECTED"
    TEACHER_DEPENDENCY_CHANGED = "TEACHER_DEPENDENCY_CHANGED"
    TRAINING_CANDIDATE_CREATED = "TRAINING_CANDIDATE_CREATED"


def clamp_unit(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise FailClosed(f"{name}_BOOLEAN_INVALID")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise FailClosed(f"{name}_OUT_OF_RANGE:{number}")
    return number


@dataclass(frozen=True)
class LearningTrace:
    trace_id: str
    task_id: str
    result_id: str
    idempotency_key: str
    decision_summary: str
    uncertainty: float
    created_at: str
    schema_version: str = SCHEMA_VERSION
    evidence_basis: tuple[str, ...] = field(default_factory=tuple)
    actions_taken: tuple[str, ...] = field(default_factory=tuple)
    correction_summary: str = ""
    artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    experience_refs: tuple[str, ...] = field(default_factory=tuple)
    failure_refs: tuple[str, ...] = field(default_factory=tuple)
    skill_refs: tuple[str, ...] = field(default_factory=tuple)
    content_sha256: str = ""

    def stable_payload(self) -> dict:
        return {
            "task_id": self.task_id,
            "result_id": self.result_id,
            "idempotency_key": self.idempotency_key,
            "decision_summary": self.decision_summary,
            "uncertainty": self.uncertainty,
            "schema_version": self.schema_version,
            "evidence_basis": list(self.evidence_basis),
            "actions_taken": list(self.actions_taken),
            "correction_summary": self.correction_summary,
            "artifact_refs": list(self.artifact_refs),
            "evidence_refs": list(self.evidence_refs),
            "experience_refs": list(self.experience_refs),
            "failure_refs": list(self.failure_refs),
            "skill_refs": list(self.skill_refs),
        }

    def sealed(self) -> "LearningTrace":
        validate_refs(self.artifact_refs)
        validate_refs(self.evidence_refs)
        validate_refs(self.experience_refs)
        validate_refs(self.failure_refs)
        validate_refs(self.skill_refs)
        clamp_unit(self.uncertainty, "UNCERTAINTY")
        digest = sha256_obj(self.stable_payload())
        payload = {k: v for k, v in self.__dict__.items() if k != "content_sha256"}
        return LearningTrace(**{**payload, "content_sha256": digest})


@dataclass(frozen=True)
class TeacherStudentDifferential:
    differential_id: str
    task_id: str
    teacher_result_ref: str
    student_result_ref: str
    outcome: DifferentialOutcome
    decision_summary: str
    evidence_basis: tuple[str, ...]
    actions_taken: tuple[str, ...]
    correction_summary: str
    uncertainty: float
    teacher_verification_status: TeacherVerificationStatus
    evidence_strength: float
    contradiction_state: str
    teacher_error_detected: bool
    educational_only: bool
    independent_verifier_refs: tuple[str, ...] = field(default_factory=tuple)
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class DebtPaymentEvidence:
    required_practice_completed: bool
    replay_passed: bool
    transfer_test_passed: bool
    competency_validation_accepted: bool
    evidence_refs: tuple[str, ...]
    reading_only: bool = False
    observing_only: bool = False


@dataclass(frozen=True)
class CompetencyEvidence:
    practice: bool
    replay: bool
    verification: bool
    transfer_tests: bool
    evidence_refs: tuple[str, ...]
    teacher_answer_only: bool = False
    student_read_only: bool = False
    synthetic_repetition_only: bool = False
    llm_claims_learning: bool = False


@dataclass(frozen=True)
class ExpectedLearningValue:
    recurrence_probability: float
    strategic_value: float
    novelty: float
    generalizability: float
    uncertainty: float
    expected_competency_gain: float
    learning_cost: float
    teacher_cost: float

    def score(self) -> float:
        return (
            0.15 * clamp_unit(self.recurrence_probability, "RECURRENCE")
            + 0.15 * clamp_unit(self.strategic_value, "STRATEGIC")
            + 0.10 * clamp_unit(self.novelty, "NOVELTY")
            + 0.15 * clamp_unit(self.generalizability, "GENERALIZABILITY")
            + 0.10 * clamp_unit(self.uncertainty, "UNCERTAINTY")
            + 0.20 * clamp_unit(self.expected_competency_gain, "GAIN")
            - 0.08 * clamp_unit(self.learning_cost, "LEARNING_COST")
            - 0.07 * clamp_unit(self.teacher_cost, "TEACHER_COST")
        )
