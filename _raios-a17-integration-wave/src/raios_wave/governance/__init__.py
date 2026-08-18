"""Governance: no auto-canonical promotion, no model deletion, no V9 mutation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import EventType

FORBIDDEN_V9_PREFIXES = (
    "RAIOS/V9/",
    "RAIOS\\V9\\",
)

FORBIDDEN_ACTIONS = {
    "DELETE_MODEL": "AUTO_TEACHER_DELETE_REJECTED",
    "PROMOTE_CANONICAL": "AUTO_CANONICAL_PROMOTION_REJECTED",
    "MUTATE_V9": "RAIOS_V9_MUTATION_REJECTED",
    "APPLY_CORTEX_TEXT": "DIRECT_CANONICAL_MUTATION_REJECTED",
    "PAY_LEARNING_DEBT": "AUTO_DEBT_PAYMENT_REJECTED",
}


class Governance:
    def __init__(self, store: Any) -> None:
        self.store = store

    def reject(self, action: str, detail: dict[str, Any] | None = None) -> None:
        reason = FORBIDDEN_ACTIONS.get(action, f"GOVERNANCE_REJECTED:{action}")
        payload = {"action": action, "reason": reason, "detail": detail or {}}
        action_id = deterministic_id("gov", action, canonical_json(payload))
        self.store.conn.execute(
            """
            INSERT INTO governance_actions(action_id, action, allowed, reason, payload_json, created_at)
            VALUES (?, ?, 0, ?, ?, ?)
            """,
            (action_id, action, reason, canonical_json(payload), utc_now()),
        )
        self.store.append_event(EventType.GOVERNANCE_REJECTED, action_id, payload)
        raise FailClosed(reason)

    def assert_not_v9_path(self, path: str | Path) -> None:
        text = str(path).replace("\\", "/")
        if "/RAIOS/V9/" in f"/{text}" or text.startswith("RAIOS/V9/"):
            self.reject("MUTATE_V9", {"path": text})

    def assert_no_model_delete(self) -> None:
        self.reject("DELETE_MODEL")

    def assert_no_canonical_promotion(self) -> None:
        self.reject("PROMOTE_CANONICAL")

    def record_external_approval(self, action: str, token: str) -> dict[str, Any]:
        if not token or not token.startswith("GOVERNED:"):
            raise FailClosed("GOVERNED_APPROVAL_MISSING")
        payload = {"action": action, "token": token, "allowed": True}
        action_id = deterministic_id("govok", action, token)
        self.store.conn.execute(
            """
            INSERT INTO governance_actions(action_id, action, allowed, reason, payload_json, created_at)
            VALUES (?, ?, 1, ?, ?, ?)
            """,
            (action_id, action, "EXTERNAL_GOVERNED_APPROVAL", canonical_json(payload), utc_now()),
        )
        return payload
