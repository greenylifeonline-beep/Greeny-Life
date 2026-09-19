"""Canonical NOW slice over TASKS.json. Not a second ledger. NOW.md is not authority."""
from __future__ import annotations

from typing import Any

PRIO = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _visible(task: dict[str, Any]) -> bool:
    return bool(
        task.get("visible_on_command_center")
        or str(task.get("board_visibility") or "").upper() == "REQUIRED"
        or str(task.get("dispatch_status") or "").upper() == "SYSTEM_FIRST_ACTIVE"
        or str(task.get("entity") or "").upper() == "GOAL"
    )


def now_tasks(tasks: list[dict[str, Any]], *, limit: int = 48, next_limit: int = 8) -> list[dict[str, Any]]:
    live: list[dict[str, Any]] = []
    queued: list[dict[str, Any]] = []
    for task in tasks:
        status = str(task.get("status") or "UNKNOWN").upper()
        if status in {"DONE", "CANCELLED", "SUPERSEDED", "ARCHIVED"} and not _visible(task):
            continue
        if status not in {"IN_PROGRESS", "BLOCKED", "READY"} and not _visible(task):
            continue
        row = {
            "id": task.get("id"),
            "title": task.get("title"),
            "status": status,
            "claimed_by": task.get("claimed_by"),
            "assigned_to": task.get("assigned_to"),
            "owner": task.get("assigned_to") or task.get("claimed_by"),
            "blocker": task.get("blocker"),
            "next_step": task.get("next_step"),
            "priority": task.get("scheduler_priority"),
            "dispatch_status": task.get("dispatch_status"),
            "entity": task.get("entity"),
            "visible": _visible(task),
            "allowed_agents": list(task.get("allowed_agents") or []),
        }
        if status in {"IN_PROGRESS", "BLOCKED"} or _visible(task):
            live.append(row)
        elif status == "READY" and str(task.get("scheduler_priority") or "").upper() in {"CRITICAL", "HIGH"}:
            queued.append(row)
    key = lambda r: (
        0 if r["status"] == "IN_PROGRESS" else 1 if r["status"] == "BLOCKED" else 2,
        PRIO.get(str(r.get("priority") or "").upper(), 9),
        0 if r.get("visible") else 1,
        str(r.get("id") or ""),
    )
    live.sort(key=key)
    queued.sort(key=key)
    return (live + queued[:next_limit])[:limit]


def now_from_projected(projected: list[dict[str, Any]], source_tasks: list[dict[str, Any]], *, limit: int = 48) -> list[dict[str, Any]]:
    wanted = {row.get("id"): i for i, row in enumerate(now_tasks(source_tasks, limit=limit))}
    raw = {t.get("id"): t for t in source_tasks}
    out: list[dict[str, Any]] = []
    for row in projected:
        if row.get("id") not in wanted:
            continue
        task = raw.get(row.get("id")) or {}
        item = dict(row)
        item["priority"] = task.get("scheduler_priority")
        item["entity"] = task.get("entity")
        item["visible"] = _visible(task)
        out.append(item)
    out.sort(key=lambda r: wanted.get(r.get("id"), 999))
    return out


def render_md(doc: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    program = str(doc.get("active_program_id") or "")
    lines = [
        "# NOW — canonical task ledger",
        "",
        "Authority: `.ai-os/state/TASKS.json`. `.ai-os/board/NOW.md` is not the work board.",
        f"Program: `{program}`",
        "",
        "| status | id | owner | blocker |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        blocker = str(row.get("blocker") or "—").replace("|", "/")[:80]
        owner = str(row.get("owner") or row.get("claimed_by") or "—")
        lines.append(f"| {row.get('status')} | `{row.get('id')}` | {owner} | {blocker} |")
    lines.extend(["", "C6 live-bind remains required before P0 mutation. Do not fake DONE.", ""])
    return "\n".join(lines)
