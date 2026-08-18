from __future__ import annotations

from .models import (
    DebtState,
    EpistemicState,
    FailClosed,
    KnowledgeMaturity,
    TeacherDependencyState,
    TrainingState,
)

DEBT_TRANSITIONS = {
    DebtState.OPEN: {DebtState.ASSIGNED, DebtState.DEFERRED, DebtState.INVALIDATED},
    DebtState.ASSIGNED: {DebtState.STUDYING, DebtState.DEFERRED, DebtState.INVALIDATED},
    DebtState.STUDYING: {DebtState.PRACTICING, DebtState.DEFERRED, DebtState.INVALIDATED},
    DebtState.PRACTICING: {DebtState.REPLAY_PENDING, DebtState.DEFERRED, DebtState.INVALIDATED},
    DebtState.REPLAY_PENDING: {DebtState.VALIDATION_PENDING, DebtState.PRACTICING, DebtState.DEFERRED, DebtState.INVALIDATED},
    DebtState.VALIDATION_PENDING: {DebtState.PAID, DebtState.PRACTICING, DebtState.DEFERRED, DebtState.INVALIDATED},
    DebtState.PAID: set(),
    DebtState.DEFERRED: {DebtState.ASSIGNED, DebtState.INVALIDATED},
    DebtState.INVALIDATED: set(),
}

MATURITY_ORDER = [
    KnowledgeMaturity.SEEN,
    KnowledgeMaturity.UNDERSTOOD,
    KnowledgeMaturity.CONNECTED,
    KnowledgeMaturity.PRACTICED,
    KnowledgeMaturity.VALIDATED,
    KnowledgeMaturity.TRANSFERABLE,
    KnowledgeMaturity.MASTERED,
]

TEACHER_DEP_TRANSITIONS = {
    TeacherDependencyState.TEACHER_SOLVES: {
        TeacherDependencyState.STUDENT_CO_SOLVES,
    },
    TeacherDependencyState.STUDENT_CO_SOLVES: {
        TeacherDependencyState.STUDENT_SOLVES_TEACHER_VERIFIES,
        TeacherDependencyState.TEACHER_SOLVES,
    },
    TeacherDependencyState.STUDENT_SOLVES_TEACHER_VERIFIES: {
        TeacherDependencyState.STUDENT_INDEPENDENT,
        TeacherDependencyState.STUDENT_CO_SOLVES,
    },
    TeacherDependencyState.STUDENT_INDEPENDENT: {
        TeacherDependencyState.TEACHER_AUDIT_ONLY,
        TeacherDependencyState.STUDENT_SOLVES_TEACHER_VERIFIES,
    },
    TeacherDependencyState.TEACHER_AUDIT_ONLY: {
        TeacherDependencyState.RETIRED,
        TeacherDependencyState.STUDENT_INDEPENDENT,
    },
    TeacherDependencyState.RETIRED: set(),
}

TRAINING_TRANSITIONS = {
    TrainingState.DRAFT: {TrainingState.VALIDATED, TrainingState.REJECTED, TrainingState.QUARANTINED},
    TrainingState.VALIDATED: {TrainingState.PROMOTED, TrainingState.REJECTED, TrainingState.QUARANTINED},
    TrainingState.PROMOTED: set(),
    TrainingState.REJECTED: set(),
    TrainingState.QUARANTINED: {TrainingState.REJECTED},
}


def assert_debt_transition(current: DebtState, nxt: DebtState) -> None:
    if nxt not in DEBT_TRANSITIONS[current]:
        raise FailClosed(f"ILLEGAL_DEBT_TRANSITION:{current.value}->{nxt.value}")


def assert_maturity_transition(current: KnowledgeMaturity, nxt: KnowledgeMaturity) -> None:
    if MATURITY_ORDER.index(nxt) != MATURITY_ORDER.index(current) + 1:
        raise FailClosed(f"ILLEGAL_MATURITY_JUMP:{current.value}->{nxt.value}")


def assert_teacher_dep_transition(current: TeacherDependencyState, nxt: TeacherDependencyState) -> None:
    if nxt not in TEACHER_DEP_TRANSITIONS[current]:
        raise FailClosed(f"ILLEGAL_TEACHER_DEPENDENCY_TRANSITION:{current.value}->{nxt.value}")


def assert_training_transition(current: TrainingState, nxt: TrainingState) -> None:
    if nxt not in TRAINING_TRANSITIONS[current]:
        raise FailClosed(f"ILLEGAL_TRAINING_TRANSITION:{current.value}->{nxt.value}")


def assert_not_synthetic_truth_escalation(origin: str, current: EpistemicState, nxt: EpistemicState) -> None:
    if origin == "SYNTHETIC" and current in {EpistemicState.UNVERIFIED, EpistemicState.EVIDENCE_BOUNDED} and nxt == EpistemicState.VERIFIED:
        raise FailClosed("SYNTHETIC_TRUTH_ESCALATION_REJECTED")
