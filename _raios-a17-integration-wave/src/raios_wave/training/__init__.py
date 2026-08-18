"""Validated training-candidate pipeline. Blind teacher copies are rejected."""
from __future__ import annotations

from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import AuthorityState, EventType, TrainingKind, TrainingState
from ..transitions import assert_training_transition


class TrainingCorpus:
    def __init__(self, store: Any) -> None:
        self.store = store

    def create(self, *, kind: TrainingKind | str, record: dict[str, Any]) -> dict[str, Any]:
        kind = TrainingKind(kind)
        required = (
            "teacher_source",
            "student_baseline",
            "teacher_output",
            "differential",
            "evidence",
            "validation_result",
            "transfer_result",
        )
        missing = [key for key in required if key not in record]
        if missing:
            raise FailClosed("TRAINING_CANDIDATE_MISSING:" + ",".join(missing))
        if record.get("copy_teacher_blindly"):
            raise FailClosed("BLIND_TEACHER_COPY_REJECTED")
        validation = record["validation_result"]
        if validation not in {"PASS", "FAIL", "PENDING"}:
            raise FailClosed("TRAINING_VALIDATION_UNKNOWN")
        state = TrainingState.DRAFT
        authority = AuthorityState.CANDIDATE
        if validation != "PASS":
            # Still draft; cannot be validated without PASS.
            pass
        quality = float(record.get("quality_score") or 0.0)
        candidate_id = deterministic_id("train", kind.value, canonical_json(record.get("differential")))
        payload = {
            "candidate_id": candidate_id,
            "kind": kind.value,
            "teacher_source": record["teacher_source"],
            "student_baseline": record["student_baseline"],
            "teacher_output": record["teacher_output"],
            "differential": record["differential"],
            "evidence": record["evidence"],
            "validation_result": validation,
            "transfer_result": record["transfer_result"],
            "license": record.get("license") or record.get("provenance"),
            "provenance": record.get("provenance"),
            "quality_score": quality,
            "authority_state": authority.value,
            "state": state.value,
            "canonical": False,
        }
        with self.store.transaction():
            self.store.conn.execute(
                """
                INSERT OR REPLACE INTO candidates(
                    candidate_id, kind, capability, authority_state, canonical, payload_json, created_at
                ) VALUES (?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    candidate_id,
                    kind.value,
                    record.get("capability"),
                    authority.value,
                    canonical_json(payload),
                    utc_now(),
                ),
            )
            self.store.append_event(
                EventType.TRAINING_CANDIDATE_CREATED,
                candidate_id,
                {"kind": kind.value, "validation_result": validation, "canonical": False},
            )
        return payload

    def promote_validated(self, candidate_id: str) -> dict[str, Any]:
        import json

        row = self.store.conn.execute(
            "SELECT payload_json FROM candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if not row:
            raise FailClosed("TRAINING_CANDIDATE_UNKNOWN")
        payload = json.loads(row["payload_json"])
        if payload.get("validation_result") != "PASS":
            raise FailClosed("TRAINING_CANDIDATE_REQUIRES_VALIDATION")
        if payload.get("transfer_result") not in {"PASS", True, "pass"}:
            raise FailClosed("TRAINING_CANDIDATE_REQUIRES_TRANSFER")
        current = TrainingState(payload["state"])
        nxt = TrainingState.VALIDATED
        assert_training_transition(current, nxt)
        payload["state"] = nxt.value
        payload["authority_state"] = AuthorityState.VALIDATED.value
        payload["canonical"] = False
        self.store.conn.execute(
            "UPDATE candidates SET authority_state = ?, payload_json = ? WHERE candidate_id = ?",
            (payload["authority_state"], canonical_json(payload), candidate_id),
        )
        return payload
