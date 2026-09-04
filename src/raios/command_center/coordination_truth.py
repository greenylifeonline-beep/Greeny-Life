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


def _acceleration_allowed(task: dict[str, Any]) -> bool:
    return bool(
        task.get("hard_not_before") is not True
        and task.get("acceleration_allowed", True) is not False
    )


def _ahead_of_plan(task: dict[str, Any], *, now: datetime | None = None) -> bool:
    now = now or _utc_now()
    not_before = _parse_time(task.get("not_before"))
    return bool(not_before is not None and not_before > now)


def task_truth_state(task: dict[str, Any], done_ids: set[str] | None = None,
                     *, now: datetime | None = None) -> str:
    status = str(task.get("status") or "UNKNOWN").upper()
    done_ids = done_ids or set()
    now = now or _utc_now()
    if status == "DONE":
        return "DONE"
    if status == "BLOCKED":
        return "BLOCKED" if task_claim_is_current(task) else "STALE_CLAIM_REQUIRES_RECONCILIATION"
    if status == "IN_PROGRESS" or str(task.get("dispatch_status") or "").upper() == "PENDING_ACCEPTANCE":
        return "ACTIVE_VERIFIED" if task_claim_is_current(task) else "STALE_CLAIM_REQUIRES_RECONCILIATION"
    if status == "READY":
        if _ahead_of_plan(task, now=now) and not _acceleration_allowed(task):
            return "FUTURE_PLANNED"
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
        "FUTURE_PLANNED": [],
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
            "program_id": task.get("program_id"),
            "target_month": task.get("target_month"),
            "not_before": task.get("not_before"),
            "horizon_end": task.get("horizon_end"),
            "milestone": task.get("milestone"),
            "ahead_of_plan": _ahead_of_plan(task),
            "acceleration_allowed": _acceleration_allowed(task),
            "hard_not_before": task.get("hard_not_before") is True,
            "method_strategy": task.get("method_strategy"),
        }
        buckets.setdefault(truth, []).append(row)
    required = [row for key, rows in buckets.items() if key != "DONE" for row in rows]
    actionable = (
        buckets["ACTIVE_VERIFIED"] + buckets["REQUIRED_NEXT"] +
        buckets["WAITING_DEPENDENCIES"] + buckets["BLOCKED"] +
        buckets["STALE_CLAIM_REQUIRES_RECONCILIATION"]
    )
    return {
        "schema": "raios.work-lifecycle.v2",
        "counts": {key: len(rows) for key, rows in buckets.items()},
        "actionable_backlog_count": len(actionable),
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
        "future_planned": lifecycle["buckets"]["FUTURE_PLANNED"],
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


_PRIORITY_MAP = {
    "CRITICAL": 5,
    "URGENT": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "NORMAL": 1,
    "LOW": 0,
}


def _numeric_priority(task: dict[str, Any]) -> int:
    raw = task.get("scheduler_priority", task.get("priority", 0))
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw or "").strip().upper()
    if text in _PRIORITY_MAP:
        return _PRIORITY_MAP[text]
    try:
        return int(text)
    except ValueError:
        return 0


def dependency_impact(task_id: str, tasks: list[dict[str, Any]]) -> tuple[int, int]:
    reverse: dict[str, set[str]] = {}
    live_ids = {str(t.get("id")) for t in tasks if str(t.get("status") or "").upper() != "DONE"}
    for task in tasks:
        child = str(task.get("id") or "")
        if not child or child not in live_ids:
            continue
        for dep in (task.get("dependencies") or []):
            reverse.setdefault(str(dep), set()).add(child)
    direct = len(reverse.get(task_id, set()))
    seen: set[str] = set()
    stack = list(reverse.get(task_id, set()))
    while stack:
        child = stack.pop()
        if child in seen:
            continue
        seen.add(child)
        stack.extend(reverse.get(child, set()) - seen)
    return direct, len(seen)


def dispatch_priority_score(task: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any]:
    task_id = str(task.get("id") or "")
    direct, transitive = dependency_impact(task_id, tasks)
    explicit = _numeric_priority(task)
    ahead = _ahead_of_plan(task)
    acceleration = _acceleration_allowed(task)
    acceleration_bonus = 5000 if ahead and acceleration else 0
    compression_bonus = int(task.get("time_compression_priority") or 0) * 100
    score = (
        explicit * 100000
        + transitive * 1000
        + direct * 100
        + acceleration_bonus
        + compression_bonus
        + 10
    )
    return {
        "score": score,
        "explicit_priority": explicit,
        "direct_dependents": direct,
        "transitive_dependents": transitive,
        "critical_path": transitive > 0,
        "resumable_checkpoint": bool(task.get("resume_checkpoint")),
        "ahead_of_plan": ahead,
        "acceleration_allowed": acceleration,
        "acceleration_bonus": acceleration_bonus,
        "time_compression_priority": int(task.get("time_compression_priority") or 0),
    }


