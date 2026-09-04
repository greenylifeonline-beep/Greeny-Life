from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .coordination_truth import (
    build_dispatch_plan, build_founder_brief, build_work_lifecycle, task_claim_is_current,
)


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current(expiry: str | None) -> bool:
    if not expiry:
        return False
    try:
        return datetime.fromisoformat(str(expiry).replace("Z", "+00:00")) > datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


def _matches_actor(task: dict[str, Any], seat: str, actor_id: str | None,
                   aliases: list[str] | None = None,
                   alias_prefixes: list[str] | None = None) -> bool:
    values = {
        str(task.get("claimed_by") or "").upper(),
        str(task.get("assigned_to") or "").upper(),
    }
    values.discard("")
    candidates = {str(seat).upper()}
    if actor_id:
        candidates.add(str(actor_id).upper())
    candidates.update(str(x).upper() for x in (aliases or []))
    if values & candidates:
        return True
    return any(value.startswith(str(prefix).upper())
               for value in values for prefix in (alias_prefixes or []))


def _seat_for_actor(actor: str, rows: list[dict[str, Any]]) -> str | None:
    value = str(actor or "").upper().strip()
    if not value:
        return None
    exact: set[str] = set()
    prefix: set[str] = set()
    for row in rows:
        seat = str(row.get("seat") or "").upper()
        candidates = {seat, str(row.get("actor_id") or "").upper()}
        candidates.update(str(x).upper() for x in (row.get("aliases") or []))
        candidates.discard("")
        if value in candidates:
            exact.add(seat)
        if any(value.startswith(str(p).upper()) for p in (row.get("alias_prefixes") or [])):
            prefix.add(seat)
    if len(exact) == 1:
        return next(iter(exact))
    if not exact and len(prefix) == 1:
        return next(iter(prefix))
    return None


