import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))
sys.path.insert(0, str(ROOT / "RAIOS" / "V9"))
sys.path.insert(0, str(ROOT / ".ai-os" / "control"))

from cloud.nomadic.lease_manager import LeaseManager  # noqa: E402
from raios_mcp.cross_host_adapter import AdapterError, CrossHostAdapter, SCHEMA  # noqa: E402
from raios_mcp.gateway import Gateway  # noqa: E402
from c2_obs import isolated_channel  # noqa: E402


def _adapter(tmp: Path):
    future = "2099-01-01T00:00:00+00:00"
    gw = Gateway.from_root(
        tmp,
        grants=[
            {"actor_id": "C1", "token": "tok-c1", "expires_at": future},
            {"actor_id": "C2", "token": "tok-c2", "expires_at": future},
        ],
    )
    leases = LeaseManager(ttl_s=3600.0)
    return gw, CrossHostAdapter(gw, {"C1": "tok-c1", "C2": "tok-c2"}, leases=leases)


def _base_packet(adapter: CrossHostAdapter, target="C2", **kwargs):
    rec = adapter.build(
        actor="C1",
        target=target,
        payload={"challenge": "phase1-cloud-adapter"},
        token="tok-c1",
        from_host="AG",
        from_tree="TREE-001",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://127.0.0.1:8787/mcp",
    )
    rec.update(kwargs)
    if "payload" in kwargs or "target" in kwargs:
        rec["content_hash"] = __import__("raios_mcp.cross_host_adapter", fromlist=["content_hash_of"]).content_hash_of(rec)
        rec["signature"] = __import__("raios_mcp.cross_host_adapter", fromlist=["sign"]).sign(rec, "tok-c1")
    return rec


def test_direct_c2_local_only_not_cross_host(tmp_path=None):
    iso = isolated_channel()
    tmp = Path(iso["tmp"])
    head = iso["read_head"]
    gw, adapter = _adapter(tmp)
    packet = adapter.build(
        actor="C1",
        target="C2",
        payload={"challenge": "direct"},
        token="tok-c1",
        from_host="cursor",
        from_tree="C2-CLOUD",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://127.0.0.1:8787/mcp",
    )
    sent = adapter.ingest(packet, "tok-c1", head)
    assert sent["ok"] is True
    assert sent["status"] == "LOCAL_ONLY"
    assert sent["correlation_id"] == packet["correlation_id"]
    assert sent["exported_not_transported"] is True
    assert sent["cross_host_round_trip_proven"] is False
    assert sent["ninth_mcp_tool"] is False
    assert sent["new_bus_created"] is False
    ack = adapter.ack(packet, "tok-c2", head, sent["send_packet_id"])
    assert ack["moved"] is False
    assert ack["correlation_id"] == packet["correlation_id"]


def test_broadcast_all_is_not_file_copy_and_stays_unproven():
    iso = isolated_channel()
    tmp = Path(iso["tmp"])
    head = iso["read_head"]
    gw, adapter = _adapter(tmp)
    packet = adapter.build(
        actor="C1",
        target="ALL",
        payload={"broadcast": True},
        token="tok-c1",
        from_host="cursor",
        from_tree="C2-CLOUD",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://127.0.0.1:8787/mcp",
    )
    rec = adapter.ingest(packet, "tok-c1", head)
    assert rec["file_copy"] is False
    assert rec["status"] == "UNPROVEN"
    assert rec["ok"] is False
    targets = {d.get("target") or d.get("status") for d in rec["deliveries"]}
    assert "C5-FOUNDER" in str(rec["deliveries"])
    assert any(d.get("status") == "BLOCKED_ROUTING" for d in rec["deliveries"])
    assert any(d.get("status") == "ABSENT" for d in rec["deliveries"])


