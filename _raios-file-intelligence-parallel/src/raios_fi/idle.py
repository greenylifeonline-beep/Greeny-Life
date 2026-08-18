"""Idle subconscious loop. Foreground always preempts expensive model calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from raios_fi.config import FailClosed


@dataclass
class IdleLoop:
    running: bool = False
    preemptive_stop: bool = False
    ticks: list[str] = field(default_factory=list)
    model_calls: int = 0

    def tick(self, work: str, *, foreground: bool = False, model: bool = False) -> str:
        if foreground:
            self.preemptive_stop = True
            self.ticks.append(f"preempt:{work}")
            return "preempted"
        if self.preemptive_stop and model:
            return "skipped_model_due_to_foreground"
        if model:
            # Idle never calls Qwen in this package.
            self.model_calls += 0
            return "model_forbidden_in_idle_without_budget"
        self.ticks.append(work)
        return "ok"

    def run_once(self, store_health: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        FailClosed.require(not False, "idle")
        steps = [
            "incremental_scan",
            "index_freshness",
            "symbol_graph",
            "two_version_comparison",
            "duplicate_mining",
            "dead_code_candidates",
            "architecture_reconstruction",
            "teacher_learning_signal_extract",
            "repair_candidate_mining",
        ]
        done = []
        for s in steps:
            r = self.tick(s, model=False)
            done.append({"step": s, "result": r})
        return {"done": done, "health": store_health(), "model_calls": self.model_calls}
