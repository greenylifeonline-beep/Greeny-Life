"""A17.8 Teacher retirement engine.

Retirement is capability-specific first. Models are never deleted automatically.
Deletion remains external, manual, and governed.
"""
from __future__ import annotations

import json
from typing import Any

from ..identity import FailClosed, canonical_json, utc_now
from ..models import EventType, RetirementDecision, TeacherLifecycle
from ..transitions import assert_teacher_lifecycle


class RetirementEngine:
    def __init__(self, store: Any, mastery: Any, governance: Any) -> None:
        self.store = store
        self.mastery = mastery
        self.governance = governance

    def upsert_teacher_capability(
        self,
        teacher_id: str,
        capability: str,
        model: str,
        *,
        unique_capability: bool = False,
        lifecycle: TeacherLifecycle = TeacherLifecycle.ACTIVE_TEACHER,
    ) -> dict[str, Any]:
        payload = {
            "teacher_id": teacher_id,
            "capability": capability,
            "model": model,
            "lifecycle": lifecycle.value,
            "unique_capability": unique_capability,
            "deletion_performed": False,
        }
        self.store.conn.execute(
            """
            INSERT INTO teacher_capability(
                teacher_id, capability, model, lifecycle, unique_capability, payload_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(teacher_id, capability) DO UPDATE SET
                model=excluded.model,
                unique_capability=excluded.unique_capability,
                payload_json=excluded.payload_json,
                updated_at=excluded.updated_at
            """,
            (
                teacher_id,
                capability,
                model,
                lifecycle.value,
                1 if unique_capability else 0,
                canonical_json(payload),
                utc_now(),
            ),
        )
        return payload

    def transition(self, teacher_id: str, capability: str, nxt: TeacherLifecycle) -> dict[str, Any]:
        row = self._row(teacher_id, capability)
        current = TeacherLifecycle(row["lifecycle"])
        before = dict(row)
        try:
            assert_teacher_lifecycle(current, nxt)
        except FailClosed:
            after = self._row(teacher_id, capability)
            if after["lifecycle"] != before["lifecycle"]:
                raise FailClosed("REJECTED_TRANSITION_MUTATED_STATE")
            raise
        payload = json.loads(row["payload_json"])
        payload["lifecycle"] = nxt.value
        payload["updated_at"] = utc_now()
        self.store.conn.execute(
            """
            UPDATE teacher_capability
            SET lifecycle = ?, payload_json = ?, updated_at = ?
            WHERE teacher_id = ? AND capability = ?
            """,
            (nxt.value, canonical_json(payload), payload["updated_at"], teacher_id, capability),
        )
        return payload

    def evaluate(self, teacher_id: str, capability: str) -> dict[str, Any]:
        row = self._row(teacher_id, capability)
        evaluation = self.mastery.evaluate(capability)
        gates = evaluation["gates"]
        unique = bool(row["unique_capability"])
        blockers: list[str] = []
        ranked: list[RetirementDecision] = []
        if unique:
            blockers.append("unique_capability")
            ranked.append(RetirementDecision.BLOCKED_BY_UNIQUE_CAPABILITY)
        if not gates["unseen_transfer"]:
            blockers.append("unseen_transfer")
            ranked.append(RetirementDecision.BLOCKED_BY_TRANSFER)
        if not gates["retention_gate"]:
            blockers.append("retention")
            ranked.append(RetirementDecision.BLOCKED_BY_RETENTION)
        if not gates["regression_gate"] or not gates["verifier_failure"]:
            blockers.append("regression_or_verifier")
            ranked.append(RetirementDecision.BLOCKED_BY_REGRESSION)
        if not evaluation["dimensions"]["evidence_refs"]:
            blockers.append("evidence")
            ranked.append(RetirementDecision.BLOCKED_BY_EVIDENCE)
        if not evaluation["empirical_mastery"] and not ranked:
            blockers.append("mastery_incomplete")
            ranked.append(RetirementDecision.NOT_ELIGIBLE)
        decision = ranked[0] if ranked else RetirementDecision.RETIREMENT_ELIGIBLE
        result = {
            "teacher_id": teacher_id,
            "capability": capability,
            "model": row["model"],
            "lifecycle": row["lifecycle"],
            "decision": decision.value,
            "blockers": blockers,
            "capability_specific": True,
            "model_deleted": False,
            "auto_delete": False,
            "deletion_requires": "HUMAN_GOVERNED_APPROVAL",
            "mastery": evaluation,
            "canonical": False,
        }
        with self.store.transaction():
            self.store.append_event(EventType.RETIREMENT_EVALUATED, f"{teacher_id}:{capability}", result)
        return result

    def evaluate_model_retirement(self, teacher_id: str) -> dict[str, Any]:
        rows = self.store.conn.execute(
            "SELECT capability, lifecycle, unique_capability, model FROM teacher_capability WHERE teacher_id = ?",
            (teacher_id,),
        ).fetchall()
        if not rows:
            raise FailClosed("TEACHER_UNKNOWN")
        cap_results = [self.evaluate(teacher_id, row["capability"]) for row in rows]
        unique_remaining = [row["capability"] for row in rows if row["unique_capability"]]
        all_retired_for_cap = all(
            row["lifecycle"] == TeacherLifecycle.RETIRED_FOR_CAPABILITY.value for row in rows
        )
        all_eligible = all(item["decision"] == RetirementDecision.RETIREMENT_ELIGIBLE.value for item in cap_results)
        decision = RetirementDecision.RETIRED_MODEL if False else RetirementDecision.NOT_ELIGIBLE
        blockers: list[str] = []
        if unique_remaining:
            decision = RetirementDecision.BLOCKED_BY_UNIQUE_CAPABILITY
            blockers.append("unique_capability_remains")
        elif not all_eligible:
            decision = RetirementDecision.NOT_ELIGIBLE
            blockers.append("not_all_capabilities_eligible")
        elif not all_retired_for_cap:
            decision = RetirementDecision.NOT_ELIGIBLE
            blockers.append("not_all_capabilities_retired")
        else:
            decision = RetirementDecision.RETIREMENT_ELIGIBLE
        result = {
            "teacher_id": teacher_id,
            "model": rows[0]["model"],
            "decision": decision.value,
            "capabilities": cap_results,
            "model_deleted": False,
            "auto_delete": False,
            "retired_model_requires_governed_deletion": True,
            "blockers": blockers,
        }
        return result

    def delete_model(self, teacher_id: str, approval_token: str | None = None) -> None:
        if not approval_token:
            self.governance.assert_no_model_delete()
        self.governance.record_external_approval("DELETE_MODEL_EXTERNAL", approval_token or "")
        raise FailClosed("MODEL_DELETION_REMAINS_EXTERNAL")

    def _row(self, teacher_id: str, capability: str) -> Any:
        row = self.store.conn.execute(
            "SELECT * FROM teacher_capability WHERE teacher_id = ? AND capability = ?",
            (teacher_id, capability),
        ).fetchone()
        if not row:
            raise FailClosed("TEACHER_CAPABILITY_UNKNOWN")
        return row
