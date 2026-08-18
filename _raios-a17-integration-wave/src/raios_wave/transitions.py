"""Fix illegal knowledge-state check for non-canonical forward steps."""
from __future__ import annotations

from .identity import FailClosed
from .models import (
    AuthorityState,
    DebtStatus,
    KnowledgeDebtStatus,
    KnowledgeState,
    LearningStage,
    TeacherLifecycle,
    TrainingState,
)

LEARNING_STAGE_ORDER = [
    LearningStage.ATTENDANCE_REQUIRED,
    LearningStage.READ,
    LearningStage.PARSED,
    LearningStage.UNDERSTANDING_CHECKED,
    LearningStage.LINKED,
    LearningStage.PRACTICED,
    LearningStage.TRANSFER_TESTED,
    LearningStage.VALIDATED,
]

KNOWLEDGE_STATE_ORDER = [
    KnowledgeState.DISCOVERED,
    KnowledgeState.UNDERSTOOD,
    KnowledgeState.LINKED,
    KnowledgeState.PRACTICED,
    KnowledgeState.TRANSFER_TESTED,
    KnowledgeState.VALIDATED,
    KnowledgeState.CANONICAL,
]

TEACHER_LIFECYCLE = {
    TeacherLifecycle.ACTIVE_TEACHER: {TeacherLifecycle.CAPABILITY_INVENTORIED},
    TeacherLifecycle.CAPABILITY_INVENTORIED: {TeacherLifecycle.TEACHING},
    TeacherLifecycle.TEACHING: {
        TeacherLifecycle.TRANSFER_VALIDATING,
        TeacherLifecycle.CAPABILITY_INVENTORIED,
    },
    TeacherLifecycle.TRANSFER_VALIDATING: {
        TeacherLifecycle.SAMPLED_AUDIT,
        TeacherLifecycle.TEACHING,
    },
    TeacherLifecycle.SAMPLED_AUDIT: {
        TeacherLifecycle.RETIRED_FOR_CAPABILITY,
        TeacherLifecycle.TEACHING,
        TeacherLifecycle.TRANSFER_VALIDATING,
    },
    TeacherLifecycle.RETIRED_FOR_CAPABILITY: {
        TeacherLifecycle.RETIRED_MODEL,
        TeacherLifecycle.SAMPLED_AUDIT,
    },
    TeacherLifecycle.RETIRED_MODEL: set(),
}

DEBT_TRANSITIONS = {
    DebtStatus.OPEN: {DebtStatus.ASSIGNED, DebtStatus.DEFERRED, DebtStatus.INVALIDATED},
    DebtStatus.ASSIGNED: {DebtStatus.STUDYING, DebtStatus.DEFERRED, DebtStatus.INVALIDATED},
    DebtStatus.STUDYING: {DebtStatus.PRACTICING, DebtStatus.DEFERRED, DebtStatus.INVALIDATED},
    DebtStatus.PRACTICING: {DebtStatus.TRANSFER_PENDING, DebtStatus.DEFERRED, DebtStatus.INVALIDATED},
    DebtStatus.TRANSFER_PENDING: {
        DebtStatus.VALIDATION_PENDING,
        DebtStatus.PRACTICING,
        DebtStatus.DEFERRED,
        DebtStatus.INVALIDATED,
    },
    DebtStatus.VALIDATION_PENDING: {
        DebtStatus.PAID,
        DebtStatus.PRACTICING,
        DebtStatus.DEFERRED,
        DebtStatus.INVALIDATED,
    },
    DebtStatus.PAID: set(),
    DebtStatus.DEFERRED: {DebtStatus.ASSIGNED, DebtStatus.INVALIDATED},
    DebtStatus.INVALIDATED: set(),
}

KNOWLEDGE_DEBT_TRANSITIONS = {
    KnowledgeDebtStatus.OPEN: {KnowledgeDebtStatus.SCHEDULED, KnowledgeDebtStatus.DEFERRED},
    KnowledgeDebtStatus.SCHEDULED: {KnowledgeDebtStatus.STUDYING, KnowledgeDebtStatus.DEFERRED},
    KnowledgeDebtStatus.STUDYING: {KnowledgeDebtStatus.PRACTICING, KnowledgeDebtStatus.DEFERRED},
    KnowledgeDebtStatus.PRACTICING: {KnowledgeDebtStatus.TRANSFER_PENDING, KnowledgeDebtStatus.DEFERRED},
    KnowledgeDebtStatus.TRANSFER_PENDING: {
        KnowledgeDebtStatus.RESOLVED,
        KnowledgeDebtStatus.PRACTICING,
        KnowledgeDebtStatus.DEFERRED,
    },
    KnowledgeDebtStatus.RESOLVED: set(),
    KnowledgeDebtStatus.DEFERRED: {KnowledgeDebtStatus.SCHEDULED},
}