def _task_allowed_for_route(task: dict[str, Any], row: dict[str, Any]) -> bool:
    allowed = {str(x).upper() for x in (task.get("allowed_agents") or []) if str(x).strip()}
    if not allowed:
        return True
    aliases = {str(row.get("seat") or "").upper(), str(row.get("actor_id") or "").upper()}
    aliases.update(str(x).upper() for x in (row.get("aliases") or []))
    aliases.discard("")
    prefixes = [str(x).upper() for x in (row.get("alias_prefixes") or []) if str(x).strip()]
    if allowed & aliases:
        return True
    return any(alias.startswith(prefix) for alias in allowed for prefix in prefixes)


def _scope_overlap(left: str, right: str) -> bool:
    a = str(left or "").replace("\\", "/").rstrip("/*/")
    b = str(right or "").replace("\\", "/").rstrip("/*/")
    return bool(a and b and (a == b or a.startswith(b + "/") or b.startswith(a + "/")))


def build_dispatch_plan(tasks: list[dict[str, Any]], route_rows: list[dict[str, Any]],
                        active_scope_reservations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    done_ids = {str(t.get("id")) for t in tasks if str(t.get("status") or "").upper() == "DONE"}
    reservations = list(active_scope_reservations or [])
    queue = []
    for task in tasks:
        if str(task.get("status") or "").upper() != "READY":
            continue
        if _ahead_of_plan(task) and not _acceleration_allowed(task):
            continue
        deps = [str(x) for x in (task.get("dependencies") or []) if str(x)]
        if not all(dep in done_ids for dep in deps):
            continue
        rank = dispatch_priority_score(task, tasks)
        eligible = []
        ready = []
        available = []
        for row in route_rows:
            seat = str(row.get("seat") or "").upper()
            if not seat or seat == "C1" or not _task_allowed_for_route(task, row):
                continue
            eligible.append(seat)
            if row.get("coordination_available") is True or str(row.get("availability_claim") or "").upper() == "AVAILABLE":
                available.append(seat)
            if row.get("auto_routable") is True:
                ready.append(seat)
        scope_conflicts = []
        for reservation in reservations:
            for wanted in (task.get("scope") or []):
                if _scope_overlap(wanted, reservation.get("scope")):
                    scope_conflicts.append({
                        "lock_id": reservation.get("lock_id"),
                        "task_id": reservation.get("task_id"),
                        "actor": reservation.get("actor"),
                        "wanted_scope": wanted,
                        "active_scope": reservation.get("scope"),
                    })
        auto_authorized = (
            task.get("automatic_dispatch") is True
            and str(task.get("dispatch_authorized_by") or "").upper() == "C1"
        )
        founder_ok = founder_gate_satisfied(task)
        if not founder_ok:
            blocker = "FOUNDER_DECISION_REQUIRED"
        elif scope_conflicts:
            blocker = "ACTIVE_SCOPE_CONFLICT"
        elif not eligible:
            blocker = "NO_ELIGIBLE_COUNCIL_SEAT"
        elif not ready:
            blocker = "ELIGIBLE_SEAT_NOT_EXECUTION_READY"
        elif not auto_authorized:
            blocker = "AUTO_DISPATCH_NOT_AUTHORIZED"
        else:
            blocker = None
        queue.append({
            "task_id": task.get("id"),
            "title": task.get("title"),
            "score": rank["score"],
            "critical_path": rank["critical_path"],
            "direct_dependents": rank["direct_dependents"],
            "transitive_dependents": rank["transitive_dependents"],
            "explicit_priority": rank["explicit_priority"],
            "resumable_checkpoint": rank["resumable_checkpoint"],
            "eligible_seats": sorted(set(eligible)),
            "coordination_available_seats": sorted(set(available)),
            "execution_ready_seats": sorted(set(ready)),
            "automatic_dispatch_authorized": auto_authorized,
            "founder_gate_satisfied": founder_ok,
            "scope_conflicts": scope_conflicts,
            "blocker": blocker,
            "dispatchable_now": blocker is None,
            "scope": list(task.get("scope") or []),
            "dependencies": deps,
            "program_id": task.get("program_id"),
            "target_month": task.get("target_month"),
            "milestone": task.get("milestone"),
            "ahead_of_plan": rank["ahead_of_plan"],
            "acceleration_allowed": rank["acceleration_allowed"],
            "acceleration_bonus": rank["acceleration_bonus"],
            "method_strategy": task.get("method_strategy"),
            "goal_contract": task.get("goal_contract"),
        })
    queue.sort(key=lambda row: (-int(row["score"]), str(row["task_id"])))
    for index, row in enumerate(queue, 1):
        row["rank"] = index
    return {
        "schema": "raios.dispatch-plan.v1",
        "queue": queue,
        "dispatchable_now": [row for row in queue if row["dispatchable_now"]],
        "blocked_count": sum(1 for row in queue if not row["dispatchable_now"]),
        "ready_count": len(queue),
        "policy": "DEPENDENCY_IMPACT_THEN_EXPLICIT_PRIORITY_THEN_STABLE_TASK_ID",
    }
