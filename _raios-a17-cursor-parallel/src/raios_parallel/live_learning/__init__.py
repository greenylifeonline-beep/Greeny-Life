"""A17.14 Live student execution engine with contamination protection."""
from __future__ import annotations

import json
from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, sha256_text, utc_now
from ..models import LiveStage, StudentState
from ..transitions import assert_student

HIDDEN_STAGES = {LiveStage.BASELINE, LiveStage.UNSEEN_TRANSFER, LiveStage.FREEZE_BASELINE}


class LiveStudentEngine:
    def __init__(self, store: Any) -> None:
        self.store = store

    def start_session(self, *, capability: str, teaching_packet: dict[str, Any], practice_plan: dict[str, Any] | None = None) -> dict[str, Any]:
        token = teaching_packet.get("contamination_token") or sha256_text(canonical_json(teaching_packet))[:16]
        packet_ref = self.store.put_bytes(canonical_json(teaching_packet).encode("utf-8"))
        session_id = deterministic_id("sess", capability, token)
        payload = {
            "session_id": session_id,
            "capability": capability,
            "state": StudentState.BASELINE_REQUIRED.value,
            "baseline_frozen": False,
            "teacher_visible": False,
            "contamination_token": token,
            "packet_ref": f"artifact://sha256/{packet_ref}",
            "practice_plan": practice_plan or {},
            "stages": [],
            "baseline": None,
            "evidence": {
                "unseen_transfer": False,
                "retention": False,
                "independent_verification": False,
            },
            "mastered": False,
            "canonical": False,
        }
        self.store.conn.execute(
            """
            INSERT INTO live_sessions(
                session_id, capability, state, baseline_frozen, teacher_visible,
                contamination_token, payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, 0, 0, ?, ?, ?, ?)
            """,
            (session_id, capability, payload["state"], token, canonical_json(payload), utc_now(), utc_now()),
        )
        self.store.append_event("SESSION_STARTED", session_id, {"capability": capability, "teacher_visible": False})
        return payload

    def attempt(self, session_id: str, stage: LiveStage | str, attempt: dict[str, Any]) -> dict[str, Any]:
        stage = LiveStage(stage)
        session = self._load(session_id)
        if stage is LiveStage.UNSEEN_TRANSFER:
            session["teacher_visible"] = False
        self._assert_contamination(session, stage, attempt)
        if stage is LiveStage.BASELINE:
            if session["state"] != StudentState.BASELINE_REQUIRED.value:
                raise FailClosed("BASELINE_ALREADY_CONSUMED")
            session["baseline"] = attempt
            session["stages"].append({"stage": stage.value, "at": utc_now()})
        elif stage is LiveStage.FREEZE_BASELINE:
            if not session.get("baseline"):
                raise FailClosed("BASELINE_REQUIRED_BEFORE_FREEZE")
            session = self._transition(session, StudentState.BASELINE_FROZEN)
            session["baseline_frozen"] = True
            session["baseline_frozen_at"] = utc_now()
        elif stage is LiveStage.TEACHER_EXPOSURE:
            if not session["baseline_frozen"]:
                raise FailClosed("BASELINE_MUST_BE_FROZEN_BEFORE_TEACHING")
            session = self._transition(session, StudentState.TEACHING_ACTIVE)
            session["teacher_visible"] = True
        elif stage is LiveStage.GUIDED_PRACTICE:
            session = self._transition(session, StudentState.PRACTICE_ACTIVE)
        elif stage is LiveStage.UNSEEN_TRANSFER:
            session["teacher_visible"] = False
            session = self._transition(session, StudentState.TRANSFER_PENDING)
            passed = bool(attempt.get("pass"))
            session["evidence"]["unseen_transfer"] = passed
            session = self._transition(
                session, StudentState.TRANSFER_PASSED if passed else StudentState.TRANSFER_FAILED
            )
        elif stage is LiveStage.RETENTION:
            if session["state"] == StudentState.TRANSFER_PASSED.value:
                session = self._transition(session, StudentState.RETENTION_PENDING)
            if session["state"] != StudentState.RETENTION_PENDING.value:
                raise FailClosed("RETENTION_REQUIRES_TRANSFER_PASS")
            passed = bool(attempt.get("pass"))
            session["evidence"]["retention"] = passed
            session = self._transition(
                session, StudentState.RETENTION_PASSED if passed else StudentState.NOT_MASTERED
            )
        elif stage is LiveStage.INDEPENDENT_VERIFICATION:
            if session["state"] == StudentState.RETENTION_PASSED.value:
                session = self._transition(session, StudentState.VERIFICATION_PENDING)
            if session["state"] != StudentState.VERIFICATION_PENDING.value:
                raise FailClosed("INDEPENDENT_VERIFICATION_REQUIRES_RETENTION")
            passed = bool(attempt.get("pass"))
            session["evidence"]["independent_verification"] = passed
            if not passed:
                session = self._transition(session, StudentState.NOT_MASTERED)
        elif stage is LiveStage.COMPETENCY_UPDATE:
            session = self.evaluate_mastery(session_id)
            return session
        elif stage in {LiveStage.DIFFERENTIAL, LiveStage.FAILURE_INJECTION, LiveStage.RECOVERY}:
            session["stages"].append({"stage": stage.value, "attempt": attempt, "at": utc_now()})
        else:
            raise FailClosed(f"UNKNOWN_LIVE_STAGE:{stage.value}")
        session["stages"].append({"stage": stage.value, "at": utc_now()})
        self._save(session)
        return session

    def evaluate_mastery(self, session_id: str) -> dict[str, Any]:
        session = self._load(session_id)
        evidence = session["evidence"]
        missing = [k for k, v in evidence.items() if not v]
        if not session["baseline_frozen"]:
            missing.append("baseline_frozen")
        if missing:
            session["mastered"] = False
            if session["state"] != StudentState.NOT_MASTERED.value:
                try:
                    session = self._transition(session, StudentState.NOT_MASTERED)
                except FailClosed:
                    session["state"] = StudentState.NOT_MASTERED.value
                    session["transition_blocked_to_mastered"] = True
            session["mastery_blockers"] = missing
            self._save(session)
            raise FailClosed("MASTERY_IMPOSSIBLE_WITHOUT:" + ",".join(missing))
        if session["state"] != StudentState.VERIFICATION_PENDING.value:
            raise FailClosed("MASTERY_REQUIRES_VERIFICATION_PENDING")
        session = self._transition(session, StudentState.MASTERED)
        session["mastered"] = True
        self._save(session)
        return session

    def _assert_contamination(self, session: dict[str, Any], stage: LiveStage, attempt: dict[str, Any]) -> None:
        token = session["contamination_token"]
        blob = canonical_json(attempt)
        hidden_baseline = stage in {LiveStage.BASELINE, LiveStage.FREEZE_BASELINE}
        if hidden_baseline and session.get("teacher_visible"):
            raise FailClosed("TEACHER_CONTENT_MUST_REMAIN_HIDDEN")
        if stage in {LiveStage.BASELINE, LiveStage.UNSEEN_TRANSFER, LiveStage.FREEZE_BASELINE}:
            if token and token in blob:
                raise FailClosed("TEACHER_CONTENT_CONTAMINATION")
            if attempt.get("used_teacher_content"):
                raise FailClosed("TEACHER_CONTENT_CONTAMINATION")

    def _transition(self, session: dict[str, Any], nxt: StudentState) -> dict[str, Any]:
        current = StudentState(session["state"])
        snapshot = session["state"]
        try:
            assert_student(current, nxt)
        except FailClosed:
            after = self._load(session["session_id"])
            if after["state"] != snapshot:
                raise FailClosed("REJECTED_TRANSITION_MUTATED_STATE")
            raise
        session["state"] = nxt.value
        return session

    def _load(self, session_id: str) -> dict[str, Any]:
        row = self.store.conn.execute(
            "SELECT payload_json FROM live_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            raise FailClosed("SESSION_UNKNOWN")
        return json.loads(row["payload_json"])

    def _save(self, session: dict[str, Any]) -> None:
        self.store.conn.execute(
            """
            UPDATE live_sessions
            SET state = ?, baseline_frozen = ?, teacher_visible = ?, payload_json = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (
                session["state"],
                1 if session.get("baseline_frozen") else 0,
                1 if session.get("teacher_visible") else 0,
                canonical_json(session),
                utc_now(),
                session["session_id"],
            ),
        )
        self.store.append_event("SESSION_UPDATED", session["session_id"], {"state": session["state"]})
