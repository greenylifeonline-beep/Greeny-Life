from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
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
UNAVAILABLE_EXECUTOR_STATES = {
    "UNAVAILABLE","DISABLED","BLOCKED","NOT_BOUND","NO_EXECUTOR",
    "PRODUCT_GATE_DISABLED","FEATURE_GATE_DISABLED",
}


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


def _substantive_checkpoint(task: dict[str, Any]) -> tuple[bool, datetime | None, list[str]]:
    checkpoint = task.get("resume_checkpoint") or {}
    reasons: list[str] = []
    if checkpoint.get("completed_steps"):
        reasons.append("completed_steps")
    if checkpoint.get("changed_files"):
        reasons.append("changed_files")
    if checkpoint.get("validation"):
        reasons.append("validation")
    if checkpoint.get("evidence_refs"):
        reasons.append("evidence_refs")
    stamp = _parse_time(task.get("checkpoint_updated_at") or checkpoint.get("created_at"))
    return bool(reasons), stamp, reasons


def task_work_proof(task: dict[str, Any]) -> dict[str, Any]:
    accepted = _parse_time(task.get("accepted_at"))
    started = _parse_time(task.get("started_at"))
    updated = _parse_time(task.get("updated_at"))
    checkpoint_ok, checkpoint_at, checkpoint_reasons = _substantive_checkpoint(task)
    reasons: list[str] = []
    proof_at: datetime | None = None

    explicit = task.get("execution_proof") or task.get("work_proof")
    if isinstance(explicit, dict) and explicit.get("verified") is True:
        explicit_at = _parse_time(
            explicit.get("verified_at") or explicit.get("at") or task.get("work_proof_at")
        )
        if accepted is None or (explicit_at is not None and explicit_at >= accepted):
            reasons.append("verified_execution_proof")
            proof_at = explicit_at

    for key in ("work_proof_at", "last_progress_at", "execution_proven_at"):
        stamp = _parse_time(task.get(key))
        if stamp is not None and (accepted is None or stamp >= accepted):
            reasons.append(key)
            proof_at = max(filter(None, [proof_at, stamp]), default=stamp)

    if checkpoint_ok and checkpoint_at is not None and (
        accepted is None or checkpoint_at >= accepted
    ):
        reasons.extend(f"checkpoint:{x}" for x in checkpoint_reasons)
        proof_at = max(filter(None, [proof_at, checkpoint_at]), default=checkpoint_at)

    if accepted is None and started is not None and updated is not None and updated > started:
        if task.get("evidence"):
            reasons.append("task_evidence_after_start")
        if task.get("report_summary"):
            reasons.append("report_summary_after_start")
        if task.get("validation"):
            reasons.append("validation_after_start")
        if reasons:
            proof_at = max(filter(None, [proof_at, updated]), default=updated)

    return {
        "proven": bool(reasons),
        "proof_at": proof_at.isoformat() if proof_at is not None else None,
        "reasons": list(dict.fromkeys(reasons)),
        "accepted_at": task.get("accepted_at"),
        "checkpoint_updated_at": task.get("checkpoint_updated_at"),
    }


