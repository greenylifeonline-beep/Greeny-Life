"""Delegated native execution stays on the existing capability and lease path."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from raios.c1c5.capabilities import CAPABILITY_HEALTH  # noqa: E402
from raios_mcp.gateway import Actor, Gateway, GatewayError  # noqa: E402


def _actor() -> Actor:
    return Actor(
        actor_id="C2",
        actor_role="CURSOR",
        instance_role="local",
        tools=["send_packet"],
        deny=[],
        token_sha256="abc",
        scopes=["send_packet"],
        expires_at=None,
    )


def _grant(**extra):
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    body = {
        "capability": CAPABILITY_HEALTH,
        "task_id": "TASK-NATIVE-1",
        "idempotency_key": "idem-native-1",
        "nonce": "nonce-native-0001",
        "correlation_id": "corr-native-1",
        "packet_id": "pkt-native-1",
        "grant_expires_at": expires.isoformat(),
        "requested_head": "dfc08e62a6392af53c9995e74278a5ba6d153a84",
        "scope": "native:C2:" + CAPABILITY_HEALTH,
    }
    body.update(extra)
    return body


def test_shell_intent_stays_denied(tmp_path):
    gateway = Gateway(root=tmp_path, policy={}, actors={})
    with pytest.raises(GatewayError) as err:
        gateway._bind_identity(_actor(), "send_packet", {"execution_intent": "EXECUTE", "actor_id": "C2"})
    assert err.value.code == "ESCALATION_DENIED"


def test_delegated_health_is_not_c1_and_replays_once(tmp_path, monkeypatch):
    import raios.c1c5.capabilities as caps

    monkeypatch.setattr(caps, "invoke", lambda capability, health=None: {"INVOKED": True, "result": {"LIVE": True}})
    gateway = Gateway(root=tmp_path, policy={}, actors={})
    first = gateway._delegated_execution(_actor(), _grant(), "DELEGATED")
    assert first["invoked"] is True
    assert first["principal"] == "C2"
    assert first["shell"] is False
    assert first["receipt"]["AUTHORITY_SOURCE"] == "NATIVE_DELEGATED_GRANT"
    assert first["receipt"]["ACTOR_IS_STATIC_C1"] is False
    second = gateway._delegated_execution(_actor(), _grant(nonce="nonce-native-0002"), "DELEGATED")
    assert second["idempotent_replay"] is True
    assert second["invoked"] is False


def test_expired_grant_and_reused_nonce_and_shell_are_rejected(tmp_path, monkeypatch):
    import raios.c1c5.capabilities as caps

    monkeypatch.setattr(caps, "invoke", lambda capability, health=None: {"INVOKED": True, "result": {"LIVE": True}})
    gateway = Gateway(root=tmp_path, policy={}, actors={})
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with pytest.raises(GatewayError) as expired:
        gateway._delegated_execution(_actor(), _grant(idempotency_key="idem-exp", grant_expires_at=past), "DELEGATED")
    assert expired.value.code == "EXPIRED"
    with pytest.raises(GatewayError) as shell:
        gateway._delegated_execution(
            _actor(),
            _grant(capability="shell", idempotency_key="idem-shell", scope="native:C2:shell"),
            "DELEGATED",
        )
    assert shell.value.code == "CAPABILITY_DENIED"
    gateway._delegated_execution(_actor(), _grant(idempotency_key="idem-nonce"), "DELEGATED")
    with pytest.raises(GatewayError) as replay:
        gateway._delegated_execution(
            _actor(),
            _grant(idempotency_key="idem-nonce-2", nonce="nonce-native-0001"),
            "DELEGATED",
        )
    assert replay.value.code == "REPLAY"


def test_bad_fence_is_rejected_without_invoke(tmp_path, monkeypatch):
    import raios.c1c5.capabilities as caps

    called = {"n": 0}

    def _invoke(capability, health=None):
        called["n"] += 1
        return {"INVOKED": True, "result": {"LIVE": True}}

    monkeypatch.setattr(caps, "invoke", _invoke)
    gateway = Gateway(root=tmp_path, policy={}, actors={})
    with pytest.raises(GatewayError) as err:
        gateway._delegated_execution(
            _actor(),
            _grant(idempotency_key="idem-fence", lease_id="L-missing", fence_token="1"),
            "DELEGATED",
        )
    assert err.value.code == "ESCALATION_DENIED"
    assert called["n"] == 0


def test_second_writer_on_same_scope_is_rejected(tmp_path, monkeypatch):
    import raios.c1c5.capabilities as caps

    monkeypatch.setattr(caps, "invoke", lambda capability, health=None: {"INVOKED": True, "result": {"LIVE": True}})
    gateway = Gateway(root=tmp_path, policy={}, actors={})
    other = _actor()
    held = gateway._fabric()[2](tmp_path / ".ai-os" / "state" / "command-fabric" / "leases")
    held.acquire(
        owner="RAIOS_SYSTEM",
        lease_holder="C3",
        scope="native:C2:" + CAPABILITY_HEALTH,
        task_id="TASK-OTHER",
        correlation_id="corr-other",
        capability=CAPABILITY_HEALTH,
        resource_or_target="native",
        idempotency_key="idem-other",
        provenance_ref="TEST",
        ttl_seconds=120,
    )
    with pytest.raises(GatewayError) as err:
        gateway._delegated_execution(other, _grant(idempotency_key="idem-conflict", nonce="nonce-conflict-0002"), "DELEGATED")
    assert err.value.code == "ESCALATION_DENIED"
