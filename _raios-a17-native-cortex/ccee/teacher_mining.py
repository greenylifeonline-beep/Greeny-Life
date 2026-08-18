"""Teacher strategy mining. Outputs are never memorized as canonical skill."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import TEMPORARY_TEACHERS, FailClosed, deterministic_id, native_root, utc_now
from .event_bus import EventBus
from .ledger import Ledger

PATTERNS = (
    "decomposition",
    "debugging",
    "verification",
    "tool_order",
    "coding_heuristic",
    "uncertainty_handling",
    "failure_recovery",
    "repository_reasoning",
    "negative_control",
    "stopping_rule",
)


class TeacherMining:
    def __init__(self, ledger: Ledger, bus: EventBus, repo_root: Path | None = None) -> None:
        self.ledger = ledger
        self.bus = bus
        self.repo_root = repo_root
        self.harvest = native_root(repo_root) / "experience" / "raw" / "teacher-harvest"

    def corpus_status(self) -> dict[str, Any]:
        if not self.harvest.exists():
            return {"status": "MISSING", "teachers": list(TEMPORARY_TEACHERS), "observations": 0, "invented": False}
        files = list(self.harvest.rglob("*.json"))
        return {"status": "FOUND", "teachers": list(TEMPORARY_TEACHERS), "observations": len(files), "invented": False}

    def extract_from_text(self, teacher: str, text: str) -> list[dict[str, Any]]:
        if teacher not in TEMPORARY_TEACHERS:
            raise FailClosed(f"UNKNOWN_TEACHER:{teacher}")
        found = []
        blob = text.lower()
        mapping = {
            "decomposition": ("step", "break", "first"),
            "debugging": ("trace", "stack", "repro"),
            "verification": ("hash", "assert", "verify"),
            "tool_order": ("then", "before", "after"),
            "coding_heuristic": ("parse", "patch", "retest"),
            "uncertainty_handling": ("unknown", "uncertain", "maybe"),
            "failure_recovery": ("retry", "backoff", "fail closed"),
            "repository_reasoning": ("git", "worktree", "commit"),
            "negative_control": ("must not", "forbidden", "false pass"),
            "stopping_rule": ("stop", "enough", "exit"),
        }
        for kind, needles in mapping.items():
            if any(n in blob for n in needles):
                rec = {
                    "strategy_id": deterministic_id("strat", teacher, kind, text[:40]),
                    "teacher": teacher,
                    "kind": "TeacherStrategy",
                    "pattern": kind,
                    "source_excerpt": text[:180],
                    "canonical": False,
                    "memorized_output": False,
                    "student_must_test_without_teacher": True,
                    "created_at": utc_now(),
                }
                self.ledger.put("strategies", "strategy_id", rec["strategy_id"], rec, extra={"teacher": teacher})
                self.bus.emit("TEACHER_OBSERVATION", "teacher_mining", rec)
                found.append(rec)
        return found

    def load_observations(self) -> list[dict[str, Any]]:
        status = self.corpus_status()
        if status["status"] != "FOUND":
            return []
        out = []
        for path in sorted(self.harvest.rglob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            teacher = data.get("model") or data.get("teacher") or "unknown"
            text = str(data.get("raw_text") or data.get("output") or "")
            if teacher in TEMPORARY_TEACHERS and text:
                out.extend(self.extract_from_text(teacher, text))
        return out