def task_truth_state(task: dict[str, Any], done_ids: set[str] | None = None,
                     *, now: datetime | None = None) -> str:
    status = str(task.get("status") or "UNKNOWN").upper()
    done_ids = done_ids or set()
    now = now or _utc_now()
    if status == "DONE":
        return "DONE"
    if status in {"SUPERSEDED", "CANCELLED", "ARCHIVED"}:
        return "SUPERSEDED_OR_CANCELLED"
    if status == "BLOCKED":
        return "BLOCKED" if task_claim_is_current(task) else "STALE_CLAIM_REQUIRES_RECONCILIATION"
    dispatch = str(task.get("dispatch_status") or "").upper()
    if dispatch == "PENDING_ACCEPTANCE":
        return "PENDING_ACCEPTANCE" if task_claim_is_current(task) else "STALE_CLAIM_REQUIRES_RECONCILIATION"
    if status == "IN_PROGRESS":
        if not task_claim_is_current(task):
            return "STALE_CLAIM_REQUIRES_RECONCILIATION"
        return "ACTIVE_VERIFIED" if task_work_proof(task)["proven"] else "ACCEPTED_AWAITING_WORK_PROOF"
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
        "SUPERSEDED_OR_CANCELLED": [],
        "PENDING_ACCEPTANCE": [],
        "ACCEPTED_AWAITING_WORK_PROOF": [],
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
        work_proof = task_work_proof(task)
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
            "superseded_by": task.get("superseded_by"),
            "closure_reason": task.get("closure_reason"),
            "acceptance_fingerprint": task.get("acceptance_fingerprint"),
            "first_work_proof_deadline": task.get("first_work_proof_deadline"),
            "executor_backend": task.get("executor_backend"),
            "executor_backends": task.get("executor_backends"),
            "work_proof_state": "PROVEN" if work_proof["proven"] else "UNPROVEN",
            "work_proof_at": work_proof["proof_at"],
            "work_proof_reasons": work_proof["reasons"],
            "executor_proof_state": (
                "PROVEN"
                if isinstance(task.get("executor_proof"), dict)
                and task["executor_proof"].get("verified") is True
                else "UNPROVEN"
            ),
            "executor_id": (
                (task.get("executor_proof") or {}).get("executor_id")
                if isinstance(task.get("executor_proof"), dict)
                else None
            ),
        }
        buckets.setdefault(truth, []).append(row)
    required = [
        row
        for key, rows in buckets.items()
        if key not in {"DONE", "SUPERSEDED_OR_CANCELLED"}
        for row in rows
    ]
    actionable = (
        buckets["PENDING_ACCEPTANCE"] +
        buckets["ACCEPTED_AWAITING_WORK_PROOF"] +
        buckets["ACTIVE_VERIFIED"] + buckets["REQUIRED_NEXT"] +
        buckets["WAITING_DEPENDENCIES"] + buckets["BLOCKED"] +
        buckets["STALE_CLAIM_REQUIRES_RECONCILIATION"]
    )
    return {
        "schema": "raios.work-lifecycle.v3",
        "counts": {key: len(rows) for key, rows in buckets.items()},
        "actionable_backlog_count": len(actionable),
        "buckets": buckets,
        "required_backlog_count": len(required),
        "required_backlog": required,
        "complete": len(required) == 0,
    }


