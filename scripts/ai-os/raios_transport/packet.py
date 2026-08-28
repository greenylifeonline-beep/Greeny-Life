"""raios.cross-host-packet.v1 HMAC helpers. Same semantics as the existing adapter."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = "raios.cross-host-packet.v1"
TARGETS = ("C1", "C2", "C5-PUBLIC", "C5-FOUNDER", "C6", "ALL")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(packet: dict[str, Any]) -> str:
    body = {k: packet[k] for k in packet if k != "signature"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def content_hash_of(packet: dict[str, Any]) -> str:
    payload = packet.get("payload") if isinstance(packet.get("payload"), dict) else {}
    return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))


def sign(packet: dict[str, Any], token: str) -> str:
    if not token:
        raise ValueError("UNAUTHENTICATED")
    return hmac.new(token.encode("utf-8"), canonical(packet).encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(packet: dict[str, Any], token: str) -> None:
    expected = sign(packet, token)
    got = str(packet.get("signature") or "")
    if not got or not hmac.compare_digest(expected, got):
        raise ValueError("INVALID_SIGNATURE")


def parse_dt(value: str) -> datetime:
    rec = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if rec.tzinfo is None:
        rec = rec.replace(tzinfo=timezone.utc)
    return rec


def deterministic_msg_id(kind: str, packet_id: str, correlation_id: str) -> str:
    return f"raios:{kind}:{packet_id}:{correlation_id}"


def ensure_hmac_token(path: Path, explicit: str = "") -> str:
    env = os.environ.get("RAIOS_FABRIC_HMAC_TOKEN") or explicit
    if env:
        return env.strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    token = secrets.token_hex(32)
    path.write_text(token, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return token


def build_packet(
    *,
    token: str,
    actor: str,
    target: str,
    payload: dict[str, Any],
    sender_runtime: str,
    receiver_runtime: str,
    role_id: str,
    expires_seconds: int = 300,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    corr = "corr-" + uuid.uuid4().hex[:12]
    packet: dict[str, Any] = {
        "schema": SCHEMA,
        "message_id": "MSG-" + uuid.uuid4().hex[:16],
        "correlation_id": corr,
        "packet_id": "pkt-" + uuid.uuid4().hex[:12],
        "actor": actor,
        "target": target,
        "from_host": "AG",
        "from_tree": "TREE-001",
        "to_host": "AG",
        "to_tree": "TREE-001",
        "intent": "RETURN_RUNTIME_IDENTITY",
        "created_at": now.isoformat(),
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=expires_seconds)).isoformat(),
        "nonce": uuid.uuid4().hex,
        "payload": payload,
        "return_path": "results/" + corr,
        "requires_ack": True,
        "role_id": role_id,
        "runtime_id": sender_runtime,
        "sender_runtime": sender_runtime,
        "receiver_runtime": receiver_runtime,
        "delivery_attempt": 1,
        "auth_context": {
            "method": "mcp-bearer-hmac",
            "actor_id": actor,
            "token_present": True,
        },
    }
    if extra:
        packet.update(extra)
    packet["content_hash"] = content_hash_of(packet)
    packet["signature"] = sign(packet, token)
    return packet


def validate_packet(packet: dict[str, Any], token: str, allowed_actors: set[str], seen: set[str] | None = None) -> str:
    if packet.get("schema") != SCHEMA:
        return "INVALID_SCHEMA"
    required = (
        "message_id",
        "correlation_id",
        "packet_id",
        "actor",
        "target",
        "from_host",
        "from_tree",
        "to_host",
        "to_tree",
        "created_at",
        "expires_at",
        "nonce",
        "payload",
        "content_hash",
        "signature",
        "return_path",
        "requires_ack",
    )
    if any(k not in packet for k in required):
        return "MISSING_FIELDS"
    if packet["packet_id"] == packet["correlation_id"]:
        return "INVALID_PACKET"
    if packet.get("target") not in TARGETS:
        return "INVALID_SCHEMA"
    if not isinstance(packet.get("payload"), dict):
        return "INVALID_SCHEMA"
    if packet.get("content_hash") != content_hash_of(packet):
        return "INVALID_SCHEMA"
    if packet.get("actor") not in allowed_actors:
        return "UNAUTHORIZED_ACTOR"
    try:
        if parse_dt(str(packet.get("expires_at"))) <= datetime.now(timezone.utc):
            return "EXPIRED"
    except Exception:
        return "EXPIRED"
    used = seen or set()
    if packet["nonce"] in used or packet["packet_id"] in used:
        return "REPLAY"
    if not token:
        return "UNAUTHENTICATED"
    try:
        verify_signature(packet, token)
    except Exception:
        return "INVALID_SIGNATURE"
    return "OK"
