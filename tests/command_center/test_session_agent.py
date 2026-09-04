from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from raios.council_ops.session_agent import SeatSessionAgent


def iso(minutes: int = 5) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def test_session_agent_reads_new_delivery_and_writes_real_actor_ack(tmp_path):
    repo = tmp_path / "Greeny-Life"; repo.mkdir()
    runtime = tmp_path / "runtime"; runtime.mkdir()
    auth = runtime / "auth.json"; auth.write_text("{}", encoding="utf-8")
    agent = SeatSessionAgent(repo, runtime, "C6", auth, "C6-ACTOR", "c6-live", "AG", "s6")
    agent.started_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    (runtime / "actor-bindings.json").write_text(json.dumps({"bindings": {"C6": {
        "actor_id": "C6-ACTOR", "origin_instance": "c6-live", "device_id": "AG",
        "session_id": "s6", "auth_evidence": "proof", "lease_expires_at": iso()}}}), encoding="utf-8")
    (runtime / "presence.json").write_text(json.dumps({"seats": {"C6": {"receipt": "presence-proof"}}}), encoding="utf-8")
    delivery = repo / ".ai-os" / "state" / "command-fabric" / "deliveries" / "C6" / "MSG-1.json"
    delivery.parent.mkdir(parents=True)
    delivery.write_text(json.dumps({
        "schema": "raios.message.v1", "message_id": "MSG-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": {"task_id": "T-1", "text": "hello"}
    }), encoding="utf-8")
    assert agent.consume_once() == 1
    ack = repo / ".ai-os" / "receipts" / "command-fabric" / "MSG-1.C6.actor.ack.receipt.json"
    row = json.loads(ack.read_text(encoding="utf-8"))
    assert row["ack_type"] == "ACTOR_ACK" and row["status"] == "READ"
    assert row["actor"] == "C6-ACTOR" and row["session_id"] == "s6"
    assert row["synthetic"] is False and row["canonical_mutation"] is False


def test_session_agent_signs_assignment_with_current_session_proof(tmp_path, monkeypatch):
    repo = tmp_path / "Greeny-Life"; repo.mkdir()
    runtime = tmp_path / "runtime"; runtime.mkdir()
    auth = runtime / "auth.json"; auth.write_text("{}", encoding="utf-8")
    agent = SeatSessionAgent(repo, runtime, "C6", auth, "C6-ACTOR", "c6-live", "AG", "s6")
    (runtime / "actor-bindings.json").write_text(json.dumps({"bindings": {"C6": {
        "actor_id": "C6-ACTOR", "origin_instance": "c6-live", "device_id": "AG",
        "session_id": "s6", "auth_evidence": "proof", "lease_expires_at": iso()}}}), encoding="utf-8")
    (runtime / "presence.json").write_text(json.dumps({"seats": {"C6": {
        "attendance_fingerprint": "ATTENDANCE-123", "receipt": "presence-proof"}}}), encoding="utf-8")
    calls = []
    def fake_http(path, *, method="GET", payload=None, csrf=None):
        calls.append((path, method, payload, csrf))
        if path == "/api/bootstrap":
            return {"csrf": "csrf-token"}
        return {"status": "ACCEPTED", "acceptance_fingerprint": "ACCEPT-123",
                "signature_mode": "SESSION_BOUND_ATTENDANCE_FINGERPRINT"}
    monkeypatch.setattr(agent, "_http_json", fake_http)
    msg = {"payload": {"text": "TASK_ASSIGNMENT\nTASK_ID=T-9\nTARGET=C6\nDISPATCH_ID=DSP-9"}}
    out = agent._accept_task_assignment(msg)
    assert out["status"] == "ACCEPTED"
    post = calls[-1]
    assert post[0] == "/api/task-accept" and post[1] == "POST"
    assert post[2]["task_id"] == "T-9" and post[2]["actor"] == "C6"
    assert post[2]["actor_proof"]["attendance_fingerprint"] == "ATTENDANCE-123"
    assert post[2]["actor_proof"]["session_id"] == "s6"


def test_session_agent_rejects_assignment_for_other_seat_without_post(tmp_path, monkeypatch):
    repo = tmp_path / "Greeny-Life"; repo.mkdir()
    runtime = tmp_path / "runtime"; runtime.mkdir()
    auth = runtime / "auth.json"; auth.write_text("{}", encoding="utf-8")
    agent = SeatSessionAgent(repo, runtime, "C6", auth, "C6-ACTOR", "c6-live", "AG", "s6")
    called = []
    monkeypatch.setattr(agent, "_http_json", lambda *a, **k: called.append((a, k)))
    out = agent._accept_task_assignment(
        {"payload": {"text": "TASK_ASSIGNMENT\nTASK_ID=T-9\nTARGET=C2\nDISPATCH_ID=DSP-9"}})
    assert out["status"] == "TARGET_MISMATCH"
    assert called == []


def test_session_agent_singleton_rejects_duplicate_for_same_seat(tmp_path):
    repo = tmp_path / "Greeny-Life"; repo.mkdir()
    runtime = tmp_path / "runtime"; runtime.mkdir()
    auth = runtime / "auth.json"; auth.write_text("{}", encoding="utf-8")
    first = SeatSessionAgent(repo, runtime, "C6", auth, "C6-ACTOR", "c6-live", "AG", "s6")
    second = SeatSessionAgent(repo, runtime, "C6", auth, "C6-ACTOR", "c6-live", "AG", "s6")
    first._acquire_singleton()
    with pytest.raises(RuntimeError, match="SEAT_SESSION_SINGLETON_ALREADY_RUNNING"):
        second._acquire_singleton()


def test_session_agent_does_not_ack_delivery_older_than_session(tmp_path):
    repo = tmp_path / "Greeny-Life"; repo.mkdir()
    runtime = tmp_path / "runtime"; runtime.mkdir()
    auth = runtime / "auth.json"; auth.write_text("{}", encoding="utf-8")
    agent = SeatSessionAgent(repo, runtime, "C6", auth, "C6-ACTOR", "c6-live", "AG", "s6")
    (runtime / "actor-bindings.json").write_text(json.dumps({"bindings": {"C6": {
        "actor_id": "C6-ACTOR", "device_id": "AG", "session_id": "s6", "lease_expires_at": iso()}}}), encoding="utf-8")
    delivery = repo / ".ai-os" / "state" / "command-fabric" / "deliveries" / "C6" / "MSG-old.json"
    delivery.parent.mkdir(parents=True)
    delivery.write_text(json.dumps({
        "schema": "raios.message.v1", "message_id": "MSG-old",
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "payload": {"task_id": "T-old"}
    }), encoding="utf-8")
    assert agent.consume_once() == 0
    ack = repo / ".ai-os" / "receipts" / "command-fabric" / "MSG-old.C6.actor.ack.receipt.json"
    assert not ack.exists()
