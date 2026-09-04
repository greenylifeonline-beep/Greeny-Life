from __future__ import annotations

import json
from pathlib import Path

from raios.command_center.client_activity import ClientActivityView


class Routes:
    def snapshot(self):
        return {
            "auto_routable": ["C6"], "auto_routable_count": 1,
            "seats": [
                {"seat": "C2", "actor_role": "EXECUTIVE", "actor_id": None,
                 "present": False, "presence_state": "UNKNOWN", "presence_signature_valid": False,
                 "availability_claim": "AVAILABLE", "availability_claim_current": True,
                 "availability_source": "C1_ATTESTATION",
                 "availability_attested_at": "2026-09-04T02:00:00+00:00",
                 "availability_expires_at": "2026-09-04T02:30:00+00:00",
                 "availability_reason": "C1_CONFIRMED_AVAILABLE",
                 "consumer_current": False, "auto_routable": False},
                {"seat": "C3", "actor_role": "CONSULTANT", "actor_id": None,
                 "present": False, "presence_state": "UNKNOWN", "presence_signature_valid": False,
                 "consumer_current": False, "auto_routable": False},
                {"seat": "C4", "actor_role": "ASSESSOR", "actor_id": None,
                 "present": False, "presence_state": "ABSENT", "presence_signature_valid": True,
                 "consumer_current": False, "auto_routable": False},
                {"seat": "C6", "actor_role": "ESTATE", "actor_id": "C6-ACTOR",
                 "session_id": "S6", "origin_instance": "C6-LIVE", "device_id": "AG",
                 "present": True, "presence_state": "PRESENT", "presence_signature_valid": True,
                 "consumer_current": True, "auto_routable": True},
            ],
        }


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_snapshot_separates_live_activity_from_stale_claim(tmp_path):
    repo = tmp_path / "repo"
    write_json(repo / ".ai-os/state/TASKS.json", {"tasks": [
        {"id": "T-C3", "title": "old", "status": "IN_PROGRESS", "claimed_by": "C3"},
        {"id": "T-C6", "title": "live", "status": "IN_PROGRESS", "claimed_by": "C6-ACTOR",
         "dispatch_status": "ACCEPTED"},
    ]})
    view = ClientActivityView(repo, Routes())
    snap = view.snapshot()
    by = {row["seat"]: row for row in snap["clients"]}
    assert snap["schema"] == "raios.client-activity.v4"
    assert snap["canonical_coordination_source"] is True
    assert by["C2"]["availability"] == "AVAILABLE"
    assert by["C2"]["execution_ready"] is False
    assert by["C2"]["work_phase"] == "AVAILABLE_NOT_EXECUTION_READY"
    assert by["C3"]["state"] == "STALE_OR_UNBOUND_CLAIM"
    assert by["C3"]["availability"] == "UNKNOWN"
    assert by["C4"]["availability"] == "OFFLINE"
    assert by["C4"]["verified"] is True
    assert by["C6"]["state"] == "WORKING"
    assert by["C6"]["availability"] == "BUSY"
    assert by["C6"]["verified"] is True
    assert by["C6"]["current_tasks"][0]["id"] == "T-C6"
    assert snap["live_notifiable"] == ["C6"]
    assert snap["availability_summary"] == {"AVAILABLE": 1, "BUSY": 1, "OFFLINE": 1, "UNKNOWN": 1}
    assert snap["work_lifecycle"]["counts"]["ACTIVE_VERIFIED"] == 1
    assert snap["work_lifecycle"]["counts"]["STALE_CLAIM_REQUIRES_RECONCILIATION"] == 1
    assert snap["founder_brief"]["prepared_for_founder_return"] is True


def test_unified_source_includes_nonseat_actor_worker_and_scope_reservations(tmp_path):
    repo = tmp_path / "repo"
    write_json(repo / ".ai-os/state/TASKS.json", {"tasks": [{
        "id": "SYS-COORD", "title": "coord", "status": "IN_PROGRESS",
        "claimed_by": "CHATGPT-NORMAL", "scope": ["src/raios/command_center"],
        "dispatch_status": "SYSTEM_FIRST_ACTIVE"
    }]})
    write_json(repo / ".ai-os/state/LOCKS.json", {"locks": [{
        "id": "L-SYS", "task_id": "SYS-COORD", "agent": "CHATGPT-NORMAL",
        "lease_holder": "CHATGPT-NORMAL", "scope": "src/raios/command_center",
        "status": "ACTIVE", "owner": "RAIOS_SYSTEM", "lock_kind": "COORDINATION_CONTROL_PLANE"
    }]})
    write_json(repo / ".ai-os/state/command-fabric/WORKER-REGISTRY.json", {"workers": [{
        "worker_id": "RAIOS-WORKER@TEST", "kind": "MESSAGE_PICKUP", "liveness": "LIVE",
        "heartbeat": "now", "lease_expires_at": "2999-01-01T00:00:00+00:00",
        "owner": "RAIOS_SYSTEM"
    }]})
    snap = ClientActivityView(repo, Routes()).snapshot()
    assert snap["canonical_endpoint"] == "/api/client-activity"
    assert snap["other_active_actors"][0]["actor_id"] == "CHATGPT-NORMAL"
    assert snap["other_active_actors"][0]["current_tasks"][0]["id"] == "SYS-COORD"
    assert snap["active_scope_reservations"][0]["scope"] == "src/raios/command_center"
    assert snap["workers"][0]["availability"] == "AVAILABLE"


def test_notification_status_requires_real_actor_ack(tmp_path):
    repo = tmp_path / "repo"
    write_json(repo / ".ai-os/state/TASKS.json", {"tasks": []})
    view = ClientActivityView(repo, Routes())
    mid = "MSG-TEST"
    write_json(repo / f".ai-os/state/command-fabric/outbox/{mid}.C3.delivery.ack.json", {
        "ack_type": "DELIVERY_ACK", "status": "QUEUED_FOR_SEAT"
    })
    write_json(repo / f".ai-os/state/command-fabric/outbox/{mid}.C6.delivery.ack.json", {
        "ack_type": "DELIVERY_ACK", "status": "QUEUED_FOR_SEAT"
    })
    write_json(repo / f".ai-os/receipts/command-fabric/{mid}.C6.actor.ack.receipt.json", {
        "ack_type": "ACTOR_ACK", "status": "READ", "actor": "C6-ACTOR",
        "session_id": "S6", "synthetic": False
    })
    status = view.notification_status(mid)
    by = {row["seat"]: row for row in status["clients"]}
    assert by["C3"]["state"] == "DELIVERED_NOT_CONSUMED"
    assert by["C6"]["state"] == "AVAILABLE_READ"
    assert status["available_now"] == ["C6"]
