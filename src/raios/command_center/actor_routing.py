from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .coordination_truth import aliases_for_seat, canonical_seat

COUNCIL_SEATS = tuple(f"C{i}" for i in range(1, 13))


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _current_expiry(expiry: str | None) -> bool:
    if not expiry:
        return False
    try:
        return datetime.fromisoformat(str(expiry).replace("Z", "+00:00")) > _utc_now()
    except (TypeError, ValueError):
        return False


def lease_current(row: dict[str, Any]) -> bool:
    state = str(row.get("presence") or "").upper()
    return (
        state == "PRESENT"
        and row.get("signature_valid") is True
        and _current_expiry(row.get("lease_expires_at"))
    )


class ActorRouteRegistry:
    def __init__(self, repo: Path, *, presence_path: Path | None = None,
                 bindings_path: Path | None = None, consumers_path: Path | None = None) -> None:
        self.repo = repo.resolve()
        self.seat_map_path = self.repo / ".ai-os" / "mcp" / "SEAT-MAP.json"
        base = Path.home() / ".raios" / "runtime" / "council-ops"
        p_default = Path(os.getenv("RAIOS_COUNCIL_PRESENCE", str(base / "presence.json")))
        b_default = Path(os.getenv("RAIOS_ACTOR_BINDINGS", str(base / "actor-bindings.json")))
        c_default = Path(os.getenv("RAIOS_SEAT_CONSUMERS", str(base / "consumers")))
        self.presence_path = (presence_path or p_default).resolve()
        self.bindings_path = (bindings_path or b_default).resolve()
        self.consumers_path = (consumers_path or c_default).resolve()
        self.challenge_path = self.presence_path.parent / "presence-challenges.json"
        self._process_cache_at = 0.0
        self._process_cache: set[str] = set()

    def _binding_current(self, row: dict[str, Any]) -> bool:
        required = ("actor_id", "origin_instance", "device_id", "session_id", "auth_evidence", "lease_expires_at")
        if any(not row.get(key) for key in required):
            return False
        return _current_expiry(row.get("lease_expires_at"))
    def _consumer_current(self, row: dict[str, Any], binding: dict[str, Any]) -> bool:
        if str(row.get("state") or "").upper() != "ONLINE":
            return False
        required = ("actor_id", "device_id", "session_id", "lease_expires_at")
        if any(not row.get(key) for key in required):
            return False
        if row.get("actor_id") != binding.get("actor_id"):
            return False
        if row.get("session_id") != binding.get("session_id"):
            return False
        if row.get("device_id") != binding.get("device_id"):
            return False
        return _current_expiry(row.get("lease_expires_at"))

    def _process_names(self) -> set[str]:
        now=time.monotonic()
        if now-self._process_cache_at < 15:
            return set(self._process_cache)
        names:set[str]=set()
        try:
            raw=subprocess.check_output(
                ["tasklist","/FO","CSV","/NH"],text=True,stderr=subprocess.DEVNULL,
                timeout=5,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            for row in csv.reader(io.StringIO(raw)):
                if row:
                    names.add(str(row[0]).lower())
        except Exception:
            pass
        self._process_cache_at=now;self._process_cache=names
        return set(names)
    def canonical_seats(self) -> set[str]:
        seat_map = _load(self.seat_map_path, {"seats": {}})
        return set((seat_map.get("seats") or {}).keys())
    def snapshot(self) -> dict[str, Any]:
        seat_map = _load(self.seat_map_path, {"seats": {}})
        presence = _load(self.presence_path, {"seats": {}})
        bindings = _load(self.bindings_path, {"bindings": {}})
        challenges = _load(self.challenge_path, {"challenges": {}})
        process_names = self._process_names()
        rows: list[dict[str, Any]] = []
        auto: list[str] = []
        coordination_available: list[str] = []
        for seat, spec in (seat_map.get("seats") or {}).items():
            aliases, alias_prefixes = aliases_for_seat(seat, seat_map)
            p = (presence.get("seats") or {}).get(seat) or {}
            b = (bindings.get("bindings") or {}).get(seat) or {}
            c = _load(self.consumers_path / f"{seat}.json", {})
            present = lease_current(p)
            availability_claim = str(p.get("availability") or "UNKNOWN").upper()
            availability_claim_current = (
                availability_claim in {"AVAILABLE", "BUSY", "OFFLINE"}
                and _current_expiry(p.get("availability_expires_at"))
            )
            binding_current = self._binding_current(b)
            consumer_current = self._consumer_current(c, b)
            configured_processes={str(x).lower() for x in (spec.get("process_names") or []) if str(x).strip()}
            process_candidate=bool(configured_processes & process_names)
            pending_probe=False;pending_challenge_id=None;pending_probe_expires_at=None
            for probe in (challenges.get("challenges") or {}).values():
                if str(probe.get("seat") or "").upper()!=seat or probe.get("status")!="PENDING":
                    continue
                if _current_expiry(probe.get("expires_at")):
                    pending_probe=True
                    pending_challenge_id=probe.get("challenge_id")
                    pending_probe_expires_at=probe.get("expires_at")
                    break
            routable = present and binding_current and consumer_current
            coordination_current = (
                routable or present or
                (availability_claim_current and availability_claim == "AVAILABLE")
            )
            if routable:
                discovery_state="VERIFIED_EXECUTION_READY"
            elif consumer_current and binding_current:
                discovery_state="LIVE_SESSION_REQUIRES_RESIGN"
            elif process_candidate or (availability_claim_current and availability_claim=="AVAILABLE"):
                discovery_state="DISCOVERED_LIVE_UNVERIFIED"
            elif pending_probe:
                discovery_state="PROBE_PENDING"
            else:
                discovery_state="UNKNOWN"
            if routable:
                auto.append(seat)
            if coordination_current:
                coordination_available.append(seat)
            rows.append({
                "seat": seat,
                "defined": True,
                "actor_role": spec.get("actor_role"),
                "instance_role": spec.get("instance_role"),
                "aliases": aliases,
                "alias_prefixes": alias_prefixes,
                "present": present,
                "presence_state": str(p.get("presence") or "UNKNOWN").upper(),
                "presence_last_seen": p.get("last_seen"),
                "presence_checked_in_at": p.get("checked_in_at"),
                "presence_checked_out_at": p.get("checked_out_at"),
                "presence_signature_valid": p.get("signature_valid") is True,
                "presence_lease_expires_at": p.get("lease_expires_at"),
                "capabilities": list(p.get("capabilities") or []),
                "availability_claim": availability_claim,
                "availability_claim_current": availability_claim_current,
                "availability_source": p.get("availability_source"),
                "availability_attested_at": p.get("availability_attested_at"),
                "availability_expires_at": p.get("availability_expires_at"),
                "availability_reason": p.get("availability_reason"),
                "actor_bound": bool(b.get("actor_id")),
                "session_bound": bool(b.get("session_id")),
                "binding_current": binding_current,
                "binding_lease_expires_at": b.get("lease_expires_at"),
                "consumer_current": consumer_current,
                "consumer_lease_expires_at": c.get("lease_expires_at"),
                "actor_id": b.get("actor_id"),
                "origin_instance": b.get("origin_instance"),
                "device_id": b.get("device_id"),
                "session_id": b.get("session_id"),
                "auto_routable": routable,
                "coordination_available": coordination_current,
                "process_candidate": process_candidate,
                "configured_process_names": sorted(configured_processes),
                "probe_pending": pending_probe,
                "probe_challenge_id": pending_challenge_id,
                "probe_expires_at": pending_probe_expires_at,
                "discovery_state": discovery_state,
            })
        return {
            "schema": "raios.actor-route-registry.v2",
            "generated_at": _utc_now().isoformat(),
            "auto_routable": auto,
            "auto_routable_count": len(auto),
            "coordination_available": coordination_available,
            "coordination_available_count": len(coordination_available),
            "seats": rows,
            "identity_ne_presence": True,
            "availability_ne_execution_readiness": True,
            "presence_ne_binding": True,
            "binding_ne_consumer": True,
            "delivery_ack_ne_actor_ack": True,
            "process_discovery_ne_presence_proof": True,
            "live_session_ne_signed_presence": True,
        }

    def resolve(self, requested: list[str]) -> dict[str, Any]:
        snap = self.snapshot()
        automatic = set(snap["auto_routable"])
        seat_map = _load(self.seat_map_path, {"seats": {}})
        canonical = set((seat_map.get("seats") or {}).keys())
        resolved: list[str] = []
        owner_selected_unbound: list[str] = []
        rejected: list[str] = []
        modes: dict[str, str] = {}
        for raw in requested:
            target = str(raw).upper()
            if target in {"ALL", "ALL_AVAILABLE"}:
                for seat in snap["coordination_available"]:
                    if seat not in resolved:
                        resolved.append(seat)
                        modes[seat] = ("AUTO_LIVE_BOUND_CONSUMER" if seat in automatic
                                       else "AUTO_COORDINATION_AVAILABLE")
                continue
            if target == "ALL_ONLINE":
                for seat in snap["auto_routable"]:
                    if seat not in resolved:
                        resolved.append(seat)
                        modes[seat] = "AUTO_LIVE_BOUND_CONSUMER"
                continue
            resolved_target = canonical_seat(target, seat_map)
            if resolved_target is None or resolved_target not in canonical:
                rejected.append(target)
                continue
            target = resolved_target
            if target not in resolved:
                resolved.append(target)
            if target in automatic:
                modes[target] = "C1_SELECTED_LIVE_BOUND_CONSUMER"
            else:
                modes[target] = "C1_SELECTED_UNBOUND"
                owner_selected_unbound.append(target)
        return {
            "targets": resolved,
            "routing_modes": modes,
            "owner_selected_unbound": owner_selected_unbound,
            "rejected": rejected,
            "auto_routable_snapshot": snap["auto_routable"],
        }
