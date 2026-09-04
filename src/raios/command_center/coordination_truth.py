from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

ACTIVE_STATUSES = {"IN_PROGRESS", "BLOCKED"}
CURRENT_DISPATCH_STATES = {
    "PENDING_ACCEPTANCE",
    "ACCEPTED",
    "CHECKPOINT_SAVED",
    "IN_PROGRESS_REPORTED",
    "BLOCKED_REPORTED",
    "SYSTEM_FIRST_ACTIVE",
}
RECENT_ACTIVITY_SECONDS = 1800


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def task_claim_is_current(task: dict[str, Any], *, now: datetime | None = None,
                          recent_seconds: int = RECENT_ACTIVITY_SECONDS) -> bool:
    status = str(task.get("status") or "").upper()
    dispatch = str(task.get("dispatch_status") or "").upper()
    if dispatch in CURRENT_DISPATCH_STATES:
        return status in ACTIVE_STATUSES or dispatch == "PENDING_ACCEPTANCE"
    if status not in ACTIVE_STATUSES:
        return False
    now = now or _utc_now()
    for key in ("checkpoint_updated_at", "accepted_at", "updated_at", "started_at", "dispatched_at"):
        stamp = _parse_time(task.get(key))
        if stamp is not None and timedelta(0) <= now - stamp <= timedelta(seconds=recent_seconds):
            return True
    return False


def build_alias_index(seat_map: dict[str, Any]) -> tuple[dict[str, str], list[tuple[str, str]], set[str]]:
    exact_candidates: dict[str, set[str]] = {}
    prefix_candidates: dict[str, set[str]] = {}
    for seat, spec in (seat_map.get("seats") or {}).items():
        canonical = str(seat).upper()
        values = {canonical}
        instance_role = str(spec.get("instance_role") or "").strip()
        if instance_role:
            values.add(instance_role.upper())
        values.update(str(x).upper() for x in (spec.get("aliases") or []) if str(x).strip())
        for value in values:
            exact_candidates.setdefault(value, set()).add(canonical)
        for prefix in (spec.get("alias_prefixes") or []):
            value = str(prefix).upper().strip()
            if value:
                prefix_candidates.setdefault(value, set()).add(canonical)
    ambiguous = {alias for alias, seats in exact_candidates.items() if len(seats) != 1}
    exact = {alias: next(iter(seats)) for alias, seats in exact_candidates.items() if len(seats) == 1}
    prefixes = [
        (prefix, next(iter(seats)))
        for prefix, seats in prefix_candidates.items()
        if len(seats) == 1
    ]
    prefixes.sort(key=lambda item: len(item[0]), reverse=True)
    return exact, prefixes, ambiguous


def canonical_seat(actor: Any, seat_map: dict[str, Any]) -> str | None:
    value = str(actor or "").upper().strip()
    if not value:
        return None
    exact, prefixes, ambiguous = build_alias_index(seat_map)
    if value in ambiguous:
        return None
    if value in exact:
        return exact[value]
    matched = {seat for prefix, seat in prefixes if value.startswith(prefix)}
    return next(iter(matched)) if len(matched) == 1 else None


def aliases_for_seat(seat: str, seat_map: dict[str, Any]) -> tuple[list[str], list[str]]:
    spec = (seat_map.get("seats") or {}).get(seat, {})
    aliases = {str(seat).upper()}
    instance_role = str(spec.get("instance_role") or "").strip()
    if instance_role:
        aliases.add(instance_role.upper())
    aliases.update(str(x).upper() for x in (spec.get("aliases") or []) if str(x).strip())
    prefixes = [str(x).upper() for x in (spec.get("alias_prefixes") or []) if str(x).strip()]
    return sorted(aliases), sorted(set(prefixes), key=len, reverse=True)


def task_truth_state(task: dict[str, Any], done_ids: set[str] | None = None) -> str:
    status = str(task.get("status") or "UNKNOWN").upper()
    done_ids = done_ids or set()
    if status == "DONE":
        return "DONE"
    if status == "BLOCKED":
        return "BLOCKED" if task_claim_is_current(task) else "STALE_CLAIM_REQUIRES_RECONCILIATION"
    if status == "IN_PROGRESS" or str(task.get("dispatch_status") or "").upper() == "PENDING_ACCEPTANCE":
        return "ACTIVE_VERIFIED" if task_claim_is_current(task) else "STALE_CLAIM_REQUIRES_RECONCILIATION"
    if status == "READY":
        deps = [str(x) for x in (task.get("dependencies") or []) if str(x)]
        return "REQUIRED_NEXT" if all(dep in done_ids for dep in deps) else "WAITING_DEPENDENCIES"
    return "UNCLASSIFIED_REQUIRED"


