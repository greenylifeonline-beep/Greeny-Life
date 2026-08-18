"""A17.6 Differential + assimilation engine.

The teacher is never assumed correct. Outputs are candidates only.
VALIDATED != CANONICAL. Learning debt cannot auto-pay.
"""
from __future__ import annotations

import json
from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import (
    AuthorityState,
    DifferentialOutcome,
    DifferentialRecord,
    EventType,
    to_jsonable,
)


def _as_set(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        return {values} if values.strip() else set()
    return {str(v) for v in values if str(v).strip()}


def _ordered(values: set[str]) -> tuple[str, ...]:
    return tuple(sorted(values))


class DifferentialEngine:
    def __init__(self, store: Any) -> None:
        self.store = store

    def compare(
        self,
        student: dict[str, Any],
        teacher: dict[str, Any],
        *,
        independent_verifier: dict[str, Any] | None = None,
        task_id: str | None = None,
        capability: str | None = None,
    ) -> dict[str, Any]:
        task_id = task_id or str(student.get("task_id") or teacher.get("task_id") or "")
        capability = capability or str(student.get("capability") or teacher.get("capability") or "")
        if not task_id or not capability:
            raise FailClosed("DIFFERENTIAL_MISSING_TASK_OR_CAPABILITY")

        student_items = self._bag(student)
        teacher_items = self._bag(teacher)
        student_missed = teacher_items["all"] - student_items["all"]
        teacher_added = teacher_items["all"] - student_items["all"]
        teacher_missed = student_items["all"] - teacher_items["all"]
        missing_concepts = teacher_items["claims"] - student_items["claims"]
        wrong_tool_selection = teacher_items["tools"] - student_items["tools"]
        better_tool_sequence = teacher_items["procedures"] - student_items["procedures"]
        reusable = teacher_items["heuristics"] | teacher_items["procedures"]
        weaker_teacher = student_items["heuristics"] - teacher_items["heuristics"] if student_items["all"] else set()

        student_correct = self._correctness(student, independent_verifier, "student")
        teacher_correct = self._correctness(teacher, independent_verifier, "teacher")
        outcome = self._outcome(student_correct, teacher_correct, student_items, teacher_items)

        teacher_error_possibility: set[str] = set()
        if teacher_correct is not True:
            teacher_error_possibility.add("TEACHER_NOT_ASSUMED_CORRECT")
        if teacher_correct is False:
            teacher_error_possibility.add("TEACHER_MARKED_INCORRECT")
        if outcome in {
            DifferentialOutcome.STUDENT_RIGHT_TEACHER_WRONG,
            DifferentialOutcome.BOTH_PARTIAL,
            DifferentialOutcome.UNRESOLVED,
        }:
            teacher_error_possibility.add(outcome.value)

        bad_assumptions = _as_set(student.get("bad_assumptions")) | _as_set(teacher.get("student_bad_assumptions"))
        ignored_evidence = _as_set(student.get("ignored_evidence"))
        missing_prerequisites = _as_set(student.get("missing_prerequisites")) | _as_set(teacher.get("prerequisites")) - student_items["claims"]
        open_uncertainty = (
            _as_set(student.get("uncertainties"))
            | _as_set(teacher.get("uncertainties"))
            | ({"UNRESOLVED_DIFFERENTIAL"} if outcome is DifferentialOutcome.UNRESOLVED else set())
        )
        if independent_verifier is None and (student_correct is None or teacher_correct is None):
            open_uncertainty.add("NO_INDEPENDENT_VERIFIER")

        record = DifferentialRecord(
            differential_id=deterministic_id(
                "diff",
                task_id,
                capability,
                str(student.get("observation_id") or student.get("actor") or "student"),
                str(teacher.get("observation_id") or teacher.get("teacher_id") or "teacher"),
            ),
            task_id=task_id,
            capability=capability,
            student_observation_id=student.get("observation_id"),
            teacher_observation_id=teacher.get("observation_id"),
            outcome=outcome,
            student_missed=_ordered(student_missed),
            teacher_added=_ordered(teacher_added),
            teacher_missed=_ordered(teacher_missed),
            missing_concepts=_ordered(missing_concepts),
            bad_assumptions=_ordered(bad_assumptions),
            ignored_evidence=_ordered(ignored_evidence),
            wrong_tool_selection=_ordered(wrong_tool_selection),
            better_tool_sequence=_ordered(better_tool_sequence),
            superior_strategy=_ordered(teacher_items["heuristics"] - student_items["heuristics"]),
            weaker_teacher_strategy=_ordered(weaker_teacher),
            teacher_error_possibility=_ordered(teacher_error_possibility),
            missing_prerequisites=_ordered(missing_prerequisites),
            reusable_patterns=_ordered(reusable),
            skill_candidates=_ordered(_as_set(teacher.get("skill_candidates")) | _as_set(student.get("skill_candidates"))),
            policy_candidates=_ordered(_as_set(teacher.get("policy_candidates"))),
            failure_recovery_candidates=_ordered(
                _as_set(teacher.get("recovery_patterns")) | _as_set(teacher.get("failure_patterns"))
            ),
            open_uncertainty=_ordered(open_uncertainty),
            teacher_assumed_correct=False,
        )
        payload = to_jsonable(record.__dict__)
        payload["canonical"] = False
        with self.store.transaction():
            self.store.conn.execute(
                """
                INSERT OR REPLACE INTO differentials(
                    differential_id, task_id, capability, outcome, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.differential_id,
                    record.task_id,
                    record.capability,
                    record.outcome.value,
                    canonical_json(payload),
                    record.created_at,
                ),
            )
            self.store.append_event(
                EventType.DIFFERENTIAL_COMPUTED,
                record.differential_id,
                {"outcome": record.outcome.value, "teacher_assumed_correct": False},
            )
            candidates = self._assimilate(record, payload)
            payload["candidates"] = candidates
        return payload

    def _bag(self, attempt: dict[str, Any]) -> dict[str, set[str]]:
        claims = _as_set(attempt.get("claims"))
        procedures = _as_set(attempt.get("procedures"))
        heuristics = _as_set(attempt.get("heuristics"))
        tools = _as_set(attempt.get("tool_strategies") or attempt.get("tools"))
        text = str(attempt.get("raw_text") or attempt.get("text") or "")
        tokens = {tok.strip() for tok in re_split(text) if len(tok.strip()) > 3}
        return {
            "claims": claims,
            "procedures": procedures,
            "heuristics": heuristics,
            "tools": tools,
            "all": claims | procedures | heuristics | tools | tokens,
        }

    def _correctness(
        self,
        attempt: dict[str, Any],
        verifier: dict[str, Any] | None,
        role: str,
    ) -> bool | None:
        if verifier and role in verifier:
            value = verifier[role]
            if value is None:
                return None
            return bool(value)
        if "correct" in attempt:
            return bool(attempt["correct"])
        if "result_correct" in attempt:
            return bool(attempt["result_correct"])
        return None

    def _outcome(
        self,
        student_correct: bool | None,
        teacher_correct: bool | None,
        student_items: dict[str, set[str]],
        teacher_items: dict[str, set[str]],
    ) -> DifferentialOutcome:
        if student_correct is True and teacher_correct is False:
            return DifferentialOutcome.STUDENT_RIGHT_TEACHER_WRONG
        if student_correct is False and teacher_correct is True:
            return DifferentialOutcome.STUDENT_WRONG_TEACHER_RIGHT
        if student_correct is False and teacher_correct is False:
            return DifferentialOutcome.BOTH_WRONG
        if student_correct is True and teacher_correct is True:
            if student_items["all"] != teacher_items["all"]:
                return DifferentialOutcome.BOTH_CORRECT_DIFFERENT
            return DifferentialOutcome.BOTH_CORRECT_DIFFERENT if student_items["procedures"] != teacher_items["procedures"] else DifferentialOutcome.BOTH_CORRECT_DIFFERENT
        if student_correct is None or teacher_correct is None:
            overlap = student_items["all"] & teacher_items["all"]
            if overlap and (student_items["all"] - teacher_items["all"]) and (teacher_items["all"] - student_items["all"]):
                return DifferentialOutcome.BOTH_PARTIAL
            return DifferentialOutcome.UNRESOLVED
        overlap = student_items["all"] & teacher_items["all"]
        if overlap and (student_items["all"] != teacher_items["all"]):
            return DifferentialOutcome.BOTH_PARTIAL
        return DifferentialOutcome.UNRESOLVED

    def _assimilate(self, record: DifferentialRecord, payload: dict[str, Any]) -> dict[str, str]:
        created: dict[str, str] = {}
        specs = [
            ("KnowledgeCandidate", "knowledge", record.missing_concepts + record.reusable_patterns),
            ("SkillCandidate", "skill", record.skill_candidates + record.reusable_patterns),
            ("PolicyCandidate", "policy", record.policy_candidates),
            ("TrainingCandidate", "training", record.reusable_patterns),
            ("TransferTestCandidate", "transfer", record.open_uncertainty and ("unseen-transfer:" + record.capability,)),
            ("LearningDebtCandidate", "learning_debt", record.missing_concepts + record.missing_prerequisites + record.student_missed),
        ]
        for kind, slug, items in specs:
            if not items:
                continue
            candidate_id = deterministic_id("cand", slug, record.differential_id, kind)
            body = {
                "candidate_id": candidate_id,
                "kind": kind,
                "capability": record.capability,
                "items": list(items),
                "differential_id": record.differential_id,
                "authority_state": AuthorityState.CANDIDATE.value,
                "canonical": False,
                "validated": False,
                "learning_complete": False,
            }
            self.store.conn.execute(
                """
                INSERT OR REPLACE INTO candidates(
                    candidate_id, kind, capability, authority_state, canonical, payload_json, created_at
                ) VALUES (?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    candidate_id,
                    kind,
                    record.capability,
                    AuthorityState.CANDIDATE.value,
                    canonical_json(body),
                    utc_now(),
                ),
            )
            self.store.append_event(EventType.CANDIDATE_CREATED, candidate_id, {"kind": kind, "canonical": False})
            created[kind] = candidate_id
            if kind == "LearningDebtCandidate":
                debt_id = deterministic_id("ldebt", record.capability, record.differential_id)
                self.store.conn.execute(
                    """
                    INSERT OR REPLACE INTO learning_debt(
                        debt_id, capability, status, payload_json, created_at, updated_at
                    ) VALUES (?, ?, 'OPEN', ?, ?, ?)
                    """,
                    (debt_id, record.capability, canonical_json({"auto_pay": False, **body}), utc_now(), utc_now()),
                )
                created["learning_debt_id"] = debt_id
        return created


def re_split(text: str) -> list[str]:
    out: list[str] = []
    buf = []
    for ch in text.lower():
        if ch.isalnum() or ch in "-_":
            buf.append(ch)
        elif buf:
            out.append("".join(buf))
            buf = []
    if buf:
        out.append("".join(buf))
    return out
