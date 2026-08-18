"""Governance: no auto-canonical, no model delete, no V9 mutation, no tool execution from model text."""
from __future__ import annotations

from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now

REASONS = {
    "DELETE_MODEL": "AUTO_TEACHER_DELETE_REJECTED",
    "PROMOTE_CANONICAL": "AUTO_CANONICAL_PROMOTION_REJECTED",
    "MUTATE_V9": "RAIOS_V9_MUTATION_REJECTED",
    "EXECUTE_FROM_MODEL": "MODEL_OUTPUT_CANNOT_EXECUTE_TOOLS",
    "AUTO_ACTIVATE_SKILL": "SKILL_CANDIDATE_CANNOT_AUTO_ACTIVATE",
    "AUTO_PROMOTE_ADAPTER": "ADAPTER_CANNOT_AUTO_PROMOTE",
    "AUTO_PAY_DEBT": "READING_ALONE_DOES_NOT_PAY_DEBT",
    "AUTO_REPAIR_CANONICAL": "AUTO_REPAIR_CANONICAL_REJECTED",
}


class Governance:
    def __init__(self, store: Any) -> None:
        self.store = store

    def reject(self, action: str, detail: dict[str, Any] | None = None) -> None:
        reason = REASONS.get(action, f"GOVERNANCE_REJECTED:{action}")
        payload = {"action": action, "reason": reason, "detail": detail or {}}
        action_id = deterministic_id("gov", action, reason)
        self.store.conn.execute(
            """
            INSERT INTO governance_actions(action_id, action, allowed, reason, payload_json, created_at)
            VALUES (?, ?, 0, ?, ?, ?)
            """,
            (action_id, action, reason, canonical_json(payload), utc_now()),
        )
        self.store.append_event("GOVERNANCE_REJECTED", action_id, payload)
        raise FailClosed(reason)
