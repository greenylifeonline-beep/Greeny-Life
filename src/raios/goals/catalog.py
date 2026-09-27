"""Named Goal entity over the existing TASKS ledger.

Not a second task system, kernel, or program number. Programs[] and GOAL-typed
tasks are the Goal records. CURRENT-STATE.current_goal is a projection stamp.
Official P00–P12 come from OFFICIAL-EXECUTION-ORDER.json (architecture overlay),
not a new program registry.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from raios.command_center.board_now import load_tasks_document, task_lifecycle

SCHEMA = "raios.goal.v1"
OFFICIAL_ORDER_REL = (
    ".ai-os/reports/implementation-program/"
    "RAIOS-MASTER-IMPLEMENTATION-PROGRAM-001/OFFICIAL-EXECUTION-ORDER.json"
)
WAVE_PACKET_PROGRAM_LABEL = "PROGRAM-03-UCF"
MAX_PROGRAM_TASK_IDS = 48


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def _task_program_id(task: dict[str, Any]) -> str:
    return str(task.get("program_id") or task.get("program") or "").strip()


def _task_project_id(task: dict[str, Any]) -> str:
    return str(task.get("project_id") or task.get("project") or "").strip()


def _current_phase(program: dict[str, Any]) -> Any:
    if program.get("current_phase"):
        return program.get("current_phase")
    if program.get("phase"):
        return program.get("phase")
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    for row in program.get("monthly_milestones") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("month") or "") == month:
            return row.get("milestone") or row.get("month")
    milestones = [row for row in (program.get("monthly_milestones") or []) if isinstance(row, dict)]
    if milestones:
        return milestones[0].get("milestone") or milestones[0].get("month")
    return "UNKNOWN"


def _counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    active = blocked = review = promo = 0
    for task in rows:
        status = str(task.get("status") or "").upper()
        dispatch = str(task.get("dispatch_status") or "").upper()
        review_state = str(task.get("review_state") or "").upper()
        promo_state = str(task.get("promotion_state") or "").upper()
        if status in {"IN_PROGRESS", "READY"}:
            active += 1
        if status == "BLOCKED":
            blocked += 1
        if "REVIEW" in dispatch or review_state in {"READY_FOR_REVIEW", "REVIEW_REQUIRED"}:
            review += 1
        if "PROMOTION" in dispatch or promo_state in {"READY_FOR_PROMOTION"}:
            promo += 1
    return {
        "ACTIVE_TASKS": active,
        "BLOCKED_TASKS": blocked,
        "READY_FOR_REVIEW": review,
        "READY_FOR_PROMOTION": promo,
    }


def _latest_field(rows: list[dict[str, Any]], key: str) -> Any:
    dated: list[tuple[str, Any]] = []
    for task in rows:
        value = task.get(key)
        if value in (None, "", []):
            continue
        dated.append((str(task.get("updated_at") or task.get("completed_at") or ""), value))
    if not dated:
        return None
    dated.sort(key=lambda item: item[0], reverse=True)
    return dated[0][1]


def program_task_map(tasks_doc: dict[str, Any], repo: Path | None = None) -> dict[str, Any]:
    programs = list(tasks_doc.get("programs") or [])
    tasks = [t for t in (tasks_doc.get("tasks") or []) if isinstance(t, dict)]
    active = str(tasks_doc.get("active_program_id") or "")
    by_program: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        pid = _task_program_id(task) or "_UNSCOPED"
        by_program.setdefault(pid, []).append(task)

    ledger: list[dict[str, Any]] = []
    for program in programs:
        if not isinstance(program, dict):
            continue
        pid = str(program.get("id") or program.get("program_id") or "").strip()
        if not pid:
            continue
        rows = by_program.get(pid) or []
        projects: dict[str, dict[str, Any]] = {}
        for task in rows:
            proj = _task_project_id(task) or "UNSCOPED"
            bucket = projects.setdefault(proj, {
                "project_id": proj,
                "project_name": task.get("project_name") or (None if proj == "UNSCOPED" else proj),
                "source": "TASKS.json#tasks.project_id" if _task_project_id(task) else "UNSCOPED",
                "task_ids": [],
            })
            if len(bucket["task_ids"]) < MAX_PROGRAM_TASK_IDS:
                bucket["task_ids"].append(task.get("id"))
        counts = _counts(rows)
        latest_evidence = _latest_field(rows, "evidence")
        if latest_evidence is None and program.get("baseline_evidence"):
            latest_evidence = "TASKS.json#programs.baseline_evidence"
        ledger.append({
            "PROGRAM_ID": pid,
            "PROGRAM_NAME": str(program.get("title") or program.get("name") or program.get("mission") or pid)[:240],
            "AUTHORITY": program.get("authorized_by") or program.get("authority") or "UNKNOWN",
            "STATUS": str(program.get("status") or "ACTIVE"),
            "PRIORITY": program.get("priority") or program.get("scheduler_priority") or "UNKNOWN",
            "CURRENT_PHASE": _current_phase(program),
            "PROJECTS": list(projects.values()),
            "ACTIVE_TASKS": counts["ACTIVE_TASKS"],
            "BLOCKED_TASKS": counts["BLOCKED_TASKS"],
            "READY_FOR_REVIEW": counts["READY_FOR_REVIEW"],
            "READY_FOR_PROMOTION": counts["READY_FOR_PROMOTION"],
            "LATEST_EVIDENCE": latest_evidence,
            "LATEST_DECISION": program.get("decision") or _latest_field(rows, "decision"),
            "active": pid == active,
            "source": "TASKS.json#programs",
            "second_program_registry": False,
        })

    architecture: list[dict[str, Any]] = []
    official = {}
    if repo is not None:
        official = _load(Path(repo) / OFFICIAL_ORDER_REL, {})
    for row in official.get("programs") or []:
        if not isinstance(row, dict):
            continue
        architecture.append({
            "PROGRAM_ID": row.get("id"),
            "PROGRAM_NAME": row.get("name") or row.get("Purpose") or row.get("purpose"),
            "AUTHORITY": official.get("authority") or "C1",
            "STATUS": official.get("IMPLEMENTATION") or official.get("STATUS") or "UNKNOWN",
            "PRIORITY": "UNKNOWN",
            "CURRENT_PHASE": "PLANNING_ONLY" if row.get("planning_only") is True or official.get("do_not_implement") is True else "UNKNOWN",
            "PROJECTS": [],
            "ACTIVE_TASKS": None,
            "BLOCKED_TASKS": None,
            "READY_FOR_REVIEW": None,
            "READY_FOR_PROMOTION": None,
            "LATEST_EVIDENCE": None,
            "LATEST_DECISION": official.get("decision"),
            "constitutional": row.get("constitutional") is True,
            "source": "OFFICIAL-EXECUTION-ORDER.json",
            "implementation_started": official.get("IMPLEMENTATION") not in {None, "NOT_STARTED"},
            "do_not_implement": official.get("do_not_implement") is True,
        })

    official_p03 = next((p for p in architecture if p.get("PROGRAM_ID") == "P03"), None)
    official_p12 = next((p for p in architecture if p.get("PROGRAM_ID") == "P12"), None)
    official_p00 = next((p for p in architecture if p.get("PROGRAM_ID") == "P00"), None)
    return {
        "schema": "raios.program-task-map.v1",
        "active_program_id": active or None,
        "ledger_programs": ledger,
        "architecture_programs": architecture,
        "second_program_registry": False,
        "constitution_redesigned": False,
        "wave_packet_program_label": WAVE_PACKET_PROGRAM_LABEL,
        "official_p00": official_p00,
        "official_p03_name": (official_p03 or {}).get("PROGRAM_NAME"),
        "official_communication_fabric": official_p12,
        "program_label_class": "CONFLICTING" if (official_p03 or {}).get("PROGRAM_NAME") and (official_p03 or {}).get("PROGRAM_NAME") != "Unified Communication Fabric" else "DIRECT",
        "law": [
            "ONE_CANONICAL_TASK_LEDGER",
            "OFFICIAL_ORDER_NE_TASK_LEDGER",
            "P03_OFFICIAL_IS_PROVIDER_FABRIC",
            "UCF_OFFICIAL_IS_P12_COMMUNICATION_FABRIC",
            "P00_FOUNDATION_NOT_REDESIGNED",
            "TASK_STATES_NOT_COLLAPSED_TO_DONE",
        ],
    }


def load_goals(repo: Path) -> dict[str, Any]:
    repo = Path(repo).resolve()
    tasks_doc = load_tasks_document(repo / ".ai-os" / "state" / "TASKS.json", {})
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
            "lifecycle": task_lifecycle(task),
        })
    return {
        "schema": "raios.goal-catalog.v1",
        "active_program_id": active or None,
        "count": len(goals),
        "goals": goals,
        "program_operations": program_task_map(tasks_doc, repo),
        "second_goal_ledger": False,
        "second_program_registry": False,
        "kernel": False,
    }


def require_named_goal(catalog: dict[str, Any], goal_id: str) -> dict[str, Any]:
    row = next((g for g in catalog.get("goals") or [] if g.get("goal_id") == goal_id), None)
    if not row:
        raise ValueError("NAMED_GOAL_MISSING::" + goal_id)
    return row
