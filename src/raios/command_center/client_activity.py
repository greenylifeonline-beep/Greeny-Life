from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def _matches_actor(task: dict[str, Any], seat: str, actor_id: str | None) -> bool:
    values = {str(task.get("claimed_by") or ""), str(task.get("assigned_to") or "")}
    candidates = {seat}
    if actor_id:
        candidates.add(actor_id)
    return bool(values & candidates)


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
        clients = []
        for row in route_snapshot.get("seats", []):
            seat = str(row.get("seat") or "")
            actor_id = row.get("actor_id")
            current = [t for t in tasks if t.get("status") in ("IN_PROGRESS", "BLOCKED") and _matches_actor(t, seat, actor_id)]
            pending = [t for t in tasks if t.get("dispatch_status") == "PENDING_ACCEPTANCE" and _matches_actor(t, seat, actor_id)]
            last_ack = self._latest_actor_ack(seat)
            if row.get("auto_routable"):
                state = "ASSIGNED_PENDING_ACCEPTANCE" if pending else ("WORKING" if current else "IDLE")
            elif current or pending:
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
                reason = row.get("availability_reason") or "RECENT_VERIFIED_AVAILABILITY_ATTESTATION"
                execution_ready = False
            elif presence_state == "ABSENT":
                availability = "OFFLINE"
                verified = row.get("presence_signature_valid") is True
                source = "SELF_SIGNED_PRESENCE" if verified else "UNVERIFIED_PRESENCE"
                if current or pending:
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
                source = "INSUFFICIENT_LIVE_EVIDENCE"
                if current or pending:
                    work_phase = "STALE_TASK_CLAIM_REQUIRES_RECONCILIATION"
                    required_action = "SIGN_CHECK_IN_OR_SYSTEM_RETURN_TASK_FROM_CHECKPOINT"
                    reason = "TASK_REFERENCE_EXISTS_WITHOUT_CURRENT_SIGNED_BOUND_CONSUMER"
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
        for task in tasks:
            if task.get("status") not in ("IN_PROGRESS", "BLOCKED") and task.get("dispatch_status") != "PENDING_ACCEPTANCE":
                continue
            actor = str(task.get("claimed_by") or task.get("assigned_to") or "").strip()
            if not actor or actor.upper() in seat_ids or actor.upper() in known_workers:
                continue
            row = other_map.setdefault(actor, {"actor_id": actor, "availability": "BUSY",
                                               "execution_ready": False, "current_tasks": [],
                                               "source": "CANONICAL_TASK_LEDGER"})
            row["current_tasks"].append({"id": task.get("id"), "status": task.get("status"),
                                         "scope": list(task.get("scope") or [])})
        return {
            "schema": "raios.client-activity.v3",
            "generated_at": _utc(),
            "canonical_coordination_source": True,
            "canonical_endpoint": "/api/client-activity",
            "availability_summary": availability_summary,
            "all_seats_accounted_for": len(clients) == 12,
            "coordination_notifiable": route_snapshot.get("coordination_available", []),
            "coordination_notifiable_count": route_snapshot.get("coordination_available_count", 0),
            "live_notifiable": route_snapshot.get("auto_routable", []),
            "live_notifiable_count": route_snapshot.get("auto_routable_count", 0),
            "clients": clients,
            "workers": worker_rows,
            "other_active_actors": list(other_map.values()),
            "active_scope_reservations": [{
                "lock_id": lock.get("id"),
                "task_id": lock.get("task_id"),
                "actor": lock.get("lease_holder") or lock.get("agent"),
                "scope": lock.get("scope"),
                "lock_kind": lock.get("lock_kind"),
                "owner": lock.get("owner"),
                "created_at": lock.get("created_at"),
            } for lock in active_locks],
            "source_precedence": [
                "TASKS_AND_LOCKS_FOR_ACTIVE_WORK_AND_SCOPE",
                "SIGNED_BOUND_CONSUMER_FOR_EXECUTION_READINESS",
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
                "SIGNED_PRESENCE_REQUIRED_FOR_ANY_WORK",
                "WORKER_ASSIGNMENT_REQUIRED_BEFORE_EXECUTION",
                "ALL_COORDINATION_READS_USE_CLIENT_ACTIVITY_V3",
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
