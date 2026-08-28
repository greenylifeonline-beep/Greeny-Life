#!/usr/bin/env python3
"""Cloud Adapter for raios.cross-host-packet.v1.

Maps onto existing MCP Gateway send_packet/ack_packet + nomadic lease/idempotency.
Not a bus. Not a ninth MCP tool. Not Repair RAIOS-CROSS-HOST-BRIDGE-V1.py.
Does not mint tokens, write WAL, or claim cross-host transport.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from raios_mcp.gateway import Gateway, GatewayError, write_envelope

SCHEMA = "raios.cross-host-packet.v1"
TARGETS = ("C1", "C2", "C5-PUBLIC", "C5-FOUNDER", "C6", "ALL")
LIVE_CLOUD_TARGETS = ("C2", "C5-PUBLIC")
JOB = "COMMAND_FABRIC_CLOUD_ADAPTER"
LAW = [
    "ENVELOPE_NE_BUS",
    "NO_ALTERNATE_CONTROL_PLANE",
    "NO_NINTH_MCP_TOOL",
    "ACK_IS_A_NEW_PACKET_NEVER_A_MOVE",
    "EXPORTED_NOT_TRANSPORTED_NE_CONNECTION",
    "C5_FOUNDER_FAIL_CLOSED_UNTIL_PROVEN",
    "SECRET_NE_IN_GIT_LOG_PACKET",
]


class AdapterError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(packet: dict[str, Any]) -> str:
    body = {k: packet[k] for k in packet if k != "signature"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def content_hash_of(packet: dict[str, Any]) -> str:
    payload = packet.get("payload") if isinstance(packet.get("payload"), dict) else {}
    return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))


def sign(packet: dict[str, Any], token: str) -> str:
    if not token:
        raise AdapterError("UNAUTHENTICATED", "missing token")
    return hmac.new(token.encode("utf-8"), canonical(packet).encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(packet: dict[str, Any], token: str) -> None:
    expected = sign(packet, token)
    got = str(packet.get("signature") or "")
    if not got or not hmac.compare_digest(expected, got):
        raise AdapterError("INVALID_SIGNATURE", "hmac mismatch")


def _parse_dt(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    rec = datetime.fromisoformat(text)
    if rec.tzinfo is None:
        rec = rec.replace(tzinfo=timezone.utc)
    return rec


class CrossHostAdapter:
    """Verify + route a cross-host packet through existing keepers."""

    def __init__(
        self,
        gateway: Gateway,
        token_by_actor: dict[str, str] | None = None,
        leases: Any = None,
        worker_id: str = "C2-OBS",
    ) -> None:
        self.gateway = gateway
        self.token_by_actor = dict(token_by_actor or {})
        self.leases = leases
        self.worker_id = worker_id
        self._nonces: set[str] = set()
        self._acks: set[str] = set()

    def build(
        self,
        *,
        actor: str,
        target: str,
        payload: dict[str, Any],
        token: str,
        from_host: str,
        from_tree: str,
        to_host: str,
        to_tree: str,
        return_path: str,
        expires_at: str = "2099-01-01T00:00:00+00:00",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        packet = {
            "schema": SCHEMA,
            "message_id": "MSG-" + uuid.uuid4().hex[:16],
            "correlation_id": "corr-" + uuid.uuid4().hex[:12],
            "packet_id": "pkt-" + uuid.uuid4().hex[:12],
            "actor": actor,
            "target": target,
            "from_host": from_host,
            "from_tree": from_tree,
            "to_host": to_host,
            "to_tree": to_tree,
            "intent": "CROSS_HOST_CHALLENGE",
            "created_at": utc(),
            "expires_at": expires_at,
            "nonce": uuid.uuid4().hex,
            "payload": payload,
            "return_path": return_path,
            "requires_ack": True,
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

    def ingest(self, packet: dict[str, Any], token: str | None, head: str) -> dict[str, Any]:
        self._validate_schema(packet)
        target = str(packet["target"])
        if target == "C5-FOUNDER":
            return self._blocked("BLOCKED_ROUTING", "C5-FOUNDER fail-closed until AG 8876 is proven")
        if target == "C6":
            return self._blocked("ABSENT", "C6 is not seated on this Cloud host")
        if not str(packet.get("return_path") or "").strip():
            raise AdapterError("MISSING_RETURN_PATH", "return_path required")
        if self.leases is not None:
            held = self.leases.holder(JOB)
            if held and held != self.worker_id:
                raise AdapterError("LEASE_HELD", f"holder={held}")
            claimed = self.leases.claim(JOB, self.worker_id)
            if not claimed.get("ok"):
                raise AdapterError(str(claimed.get("reason") or "LEASE_HELD"), "lease claim failed")
        if _parse_dt(str(packet["expires_at"])) <= datetime.now(timezone.utc):
            raise AdapterError("EXPIRED", "packet expired")
        nonce = str(packet["nonce"])
        if nonce in self._nonces or packet["packet_id"] in self._nonces:
            raise AdapterError("REPLAY", "nonce or packet_id already used")
        if packet["packet_id"] == packet["correlation_id"]:
            raise AdapterError("INVALID_PACKET", "packet_id must not equal correlation_id")
        if packet.get("content_hash") != content_hash_of(packet):
            raise AdapterError("INVALID_SCHEMA", "content_hash mismatch")
        if not token:
            raise AdapterError("UNAUTHENTICATED", "missing token")
        actor = self.gateway.authenticate(token)
        if actor.actor_id != str(packet["actor"]):
            raise AdapterError("UNAUTHENTICATED", "actor does not match token")
        verify_signature(packet, token)
        self._nonces.add(nonce)
        self._nonces.add(str(packet["packet_id"]))
        if target == "ALL":
            return self._broadcast(packet, token, head)
        return self._deliver(packet, actor, head)

    def ack(self, packet: dict[str, Any], token: str, head: str, causation_id: str) -> dict[str, Any]:
        if causation_id in self._acks:
            raise AdapterError("DUPLICATE_ACK", "causation already acked")
        actor = self.gateway.authenticate(token)
        env = write_envelope(actor, head, {"target_packet_id": causation_id, "status": "READ"})
        rec = self.gateway.call(actor, "ack_packet", env)
        self._acks.add(causation_id)
        return {
            "ok": True,
            "status": "LOCAL_ONLY",
            "ack_packet_id": rec.get("packet_id"),
            "causation_id": causation_id,
            "correlation_id": packet.get("correlation_id"),
            "moved": False,
            "receipt_sha256": rec.get("receipt_sha256"),
            "gl005_proven": False,
        }

    def _deliver(self, packet: dict[str, Any], actor: Any, head: str) -> dict[str, Any]:
        target = str(packet["target"])
        if target == "C5-PUBLIC":
            return {
                "ok": True,
                "status": "LOCAL_ONLY",
                "target": target,
                "message_id": packet["message_id"],
                "correlation_id": packet["correlation_id"],
                "packet_id": packet["packet_id"],
                "auth": "none-public-lane",
                "ack": None,
                "ack_reason": "C5 /api/chat is HTTP response, not MCP ACK unless wrapped",
                "return_path": packet["return_path"],
                "keeper": "scripts/ai-os/raios_c5_screen.py",
                "transport": "HTTP 127.0.0.1:8765/api/chat",
                "exported_not_transported": True,
                "cross_host_round_trip_proven": False,
                "wal_written": False,
                "gl005_proven": False,
                "law": LAW,
            }
        if target == "C1":
            return self._blocked("BLOCKED_AUTH", "live C1 MCP grant absent on this host")
        env = write_envelope(
            actor,
            head,
            {
                "to": ["C2" if target == "C2" else target],
                "text": f"{packet['intent']} {packet['message_id']}",
                "correlation_id": packet["correlation_id"],
            },
        )
        sent = self.gateway.call(actor, "send_packet", env)
        return {
            "ok": True,
            "status": "LOCAL_ONLY",
            "target": target,
            "message_id": packet["message_id"],
            "correlation_id": packet["correlation_id"],
            "packet_id": packet["packet_id"],
            "send_packet_id": sent.get("packet_id"),
            "send_receipt_sha256": sent.get("receipt_sha256"),
            "auth": "mcp-bearer-hmac",
            "return_path": packet["return_path"],
            "exported_not_transported": True,
            "cross_host_round_trip_proven": False,
            "wal_written": False,
            "gl005_proven": False,
            "ninth_mcp_tool": False,
            "new_bus_created": False,
            "law": LAW,
        }

    def _broadcast(self, packet: dict[str, Any], token: str, head: str) -> dict[str, Any]:
        deliveries = []
        for target in TARGETS:
            if target == "ALL":
                continue
            one = dict(packet)
            one["target"] = target
            one["packet_id"] = "pkt-" + uuid.uuid4().hex[:12]
            one["nonce"] = uuid.uuid4().hex
            one["content_hash"] = content_hash_of(one)
            one["signature"] = sign(one, token)
            try:
                rec = self.ingest(one, token, head)
            except AdapterError as err:
                rec = {"ok": False, "target": target, "status": "UNPROVEN", "code": err.code, "detail": err.detail}
            deliveries.append(rec)
        return {
            "ok": False,
            "status": "UNPROVEN",
            "target": "ALL",
            "message_id": packet["message_id"],
            "correlation_id": packet["correlation_id"],
            "deliveries": deliveries,
            "reason": "ALL is per-target receipts; C5-FOUNDER fail-closed; C6 ABSENT; C1 BLOCKED_AUTH",
            "file_copy": False,
            "cross_host_round_trip_proven": False,
            "gl005_proven": False,
            "law": LAW,
        }

    def _validate_schema(self, packet: dict[str, Any]) -> None:
        if packet.get("schema") != SCHEMA:
            raise AdapterError("INVALID_SCHEMA", "schema must be raios.cross-host-packet.v1")
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
        missing = [k for k in required if k not in packet]
        if missing:
            raise AdapterError("INVALID_SCHEMA", "missing " + ",".join(missing))
        if packet["target"] not in TARGETS:
            raise AdapterError("INVALID_SCHEMA", "unknown target")
        if not isinstance(packet.get("payload"), dict):
            raise AdapterError("INVALID_SCHEMA", "payload must be object")

    def _blocked(self, status: str, reason: str) -> dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "reason": reason,
            "cross_host_round_trip_proven": False,
            "wal_written": False,
            "gl005_proven": False,
            "law": LAW,
        }


def issuer_manifest() -> dict[str, Any]:
    return {
        "schema": "raios.command-fabric.issuer.v1",
        "who": "C1/owner",
        "not_this_c2": True,
        "store": ".ai-os/mcp/tokens.local.json",
        "gitignored": True,
        "example_placeholders_only": ".ai-os/mcp/ACTORS.example.json",
        "preferred": "OAuth/OIDC when ChatGPT Apps remote MCP is registered",
        "mechanism": "scoped bearer grant with expires_at; HMAC-SHA256 for cross-host packet signature",
        "never": ["git", "logs", "packets", "reports with values"],
        "health_remote_c2_ready_hardcoded_false": True,
        "gl005_proven": False,
    }