def destructive_task_requested(task: dict[str, Any]) -> bool:
    if "destructive_action_requested" in task:
        return task.get("destructive_action_requested") is True
    if task.get("irreversible_change") is True:
        return True
    text = " ".join(str(task.get(key) or "") for key in (
        "id", "title", "objective", "validation", "next_step",
        "operation", "action", "change_type",
    )).lower()
    # Audit/retention wording must not be mistaken for a destructive request.
    text = re.sub(
        r"\b(no|never|without|forbid(?:den)?|prohibit(?:ed)?)\s+"
        r"(delete|deletion|remove|removal|retire|retirement|prune|destroy|purge)\b",
        " retained_action ",
        text,
    )
    patterns = (
        r"\bdelete\b", r"\bdeletion\b", r"\bremove\b", r"\bremoval\b",
        r"\bretire\b", r"\bretirement\b", r"\bprune\b",
        r"\bdestroy\b", r"\bpurge\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def global_legacy_delete_gate_satisfied(foundation: dict[str, Any] | None) -> bool:
    facts = (foundation or {}).get("facts") or {}
    unresolved = facts.get("LEGACY_UNIQUE_VALUE_UNRESOLVED")
    return bool(
        facts.get("DEEP_LEGACY_FORENSIC_AUDIT_PASS") is True
        and facts.get("LEGACY_DELETE_ALLOWED") is True
        and facts.get("SAFE_TO_REMOVE_SOURCE") is True
        and unresolved in (0, "0")
    )


def legacy_delete_gate_satisfied(task: dict[str, Any]) -> bool:
    if not destructive_task_requested(task):
        return True
    gate = task.get("deep_legacy_forensic_gate") or {}
    required_true = (
        "authorized_surface_census_complete",
        "hash_and_lineage_complete",
        "semantic_capability_extraction_complete",
        "data_schema_knowledge_extraction_complete",
        "current_vs_legacy_coverage_complete",
        "unique_value_extracted_merged_migrated_or_retained",
        "behavior_equivalence_or_superior_replacement_proven",
        "provenance_preserved",
        "recovery_or_rollback_proven",
        "safe_to_remove_source",
    )
    if str(gate.get("status") or "").upper() != "PASS":
        return False
    if any(gate.get(key) is not True for key in required_true):
        return False
    unresolved = gate.get("unknown_unclassified_unresolved_unique_value")
    if unresolved not in (0, "0"):
        return False
    exact = gate.get("exact_redundancy") is True
    if exact:
        return gate.get("standing_c1_duplicate_authority") is True
    return gate.get("c1_specific_deletion_approval") is True


def founder_decision_required(task: dict[str, Any]) -> bool:
    explicit = task.get("requires_c1_decision") is True or task.get("requires_founder_decision") is True
    authority = str(task.get("decision_authority") or task.get("approval_authority") or "").upper()
    promotion = task.get("canonical_promotion_requested") is True or task.get("irreversible_change") is True
    gate = task.get("deep_legacy_forensic_gate") or {}
    non_exact_destructive = destructive_task_requested(task) and gate.get("exact_redundancy") is not True
    return explicit or authority in {"C1", "FOUNDER", "OWNER"} or promotion or non_exact_destructive


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
        "pending_acceptance": lifecycle["buckets"]["PENDING_ACCEPTANCE"],
        "accepted_awaiting_work_proof": lifecycle["buckets"]["ACCEPTED_AWAITING_WORK_PROOF"],
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


def executor_backend_for_seat(task: dict[str, Any], seat: str) -> dict[str, Any] | None:
    backends = task.get("executor_backends")
    if not isinstance(backends, dict):
        return None
    backend = backends.get(str(seat or "").upper())
    return backend if isinstance(backend, dict) else None


def executor_backend_allows_seat(task: dict[str, Any], seat: str) -> bool:
    backend = executor_backend_for_seat(task, seat)
    if not backend or backend.get("verified") is not True:
        return True
    return str(backend.get("state") or "").upper() not in UNAVAILABLE_EXECUTOR_STATES


def _task_allowed_for_route(task: dict[str, Any], row: dict[str, Any]) -> bool:
    allowed = {str(x).upper() for x in (task.get("allowed_agents") or []) if str(x).strip()}
    aliases = {str(row.get("seat") or "").upper(), str(row.get("actor_id") or "").upper()}
    aliases.update(str(x).upper() for x in (row.get("aliases") or []))
    aliases.discard("")
    prefixes = [str(x).upper() for x in (row.get("alias_prefixes") or []) if str(x).strip()]
    allowed_ok = (
        not allowed
        or bool(allowed & aliases)
        or any(alias.startswith(prefix) for alias in allowed for prefix in prefixes)
    )
    if not allowed_ok:
        return False
    required = {
        str(x).upper()
        for x in (task.get("required_capabilities") or [])
        if str(x).strip()
    }
    if required:
        available = {
            str(x).upper()
            for x in (row.get("capabilities") or [])
            if str(x).strip()
        }
        if not required.issubset(available):
            return False
    return executor_backend_allows_seat(task, str(row.get("seat") or ""))


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
        legacy_delete_ok = legacy_delete_gate_satisfied(task)
        if not legacy_delete_ok:
            blocker = "DEEP_LEGACY_FORENSIC_AUDIT_REQUIRED"
        elif not founder_ok:
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
            "destructive_task_requested": destructive_task_requested(task),
            "deep_legacy_forensic_gate_satisfied": legacy_delete_ok,
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
            "executor_backends": task.get("executor_backends"),
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
