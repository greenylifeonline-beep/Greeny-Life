"""A20 skill compiler foundations. No auto-activate."""
from __future__ import annotations

import json
from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import SkillLifecycle
from ..transitions import assert_skill


class SkillCompiler:
    def __init__(self, store: Any, governance: Any) -> None:
        self.store = store
        self.governance = governance

    def compile(self, source: dict[str, Any]) -> dict[str, Any]:
        required = (
            "capability", "interface", "inputs", "outputs", "procedure",
            "tool_dependencies", "source_experiences", "source_knowledge",
            "source_teachers", "tests", "transfer_tests",
        )
        missing = [k for k in required if k not in source]
        if missing:
            raise FailClosed("SKILL_MISSING:" + ",".join(missing))
        skill_id = deterministic_id("skill", source["capability"], canonical_json(source["procedure"]))
        payload = {
            **source,
            "skill_id": skill_id,
            "lifecycle": SkillLifecycle.CANDIDATE.value,
            "success_count": int(source.get("success_count") or 0),
            "failure_count": int(source.get("failure_count") or 0),
            "rollback": source.get("rollback") or {"enabled": True},
            "version": source.get("version") or "0.1.0",
            "canonical": False,
            "active": False,
        }
        self.store.conn.execute(
            """
            INSERT INTO skills(skill_id, capability, lifecycle, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (skill_id, source["capability"], payload["lifecycle"], canonical_json(payload), utc_now(), utc_now()),
        )
        self.store.append_event("SKILL_CANDIDATE", skill_id, {"canonical": False})
        return payload

    def transition(self, skill_id: str, nxt: SkillLifecycle, *, activate: bool = False) -> dict[str, Any]:
        row = self.store.conn.execute("SELECT payload_json FROM skills WHERE skill_id = ?", (skill_id,)).fetchone()
        if not row:
            raise FailClosed("SKILL_UNKNOWN")
        payload = json.loads(row["payload_json"])
        snapshot = payload["lifecycle"]
        try:
            assert_skill(SkillLifecycle(payload["lifecycle"]), nxt, activate=activate)
        except FailClosed:
            after = json.loads(
                self.store.conn.execute("SELECT payload_json FROM skills WHERE skill_id = ?", (skill_id,)).fetchone()["payload_json"]
            )
            if after["lifecycle"] != snapshot:
                raise FailClosed("REJECTED_TRANSITION_MUTATED_STATE")
            raise
        payload["lifecycle"] = nxt.value
        payload["active"] = nxt is SkillLifecycle.ACTIVE
        payload["updated_at"] = utc_now()
        self.store.conn.execute(
            "UPDATE skills SET lifecycle = ?, payload_json = ?, updated_at = ? WHERE skill_id = ?",
            (payload["lifecycle"], canonical_json(payload), payload["updated_at"], skill_id),
        )
        return payload

    def auto_activate(self, skill_id: str) -> None:
        self.governance.reject("AUTO_ACTIVATE_SKILL", {"skill_id": skill_id})
