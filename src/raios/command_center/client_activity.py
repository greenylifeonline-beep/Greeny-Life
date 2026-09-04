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
        self.receipts = self.repo / ".ai-os" / "receipts" / "command-fabric"
        self.outbox = self.repo / ".ai-os" / "state" / "command-fabric" / "outbox"

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
        clients = []
        for row in route_snapshot.get("seats", []):
            seat = str(row.get("seat") or "")
            actor_id = row.get("actor_id")
            current = [t for t in tasks if t.get("status") == "IN_PROGRESS" and _matches_actor(t, seat, actor_id)]
            last_ack = self._latest_actor_ack(seat)
            if row.get("auto_routable"):
                state = "WORKING" if current else "IDLE"
            elif current:
                state = "STALE_OR_UNBOUND_CLAIM"
            else:
                state = "OFFLINE_OR_UNBOUND"
            clients.append({
                "seat": seat,
                "actor_role": row.get("actor_role"),
                "state": state,
                "actor_id": actor_id,
                "session_id": row.get("session_id"),
                "origin_instance": row.get("origin_instance"),
                "device_id": row.get("device_id"),
                "present": row.get("present"),
                "consumer_current": row.get("consumer_current"),
                "auto_routable": row.get("auto_routable"),
                "current_tasks": [{
                    "id": t.get("id"), "title": t.get("title"),
                    "status": t.get("status"), "claimed_by": t.get("claimed_by"),
                    "assigned_to": t.get("assigned_to"),
                } for t in current],
                "last_actor_ack": {
                    "message_id": last_ack.get("message_id"),
                    "status": last_ack.get("status"),
                    "at": last_ack.get("at"),
                    "task_id": last_ack.get("task_id"),
                    "synthetic": last_ack.get("synthetic"),
                } if last_ack else None,
            })
        return {
            "schema": "raios.client-activity.v1",
            "generated_at": _utc(),
            "live_notifiable": route_snapshot.get("auto_routable", []),
            "live_notifiable_count": route_snapshot.get("auto_routable_count", 0),
            "clients": clients,
            "truth_laws": [
                "CLAIM_NE_LIVE_ACTIVITY", "DELIVERY_ACK_NE_ACTOR_ACK",
                "SERVICE_NE_SEAT_ACTOR", "ONLY_BOUND_CONSUMER_IS_AUTO_ROUTABLE",
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
