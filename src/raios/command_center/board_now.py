"""Canonical NOW slice over TASKS.json. Not a second ledger. NOW.md is not authority."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TASKS_GUARD = threading.Lock()
_TASKS_CACHE: dict[str, Any] = {"key": None, "mtime": None, "size": None, "doc": None}


def load_tasks_document(path: Path | str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load TASKS.json once per mtime. Not a second ledger. Failed parse keeps last good cache."""
    fallback = default if isinstance(default, dict) else {"tasks": []}
    target = Path(path)
    try:
        st = target.stat()
    except OSError:
        return dict(fallback)
    key = str(target.resolve())
    with _TASKS_GUARD:
        cached = _TASKS_CACHE
        if (
            cached.get("key") == key
            and cached.get("mtime") == st.st_mtime
            and cached.get("size") == st.st_size
            and isinstance(cached.get("doc"), dict)
        ):
            return cached["doc"]
        try:
            doc = json.loads(target.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            prior = cached.get("doc")
            return prior if isinstance(prior, dict) and cached.get("key") == key else dict(fallback)
        if not isinstance(doc, dict):
            return dict(fallback)
        _TASKS_CACHE.update({"key": key, "mtime": st.st_mtime, "size": st.st_size, "doc": doc})
        return doc

PRIO = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
INDEPENDENT_STATES = (
    "EDITING",
    "TESTED",
    "READY_FOR_REVIEW",
    "STAGED",
    "C1_APPROVED",
    "COMMITTED",
    "DEPLOYED",
    "CERTIFIED",
    "COMPLETE",
)


def task_lifecycle(task: dict[str, Any]) -> dict[str, Any]:
    ledger = str(task.get("status") or "UNKNOWN").upper()
    return {
        "ledger_status": ledger,
        "EDITING": task.get("editing_state") or task.get("working_tree_state") or "UNKNOWN",
        "TESTED": task.get("test_state") or "UNKNOWN",
        "READY_FOR_REVIEW": task.get("review_state") or "UNKNOWN",
        "STAGED": task.get("staged_state") or "UNKNOWN",
        "C1_APPROVED": task.get("approval_state") or "UNKNOWN",
        "COMMITTED": task.get("commit_state") or "UNKNOWN",
        "DEPLOYED": task.get("deployment_state") or "UNKNOWN",
        "CERTIFIED": task.get("certified_state") or "UNKNOWN",
        "COMPLETE": task.get("complete_state") or "UNKNOWN",
        "collapsed_to_done": False,
        "done_ne_complete": ledger == "DONE",
    }


def _visible(task: dict[str, Any]) -> bool:
    return bool(
        task.get("visible_on_command_center")
        or str(task.get("board_visibility") or "").upper() == "REQUIRED"
        or str(task.get("dispatch_status") or "").upper() == "SYSTEM_FIRST_ACTIVE"
        or str(task.get("entity") or "").upper() == "GOAL"
    )


OPEN_LEDGER = frozenset({"READY", "IN_PROGRESS", "BLOCKED"})


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def hanging_work(
    tasks: list[dict[str, Any]] | None,
    *,
    stale_after_hours: float = 24.0,
    limit: int = 64,
) -> dict[str, Any]:
    """Project open ledger rows so RAIOS can refuse silent unfinished work.

    Does not mutate TASKS.json. Does not fake DONE.
    """
    now = datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    stale: list[str] = []
    unclaimed_ready: list[str] = []
    in_progress: list[str] = []
    blocked: list[str] = []
    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        status = str(task.get("status") or "").upper()
        if status not in OPEN_LEDGER:
            continue
        tid = str(task.get("id") or "")
        claimed = task.get("claimed_by") or task.get("assigned_to")
        updated = task.get("updated_at") or task.get("checkpoint_updated_at") or task.get("started_at")
        stamp = _parse_ts(updated)
        if stamp is None:
            stale_flag = status == "IN_PROGRESS"
        else:
            stale_flag = (now - stamp).total_seconds() > stale_after_hours * 3600
        row = {
            "id": tid,
            "status": status,
            "claimed_by": claimed,
            "blocker": task.get("blocker") or task.get("return_reason"),
            "stale": stale_flag,
            "priority": task.get("scheduler_priority") or task.get("priority"),
        }
        items.append(row)
        if status == "IN_PROGRESS":
            in_progress.append(tid)
            if stale_flag:
                stale.append(tid)
        elif status == "BLOCKED":
            blocked.append(tid)
        elif status == "READY" and not claimed:
            unclaimed_ready.append(tid)
    return {
        "schema": "raios.hanging-work.v1",
        "observed_at": now.isoformat(),
        "open_count": len(items),
        "in_progress_count": len(in_progress),
        "blocked_count": len(blocked),
        "ready_unclaimed_count": len(unclaimed_ready),
        "stale_in_progress": stale[:limit],
        "must_complete_or_notify": True,
        "system_informed": True,
        "mutated_tasks_ledger": False,
        "law": "NO_HANGING_TASK_WITHOUT_SYSTEM_NOTICE",
        "items": items[:limit],
    }


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
            "program": task.get("program_id") or task.get("program"),
            "project": task.get("project_id") or task.get("project"),
            "authority": task.get("authority") or task.get("dispatch_authorized_by"),
            "worker": task.get("claimed_by") or task.get("assigned_to"),
            "reviewer": task.get("reviewer"),
            "claimed_by": task.get("claimed_by"),
            "assigned_to": task.get("assigned_to"),
            "owner": task.get("assigned_to") or task.get("claimed_by"),
            "dependency": list(task.get("dependencies") or [])[:12],
            "blocker": task.get("blocker"),
            "working_tree_state": task.get("working_tree_state") or task.get("editing_state") or "UNKNOWN",
            "test_state": task.get("test_state") or "UNKNOWN",
            "review_state": task.get("review_state") or "UNKNOWN",
            "approval_state": task.get("approval_state") or "UNKNOWN",
            "promotion_state": task.get("promotion_state") or "UNKNOWN",
            "deployment_state": task.get("deployment_state") or "UNKNOWN",
            "evidence": task.get("evidence"),
            "updated_at": task.get("updated_at") or task.get("completed_at") or task.get("blocked_at"),
            "lifecycle": task_lifecycle(task),
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
