"""A17.17 teacher retirement engine. Never deletes models."""
from __future__ import annotations

import json
from typing import Any

from ..identity import FailClosed, canonical_json, utc_now
from ..models import RetirementDecision, TeacherLifecycle
from ..transitions import assert_teacher


class RetirementEngine:
    def __init__(self, store: Any, mastery: Any, governance: Any) -> None:
        self.store = store
        self.mastery = mastery
        self.governance = governance

    def upsert(self, teacher_id: str, capability: str, model: str, *, unique: bool = False) -> dict[str, Any]:
        payload = {
            "teacher_id": teacher_id,
            "capability": capability,
            "model": model,
            "lifecycle": TeacherLifecycle.ACTIVE_TEACHER.value,
            "unique_capability": unique,
            "deletion_performed": False,
        }
        self.store.conn.execute(
            """
            INSERT INTO teacher_capability(teacher_id, capability, model, lifecycle, unique_capability, payload_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(teacher_id, capability) DO UPDATE SET
                unique_capability=excluded.unique_capability, payload_json=excluded.payload_json, updated_at=excluded.updated_at
            """,
            (teacher_id, capability, model, payload["lifecycle"], 1 if unique else 0, canonical_json(payload), utc_now()),
        )
        return payload

    def transition(self, teacher_id: str, capability: str, nxt: TeacherLifecycle) -> dict[str, Any]:
        row = self._row(teacher_id, capability)
        current = TeacherLifecycle(row["lifecycle"])
        snapshot = row["lifecycle"]
        try:
            assert_teacher(current, nxt)
        except FailClosed:
            after = self._row(teacher_id, capability)
            if after["lifecycle"] != snapshot:
                raise FailClosed("REJECTED_TRANSITION_MUTATED_STATE")
            raise
        payload = json.loads(row["payload_json"])
        payload["lifecycle"] = nxt.value
        self.store.conn.execute(
            "UPDATE teacher_capability SET lifecycle = ?, payload_json = ?, updated_at = ? WHERE teacher_id = ? AND capability = ?",
            (nxt.value, canonical_json(payload), utc_now(), teacher_id, capability),
        )
        return payload

    def evaluate(self, teacher_id: str, capability: str) -> dict[str, Any]:
        row = self._row(teacher_id, capability)
        evaluation = self.mastery.evaluate(capability)
        dep = self.mastery.teacher_dependency(capability)
        gates = evaluation["gates"]
        ranked: list[RetirementDecision] = []
        blockers: list[str] = []
        if row["unique_capability"]:
            ranked.append(RetirementDecision.BLOCKED_BY_UNIQUE_CAPABILITY)
            blockers.append("unique_capability")
        if not gates["unseen_transfer"]:
            ranked.append(RetirementDecision.BLOCKED_BY_TRANSFER)
            blockers.append("unseen_transfer")
        if not gates["retention"]:
            ranked.append(RetirementDecision.BLOCKED_BY_RETENTION)
            blockers.append("retention")
        if not gates["regression"] or not gates["verifier_failure"]:
            ranked.append(RetirementDecision.BLOCKED_BY_REGRESSION)
            blockers.append("regression")
        if dep["dependent"]:
            ranked.append(RetirementDecision.BLOCKED_BY_TEACHER_DEPENDENCY)
            blockers.append("teacher_dependency")
        if not evaluation["dimensions"].get("evidence_refs"):
            ranked.append(RetirementDecision.BLOCKED_BY_EVIDENCE)
            blockers.append("evidence")
        if not evaluation["empirical_mastery"] and not ranked:
            ranked.append(RetirementDecision.NOT_ELIGIBLE)
            blockers.append("mastery_incomplete")
        decision = ranked[0] if ranked else RetirementDecision.RETIREMENT_ELIGIBLE
        result = {
            "teacher_id": teacher_id,
            "capability": capability,
            "model": row["model"],
            "lifecycle": row["lifecycle"],
            "decision": decision.value,
            "blockers": blockers,
            "capability_specific": True,
            "auto_delete": False,
            "model_deleted": False,
            "deletion_requires": "HUMAN_GOVERNED_APPROVAL",
            "mastery": evaluation,
            "canonical": False,
        }
        self.store.append_event("RETIREMENT_EVALUATED", f"{teacher_id}:{capability}", result)
        return result

    def status(self, teacher_id: str) -> dict[str, Any]:
        rows = self.store.conn.execute(
            "SELECT capability FROM teacher_capability WHERE teacher_id = ?", (teacher_id,)
        ).fetchall()
        return {"teacher_id": teacher_id, "capabilities": [self.evaluate(teacher_id, r["capability"]) for r in rows]}

    def report(self, teacher_id: str) -> dict[str, Any]:
        return {"report": self.status(teacher_id), "auto_delete": False}

    def delete_model(self, teacher_id: str) -> None:
        self.governance.reject("DELETE_MODEL", {"teacher_id": teacher_id})

    def _row(self, teacher_id: str, capability: str) -> Any:
        row = self.store.conn.execute(
            "SELECT * FROM teacher_capability WHERE teacher_id = ? AND capability = ?",
            (teacher_id, capability),
        ).fetchone()
        if not row:
            raise FailClosed("TEACHER_CAPABILITY_UNKNOWN")
        return row