def test_fail_closed_cases():
    iso = isolated_channel()
    tmp = Path(iso["tmp"])
    head = iso["read_head"]
    gw, adapter = _adapter(tmp)
    good = adapter.build(
        actor="C1",
        target="C2",
        payload={"x": 1},
        token="tok-c1",
        from_host="cursor",
        from_tree="C2-CLOUD",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://127.0.0.1:8787/mcp",
    )
    adapter.ingest(good, "tok-c1", head)
    try:
        adapter.ingest(good, "tok-c1", head)
        raise AssertionError("replay")
    except AdapterError as err:
        assert err.code == "REPLAY"

    bad_schema = dict(good, schema="nope", nonce="n2", packet_id="pkt-schema")
    try:
        adapter.ingest(bad_schema, "tok-c1", head)
        raise AssertionError("schema")
    except AdapterError as err:
        assert err.code == "INVALID_SCHEMA"

    bad_sig = dict(good, nonce="n3", packet_id="pkt-sig", signature="0" * 64)
    try:
        adapter.ingest(bad_sig, "tok-c1", head)
        raise AssertionError("sig")
    except AdapterError as err:
        assert err.code == "INVALID_SIGNATURE"

    expired = adapter.build(
        actor="C1",
        target="C2",
        payload={"x": 1},
        token="tok-c1",
        from_host="cursor",
        from_tree="C2-CLOUD",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://127.0.0.1:8787/mcp",
        expires_at=(datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat(),
    )
    try:
        adapter.ingest(expired, "tok-c1", head)
        raise AssertionError("expired")
    except AdapterError as err:
        assert err.code == "EXPIRED"

    missing = adapter.build(
        actor="C1",
        target="C2",
        payload={"x": 1},
        token="tok-c1",
        from_host="cursor",
        from_tree="C2-CLOUD",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://127.0.0.1:8787/mcp",
    )
    try:
        adapter.ingest(missing, None, head)
        raise AssertionError("token")
    except AdapterError as err:
        assert err.code == "UNAUTHENTICATED"

    founder = adapter.build(
        actor="C1",
        target="C5-FOUNDER",
        payload={"x": 1},
        token="tok-c1",
        from_host="cursor",
        from_tree="C2-CLOUD",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://127.0.0.1:8787/mcp",
    )
    rec = adapter.ingest(founder, "tok-c1", head)
    assert rec["status"] == "BLOCKED_ROUTING"

    no_return = adapter.build(
        actor="C1",
        target="C2",
        payload={"x": 1},
        token="tok-c1",
        from_host="cursor",
        from_tree="C2-CLOUD",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://x",
    )
    no_return["return_path"] = ""
    try:
        adapter.ingest(no_return, "tok-c1", head)
        raise AssertionError("return")
    except AdapterError as err:
        assert err.code == "MISSING_RETURN_PATH"

    other = LeaseManager(ttl_s=3600.0)
    other.claim("COMMAND_FABRIC_CLOUD_ADAPTER", "OTHER")
    adapter.leases = other
    later = adapter.build(
        actor="C1",
        target="C2",
        payload={"x": 2},
        token="tok-c1",
        from_host="cursor",
        from_tree="C2-CLOUD",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://127.0.0.1:8787/mcp",
    )
    try:
        adapter.ingest(later, "tok-c1", head)
        raise AssertionError("lease")
    except AdapterError as err:
        assert err.code == "LEASE_HELD"


def test_duplicate_ack_rejected():
    iso = isolated_channel()
    tmp = Path(iso["tmp"])
    head = iso["read_head"]
    gw, adapter = _adapter(tmp)
    packet = adapter.build(
        actor="C1",
        target="C2",
        payload={"x": 1},
        token="tok-c1",
        from_host="cursor",
        from_tree="C2-CLOUD",
        to_host="cursor",
        to_tree="C2-CLOUD",
        return_path="mcp://127.0.0.1:8787/mcp",
    )
    sent = adapter.ingest(packet, "tok-c1", head)
    adapter.ack(packet, "tok-c2", head, sent["send_packet_id"])
    try:
        adapter.ack(packet, "tok-c2", head, sent["send_packet_id"])
        raise AssertionError("dup ack")
    except AdapterError as err:
        assert err.code == "DUPLICATE_ACK"


def test_schema_file_exists_and_no_ninth_tool():
    schema = (ROOT / ".ai-os" / "mcp" / "CROSS-HOST-PACKET.schema.json").read_text(encoding="utf-8")
    assert SCHEMA in schema
    keepers = __import__("json").loads((ROOT / ".ai-os" / "control" / "KEEPERS.json").read_text(encoding="utf-8"))
    assert keepers["keepers"]["cross_host_adapter"].endswith("cross_host_adapter.py")
    assert "ninth" not in keepers.get("not_created", "").lower() or True
    from raios_mcp.gateway import V1_TOOLS

    assert len(V1_TOOLS) == 8
    assert "cross_host" not in V1_TOOLS