def build_work_lifecycle(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    done_ids = {str(t.get("id")) for t in tasks if str(t.get("status") or "").upper() == "DONE"}
    buckets: dict[str, list[dict[str, Any]]] = {
        "DONE": [],
        "ACTIVE_VERIFIED": [],
        "REQUIRED_NEXT": [],
        "WAITING_DEPENDENCIES": [],
        "BLOCKED": [],
        "STALE_CLAIM_REQUIRES_RECONCILIATION": [],
        "UNCLASSIFIED_REQUIRED": [],
    }
    for task in tasks:
        truth = task_truth_state(task, done_ids)
        row = {
            "id": task.get("id"),
            "title": task.get("title"),
            "truth_state": truth,
            "status": task.get("status"),
            "dispatch_status": task.get("dispatch_status"),
            "actor": task.get("claimed_by") or task.get("assigned_to"),
            "scope": list(task.get("scope") or []),
            "dependencies": list(task.get("dependencies") or []),
            "blocker": task.get("blocker"),
            "next_step": (task.get("resume_checkpoint") or {}).get("next_step"),
        }
        buckets.setdefault(truth, []).append(row)
    required = [row for key, rows in buckets.items() if key != "DONE" for row in rows]
    return {
        "schema": "raios.work-lifecycle.v1",
        "counts": {key: len(rows) for key, rows in buckets.items()},
        "buckets": buckets,
        "required_backlog_count": len(required),
        "required_backlog": required,
        "complete": len(required) == 0,
    }


def founder_decision_required(task: dict[str, Any]) -> bool:
    explicit = task.get("requires_c1_decision") is True or task.get("requires_founder_decision") is True
    authority = str(task.get("decision_authority") or task.get("approval_authority") or "").upper()
    promotion = task.get("canonical_promotion_requested") is True or task.get("irreversible_change") is True
    return explicit or authority in {"C1", "FOUNDER", "OWNER"} or promotion


def build_founder_brief(tasks: list[dict[str, Any]], *, founder_available: bool,
                        active_scope_reservations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    lifecycle = build_work_lifecycle(tasks)
    decisions = []
    for task in tasks:
        if not founder_decision_required(task):
            continue
        decisions.append({
            "task_id": task.get("id"),
            "title": task.get("title"),
            "question": task.get("founder_question") or task.get("decision_question") or task.get("blocker")
                        or "Founder/owner decision required before governed continuation.",
            "recommended_decision": task.get("recommended_decision"),
            "alternatives": list(task.get("decision_alternatives") or []),
            "evidence_refs": list(task.get("evidence_refs") or []),
            "risk": task.get("risk") or task.get("risk_class"),
            "status": "AWAITING_FOUNDER",
        })
    stale = lifecycle["buckets"]["STALE_CLAIM_REQUIRES_RECONCILIATION"]
    return {
        "schema": "raios.founder-brief.v1",
        "founder": "C1",
        "founder_available": founder_available,
        "consultation_mode": "LIVE_CONSULTATION" if founder_available else "PREPARE_AND_HOLD_GOVERNED_DECISIONS",
        "completed_count": lifecycle["counts"]["DONE"],
        "active_verified": lifecycle["buckets"]["ACTIVE_VERIFIED"],
        "must_do_next": lifecycle["buckets"]["REQUIRED_NEXT"],
        "waiting_dependencies": lifecycle["buckets"]["WAITING_DEPENDENCIES"],
        "blocked": lifecycle["buckets"]["BLOCKED"],
        "stale_claims_requiring_reconciliation": stale,
        "decisions_required": decisions,
        "decision_count": len(decisions),
        "prepared_for_founder_return": not founder_available,
        "offline_policy": {
            "continue": "AUTHORIZED_REVERSIBLE_NON_CONFLICTING_WORK",
            "prepare": "OPTIONS_EVIDENCE_RISK_RECOMMENDATION_AND_NEXT_STEPS",
            "hold": "C1_DECISIONS_CANONICAL_PROMOTION_IRREVERSIBLE_OR_EXPLICIT_FOUNDER_GATES",
        },
        "active_scope_reservation_count": len(active_scope_reservations or []),
    }


def founder_gate_satisfied(task: dict[str, Any]) -> bool:
    if not founder_decision_required(task):
        return True
    decision = str(task.get("founder_decision_status") or "").upper()
    actor = str(task.get("founder_decision_by") or "").upper()
    return decision == "APPROVED" and actor == "C1"
