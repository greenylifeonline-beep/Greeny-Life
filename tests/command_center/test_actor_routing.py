from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from raios.command_center.actor_routing import ActorRouteRegistry


def iso(delta_minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=delta_minutes)).isoformat()


def test_all_requires_presence_binding_and_live_consumer(tmp_path):
    repo = tmp_path / "Greeny-Life"
    seatmap = repo / ".ai-os" / "mcp" / "SEAT-MAP.json"
    seatmap.parent.mkdir(parents=True)
    seatmap.write_text(json.dumps({"seats": {
        "C2": {"actor_role": "EXEC"}, "C6": {"actor_role": "ESTATE"},
        "C12": {"actor_role": "UNASSIGNED"}}}), encoding="utf-8")
    presence = tmp_path / "presence.json"
    presence.write_text(json.dumps({"seats": {
        "C2": {"presence": "PRESENT", "signature_valid": True, "lease_expires_at": iso(5)},
        "C6": {"presence": "PRESENT", "signature_valid": True, "lease_expires_at": iso(5)},
        "C12": {"presence": "PRESENT", "signature_valid": True, "lease_expires_at": iso(-5)}}}), encoding="utf-8")
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({"bindings": {
        "C6": {"actor_id": "C6-ACTOR", "origin_instance": "c6-live", "device_id": "AG",
               "session_id": "s6", "auth_evidence": "proof", "lease_expires_at": iso(5)},
        "C12": {"actor_id": "C12-ACTOR", "origin_instance": "c12-old", "device_id": "OLD",
                "session_id": "s12", "auth_evidence": "proof", "lease_expires_at": iso(5)}}}), encoding="utf-8")
    consumers = tmp_path / "consumers"
    consumers.mkdir()
    (consumers / "C6.json").write_text(json.dumps({
        "state": "ONLINE", "actor_id": "C6-ACTOR", "device_id": "AG",
        "session_id": "s6", "lease_expires_at": iso(5)}), encoding="utf-8")
    routes = ActorRouteRegistry(repo, presence_path=presence, bindings_path=bindings, consumers_path=consumers)
    out = routes.resolve(["ALL_AVAILABLE"])
    assert out["targets"] == ["C2", "C6"]
    assert out["routing_modes"]["C2"] == "AUTO_COORDINATION_AVAILABLE"
    assert out["routing_modes"]["C6"] == "AUTO_LIVE_BOUND_CONSUMER"
    online = routes.resolve(["ALL_ONLINE"])
    assert online["targets"] == ["C6"]
    assert "C12" not in out["targets"]


def test_bound_without_consumer_is_not_auto_routable(tmp_path):
    repo = tmp_path / "Greeny-Life"; seatmap = repo / ".ai-os" / "mcp" / "SEAT-MAP.json"
    seatmap.parent.mkdir(parents=True)
    seatmap.write_text(json.dumps({"seats": {"C6": {"actor_role": "ESTATE"}}}), encoding="utf-8")
    presence = tmp_path / "presence.json"
    presence.write_text(json.dumps({"seats": {"C6": {"presence": "PRESENT", "signature_valid": True, "lease_expires_at": iso(5)}}}), encoding="utf-8")
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({"bindings": {"C6": {
        "actor_id": "C6-ACTOR", "origin_instance": "c6-live", "device_id": "AG",
        "session_id": "s6", "auth_evidence": "proof", "lease_expires_at": iso(5)}}}), encoding="utf-8")
    consumers = tmp_path / "consumers"; consumers.mkdir()
    routes = ActorRouteRegistry(repo, presence_path=presence, bindings_path=bindings, consumers_path=consumers)
    assert routes.resolve(["ALL_ONLINE"])["targets"] == []
    assert routes.resolve(["ALL_AVAILABLE"])["targets"] == ["C6"]


def test_c1_named_unbound_seat_is_explicit_not_fake_live(tmp_path):
    repo = tmp_path / "Greeny-Life"; seatmap = repo / ".ai-os" / "mcp" / "SEAT-MAP.json"
    seatmap.parent.mkdir(parents=True)
    seatmap.write_text(json.dumps({"seats": {"C2": {"actor_role": "EXEC"}}}), encoding="utf-8")
    presence = tmp_path / "presence.json"; presence.write_text(json.dumps({"seats": {}}), encoding="utf-8")
    bindings = tmp_path / "bindings.json"; bindings.write_text(json.dumps({"bindings": {}}), encoding="utf-8")
    consumers = tmp_path / "consumers"; consumers.mkdir()
    routes = ActorRouteRegistry(repo, presence_path=presence, bindings_path=bindings, consumers_path=consumers)
    out = routes.resolve(["C2"])
    assert out["targets"] == ["C2"]
    assert out["routing_modes"]["C2"] == "C1_SELECTED_UNBOUND"
    assert out["owner_selected_unbound"] == ["C2"]