class ClientActivityView:
    def __init__(self, repo: Path, routes) -> None:
        self.repo = repo.resolve()
        self.routes = routes
        self.tasks_path = self.repo / ".ai-os" / "state" / "TASKS.json"
        self.locks_path = self.repo / ".ai-os" / "state" / "LOCKS.json"
        self.receipts = self.repo / ".ai-os" / "receipts" / "command-fabric"
        self.outbox = self.repo / ".ai-os" / "state" / "command-fabric" / "outbox"
        self.worker_registry = self.repo / ".ai-os" / "state" / "command-fabric" / "WORKER-REGISTRY.json"

    def _tasks(self) -> list[dict[str, Any]]:
        return list((_load(self.tasks_path, {"tasks": []}).get("tasks") or []))

    def _latest_actor_ack(self, seat: str) -> dict[str, Any] | None:
        rows: list[tuple[float, dict[str, Any]]] = []
        for path in self.receipts.glob(f"MSG-*.{seat}.actor.ack.receipt.json"):
            try:
                data = _load(path, {})
                rows.append((path.stat().st_mtime, data))
            except OSError:
                continue
        return max(rows, key=lambda item: item[0])[1] if rows else None

    def snapshot(self) -> dict[str, Any]:
        route_snapshot = self.routes.snapshot()
        tasks = self._tasks()
        active_locks = [x for x in (_load(self.locks_path, {"locks": []}).get("locks") or [])
                        if str(x.get("status") or "").upper() == "ACTIVE"]
        route_rows = list(route_snapshot.get("seats", []))
        clients = []
        for row in route_rows:
            seat = str(row.get("seat") or "")
            actor_id = row.get("actor_id")
            matched = [t for t in tasks if
                       (t.get("status") in ("IN_PROGRESS", "BLOCKED") or
                        t.get("dispatch_status") == "PENDING_ACCEPTANCE") and
                       _matches_actor(t, seat, actor_id, row.get("aliases"), row.get("alias_prefixes"))]
            verified_claims = [t for t in matched if row.get("auto_routable") is True and task_claim_is_current(t)]
            current = [t for t in verified_claims if t.get("status") in ("IN_PROGRESS", "BLOCKED")]
            pending = [t for t in verified_claims if t.get("dispatch_status") == "PENDING_ACCEPTANCE"]
            stale_claims = [t for t in matched if t not in verified_claims]
            last_ack = self._latest_actor_ack(seat)
            if row.get("auto_routable"):
                state = "ASSIGNED_PENDING_ACCEPTANCE" if pending else ("WORKING" if current else "IDLE")
            elif stale_claims:
                state = "STALE_OR_UNBOUND_CLAIM"
            else:
                state = "OFFLINE_OR_UNBOUND"
            presence_state = str(row.get("presence_state") or "UNKNOWN").upper()
            attested_available = (
                row.get("availability_claim_current") is True
                and str(row.get("availability_claim") or "").upper() == "AVAILABLE"
            )
            if row.get("auto_routable"):
                availability = "BUSY" if (current or pending) else "AVAILABLE"
                verified = True
                source = "RUNTIME_BOUND_CONSUMER"
                if pending:
                    work_phase = "ASSIGNED_PENDING_ACCEPTANCE"
                    required_action = "ACCEPT_ASSIGNED_TASK"
                    reason = "RAIOS_WORKER_ASSIGNED_TASK_AWAITING_EXPLICIT_ACCEPTANCE"
                elif current:
                    blocked = any(t.get("status") == "BLOCKED" for t in current)
                    work_phase = "BLOCKED_AWAITING_SYSTEM" if blocked else "EXECUTING"
                    required_action = ("WAIT_FOR_SYSTEM_RESOLUTION_OR_SUBMIT_CHECKPOINT" if blocked
                                       else "EXECUTE_ONLY_ASSIGNED_SCOPE_AND_SUBMIT_EVIDENCE")
                    reason = "BLOCKED_CANONICAL_TASK_STILL_RESERVED" if blocked else "ACTIVE_CANONICAL_TASK"
                else:
                    work_phase = "WAITING_FOR_ASSIGNMENT"
                    required_action = "WAIT_FOR_RAIOS_WORKER_DISPATCH"
                    reason = "SIGNED_PRESENT_IDLE_AND_ELIGIBLE"
                execution_ready = not (current or pending)
            elif attested_available:
                availability = "AVAILABLE"
                verified = True
                source = row.get("availability_source") or "AVAILABILITY_ATTESTATION"
                work_phase = "AVAILABLE_NOT_EXECUTION_READY"
                required_action = "SIGN_CHECK_IN_WHEN_ASSIGNED_WORK"
                reason = ("CURRENT_AVAILABILITY_SUPERSEDES_LEGACY_UNVERIFIED_CLAIMS"
                          if stale_claims else
                          (row.get("availability_reason") or "RECENT_VERIFIED_AVAILABILITY_ATTESTATION"))
                execution_ready = False
            elif presence_state == "ABSENT":
                availability = "OFFLINE"
                verified = row.get("presence_signature_valid") is True
                source = "SELF_SIGNED_PRESENCE" if verified else "UNVERIFIED_PRESENCE"
                if stale_claims:
                    work_phase = "STALE_TASK_CLAIM_REQUIRES_RECONCILIATION"
                    required_action = "SYSTEM_RETURN_OR_REASSIGN_FROM_CHECKPOINT"
                    reason = "SIGNED_OUT_BUT_TASK_REFERENCE_REMAINS"
                else:
                    work_phase = "SIGNED_OUT"
                    required_action = "SIGN_CHECK_IN_BEFORE_ANY_WORK"
                    reason = "MEMBER_EXPLICITLY_SIGNED_OUT"
                execution_ready = False
            else:
                availability = "UNKNOWN"
                verified = False
                discovery = str(row.get("discovery_state") or "UNKNOWN")
                source = "DISCOVERY_EVIDENCE" if discovery != "UNKNOWN" else "INSUFFICIENT_LIVE_EVIDENCE"
                if stale_claims:
                    work_phase = "STALE_TASK_CLAIM_REQUIRES_RECONCILIATION"
                    required_action = "SIGN_CHECK_IN_OR_SYSTEM_RETURN_TASK_FROM_CHECKPOINT"
                    reason = "TASK_REFERENCE_EXISTS_WITHOUT_CURRENT_SIGNED_BOUND_CONSUMER"
                elif discovery == "LIVE_SESSION_REQUIRES_RESIGN":
                    work_phase = "LIVE_SESSION_REQUIRES_RESIGN"
                    required_action = "RESPOND_TO_PRESENCE_CHALLENGE"
                    reason = "LIVE_BOUND_SESSION_DETECTED_BUT_SIGNED_PRESENCE_EXPIRED"
                elif discovery == "DISCOVERED_LIVE_UNVERIFIED":
                    work_phase = "DISCOVERED_LIVE_UNVERIFIED"
                    required_action = "RESPOND_TO_PRESENCE_CHALLENGE"
                    reason = "LIVE_PROCESS_OR_CURRENT_ATTESTATION_DISCOVERED_BUT_SELF_SIGNATURE_REQUIRED"
                elif discovery == "PROBE_PENDING":
                    work_phase = "PRESENCE_PROBE_PENDING"
                    required_action = "RESPOND_TO_PRESENCE_CHALLENGE"
                    reason = "SYSTEM_SENT_AVAILABILITY_CHALLENGE_AWAITING_SIGNED_RESPONSE"
                else:
                    work_phase = "SIGN_IN_REQUIRED" if not row.get("present") else "LIVE_BINDING_REQUIRED"
                    required_action = "SIGN_CHECK_IN_AND_BIND_LIVE_SESSION"
                    reason = "NO_CURRENT_SIGNED_BOUND_CONSUMER_PROOF"
                execution_ready = False
            presence = "PRESENT" if row.get("present") else ("LEFT" if presence_state == "ABSENT" else "AWAY")
            clients.append({
                "seat": seat,
                "actor_role": row.get("actor_role"),
                "state": state,
                "availability": availability,
                "presence": presence,
                "last_seen": row.get("presence_last_seen"),
                "source": source,
                "verified": verified,
                "discovery_state": row.get("discovery_state"),
                "process_candidate": row.get("process_candidate") is True,
                "probe_pending": row.get("probe_pending") is True,
                "probe_challenge_id": row.get("probe_challenge_id"),
                "probe_expires_at": row.get("probe_expires_at"),
                "execution_ready": execution_ready,
                "coordination_available": availability == "AVAILABLE",
                "availability_attested_at": row.get("availability_attested_at"),
                "availability_expires_at": row.get("availability_expires_at"),
                "work_phase": work_phase,
                "required_action": required_action,
                "reason": reason,
                "actor_id": actor_id,
                "session_id": row.get("session_id"),
                "origin_instance": row.get("origin_instance"),
                "device_id": row.get("device_id"),
                "present": row.get("present"),
                "consumer_current": row.get("consumer_current"),
                "auto_routable": row.get("auto_routable"),
                "current_tasks": [{
                    "id": t.get("id"), "title": t.get("title"),
                    "status": t.get("status"), "dispatch_status": t.get("dispatch_status"),
                    "claimed_by": t.get("claimed_by"), "assigned_to": t.get("assigned_to"),
                    "scope": list(t.get("scope") or []),
                } for t in (pending + current)],
                "stale_task_claims": [{
                    "id": t.get("id"), "title": t.get("title"),
                    "status": t.get("status"), "dispatch_status": t.get("dispatch_status"),
                    "claimed_by": t.get("claimed_by"), "assigned_to": t.get("assigned_to"),
                    "scope": list(t.get("scope") or []),
                    "truth_state": "STALE_CLAIM_REQUIRES_RECONCILIATION",
                } for t in stale_claims],
                "last_actor_ack": {
                    "message_id": last_ack.get("message_id"),
                    "status": last_ack.get("status"),
                    "at": last_ack.get("at"),
                    "task_id": last_ack.get("task_id"),
                    "synthetic": last_ack.get("synthetic"),
                } if last_ack else None,
            })
        availability_summary = {
            key: sum(1 for row in clients if row.get("availability") == key)
            for key in ("AVAILABLE", "BUSY", "OFFLINE", "UNKNOWN")
        }
        work_lifecycle = build_work_lifecycle(tasks)
        worker_rows = []
        worker_state = _load(self.worker_registry, {"workers": []})
        for worker in worker_state.get("workers", []):
            live = str(worker.get("liveness") or "").upper() == "LIVE" and _current(worker.get("lease_expires_at"))
            worker_rows.append({
                "actor_id": worker.get("worker_id"),
                "kind": worker.get("kind"),
                "availability": "AVAILABLE" if live else "OFFLINE",
                "execution_ready": live,
                "liveness": worker.get("liveness"),
                "heartbeat": worker.get("heartbeat"),
                "lease_expires_at": worker.get("lease_expires_at"),
                "owner": worker.get("owner"),
                "reason": "CURRENT_WORKER_HEARTBEAT" if live else "WORKER_HEARTBEAT_STALE_OR_ABSENT",
            })
        seat_ids = {str(row.get("seat") or "").upper() for row in clients}
        known_workers = {str(row.get("actor_id") or "").upper() for row in worker_rows}
        other_map: dict[str, dict[str, Any]] = {}
        stale_other_map: dict[str, dict[str, Any]] = {}
        for task in tasks:
            if task.get("status") not in ("IN_PROGRESS", "BLOCKED") and task.get("dispatch_status") != "PENDING_ACCEPTANCE":
                continue
            actor = str(task.get("claimed_by") or task.get("assigned_to") or "").strip()
            canonical_owner = _seat_for_actor(actor, route_rows)
            if not actor or canonical_owner or actor.upper() in known_workers:
                continue
            current_truth = task_claim_is_current(task)
            target_map = other_map if current_truth else stale_other_map
            row = target_map.setdefault(actor, {
                "actor_id": actor,
                "availability": "BUSY" if current_truth else "UNKNOWN",
                "execution_ready": False,
                "current_tasks": [],
                "source": "CANONICAL_TASK_LEDGER",
                "truth_state": "CURRENT_VERIFIED_CLAIM" if current_truth else "STALE_CLAIM_REQUIRES_RECONCILIATION",
            })
            row["current_tasks"].append({"id": task.get("id"), "status": task.get("status"),
                                         "dispatch_status": task.get("dispatch_status"),
                                         "scope": list(task.get("scope") or [])})
        task_index = {str(t.get("id")): t for t in tasks if t.get("id")}
        reservations = []
        for lock in active_locks:
            task = task_index.get(str(lock.get("task_id") or ""))
            if task is None:
                reservation_state = "ORPHAN_LOCK_REQUIRES_RECONCILIATION"
            elif task_claim_is_current(task):
                reservation_state = "CURRENT_ACTIVE_RESERVATION"
            else:
                reservation_state = "STALE_TASK_LOCK_REQUIRES_RECONCILIATION"
            reservations.append({
                "lock_id": lock.get("id"),
                "task_id": lock.get("task_id"),
                "actor": lock.get("lease_holder") or lock.get("agent"),
                "scope": lock.get("scope"),
                "lock_kind": lock.get("lock_kind"),
                "owner": lock.get("owner"),
                "created_at": lock.get("created_at"),
                "reservation_state": reservation_state,
            })
        founder_available = any(
            row.get("seat") == "C1" and row.get("availability") == "AVAILABLE"
            for row in clients
        )
        current_reservations = [r for r in reservations
                                if r["reservation_state"] == "CURRENT_ACTIVE_RESERVATION"]
        founder_brief = build_founder_brief(
            tasks, founder_available=founder_available,
            active_scope_reservations=current_reservations)
        presence_anomalies = [{
            "seat": row.get("seat"),
            "availability": row.get("availability"),
            "execution_ready": row.get("execution_ready"),
            "discovery_state": row.get("discovery_state"),
            "work_phase": row.get("work_phase"),
            "required_action": row.get("required_action"),
            "reason": row.get("reason"),
            "probe_pending": row.get("probe_pending"),
            "probe_challenge_id": row.get("probe_challenge_id"),
        } for row in clients
          if row.get("execution_ready") is not True and str(row.get("discovery_state") or "UNKNOWN") != "UNKNOWN"]
        founder_brief["presence_anomalies"] = presence_anomalies
        founder_brief["presence_anomaly_count"] = len(presence_anomalies)
        founder_brief["presence_attention_required"] = bool(presence_anomalies)
        dispatch_plan = build_dispatch_plan(tasks, route_rows, current_reservations)
        return {
            "schema": "raios.client-activity.v4",
            "generated_at": _utc(),
            "canonical_coordination_source": True,
            "canonical_endpoint": "/api/client-activity",
            "availability_summary": availability_summary,
            "work_lifecycle": work_lifecycle,
            "founder_brief": founder_brief,
            "presence_anomalies": presence_anomalies,
            "dispatch_plan": dispatch_plan,
            "all_seats_accounted_for": len(clients) == 12,
            "coordination_notifiable": route_snapshot.get("coordination_available", []),
            "coordination_notifiable_count": route_snapshot.get("coordination_available_count", 0),
            "live_notifiable": route_snapshot.get("auto_routable", []),
            "live_notifiable_count": route_snapshot.get("auto_routable_count", 0),
            "clients": clients,
            "workers": worker_rows,
            "other_active_actors": list(other_map.values()),
            "unverified_work_claims": list(stale_other_map.values()),
            "active_scope_reservations": reservations,
            "current_scope_reservations": [r for r in reservations
                                           if r["reservation_state"] == "CURRENT_ACTIVE_RESERVATION"],
            "stale_scope_reservations": [r for r in reservations
                                         if r["reservation_state"] != "CURRENT_ACTIVE_RESERVATION"],
            "source_precedence": [
                "CURRENT_VERIFIED_TASKS_AND_LOCKS_FOR_ACTIVE_WORK_AND_SCOPE",
                "SIGNED_BOUND_CONSUMER_FOR_EXECUTION_READINESS",
                "STALE_CLAIMS_ARE_VISIBLE_BUT_NOT_CURRENT_WORK",
                "CURRENT_AVAILABILITY_ATTESTATION_FOR_COORDINATION_AVAILABILITY",
                "SIGNED_OUT_FOR_OFFLINE",
                "UNKNOWN_WHEN_NO_CURRENT_VERIFIED_FACT",
            ],
            "freshness_policy": "NEWER_CURRENT_VERIFIED_FACT_SUPERSEDES_OLDER_COORDINATION_FACT",
            "work_gate": {
                "sequence": [
                    "SIGNED_CHECK_IN", "WAIT_FOR_RAIOS_WORKER_ASSIGNMENT",
                    "EXPLICIT_ACCEPTANCE", "EXECUTE_ONLY_ASSIGNED_SCOPE",
                    "SUBMIT_CHECKPOINTS_AND_EVIDENCE", "SYSTEM_VERIFIES_AND_RELEASES",
                ],
                "availability_requires_execution_binding": False,
                "execution_requires_signed_live_binding": True,
                "live_bound_consumer_required": True,
                "self_claim_allowed": False,
                "direct_member_handoff_allowed": False,
                "one_active_task_per_seat": True,
                "active_scope_overlap_allowed": False,
                "evidence_required_for_completion": True,
                "visibility_required": True,
            },
            "truth_laws": [
                "CLAIM_NE_LIVE_ACTIVITY", "DELIVERY_ACK_NE_ACTOR_ACK",
                "SERVICE_NE_SEAT_ACTOR", "ONLY_BOUND_CONSUMER_IS_AUTO_ROUTABLE",
                "AVAILABILITY_NE_EXECUTION_READINESS",
                "PROCESS_DISCOVERY_NE_PRESENCE_PROOF",
                "DELIVERY_ACK_NE_PRESENCE_PROOF",
                "CHALLENGE_RESPONSE_REQUIRED_FOR_DISCOVERED_UNVERIFIED_SEAT",
                "DISCOVERED_UNVERIFIED_SEAT_MUST_RAISE_FOUNDER_ATTENTION",
                "SIGNED_PRESENCE_REQUIRED_FOR_ANY_WORK",
                "WORKER_ASSIGNMENT_REQUIRED_BEFORE_EXECUTION",
                "ALL_COORDINATION_READS_USE_CLIENT_ACTIVITY_V4",
                "FOUNDER_BRIEF_ALWAYS_PREPARED",
                "C1_GATED_DECISIONS_WAIT_WHEN_FOUNDER_OFFLINE",
                "NEWER_VERIFIED_FACT_SUPERSEDES_OLDER_COORDINATION_FACT",
                "ONE_ACTIVE_TASK_PER_SEAT", "NO_ACTIVE_SCOPE_OVERLAP",
            ],
        }

    def notification_status(self, message_id: str) -> dict[str, Any]:
        seats = [str(r.get("seat") or "") for r in self.routes.snapshot().get("seats", [])]
        rows = []
        for seat in seats:
            delivery = self.outbox / f"{message_id}.{seat}.delivery.ack.json"
            actor = self.receipts / f"{message_id}.{seat}.actor.ack.receipt.json"
            d = _load(delivery, {}) if delivery.exists() else {}
            a = _load(actor, {}) if actor.exists() else {}
            if a.get("ack_type") == "ACTOR_ACK" and a.get("status") == "READ" and a.get("synthetic") is not True:
                state = "AVAILABLE_READ"
            elif d.get("ack_type") == "DELIVERY_ACK":
                state = "DELIVERED_NOT_CONSUMED"
            else:
                state = "NO_DELIVERY_EVIDENCE"
            rows.append({
                "seat": seat,
                "state": state,
                "delivery_ack": bool(d),
                "actor_ack": bool(a),
                "actor": a.get("actor"),
                "session_id": a.get("session_id"),
                "synthetic": a.get("synthetic") if a else None,
            })
        return {
            "schema": "raios.notification-status.v1",
            "message_id": message_id,
            "generated_at": _utc(),
            "clients": rows,
            "available_now": [r["seat"] for r in rows if r["state"] == "AVAILABLE_READ"],
        }
