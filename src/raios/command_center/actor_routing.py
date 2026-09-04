from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COUNCIL_SEATS = tuple(f"C{i}" for i in range(1, 13))


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def lease_current(row: dict[str, Any]) -> bool:
    if str(row.get("presence") or "").upper() != "PRESENT":
        return False
    expiry = row.get("lease_expires_at")
    if not expiry:
        return False
    try:
        return datetime.fromisoformat(str(expiry).replace("Z", "+00:00")) > _utc_now()
    except (TypeError, ValueError):
        return False


class ActorRouteRegistry:
    """Presence + authenticated session binding view for council routing.

    Identity in SEAT-MAP is not routability. A seat is automatically routable only
    when both a current self-signed presence lease and a current actor/session
    binding exist. C1 may still name a canonical seat explicitly; that is queued as
    owner-selected work but never upgraded to ACTOR_ACK by this registry.
    """

    def __init__(
        self,
        repo: Path,
        *,
        presence_path: Path | None = None,
        bindings_path: Path | None = None,
    ) -> None:
        self.repo = repo.resolve()
        self.seat_map_path = self.repo / ".ai-os" / "mcp" / "SEAT-MAP.json"
        self.presence_path = (
            presence_path
            or Path(os.getenv(
                "RAIOS_COUNCIL_PRESENCE",
                str(Path.home() / ".raios" / "runtime" / "council-ops" / "presence.json"),
            ))
        ).resolve()
        self.bindings_path = (
            bindings_path
            or Path(os.getenv(
                "RAIOS_ACTOR_BINDINGS",
                str(Path.home() / ".raios" / "runtime" / "council-ops" / "actor-bindings.json"),
            ))
        ).resolve()

    def snapshot(self) -> dict[str, Any]:
        seat_map = _load(self.seat_map_path, {"seats": {}})
        presence = _load(self.presence_path, {"seats": {}})
        bindings = _load(self.bindings_path, {"bindings": {}})
        rows = []
        auto = []
        for seat, spec in (seat_map.get("seats") or {}).items():
            p = (presence.get("seats") or {}).get(seat) or {}
            b = (bindings.get("bindings") or {}).get(seat) or {}
            present = lease_current(p)
            binding_current = self._binding_current(b)
            routable = present and binding_current
            if routable:
                auto.append(seat)
            rows.append({
                "seat": seat,
                "defined": True,
                "actor_role": spec.get("actor_role"),
                "instance_role": spec.get("instance_role"),
                "present": present,
                "presence_lease_expires_at": p.get("lease_expires_at"),
                "actor_bound": bool(b.get("actor_id")),
                "session_bound": bool(b.get("session_id")),
                "binding_current": binding_current,
                "binding_lease_expires_at": b.get("lease_expires_at"),
                "actor_id": b.get("actor_id"),
                "origin_instance": b.get("origin_instance"),
                "device_id": b.get("device_id"),
                "session_id": b.get("session_id"),
                "auto_routable": routable,
            })
        return {
            "schema": "raios.actor-route-registry.v1",
            "generated_at": _utc_now().isoformat(),
            "auto_routable": auto,
            "auto_routable_count": len(auto),
            "seats": rows,
            "identity_ne_presence": True,
            "presence_ne_binding": True,
            "delivery_ack_ne_actor_ack": True,
        }

    def _binding_current(self, row: dict[str, Any]) -> bool:
        required = ("actor_id", "origin_instance", "device_id", "session_id", "auth_evidence", "lease_expires_at")
        if any(not row.get(key) for key in required):
            return False
        try:
            return datetime.fromisoformat(str(row["lease_expires_at"]).replace("Z", "+00:00")) > _utc_now()
        except (TypeError, ValueError):
            return False

    def canonical_seats(self) -> set[str]:
        seat_map = _load(self.seat_map_path, {"seats": {}})
        return set((seat_map.get("seats") or {}).keys())

    def resolve(self, requested: list[str]) -> dict[str, Any]:
        snap = self.snapshot()
        automatic = set(snap["auto_routable"])
        canonical = self.canonical_seats()
        resolved: list[str] = []
        owner_selected_unbound: list[str] = []
        rejected: list[str] = []
        modes: dict[str, str] = {}

        for raw in requested:
            target = str(raw).upper()
            if target in {"ALL", "ALL_ONLINE", "ALL_AVAILABLE"}:
                for seat in snap["auto_routable"]:
                    if seat not in resolved:
                        resolved.append(seat)
                        modes[seat] = "AUTO_LIVE_BOUND"
                continue
            if target not in canonical:
                rejected.append(target)
                continue
            if target not in resolved:
                resolved.append(target)
            if target in automatic:
                modes[target] = "C1_SELECTED_LIVE_BOUND"
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
