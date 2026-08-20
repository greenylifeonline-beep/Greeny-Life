"""Canonical knowledge-state machine: DISCOVERED → VALIDATED → CANONICAL.

NeuroLingua must not promote linguistic observations directly to CANONICAL.
Promotion is an explicit, policy-gated operation on the Cognitive WAL.
"""

from __future__ import annotations

from enum import Enum


class KnowledgeState(str, Enum):
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    CANONICAL = "CANONICAL"

    @property
    def rank(self) -> int:
        return {
            KnowledgeState.DISCOVERED: 0,
            KnowledgeState.VALIDATED: 1,
            KnowledgeState.CANONICAL: 2,
        }[self]


_ALLOWED_TRANSITIONS: dict[KnowledgeState, frozenset[KnowledgeState]] = {
    KnowledgeState.DISCOVERED: frozenset(
        {KnowledgeState.DISCOVERED, KnowledgeState.VALIDATED}
    ),
    KnowledgeState.VALIDATED: frozenset(
        {KnowledgeState.VALIDATED, KnowledgeState.CANONICAL}
    ),
    KnowledgeState.CANONICAL: frozenset({KnowledgeState.CANONICAL}),
}


def can_transition(current: KnowledgeState, target: KnowledgeState) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


def assert_transition(current: KnowledgeState, target: KnowledgeState) -> None:
    if not can_transition(current, target):
        raise ValueError(
            f"Illegal knowledge-state transition {current.value} → {target.value}. "
            "Canonical promotion must pass VALIDATED and existing durability policy."
        )
