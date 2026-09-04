from __future__ import annotations

import json
from pathlib import Path

from raios.command_center.client_activity import ClientActivityView


class Routes:
    def snapshot(self):
        return {
            "auto_routable": ["C6"], "auto_routable_count": 1,
            "seats": [
                {"seat": "C3", "actor_role": "CONSULTANT", "actor_id": None,
                 "present": False, "consumer_current": False, "auto_routable": False},
                {"seat": "C6", "actor_role": "ESTATE", "actor_id": "C6-ACTOR",
                 "session_id": "S6", "origin_instance": "C6-LIVE", "device_id": "AG",
                 "present": True, "consumer_current": True, "auto_routable": True},
            ],
        }


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_snapshot_separates_live_activity_from_stale_claim(tmp_path):
    repo = tmp_path / "repo"
    write_json(repo / ".ai-os/state/TASKS.json", {"tasks": [
        {"id": "T-C3", "title": "old", "status": "IN_PROGRESS", "claimed_by": "C3"},
        {"id": "T-C6", "title": "live", "status": "IN_PROGRESS", "claimed_by": "C6-ACTOR"},
    ]})
    view = ClientActivityView(repo, Routes())
    snap = view.snapshot()
    by = {row["seat"]: row for row in snap["clients"]}
    assert by["C3"]["state"] == "STALE_OR_UNBOUND_CLAIM"
    assert by["C6"]["state"] == "WORKING"
    assert by["C6"]["current_tasks"][0]["id"] == "T-C6"
    assert snap["live_notifiable"] == ["C6"]


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
