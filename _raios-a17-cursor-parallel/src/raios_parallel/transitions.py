"""Fail-closed transitions. Rejected transitions must not mutate state."""
from __future__ import annotations

from .identity import FailClosed
from .models import (
    AdapterLifecycle,
    KnowledgeDebtStatus,
    KnowledgeState,
    SkillLifecycle,
    StudentState,
    TeacherLifecycle,
    TrainingLifecycle,
)

STUDENT_TRANSITIONS = {
    StudentState.BASELINE_REQUIRED: {StudentState.BASELINE_FROZEN, StudentState.NOT_MASTERED},
    StudentState.BASELINE_FROZEN: {StudentState.TEACHING_ACTIVE, StudentState.NOT_MASTERED},
    StudentState.TEACHING_ACTIVE: {StudentState.PRACTICE_ACTIVE, StudentState.NOT_MASTERED},
    StudentState.PRACTICE_ACTIVE: {StudentState.TRANSFER_PENDING, StudentState.NOT_MASTERED},
    StudentState.TRANSFER_PENDING: {
        StudentState.TRANSFER_PASSED,
        StudentState.TRANSFER_FAILED,
        StudentState.NOT_MASTERED,
    },
    StudentState.TRANSFER_FAILED: {StudentState.PRACTICE_ACTIVE, StudentState.NOT_MASTERED},
    StudentState.TRANSFER_PASSED: {StudentState.RETENTION_PENDING, StudentState.NOT_MASTERED},
    StudentState.RETENTION_PENDING: {
        StudentState.RETENTION_PASSED,
        StudentState.NOT_MASTERED,
    },
    StudentState.RETENTION_PASSED: {StudentState.VERIFICATION_PENDING, StudentState.NOT_MASTERED},
    StudentState.VERIFICATION_PENDING: {StudentState.MASTERED, StudentState.NOT_MASTERED},
    StudentState.MASTERED: set(),
    StudentState.NOT_MASTERED: {StudentState.PRACTICE_ACTIVE, StudentState.BASELINE_REQUIRED},
}

KNOWLEDGE_ORDER = [
    KnowledgeState.DISCOVERED,
    KnowledgeState.UNDERSTOOD,
    KnowledgeState.LINKED,
    KnowledgeState.PRACTICED,
    KnowledgeState.TRANSFER_TESTED,
    KnowledgeState.VALIDATED,
    KnowledgeState.CANONICAL,
]

DEBT_TRANSITIONS = {
    KnowledgeDebtStatus.OPEN: {KnowledgeDebtStatus.PRIORITIZED, KnowledgeDebtStatus.DEFERRED, KnowledgeDebtStatus.INVALIDATED},
    KnowledgeDebtStatus.PRIORITIZED: {KnowledgeDebtStatus.STUDYING, KnowledgeDebtStatus.DEFERRED, KnowledgeDebtStatus.INVALIDATED},
    KnowledgeDebtStatus.STUDYING: {KnowledgeDebtStatus.PRACTICING, KnowledgeDebtStatus.DEFERRED, KnowledgeDebtStatus.INVALIDATED},
    KnowledgeDebtStatus.PRACTICING: {KnowledgeDebtStatus.TRANSFER_PENDING, KnowledgeDebtStatus.DEFERRED, KnowledgeDebtStatus.INVALIDATED},
    KnowledgeDebtStatus.TRANSFER_PENDING: {
        KnowledgeDebtStatus.VALIDATION_PENDING,
        KnowledgeDebtStatus.PRACTICING,
        KnowledgeDebtStatus.DEFERRED,
        KnowledgeDebtStatus.INVALIDATED,
    },
    KnowledgeDebtStatus.VALIDATION_PENDING: {
        KnowledgeDebtStatus.PAID,
        KnowledgeDebtStatus.PRACTICING,
        KnowledgeDebtStatus.DEFERRED,
        KnowledgeDebtStatus.INVALIDATED,
    },
    KnowledgeDebtStatus.PAID: set(),
    KnowledgeDebtStatus.DEFERRED: {KnowledgeDebtStatus.PRIORITIZED, KnowledgeDebtStatus.INVALIDATED},
    KnowledgeDebtStatus.INVALIDATED: set(),
}

SKILL_TRANSITIONS = {
    SkillLifecycle.CANDIDATE: {SkillLifecycle.VALIDATING, SkillLifecycle.RETIRED},
    SkillLifecycle.VALIDATING: {SkillLifecycle.VALIDATED, SkillLifecycle.CANDIDATE, SkillLifecycle.RETIRED},
    SkillLifecycle.VALIDATED: {SkillLifecycle.SHADOW, SkillLifecycle.DEPRECATED, SkillLifecycle.RETIRED},
    SkillLifecycle.SHADOW: {SkillLifecycle.CANARY, SkillLifecycle.VALIDATED, SkillLifecycle.RETIRED},
    SkillLifecycle.CANARY: {SkillLifecycle.ACTIVE, SkillLifecycle.SHADOW, SkillLifecycle.RETIRED},
    SkillLifecycle.ACTIVE: {SkillLifecycle.DEPRECATED, SkillLifecycle.RETIRED},
    SkillLifecycle.DEPRECATED: {SkillLifecycle.RETIRED},
    SkillLifecycle.RETIRED: set(),
}

