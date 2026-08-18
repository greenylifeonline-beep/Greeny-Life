"""Unseen transfer tests. Training IDs and unseen IDs are disjoint."""
from __future__ import annotations

from typing import Any

from .config import FailClosed, deterministic_id
from .event_bus import EventBus


class TransferEngine:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.train_ids: set[str] = set()
        self.unseen_ids: set[str] = set()

    def register_train(self, example_id: str) -> None:
        if example_id in self.unseen_ids:
            raise FailClosed("BENCHMARK_LEAKAGE")
        self.train_ids.add(example_id)

    def register_unseen(self, example_id: str) -> None:
        if example_id in self.train_ids:
            raise FailClosed("BENCHMARK_LEAKAGE")
        self.unseen_ids.add(example_id)

    def evaluate(self, case: dict[str, Any], diagnose, teacher_assistance: bool = False) -> dict[str, Any]:
        case_id = str(case.get("id") or deterministic_id("xfer", str(case)))
        if case_id not in self.unseen_ids:
            raise FailClosed("TRANSFER_IS_NOT_UNSEEN")
        if teacher_assistance:
            raise FailClosed("TRANSFER_REQUIRES_NO_TEACHER")
        predicted = diagnose(case)
        expected = case.get("expected")
        passed = predicted == expected
        rec = {
            "case_id": case_id,
            "passed": passed,
            "predicted": predicted,
            "expected": expected,
            "teacher_assistance": False,
            "mastery_claimed": False,
        }
        self.bus.emit("TRANSFER_RESULT", "transfer", rec)
        return rec

    def teacher_dependency(
        self,
        *,
        baseline_without_teacher: float,
        teacher_assisted: float,
        student_after_teaching: float,
        unseen_transfer: float,
        retention: float,
    ) -> dict[str, Any]:
        total = max(student_after_teaching, 1e-9)
        required = max(teacher_assisted - baseline_without_teacher, 0.0)
        return {
            "teacher_gain_required": required,
            "total_capability": total,
            "teacher_dependency": required / total,
            "unseen_transfer": unseen_transfer,
            "retention": retention,
            "deletion_forbidden": True,
            "retirement_allowed": False,
        }
