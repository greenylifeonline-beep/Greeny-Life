"""A17.15 Semantic differential + independent verifier.

Lexical overlap is a weak feature only, never final authority.
"""
from __future__ import annotations

from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import DifferentialOutcome, VerifierKind


def _tokens(text: str) -> set[str]:
    buf, out = [], []
    for ch in text.lower():
        if ch.isalnum() or ch in "-_":
            buf.append(ch)
        elif buf:
            out.append("".join(buf))
            buf = []
    if buf:
        out.append("".join(buf))
    return {t for t in out if len(t) > 2}


def _bag(answer: dict[str, Any]) -> dict[str, set[str]]:
    claims = set(map(str, answer.get("claims") or []))
    procedures = set(map(str, answer.get("procedures") or []))
    tools = set(map(str, answer.get("tools") or answer.get("tool_strategies") or []))
    evidence = set(map(str, answer.get("evidence") or []))
    return {
        "claims": claims,
        "procedures": procedures,
        "tools": tools,
        "evidence": evidence,
        "structural": claims | procedures | tools | evidence,
    }


class SemanticVerifier:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.providers = {item.value: True for item in VerifierKind}

    def compare(
        self,
        student: dict[str, Any],
        teacher: dict[str, Any],
        *,
        ground_truth: dict[str, Any] | None = None,
        test_execution: dict[str, Any] | None = None,
        structural_evidence: dict[str, Any] | None = None,
        provider: VerifierKind | str = VerifierKind.STRUCTURAL,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        provider = VerifierKind(provider)
        if provider is VerifierKind.MULTI_MODEL:
            return self._pending(provider, "MULTI_MODEL_UNAVAILABLE")
        if provider is VerifierKind.HUMAN_REVIEW:
            return self._pending(provider, "HUMAN_REVIEW_REQUIRED")
        if provider is VerifierKind.FUTURE_FRONTIER_TEACHER:
            return self._pending(provider, "FRONTIER_TEACHER_UNAVAILABLE")

        s_bag = _bag(student)
        t_bag = _bag(teacher)
        lexical = self._lexical(student, teacher)
        student_correct = self._correct(student, ground_truth, test_execution, "student")
        teacher_correct = self._correct(teacher, ground_truth, test_execution, "teacher")
        outcome = self._outcome(student_correct, teacher_correct, s_bag, t_bag)

        if provider is VerifierKind.TEST_EXECUTION and not test_execution:
            raise FailClosed("TEST_EXECUTION_EVIDENCE_MISSING")
        if provider is VerifierKind.DETERMINISTIC and ground_truth is None and test_execution is None:
            # deterministic still allowed via explicit correct flags
            if "correct" not in student and "correct" not in teacher:
                outcome = DifferentialOutcome.UNRESOLVED

        verdict = {
            "result_id": deterministic_id("ver", canonical_json(student)[:32], canonical_json(teacher)[:32], provider.value),
            "provider": provider.value,
            "outcome": outcome.value,
            "student_strengths": sorted(s_bag["structural"] - t_bag["structural"] if student_correct else s_bag["structural"] & t_bag["structural"]),
            "student_misses": sorted(t_bag["structural"] - s_bag["structural"]),
            "teacher_strengths": sorted(t_bag["structural"] - s_bag["structural"] if teacher_correct else t_bag["claims"]),
            "teacher_misses": sorted(s_bag["structural"] - t_bag["structural"]),
            "bad_assumptions": list(student.get("assumptions") or []) if student_correct is False else [],
            "missing_evidence": sorted(t_bag["evidence"] - s_bag["evidence"]),
            "ignored_evidence": list(student.get("ignored_evidence") or []),
            "tool_selection_diff": sorted(s_bag["tools"] ^ t_bag["tools"]),
            "reasoning_diff": sorted(s_bag["procedures"] ^ t_bag["procedures"]),
            "reusable_pattern": sorted(t_bag["procedures"] | s_bag["procedures"]),
            "failure_pattern": list(student.get("failures") or teacher.get("failures") or []),
            "teacher_error_probability": 0.0 if teacher_correct is True else (1.0 if teacher_correct is False else 0.5),
            "student_error_probability": 0.0 if student_correct is True else (1.0 if student_correct is False else 0.5),
            "uncertainty": 1.0 if outcome is DifferentialOutcome.UNRESOLVED else 0.2,
            "verdict": outcome.value,
            "lexical_similarity": lexical,
            "lexical_is_authority": False,
            "structural_evidence": structural_evidence or {},
            "teacher_assumed_correct": False,
            "canonical": False,
        }
        if lexical > 0.95 and outcome is DifferentialOutcome.UNRESOLVED:
            verdict["uncertainty"] = min(1.0, verdict["uncertainty"] + 0.1)
            verdict["note"] = "LEXICAL_OVERLAP_NOT_AUTHORITY"
        self.store.conn.execute(
            """
            INSERT OR REPLACE INTO verifier_results(result_id, session_id, outcome, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (verdict["result_id"], session_id, verdict["outcome"], canonical_json(verdict), utc_now()),
        )
        self.store.append_event("VERIFIER_RESULT", verdict["result_id"], {"outcome": verdict["outcome"], "provider": provider.value})
        return verdict

    def _pending(self, provider: VerifierKind, reason: str) -> dict[str, Any]:
        return {
            "provider": provider.value,
            "outcome": DifferentialOutcome.UNRESOLVED.value,
            "verdict": DifferentialOutcome.UNRESOLVED.value,
            "status": "PENDING",
            "reason": reason,
            "lexical_is_authority": False,
            "canonical": False,
        }

    def _lexical(self, student: dict[str, Any], teacher: dict[str, Any]) -> float:
        a = _tokens(str(student.get("text") or canonical_json(student)))
        b = _tokens(str(teacher.get("text") or canonical_json(teacher)))
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _correct(
        self,
        answer: dict[str, Any],
        truth: dict[str, Any] | None,
        tests: dict[str, Any] | None,
        role: str,
    ) -> bool | None:
        if tests and role in tests:
            return bool(tests[role])
        if truth and role in truth:
            return bool(truth[role])
        if "correct" in answer:
            return bool(answer["correct"])
        return None

    def _outcome(
        self,
        student_correct: bool | None,
        teacher_correct: bool | None,
        s_bag: dict[str, set[str]],
        t_bag: dict[str, set[str]],
    ) -> DifferentialOutcome:
        if student_correct is True and teacher_correct is False:
            return DifferentialOutcome.STUDENT_RIGHT_TEACHER_WRONG
        if student_correct is False and teacher_correct is True:
            return DifferentialOutcome.STUDENT_WRONG_TEACHER_RIGHT
        if student_correct is True and teacher_correct is True:
            return DifferentialOutcome.BOTH_CORRECT_DIFFERENT
        if student_correct is None or teacher_correct is None:
            overlap = s_bag["structural"] & t_bag["structural"]
            only_s = s_bag["structural"] - t_bag["structural"]
            only_t = t_bag["structural"] - s_bag["structural"]
            if overlap and only_s and only_t:
                return DifferentialOutcome.BOTH_PARTIAL
            return DifferentialOutcome.UNRESOLVED
        overlap = s_bag["structural"] & t_bag["structural"]
        if overlap and s_bag["structural"] != t_bag["structural"]:
            return DifferentialOutcome.BOTH_PARTIAL
        return DifferentialOutcome.UNRESOLVED