TRAINING_TRANSITIONS = {
    TrainingLifecycle.CANDIDATE: {TrainingLifecycle.FILTERED, TrainingLifecycle.REJECTED},
    TrainingLifecycle.FILTERED: {TrainingLifecycle.VALIDATED, TrainingLifecycle.REJECTED},
    TrainingLifecycle.VALIDATED: {TrainingLifecycle.TRAIN_READY, TrainingLifecycle.REJECTED},
    TrainingLifecycle.TRAIN_READY: {TrainingLifecycle.TRAINED, TrainingLifecycle.REJECTED},
    TrainingLifecycle.TRAINED: {TrainingLifecycle.SHADOW, TrainingLifecycle.REJECTED},
    TrainingLifecycle.SHADOW: {TrainingLifecycle.REGRESSION_TESTED, TrainingLifecycle.REJECTED},
    TrainingLifecycle.REGRESSION_TESTED: {TrainingLifecycle.CANARY, TrainingLifecycle.REJECTED},
    TrainingLifecycle.CANARY: {TrainingLifecycle.PROMOTED, TrainingLifecycle.REJECTED},
    TrainingLifecycle.PROMOTED: set(),
    TrainingLifecycle.REJECTED: set(),
}

ADAPTER_TRANSITIONS = {
    AdapterLifecycle.TRAINED: {AdapterLifecycle.SHADOW, AdapterLifecycle.RETIRED},
    AdapterLifecycle.SHADOW: {AdapterLifecycle.CANARY, AdapterLifecycle.ROLLED_BACK, AdapterLifecycle.RETIRED},
    AdapterLifecycle.CANARY: {AdapterLifecycle.ACTIVE, AdapterLifecycle.ROLLED_BACK, AdapterLifecycle.RETIRED},
    AdapterLifecycle.ACTIVE: {AdapterLifecycle.ROLLED_BACK, AdapterLifecycle.RETIRED},
    AdapterLifecycle.ROLLED_BACK: {AdapterLifecycle.SHADOW, AdapterLifecycle.RETIRED},
    AdapterLifecycle.RETIRED: set(),
}

TEACHER_LIFECYCLE = {
    TeacherLifecycle.ACTIVE_TEACHER: {TeacherLifecycle.CAPABILITY_INVENTORIED},
    TeacherLifecycle.CAPABILITY_INVENTORIED: {TeacherLifecycle.TEACHING},
    TeacherLifecycle.TEACHING: {TeacherLifecycle.TRANSFER_VALIDATING, TeacherLifecycle.CAPABILITY_INVENTORIED},
    TeacherLifecycle.TRANSFER_VALIDATING: {TeacherLifecycle.SAMPLED_AUDIT, TeacherLifecycle.TEACHING},
    TeacherLifecycle.SAMPLED_AUDIT: {
        TeacherLifecycle.RETIRED_FOR_CAPABILITY,
        TeacherLifecycle.TEACHING,
        TeacherLifecycle.TRANSFER_VALIDATING,
    },
    TeacherLifecycle.RETIRED_FOR_CAPABILITY: {TeacherLifecycle.RETIRED_MODEL, TeacherLifecycle.SAMPLED_AUDIT},
    TeacherLifecycle.RETIRED_MODEL: set(),
}


def assert_in(mapping: dict, current, nxt, code: str) -> None:
    if nxt not in mapping[current]:
        raise FailClosed(f"{code}:{current.value}->{nxt.value}")


def assert_student(current: StudentState, nxt: StudentState) -> None:
    assert_in(STUDENT_TRANSITIONS, current, nxt, "ILLEGAL_STUDENT_STATE")


def assert_knowledge(current: KnowledgeState, nxt: KnowledgeState, governed: bool = False) -> None:
    if nxt is KnowledgeState.CANONICAL:
        if current is not KnowledgeState.VALIDATED:
            raise FailClosed(f"ILLEGAL_KNOWLEDGE_STATE:{current.value}->{nxt.value}")
        if not governed:
            raise FailClosed("AUTO_CANONICAL_PROMOTION_REJECTED")
        return
    order = KNOWLEDGE_ORDER[:-1]
    if order.index(nxt) != order.index(current) + 1:
        raise FailClosed(f"ILLEGAL_KNOWLEDGE_STATE:{current.value}->{nxt.value}")


def assert_debt(current: KnowledgeDebtStatus, nxt: KnowledgeDebtStatus) -> None:
    assert_in(DEBT_TRANSITIONS, current, nxt, "ILLEGAL_KNOWLEDGE_DEBT")


def assert_skill(current: SkillLifecycle, nxt: SkillLifecycle, activate: bool = False) -> None:
    if nxt is SkillLifecycle.ACTIVE and not activate:
        raise FailClosed("SKILL_CANDIDATE_CANNOT_AUTO_ACTIVATE")
    assert_in(SKILL_TRANSITIONS, current, nxt, "ILLEGAL_SKILL_LIFECYCLE")


def assert_training(current: TrainingLifecycle, nxt: TrainingLifecycle, promote: bool = False) -> None:
    if nxt is TrainingLifecycle.PROMOTED and not promote:
        raise FailClosed("ADAPTER_CANNOT_AUTO_PROMOTE")
    assert_in(TRAINING_TRANSITIONS, current, nxt, "ILLEGAL_TRAINING_LIFECYCLE")


def assert_adapter(current: AdapterLifecycle, nxt: AdapterLifecycle, promote: bool = False) -> None:
    if nxt is AdapterLifecycle.ACTIVE and not promote:
        raise FailClosed("ADAPTER_CANNOT_AUTO_PROMOTE")
    assert_in(ADAPTER_TRANSITIONS, current, nxt, "ILLEGAL_ADAPTER_LIFECYCLE")


def assert_teacher(current: TeacherLifecycle, nxt: TeacherLifecycle) -> None:
    assert_in(TEACHER_LIFECYCLE, current, nxt, "ILLEGAL_TEACHER_LIFECYCLE")
