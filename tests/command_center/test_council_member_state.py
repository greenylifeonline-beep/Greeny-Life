from __future__ import annotations

import json
from pathlib import Path

from raios.command_center.council_member_state import (
    PRESENCE_STATE_ALLOWED,
    build_council_member_state,
    build_member_row,
)


class Routes:
    def __init__(self, seats):
        self._seats = seats

    def snapshot(self):
        return {
            "schema": "raios.actor-route-registry.v2",
            "auto_routable": [s["seat"] for s in self._seats if s.get("auto_routable")],
            "auto_routable_count": sum(1 for s in self._seats if s.get("auto_routable")),
            "coordination_available": [],
            "coordination_available_count": 0,
            "seats": self._seats,
        }


def _base_seats():
    rows = []
    for i in range(1, 13):
        seat = f"C{i}"
        rows.append({
            "seat": seat,
            "actor_role": "ROLE",
            "present": False,
            "presence_state": "UNKNOWN",
            "presence_signature_valid": False,
            "consumer_current": False,
            "auto_routable": False,
            "process_candidate": False,
        })
    return rows


def test_presence_unknown_ne_offline():
    row = {
        "seat": "C3",
        "present": False,
        "presence_state": "UNKNOWN",
        "presence_signature_valid": False,
        "auto_routable": False,
    }
    member = build_member_row("C3", row, None, None)
    assert member["presence_state"] == "UNKNOWN"
    assert member["availability"] == "UNKNOWN"
    assert member["availability"] != "OFFLINE"
    assert member["laws"]["UNKNOWN_NE_OFFLINE"] is True


def test_absent_is_offline_availability():
    row = {
        "seat": "C4",
        "present": False,
        "presence_state": "ABSENT",
        "presence_signature_valid": True,
        "auto_routable": False,
    }
    member = build_member_row("C4", row, None, None)
    assert member["presence_state"] == "ABSENT"
    assert member["availability"] == "OFFLINE"


