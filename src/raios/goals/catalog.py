"""Named Goal entity over the existing TASKS ledger.

Not a second task system, kernel, or program number. Programs[] and GOAL-typed
tasks are the Goal records. CURRENT-STATE.current_goal is a projection stamp.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "raios.goal.v1"


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def load_goals(repo: Path) -> dict[str, Any]:
    repo = Path(repo).resolve()
    tasks_doc = _load(repo / ".ai-os" / "state" / "TASKS.json", {})
    programs = list(tasks_doc.get("programs") or [])
    active = str(tasks_doc.get("active_program_id") or "")
    goals: list[dict[str, Any]] = []
    for program in programs:
        goal_id = str(program.get("id") or program.get("program_id") or "").strip()
        if not goal_id:
            continue
        goals.append({
            "schema": SCHEMA,
            "goal_id": goal_id,
            "kind": "PROGRAM",
            "title": str(program.get("title") or program.get("name") or goal_id),
            "status": str(program.get("status") or "ACTIVE"),
            "active": goal_id == active,
            "horizon_start": program.get("horizon_start"),
            "horizon_end": program.get("horizon_end"),
            "source": "TASKS.json#programs",
            "ledger": "ONE_CANONICAL_TASK_LEDGER",
        })
    for task in tasks_doc.get("tasks") or []:
        named = (
            str(task.get("entity") or "").upper() == "GOAL"
            or bool(task.get("is_goal"))
            or str(task.get("board_visibility") or "").upper() == "REQUIRED"
        )
        if not named:
            continue
        goal_id = str(task.get("id") or "").strip()
        if not goal_id:
            continue
        goals.append({
            "schema": SCHEMA,
            "goal_id": goal_id,
            "kind": "TASK_GOAL",
            "title": str(task.get("title") or goal_id),
            "status": str(task.get("status") or "UNKNOWN"),
            "active": str(task.get("status") or "").upper() in {"IN_PROGRESS", "READY", "BLOCKED"},
            "decision": task.get("decision"),
            "source": "TASKS.json#tasks",
            "ledger": "ONE_CANONICAL_TASK_LEDGER",
        })
    return {
        "schema": "raios.goal-catalog.v1",
        "active_program_id": active or None,
        "count": len(goals),
        "goals": goals,
        "second_goal_ledger": False,
        "kernel": False,
    }


def require_named_goal(catalog: dict[str, Any], goal_id: str) -> dict[str, Any]:
    row = next((g for g in catalog.get("goals") or [] if g.get("goal_id") == goal_id), None)
    if not row:
        raise ValueError("NAMED_GOAL_MISSING::" + goal_id)
    return row
