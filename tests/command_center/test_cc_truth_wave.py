from __future__ import annotations

from raios.command_center import app as cc
from raios.command_center.client_activity import ClientActivityView


class _Routes:
    def snapshot(self):
        return {"seats": [{"seat": "C2"}, {"seat": "C8"}]}


def test_model_state_timeout_is_not_empty_inventory(monkeypatch):
    monkeypatch.setattr(cc, "http_json", lambda *a, **k: (0, {"error": "TimeoutError: timed out"}))
    out = cc.model_state()
    assert out["probe_state"] == "TIMEOUT"
    assert out["count"] is None
    assert out["timeout_ne_empty_inventory"] is True
    assert out["fabric_ready"] is None
    assert out["ollama_online"] is False


def test_model_state_uses_c5_timeout_probe(monkeypatch):
    monkeypatch.setattr(cc, "http_json", lambda *a, **k: (200, {
        "status": "UNKNOWN",
        "model_fabric_ready": None,
        "model_fabric_probe_state": "TIMEOUT",
        "live_engine_count": 0,
        "live_engines": [],
        "model_fabric_error": "OLLAMA_INVENTORY_PROBE_TIMEOUT",
    }))
    out = cc.model_state()
    assert out["probe_state"] == "TIMEOUT"
    assert out["count"] is None
    assert out["models"] == []
    assert out["timeout_ne_empty_inventory"] is True


def test_c5_service_timeout_is_unknown_not_online(monkeypatch):
    monkeypatch.setattr(cc, "tcp", lambda port: True)
    monkeypatch.setattr(cc, "http_json", lambda *a, **k: (200, {
        "status": "UNKNOWN",
        "model_fabric_ready": None,
        "model_fabric_probe_state": "TIMEOUT",
        "model_fabric_error": "OLLAMA_INVENTORY_PROBE_TIMEOUT",
    }))
    out = cc.service("C5", 8766, cc.C5 + "/health")
    assert out["state"] == "UNKNOWN"
    assert out["probe_state"] == "TIMEOUT"
    assert out["timeout_ne_empty_inventory"] is True


def test_communication_trace_delivery_is_not_actor_ack(tmp_path):
    repo = tmp_path / "repo"
    outbox = repo / ".ai-os/state/command-fabric/outbox"
    receipts = repo / ".ai-os/receipts/command-fabric"
    outbox.mkdir(parents=True)
    receipts.mkdir(parents=True)
    (outbox / "MSG-1.C2.delivery.ack.json").write_text(
        '{"ack_type":"DELIVERY_ACK","status":"QUEUED_FOR_SEAT"}', encoding="utf-8"
    )
    (receipts / "MSG-1.send.json").write_text(
        '{"event":"SENT","route":"CANONICAL_LOCAL_FABRIC","at":"t0","targets":["C2"]}', encoding="utf-8"
    )
    view = ClientActivityView(repo, _Routes())
    trace = view.communication_trace("MSG-1")
    assert trace["DELIVERY_ACK"] is True
    assert trace["ACTOR_ACK"] is False
    assert trace["delivery_ack_ne_actor_ack"] is True
    c2 = next(t for t in trace["targets"] if t["target_seat"] == "C2")
    assert c2["phase"] == "DELIVERY_ACK"
    c8 = next(t for t in trace["targets"] if t["target_seat"] == "C8")
    assert c8["phase"] == "NO_EVIDENCE"


def test_communication_trace_dead_letter(tmp_path):
    repo = tmp_path / "repo"
    dead = repo / ".ai-os/state/command-fabric/dead-letter"
    receipts = repo / ".ai-os/receipts/command-fabric"
    dead.mkdir(parents=True)
    receipts.mkdir(parents=True)
    (dead / "MSG-DEAD.json").write_text('{"status":"DEAD_LETTER"}', encoding="utf-8")
    (receipts / "MSG-DEAD.send.json").write_text(
        '{"event":"SENT","targets":["C2"],"at":"t0"}', encoding="utf-8"
    )
    view = ClientActivityView(repo, _Routes())
    trace = view.communication_trace("MSG-DEAD")
    assert trace["DEAD_LETTER"] is True
    assert trace["FAILURE"] == "DEAD_LETTER"
    assert trace["ACTOR_ACK"] is False


def test_health_still_online_when_worker_unhealthy(monkeypatch):
    monkeypatch.setattr(cc.MESSAGE_WORKER, "status", lambda: {"healthy": False, "workflow_enabled": True})
    health = cc.health()
    assert health["status"] == "ONLINE"
    assert health["message_worker_ne_cc_readiness"] is True
    assert health["message_worker"]["healthy"] is False


def test_change_authority_is_read_only():
    out = cc.change_authority_state()
    assert out["promotion"] is False
    assert out["auto_approval"] is False
    assert out["canonical_head"] == cc.CANONICAL_HEAD