def test_c6_external_representation_no_fake_internal(tmp_path):
    repo = tmp_path / "repo"
    ext_dir = repo / ".ai-os/state/external-presence"
    ext_dir.mkdir(parents=True)
    (repo / ".ai-os/mcp").mkdir(parents=True)
    (repo / ".ai-os/mcp/SEAT-MAP.json").write_text(json.dumps({"seats": {
        "C6": {"actor_role": "ESTATE", "instance_role": "c6-runtime"},
    }}), encoding="utf-8")
    (repo / ".ai-os/state/TASKS.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
    (repo / ".ai-os/state/LOCKS.json").write_text(json.dumps({"locks": []}), encoding="utf-8")
    (ext_dir / "C6.json").write_text(json.dumps({
        "schema": "raios.external-presence-packet.v1",
        "seat": "C6",
        "mode": "EXTERNAL_ONLY",
        "availability": "AVAILABLE",
        "reachable": True,
        "actor_id": "C6-AG-REMOTE-RECON",
        "session_id": "EXT-SESSION-1",
        "origin_instance": "REMOTE",
        "device_id": "REMOTE-DEV",
    }), encoding="utf-8")

    seats = _base_seats()
    for s in seats:
        if s["seat"] == "C6":
            s.update({
                "present": False,
                "presence_state": "UNKNOWN",
                "actor_id": None,
                "session_id": None,
            })
    built = build_council_member_state(repo, Routes(seats))
    c6 = built["by_seat"]["C6"]
    assert c6["presence_state"] == "EXTERNAL_SESSION"
    assert c6["execution_location"] == "EXTERNAL_ONLY"
    assert c6["route_state"] == "EXTERNAL_ONLY"
    assert c6["fake_internal_session"] is False
    assert c6["auto_routable"] is False
    assert c6["external_mode"] == "EXTERNAL_ONLY"
    dump = repo / ".ai-os/state/COUNCIL-MEMBER-STATE.json"
    assert dump.exists()


def test_stale_transition():
    row = {
        "seat": "C2",
        "present": False,
        "presence_state": "UNKNOWN",
        "presence_signature_valid": False,
        "binding_current": True,
        "auto_routable": False,
        "session_id": "OLD",
    }
    member = build_member_row("C2", row, None, None)
    assert member["presence_state"] == "STALE"
    assert member["stale_transition"] is True
    assert member["route_state"] == "STALE_CLAIM"


def test_process_without_signed_presence_not_available():
    row = {
        "seat": "C5",
        "present": False,
        "presence_state": "UNKNOWN",
        "presence_signature_valid": False,
        "process_candidate": True,
        "auto_routable": False,
    }
    activity = {
        "availability": "AVAILABLE",
        "execution_ready": False,
        "work_phase": "DISCOVERED_LIVE_UNVERIFIED",
        "reason": "PROCESS",
    }
    member = build_member_row("C5", row, activity, None)
    assert member["presence_state"] == "UNKNOWN"
    assert member["availability"] != "AVAILABLE"
    assert member["availability"] == "UNKNOWN"
    assert "PROCESS_WITHOUT_SIGNED_PRESENCE" in member["availability_reason"]


def test_busy_ne_unavailable():
    row = {
        "seat": "C6",
        "present": True,
        "presence_state": "PRESENT",
        "presence_signature_valid": True,
        "presence_lease_expires_at": "2999-01-01T00:00:00+00:00",
        "auto_routable": True,
        "consumer_current": True,
    }
    activity = {
        "availability": "BUSY",
        "execution_ready": True,
        "work_phase": "EXECUTING",
        "reason": "ACTIVE",
    }
    member = build_member_row("C6", row, activity, None)
    assert member["availability"] == "BUSY"
    assert member["availability"] != "UNAVAILABLE"
    assert member["laws"]["BUSY_NE_UNAVAILABLE"] is True


def test_presence_state_allowed_set():
    assert "UNKNOWN" in PRESENCE_STATE_ALLOWED
    assert "OFFLINE" not in PRESENCE_STATE_ALLOWED
    assert "EXTERNAL_SESSION" in PRESENCE_STATE_ALLOWED


def test_busy_member_projects_current_task():
    row = {
        "seat": "C2",
        "present": True,
        "presence_state": "PRESENT",
        "presence_signature_valid": True,
        "presence_lease_expires_at": "2999-01-01T00:00:00+00:00",
        "auto_routable": True,
        "consumer_current": True,
    }
    activity = {
        "availability": "BUSY",
        "execution_ready": True,
        "work_phase": "EXECUTING",
        "current_tasks": [{"id": "TASK-1", "status": "IN_PROGRESS"}],
    }
    member = build_member_row("C2", row, activity, None)
    assert member["busy"] is True
    assert member["current_task"]["id"] == "TASK-1"
    assert member["current_tasks"][0]["status"] == "IN_PROGRESS"


def test_builder_writes_dump_and_endpoint_note(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".ai-os/mcp").mkdir(parents=True)
    (repo / ".ai-os/state").mkdir(parents=True)
    (repo / ".ai-os/mcp/SEAT-MAP.json").write_text(json.dumps({"seats": {}}), encoding="utf-8")
    (repo / ".ai-os/state/TASKS.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
    (repo / ".ai-os/state/LOCKS.json").write_text(json.dumps({"locks": []}), encoding="utf-8")
    built = build_council_member_state(repo, Routes(_base_seats()))
    assert built["schema"] == "raios.council-member-state.v1"
    assert built["COUNCIL_STATE_ENDPOINT"] == "/api/council-state"
    assert built["pending_app_py_alias"] is None
    assert built["second_registry_created"] is False
    assert len(built["members"]) == 12
    assert Path(built["dump_path"]).exists()


def test_persist_false_does_not_write_dump_and_projects_completion_laws(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".ai-os/mcp").mkdir(parents=True)
    (repo / ".ai-os/state").mkdir(parents=True)
    (repo / ".ai-os/mcp/SEAT-MAP.json").write_text(json.dumps({"seats": {}}), encoding="utf-8")
    (repo / ".ai-os/state/TASKS.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
    (repo / ".ai-os/state/LOCKS.json").write_text(json.dumps({"locks": []}), encoding="utf-8")
    built = build_council_member_state(repo, Routes(_base_seats()), persist=False)
    assert built["persisted"] is False
    assert built["dump_path"] is None
    assert not (repo / ".ai-os/state/COUNCIL-MEMBER-STATE.json").exists()
    assert "LAWS_SYSTEM_VISIBLE" in built["laws"]
    assert "NO_FAKE_DONE" in built["laws"]
    assert "COMPLETE_ASSIGNED_WORK" in built["laws"]


def test_unknown_presentation_not_offline():
    row = {
        "seat": "C8",
        "present": False,
        "presence_state": "UNKNOWN",
        "presence_signature_valid": False,
        "binding_current": False,
        "consumer_current": False,
        "auto_routable": False,
    }
    member = build_member_row("C8", row, None, None)
    assert member["presentation_state"] == "UNBOUND"
    assert member["availability"] != "OFFLINE"
    assert member["heartbeat_state"] == "UNKNOWN"
    assert member["collapsed_online"] is False
    assert member["laws"]["DELIVERY_ACK_NE_ACTOR_ACK"] is True


def test_lease_expired_presentation():
    row = {
        "seat": "C2",
        "present": True,
        "presence_state": "PRESENT",
        "presence_signature_valid": True,
        "presence_lease_expires_at": "2000-01-01T00:00:00+00:00",
        "auto_routable": False,
        "consumer_current": False,
        "binding_current": False,
    }
    member = build_member_row("C2", row, None, None)
    assert member["presence_state"] == "EXPIRED"
    assert member["presentation_state"] == "LEASE_EXPIRED"
    assert member["lease_current"] is False


def test_synthetic_ack_is_not_actor_ack():
    row = {
        "seat": "C2",
        "present": True,
        "presence_state": "PRESENT",
        "presence_signature_valid": True,
        "presence_lease_expires_at": "2999-01-01T00:00:00+00:00",
        "auto_routable": True,
        "consumer_current": True,
        "binding_current": True,
        "actor_id": "cursor-c2",
        "session_id": "S1",
    }
    activity = {
        "availability": "AVAILABLE",
        "execution_ready": True,
        "last_actor_ack": {
            "message_id": "MSG-1",
            "status": "READ",
            "synthetic": True,
            "actor": "cursor-c2",
            "session_id": "S1",
        },
    }
    member = build_member_row("C2", row, activity, None)
    assert member["actor_ack_state"] == "SYNTHETIC_NOT_ACTOR_ACK"
    assert member["actor_ack_capable"] is False
    assert member["presentation_state"] == "AVAILABLE"


def test_bound_no_heartbeat_when_last_seen_stale():
    row = {
        "seat": "C2",
        "present": True,
        "presence_state": "PRESENT",
        "presence_signature_valid": True,
        "presence_lease_expires_at": "2999-01-01T00:00:00+00:00",
        "presence_last_seen": "2000-01-01T00:00:00+00:00",
        "binding_current": True,
        "consumer_current": True,
        "auto_routable": True,
        "actor_id": "cursor-c2",
        "session_id": "S1",
    }
    member = build_member_row("C2", row, None, None)
    assert member["heartbeat_state"] == "STALE"
    assert member["heartbeat_fresh"] is False
    assert member["presentation_state"] == "BOUND_NO_HEARTBEAT"
