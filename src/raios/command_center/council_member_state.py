"""Council member-state projection for seats C1–C12.

ONE source projection over existing route/presence/client-activity truth.
No second registry. UNKNOWN != OFFLINE. BUSY != UNAVAILABLE.
C6 external mode uses EXTERNAL_SESSION / EXTERNAL_ONLY — never a fake internal session.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COUNCIL_SEATS = tuple(f"C{i}" for i in range(1, 13))

# C1 directive ALLOWED presence_state set
PRESENCE_STATE_ALLOWED = frozenset({
    "PRESENT",
    "ABSENT",
    "UNKNOWN",
    "UNPROVEN",
    "UNVERIFIED",
    "EXPIRED",
    "STALE",
    "EXTERNAL_SESSION",
})

REACHABILITY_ALLOWED = frozenset({
    "REACHABLE",
    "UNREACHABLE",
    "UNKNOWN",
    "EXTERNAL_REACHABLE",
})

EXECUTION_LOCATION_ALLOWED = frozenset({
    "INTERNAL_LOCAL",
    "EXTERNAL_ONLY",
    "EXTERNAL_SESSION",
    "UNPROVEN",
})

WORK_STATE_ALLOWED = frozenset({
    "IDLE",
    "WAITING_FOR_ASSIGNMENT",
    "ASSIGNED_PENDING_ACCEPTANCE",
    "EXECUTING",
    "BLOCKED_AWAITING_SYSTEM",
    "BUSY",
    "STALE_CLAIM",
    "SIGNED_OUT",
    "EXTERNAL_WORK",
    "UNKNOWN",
})

ROUTE_STATE_ALLOWED = frozenset({
    "AUTO_ROUTABLE",
    "NOT_ROUTABLE",
    "EXTERNAL_ONLY",
    "PROBE_PENDING",
    "STALE_CLAIM",
    "DISCOVERED_UNVERIFIED",
    "UNKNOWN",
})

AVAILABILITY_ALLOWED = frozenset({
    "AVAILABLE",
    "BUSY",
    "OFFLINE",
    "UNKNOWN",
    "UNAVAILABLE",
})

# Strict precedence (highest first) for presence_state selection
PRESENCE_PRECEDENCE = (
    "EXTERNAL_SESSION",  # external packet wins for that seat
    "ABSENT",            # explicit signed-out
    "PRESENT",           # signed current present
    "EXPIRED",           # was present, lease expired
    "STALE",             # stale transition from prior present/bound
    "UNVERIFIED",        # signature missing/invalid
    "UNPROVEN",          # declared but unproven
    "UNKNOWN",           # insufficient evidence — NEVER coerce to OFFLINE
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def _atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(raw)
    os.replace(tmp, path)


def _current(expiry: str | None) -> bool:
    if not expiry:
        return False
    try:
        return datetime.fromisoformat(str(expiry).replace("Z", "+00:00")) > datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


def _clamp(value: str, allowed: frozenset[str], default: str) -> str:
    v = str(value or "").upper()
    return v if v in allowed else default


def load_external_presence(repo: Path) -> dict[str, dict[str, Any]]:
    """Read external presence packets into seat→packet map (same projection)."""
    root = repo / ".ai-os" / "state" / "external-presence"
    out: dict[str, dict[str, Any]] = {}
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.json")):
        data = _load(path, {})
        seat = str(data.get("seat") or data.get("seat_id") or "").upper()
        if seat not in COUNCIL_SEATS:
            continue
        schema = str(data.get("schema") or "")
        mode = str(data.get("mode") or data.get("execution_mode") or "").upper()
        if schema not in {
            "raios.external-presence-packet.v1",
            "raios.external-session-presence.v1",
        } and mode not in {"EXTERNAL_SESSION", "EXTERNAL_ONLY"}:
            # Still accept explicit external packets with seat + mode
            if not mode.startswith("EXTERNAL"):
                continue
        out[seat] = {
            **data,
            "seat": seat,
            "source_path": str(path),
            "mode": mode or "EXTERNAL_SESSION",
        }
    return out


def _derive_presence_state(row: dict[str, Any], external: dict[str, Any] | None) -> tuple[str, str]:
    """Return (presence_state, reason) under strict precedence."""
    if external:
        mode = str(external.get("mode") or "EXTERNAL_SESSION").upper()
        if mode == "EXTERNAL_ONLY":
            return "EXTERNAL_SESSION", "EXTERNAL_ONLY_PACKET"
        return "EXTERNAL_SESSION", "EXTERNAL_SESSION_PACKET"

    raw = str(row.get("presence_state") or "UNKNOWN").upper()
    sig_ok = row.get("presence_signature_valid") is True
    present = row.get("present") is True
    lease_ok = _current(row.get("presence_lease_expires_at"))

    if raw == "ABSENT":
        return "ABSENT", "SIGNED_ABSENT" if sig_ok else "ABSENT_CLAIM"

    if present and sig_ok and lease_ok:
        return "PRESENT", "SIGNED_CURRENT_PRESENT"

    if present and sig_ok and not lease_ok and row.get("presence_lease_expires_at"):
        return "EXPIRED", "PRESENCE_LEASE_EXPIRED"

    if raw == "PRESENT" and not sig_ok:
        return "UNVERIFIED", "PRESENT_WITHOUT_VALID_SIGNATURE"

    if row.get("binding_current") and not (present and sig_ok and lease_ok):
        return "STALE", "STALE_BINDING_WITHOUT_CURRENT_SIGNED_PRESENCE"

    if raw in PRESENCE_STATE_ALLOWED and raw not in {"PRESENT", "ABSENT"}:
        return raw, "ROUTE_DECLARED"

    if row.get("process_candidate") and not (present and sig_ok):
        return "UNKNOWN", "PROCESS_WITHOUT_SIGNED_PRESENCE"

    if raw in {"", "UNKNOWN"} or raw not in PRESENCE_STATE_ALLOWED:
        return "UNKNOWN", "INSUFFICIENT_LIVE_EVIDENCE"

    return _clamp(raw, PRESENCE_STATE_ALLOWED, "UNKNOWN"), "NORMALIZED"


def _derive_reachability(presence_state: str, row: dict[str, Any], external: dict[str, Any] | None) -> str:
    if external:
        if external.get("reachable") is True or str(external.get("reachability") or "").upper() in {
            "REACHABLE", "EXTERNAL_REACHABLE",
        }:
            return "EXTERNAL_REACHABLE"
        if external.get("reachable") is False:
            return "UNREACHABLE"
        return "EXTERNAL_REACHABLE"
    if presence_state == "PRESENT" and row.get("consumer_current"):
        return "REACHABLE"
    if presence_state == "ABSENT":
        return "UNREACHABLE"
    if row.get("process_candidate") or row.get("probe_pending"):
        return "UNKNOWN"
    return "UNKNOWN"


def _derive_execution_location(seat: str, presence_state: str, external: dict[str, Any] | None, row: dict[str, Any]) -> str:
    if external:
        mode = str(external.get("mode") or "EXTERNAL_SESSION").upper()
        if mode == "EXTERNAL_ONLY":
            return "EXTERNAL_ONLY"
        return "EXTERNAL_SESSION"
    if seat == "C6" and presence_state == "EXTERNAL_SESSION":
        return "EXTERNAL_SESSION"
    if row.get("auto_routable") or presence_state == "PRESENT":
        return "INTERNAL_LOCAL"
    return "UNPROVEN"


def _derive_work_state(row: dict[str, Any], activity: dict[str, Any] | None, presence_state: str) -> str:
    if presence_state == "EXTERNAL_SESSION":
        ext_work = str((activity or {}).get("work_phase") or "").upper()
        return "EXTERNAL_WORK" if ext_work else "EXTERNAL_WORK"
    if presence_state == "ABSENT":
        return "SIGNED_OUT"
    phase = str((activity or {}).get("work_phase") or row.get("work_state") or "").upper()
    mapping = {
        "WAITING_FOR_ASSIGNMENT": "WAITING_FOR_ASSIGNMENT",
        "ASSIGNED_PENDING_ACCEPTANCE": "ASSIGNED_PENDING_ACCEPTANCE",
        "EXECUTING": "EXECUTING",
        "BLOCKED_AWAITING_SYSTEM": "BLOCKED_AWAITING_SYSTEM",
        "STALE_TASK_CLAIM_REQUIRES_RECONCILIATION": "STALE_CLAIM",
        "SIGNED_OUT": "SIGNED_OUT",
        "AVAILABLE_NOT_EXECUTION_READY": "IDLE",
    }
    if phase in mapping:
        return mapping[phase]
    avail = str((activity or {}).get("availability") or "").upper()
    if avail == "BUSY":
        return "BUSY"
    if row.get("auto_routable"):
        return "IDLE"
    return "UNKNOWN"


def _derive_route_state(row: dict[str, Any], presence_state: str, external: dict[str, Any] | None) -> str:
    if external:
        return "EXTERNAL_ONLY"
    if row.get("auto_routable"):
        return "AUTO_ROUTABLE"
    if row.get("probe_pending"):
        return "PROBE_PENDING"
    discovery = str(row.get("discovery_state") or "").upper()
    if discovery == "DISCOVERED_LIVE_UNVERIFIED":
        return "DISCOVERED_UNVERIFIED"
    if presence_state == "STALE":
        return "STALE_CLAIM"
    if presence_state in {"UNKNOWN", "UNPROVEN", "UNVERIFIED", "EXPIRED", "ABSENT"}:
        return "NOT_ROUTABLE"
    return "UNKNOWN"


def _derive_availability(
    presence_state: str,
    row: dict[str, Any],
    activity: dict[str, Any] | None,
    external: dict[str, Any] | None,
) -> tuple[str, bool, str]:
    """Return (availability, execution_ready, reason).

    Rules:
    - process-without-signed-presence → not AVAILABLE
    - UNKNOWN != OFFLINE
    - BUSY != UNAVAILABLE
    """
    if external:
        claim = str(external.get("availability") or "UNKNOWN").upper()
        if claim == "BUSY":
            return "BUSY", False, "EXTERNAL_BUSY"
        if claim == "AVAILABLE" and presence_state == "EXTERNAL_SESSION":
            return "AVAILABLE", False, "EXTERNAL_AVAILABLE_NOT_INTERNAL_EXECUTION"
        if claim == "OFFLINE":
            return "OFFLINE", False, "EXTERNAL_OFFLINE"
        return "UNKNOWN", False, "EXTERNAL_INSUFFICIENT"

    if activity:
        avail = str(activity.get("availability") or "UNKNOWN").upper()
        ready = activity.get("execution_ready") is True
        # Guard: process discovery alone must not be AVAILABLE
        if row.get("process_candidate") and not row.get("auto_routable") and not (
            row.get("availability_claim_current") and str(row.get("availability_claim") or "").upper() == "AVAILABLE"
        ):
            if avail == "AVAILABLE" and not row.get("presence_signature_valid"):
                return "UNKNOWN", False, "PROCESS_WITHOUT_SIGNED_PRESENCE_NOT_AVAILABLE"
        if avail == "BUSY":
            return "BUSY", ready, "ACTIVITY_BUSY_NOT_UNAVAILABLE"
        if avail in AVAILABILITY_ALLOWED:
            return avail, ready, str(activity.get("reason") or "CLIENT_ACTIVITY")
        return "UNKNOWN", False, "ACTIVITY_UNKNOWN"

    if presence_state == "ABSENT":
        return "OFFLINE", False, "SIGNED_ABSENT"
    if presence_state == "PRESENT" and row.get("auto_routable"):
        return "AVAILABLE", True, "SIGNED_BOUND_CONSUMER"
    if row.get("process_candidate") and presence_state == "UNKNOWN":
        return "UNKNOWN", False, "PROCESS_WITHOUT_SIGNED_PRESENCE_NOT_AVAILABLE"
    if presence_state in {"UNKNOWN", "UNPROVEN", "UNVERIFIED", "EXPIRED", "STALE"}:
        return "UNKNOWN", False, "UNKNOWN_NE_OFFLINE"
    return "UNKNOWN", False, "DEFAULT_UNKNOWN"


def build_member_row(
    seat: str,
    route_row: dict[str, Any] | None,
    activity_row: dict[str, Any] | None,
    external: dict[str, Any] | None,
    seat_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = route_row or {"seat": seat}
    seat_spec = seat_spec or {}
    presence_state, presence_reason = _derive_presence_state(row, external)
    presence_state = _clamp(presence_state, PRESENCE_STATE_ALLOWED, "UNKNOWN")
    reachability = _clamp(
        _derive_reachability(presence_state, row, external),
        REACHABILITY_ALLOWED,
        "UNKNOWN",
    )
    execution_location = _clamp(
        _derive_execution_location(seat, presence_state, external, row),
        EXECUTION_LOCATION_ALLOWED,
        "UNPROVEN",
    )
    work_state = _clamp(
        _derive_work_state(row, activity_row, presence_state),
        WORK_STATE_ALLOWED,
        "UNKNOWN",
    )
    route_state = _clamp(
        _derive_route_state(row, presence_state, external),
        ROUTE_STATE_ALLOWED,
        "UNKNOWN",
    )
    availability, execution_ready, avail_reason = _derive_availability(
        presence_state, row, activity_row, external,
    )
    availability = _clamp(availability, AVAILABILITY_ALLOWED, "UNKNOWN")

    # C6: never invent fake internal session when external mode active
    fake_internal = False
    if seat == "C6" and external:
        fake_internal = False
        session_id = external.get("session_id") or row.get("session_id")
        origin = external.get("origin_instance") or "EXTERNAL"
        actor_id = external.get("actor_id") or row.get("actor_id")
        device_id = external.get("device_id") or row.get("device_id")
    else:
        session_id = row.get("session_id")
        origin = row.get("origin_instance")
        actor_id = row.get("actor_id")
        device_id = row.get("device_id")

    stale_transition = presence_state in {"STALE", "EXPIRED"} or route_state == "STALE_CLAIM"

    current_tasks = list((activity_row or {}).get("current_tasks") or [])
    current_task = current_tasks[0] if current_tasks else None
    busy = work_state in {"EXECUTING", "ASSIGNED_PENDING_ACCEPTANCE", "BUSY", "BLOCKED_AWAITING_SYSTEM"}

    return {
        "seat": seat,
        "actor_role": row.get("actor_role") or seat_spec.get("actor_role"),
        "instance_role": row.get("instance_role") or seat_spec.get("instance_role"),
        "presence_state": presence_state,
        "presence_reason": presence_reason,
        "presence_state_allowed": sorted(PRESENCE_STATE_ALLOWED),
        "reachability": reachability,
        "execution_location": execution_location,
        "work_state": work_state,
        "busy": busy,
        "current_task": current_task,
        "current_tasks": current_tasks,
        "route_state": route_state,
        "availability": availability,
        "availability_reason": avail_reason,
        "execution_ready": execution_ready,
        "actor_id": actor_id,
        "session_id": session_id,
        "origin_instance": origin,
        "device_id": device_id,
        "present": presence_state == "PRESENT",
        "auto_routable": row.get("auto_routable") is True and not external,
        "process_candidate": row.get("process_candidate") is True,
        "probe_pending": row.get("probe_pending") is True,
        "discovery_state": row.get("discovery_state"),
        "stale_transition": stale_transition,
        "external_mode": str(external.get("mode")).upper() if external else None,
        "external_packet_ref": (external or {}).get("source_path"),
        "fake_internal_session": fake_internal,
        "laws": {
            "UNKNOWN_NE_OFFLINE": True,
            "BUSY_NE_UNAVAILABLE": True,
            "PROCESS_WITHOUT_SIGNED_PRESENCE_NOT_AVAILABLE": True,
            "C6_EXTERNAL_NO_FAKE_INTERNAL_SESSION": seat != "C6" or not external or fake_internal is False,
        },
    }


def build_council_member_state(
    repo: Path,
    routes,
    activity_clients: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build C1–C12 projection and refresh `.ai-os/state/COUNCIL-MEMBER-STATE.json`.

    Pass ``activity_clients`` from ClientActivityView to avoid recursion; when omitted,
    projection uses route/external evidence only (no second registry).
    """
    repo = repo.resolve()
    seat_map = _load(repo / ".ai-os" / "mcp" / "SEAT-MAP.json", {"seats": {}})
    external = load_external_presence(repo)
    route_snap = routes.snapshot() if routes is not None else {"seats": []}
    route_by = {str(r.get("seat") or "").upper(): r for r in route_snap.get("seats", [])}
    activity_by = {
        str(r.get("seat") or "").upper(): r for r in (activity_clients or [])
    }

    members = []
    for seat in COUNCIL_SEATS:
        members.append(
            build_member_row(
                seat,
                route_by.get(seat),
                activity_by.get(seat),
                external.get(seat),
                (seat_map.get("seats") or {}).get(seat),
            )
        )

    payload = {
        "schema": "raios.council-member-state.v1",
        "generated_at": utc(),
        "canonical_coordination_source": "/api/client-activity",
        "COUNCIL_STATE_ENDPOINT": "/api/council-state",
        "COUNCIL_STATE_ENDPOINT_NOTE": (
            "Canonical unified council projection: presence, reachability, work state, "
            "current task(s), availability, and routing readiness."
        ),
        "pending_app_py_alias": None,
        "existing_related_endpoint": "/api/council",
        "second_registry_created": False,
        "presence_state_allowed": sorted(PRESENCE_STATE_ALLOWED),
        "precedence": list(PRESENCE_PRECEDENCE),
        "laws": [
            "UNKNOWN_NE_OFFLINE",
            "BUSY_NE_UNAVAILABLE",
            "PROCESS_WITHOUT_SIGNED_PRESENCE_NOT_AVAILABLE",
            "C6_EXTERNAL_SESSION_OR_EXTERNAL_ONLY_NO_FAKE_INTERNAL",
            "ONE_PROJECTION_NO_SECOND_REGISTRY",
        ],
        "members": members,
        "by_seat": {m["seat"]: m for m in members},
        "counts": {
            "PRESENT": sum(1 for m in members if m["presence_state"] == "PRESENT"),
            "ABSENT": sum(1 for m in members if m["presence_state"] == "ABSENT"),
            "UNKNOWN": sum(1 for m in members if m["presence_state"] == "UNKNOWN"),
            "EXTERNAL_SESSION": sum(1 for m in members if m["presence_state"] == "EXTERNAL_SESSION"),
            "AVAILABLE": sum(1 for m in members if m["availability"] == "AVAILABLE"),
            "BUSY": sum(1 for m in members if m["availability"] == "BUSY"),
            "OFFLINE": sum(1 for m in members if m["availability"] == "OFFLINE"),
        },
    }
    dump_path = repo / ".ai-os" / "state" / "COUNCIL-MEMBER-STATE.json"
    _atomic(dump_path, payload)
    payload["dump_path"] = str(dump_path)
    return payload


def refresh_council_member_state_dump(repo: Path, routes) -> Path:
    built = build_council_member_state(repo, routes)
    return Path(built["dump_path"])
