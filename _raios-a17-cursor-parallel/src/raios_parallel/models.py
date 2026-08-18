"""Enumerations and records for A17.14–A23 parallel wave."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .identity import SCHEMA_VERSION, utc_now


class StudentState(str, Enum):
    BASELINE_REQUIRED = "BASELINE_REQUIRED"
    BASELINE_FROZEN = "BASELINE_FROZEN"
    TEACHING_ACTIVE = "TEACHING_ACTIVE"
    PRACTICE_ACTIVE = "PRACTICE_ACTIVE"
    TRANSFER_PENDING = "TRANSFER_PENDING"
    TRANSFER_PASSED = "TRANSFER_PASSED"
    TRANSFER_FAILED = "TRANSFER_FAILED"
    RETENTION_PENDING = "RETENTION_PENDING"
    RETENTION_PASSED = "RETENTION_PASSED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    MASTERED = "MASTERED"
    NOT_MASTERED = "NOT_MASTERED"


class LiveStage(str, Enum):
    BASELINE = "BASELINE"
    FREEZE_BASELINE = "FREEZE_BASELINE"
    TEACHER_EXPOSURE = "TEACHER_EXPOSURE"
    DIFFERENTIAL = "DIFFERENTIAL"
    GUIDED_PRACTICE = "GUIDED_PRACTICE"
    FAILURE_INJECTION = "FAILURE_INJECTION"
    RECOVERY = "RECOVERY"
    UNSEEN_TRANSFER = "UNSEEN_TRANSFER"
    RETENTION = "RETENTION"
    INDEPENDENT_VERIFICATION = "INDEPENDENT_VERIFICATION"
    COMPETENCY_UPDATE = "COMPETENCY_UPDATE"


class VerifierKind(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    STRUCTURAL = "STRUCTURAL"
    TEST_EXECUTION = "TEST_EXECUTION"
    MULTI_MODEL = "MULTI_MODEL"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    FUTURE_FRONTIER_TEACHER = "FUTURE_FRONTIER_TEACHER"


class DifferentialOutcome(str, Enum):
    STUDENT_RIGHT_TEACHER_WRONG = "STUDENT_RIGHT_TEACHER_WRONG"
    STUDENT_WRONG_TEACHER_RIGHT = "STUDENT_WRONG_TEACHER_RIGHT"
    BOTH_PARTIAL = "BOTH_PARTIAL"
    BOTH_CORRECT_DIFFERENT = "BOTH_CORRECT_DIFFERENT"
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
    BLOCKED_BY_TRANSFER = "BLOCKED_BY_TRANSFER"
    BLOCKED_BY_RETENTION = "BLOCKED_BY_RETENTION"
    BLOCKED_BY_REGRESSION = "BLOCKED_BY_REGRESSION"
    BLOCKED_BY_UNIQUE_CAPABILITY = "BLOCKED_BY_UNIQUE_CAPABILITY"
    BLOCKED_BY_EVIDENCE = "BLOCKED_BY_EVIDENCE"
    BLOCKED_BY_TEACHER_DEPENDENCY = "BLOCKED_BY_TEACHER_DEPENDENCY"


class KnowledgeState(str, Enum):
    DISCOVERED = "DISCOVERED"
    UNDERSTOOD = "UNDERSTOOD"
    LINKED = "LINKED"
    PRACTICED = "PRACTICED"
    TRANSFER_TESTED = "TRANSFER_TESTED"
    VALIDATED = "VALIDATED"
    CANONICAL = "CANONICAL"


class KnowledgeDebtStatus(str, Enum):
    OPEN = "OPEN"
    PRIORITIZED = "PRIORITIZED"
    STUDYING = "STUDYING"
    PRACTICING = "PRACTICING"
    TRANSFER_PENDING = "TRANSFER_PENDING"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    PAID = "PAID"
    DEFERRED = "DEFERRED"
    INVALIDATED = "INVALIDATED"


class SkillLifecycle(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class TrainingLifecycle(str, Enum):
    CANDIDATE = "CANDIDATE"
    FILTERED = "FILTERED"
    VALIDATED = "VALIDATED"
    TRAIN_READY = "TRAIN_READY"
    TRAINED = "TRAINED"
    SHADOW = "SHADOW"
    REGRESSION_TESTED = "REGRESSION_TESTED"
    CANARY = "CANARY"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"


class AdapterLifecycle(str, Enum):
    TRAINED = "TRAINED"
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    ACTIVE = "ACTIVE"
    ROLLED_BACK = "ROLLED_BACK"
    RETIRED = "RETIRED"


class DegradedMode(str, Enum):
    FULL_NATIVE_CORTEX = "FULL_NATIVE_CORTEX"
    REMOTE_CORTEX = "REMOTE_CORTEX"
    SMALL_LOCAL_FALLBACK = "SMALL_LOCAL_FALLBACK"
    DETERMINISTIC_ONLY = "DETERMINISTIC_ONLY"
    SAFE_MINIMUM = "SAFE_MINIMUM"


class ComputeProviderKind(str, Enum):
    LOCAL_CPU = "LOCAL_CPU"
    LOCAL_OLLAMA = "LOCAL_OLLAMA"
    KAGGLE_GPU = "KAGGLE_GPU"
    REMOTE_OPENAI_COMPATIBLE = "REMOTE_OPENAI_COMPATIBLE"
    FUTURE_CLOUD = "FUTURE_CLOUD"
    TEMPORARY_GPU = "TEMPORARY_GPU"


class Discovery(str, Enum):
    FOUND = "FOUND"
    MISSING = "MISSING"
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"


DEFAULT_MASTERY_THRESHOLDS = {
    "unseen_transfer": 0.80,
    "independent_success": 0.85,
    "teacher_intervention": 0.10,
    "verifier_failure": 0.05,
    "distinct_transfer_domains": 3,
    "repeated_validations": 5,
}

MASTERY_DIMENSIONS = (
    "knowledge",
    "execution",
    "transfer",
    "reliability",
    "independence",
    "retention",
    "tool_use",
    "recovery",
    "evidence_use",
    "uncertainty_calibration",
)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


@dataclass
class MasteryRecord:
    capability_id: str
    knowledge: float = 0.0
    execution: float = 0.0
    transfer: float = 0.0
    reliability: float = 0.0
    independence: float = 0.0
    retention: float = 0.0
    tool_use: float = 0.0
    recovery: float = 0.0
    evidence_use: float = 0.0
    uncertainty_calibration: float = 0.0
    teacher_intervention_rate: float = 1.0
    verifier_failure_rate: float = 1.0
    repeated_validations: int = 0
    distinct_transfer_domains: int = 0
    retention_gate: str = "UNKNOWN"
    regression_gate: str = "UNKNOWN"
    independent_verification: str = "UNKNOWN"
    evidence_refs: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=utc_now)

    def as_dict(self) -> dict[str, Any]:
        return to_jsonable(asdict(self))