TRAINING_TRANSITIONS = {
    TrainingState.DRAFT: {TrainingState.VALIDATED, TrainingState.REJECTED, TrainingState.QUARANTINED},
    TrainingState.VALIDATED: {TrainingState.REJECTED, TrainingState.QUARANTINED},
    TrainingState.REJECTED: set(),
    TrainingState.QUARANTINED: {TrainingState.REJECTED},
}

AUTHORITY_TRANSITIONS = {
    AuthorityState.CANDIDATE: {
        AuthorityState.VALIDATED,
        AuthorityState.REJECTED,
        AuthorityState.QUARANTINED,
    },
    AuthorityState.VALIDATED: {AuthorityState.REJECTED, AuthorityState.QUARANTINED},
    AuthorityState.REJECTED: set(),
    AuthorityState.QUARANTINED: {AuthorityState.REJECTED},
    AuthorityState.CANONICAL: set(),
}


def assert_forward_stage(order: list, current, nxt, code: str) -> None:
    if order.index(nxt) != order.index(current) + 1:
        raise FailClosed(f"{code}:{current.value}->{nxt.value}")


def assert_learning_stage(current: LearningStage, nxt: LearningStage) -> None:
    assert_forward_stage(LEARNING_STAGE_ORDER, current, nxt, "ILLEGAL_LEARNING_STAGE")


def assert_knowledge_state(
    current: KnowledgeState,
    nxt: KnowledgeState,
    governed_canonical: bool = False,
) -> None:
    if nxt is KnowledgeState.CANONICAL:
        if current is not KnowledgeState.VALIDATED:
            raise FailClosed(f"ILLEGAL_KNOWLEDGE_STATE:{current.value}->{nxt.value}")
        if not governed_canonical:
            raise FailClosed("AUTO_CANONICAL_PROMOTION_REJECTED")
        return
    if current is KnowledgeState.CANONICAL:
        raise FailClosed("CANONICAL_KNOWLEDGE_IS_IMMUTABLE")
    pre_canonical = KNOWLEDGE_STATE_ORDER[:-1]
    assert_forward_stage(pre_canonical, current, nxt, "ILLEGAL_KNOWLEDGE_STATE")


def assert_teacher_lifecycle(current: TeacherLifecycle, nxt: TeacherLifecycle) -> None:
    if nxt not in TEACHER_LIFECYCLE[current]:
        raise FailClosed(f"ILLEGAL_TEACHER_LIFECYCLE:{current.value}->{nxt.value}")


def assert_debt_transition(current: DebtStatus, nxt: DebtStatus) -> None:
    if nxt not in DEBT_TRANSITIONS[current]:
        raise FailClosed(f"ILLEGAL_DEBT_TRANSITION:{current.value}->{nxt.value}")


def assert_knowledge_debt_transition(current: KnowledgeDebtStatus, nxt: KnowledgeDebtStatus) -> None:
    if nxt not in KNOWLEDGE_DEBT_TRANSITIONS[current]:
        raise FailClosed(f"ILLEGAL_KNOWLEDGE_DEBT_TRANSITION:{current.value}->{nxt.value}")


def assert_training_transition(current: TrainingState, nxt: TrainingState) -> None:
    if nxt not in TRAINING_TRANSITIONS[current]:
        raise FailClosed(f"ILLEGAL_TRAINING_TRANSITION:{current.value}->{nxt.value}")


def assert_authority_transition(current: AuthorityState, nxt: AuthorityState) -> None:
    if nxt is AuthorityState.CANONICAL:
        raise FailClosed("AUTO_CANONICAL_PROMOTION_REJECTED")
    if nxt not in AUTHORITY_TRANSITIONS[current]:
        raise FailClosed(f"ILLEGAL_AUTHORITY_TRANSITION:{current.value}->{nxt.value}")
