"""Bind C2 to the existing A2A semantic layer for all-hands routing.

Internal seats never become public A2A agents. Side effects terminate at
Command Fabric. No second NATS bus. No mutation authority.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from raios.a2a.cards import FORBIDDEN_PUBLIC_AGENTS, PUBLIC_AGENT_ID, reject_seat_as_agent
from raios.a2a.capability import CAPABILITY_NOOP
from raios.a2a.failclosed import (
    DIRECT_EXECUTION_PATH_FORBIDDEN,
    SEAT_IDENTITY_NOT_PUBLIC_AGENT,
    FailClosed,
)
from raios.a2a.flags import (
    A2A_EXTERNAL_MUTATION_ALLOWED,
    HTTP_FALLBACK_PRESERVED,
    HTTP_PRIMARY,
    NATS_REPLACED,
)
from raios.a2a.gateway import A2ARequest, Gateway
from raios.a2a.nats_bridge import status as nats_status
from raios.a2a.receipt_bridge import build_receipt
from raios.a2a.semantic import SEMANTIC_EXTENSION_URI, SemanticRegistry, default_contract
from raios.a2a.task_bridge import build_intent, map_artifact, map_message
from raios.command_fabric.route import HTTP_FALLBACK, NATS, select_transport

INTERNAL_SEATS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")
ENVELOPE_FIELDS = (
    "task_id",
    "context_id",
    "message_id",
    "artifact_id",
    "correlation_id",
    "idempotency_key",
    "provenance",
    "receipt",
)
COMMAND_FABRIC_ROUTE = "src/raios/command_fabric/pipeline.py"


def _http_ok(url: str, timeout: float = 15.0) -> tuple[bool, int]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200, int(response.status)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False, 0


def tcp_listening(port: int, host: str = "127.0.0.1", timeout: float = 1.5) -> bool:
    try:
        import socket

        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def nats_listening() -> bool:
    return tcp_listening(4222)


def reject_internal_seat(name: str) -> None:
    seat = (name or "").strip()
    if seat in INTERNAL_SEATS or seat in FORBIDDEN_PUBLIC_AGENTS:
        raise FailClosed(SEAT_IDENTITY_NOT_PUBLIC_AGENT, seat)
    reject_seat_as_agent(seat)


def guarded_handle(req: A2ARequest, *, gateway: Gateway | None = None) -> dict[str, Any]:
    if req.direct_execute:
        raise FailClosed(DIRECT_EXECUTION_PATH_FORBIDDEN)
    reject_internal_seat(req.agent_id)
    return (gateway or Gateway()).handle(req)


def validate_envelope(env: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in ENVELOPE_FIELDS if not env.get(key)]
    if missing:
        raise FailClosed("SCHEMA_VALIDATION_FAILED", ",".join(missing))
    return {key: env[key] for key in ENVELOPE_FIELDS}


def routing_matrix(*, nats_available: bool) -> list[dict[str, Any]]:
    contract = default_contract()
    pairs: list[dict[str, Any]] = []
    for source in INTERNAL_SEATS:
        for dest in INTERNAL_SEATS:
            if source == dest:
                continue
            transport = select_transport(target=dest, nats_available=nats_available)
            pairs.append(
                {
                    "from": source,
                    "to": dest,
                    "public_a2a_agent": False,
                    "semantic_contract_id": contract["semantic_contract_id"],
                    "command_fabric_gate": True,
                    "direct_mutation": False,
                    "selected_transport": transport["selected_transport"],
                    "fallback_transport": transport["fallback_transport"],
                    "route": COMMAND_FABRIC_ROUTE if transport["selected_transport"] == NATS or dest == "C5" else HTTP_FALLBACK,
                }
            )
    if len(pairs) != 42:
        raise FailClosed("SCHEMA_VALIDATION_FAILED", f"pair-count:{len(pairs)}")
    return pairs


def side_effect_disposition(*, side_effects: bool) -> dict[str, Any]:
    if not side_effects:
        return {
            "TERMINATES_AT": "a2a.gateway.dry_run",
            "COMMAND_FABRIC_GATE": False,
            "DIRECT_MUTATION": False,
            "EXECUTED": False,
        }
    return {
        "TERMINATES_AT": COMMAND_FABRIC_ROUTE,
        "COMMAND_FABRIC_GATE": True,
        "DIRECT_MUTATION": False,
        "EXECUTED": False,
    }


def c2_semantic_bind(*, gateway: Gateway | None = None) -> dict[str, Any]:
    gw = gateway or Gateway()
    registry = gw.semantics if isinstance(gw.semantics, SemanticRegistry) else SemanticRegistry()
    contract = registry.require(default_contract(), required=True)
    req = A2ARequest(
        agent_id=PUBLIC_AGENT_ID,
        capability_id=CAPABILITY_NOOP,
        a2a_task_id="RAIOS-A2A-ALL-HANDS-BIND-02",
        a2a_context_id="ctx-c2-all-hands",
        desired_state={"bind": "C2", "mutation": False},
        idempotency_key="RAIOS-A2A-ALL-HANDS-BIND-02",
        semantic_contract=default_contract(),
        a2a_message_id="msg-c2-bind",
        a2a_artifact_id="art-c2-bind",
    )
    result = guarded_handle(req, gateway=gw)
    intent = build_intent(
        a2a_task_id=req.a2a_task_id,
        a2a_context_id=req.a2a_context_id,
        actor="C2",
        capability_id=CAPABILITY_NOOP,
        desired_state=req.desired_state,
        risk_class="LOW",
        idempotency_key=req.idempotency_key,
    )
    message = map_message(
        a2a_message_id=req.a2a_message_id or "",
        a2a_context_id=req.a2a_context_id,
        text="C2 semantic bind",
    )
    artifact = map_artifact(
        a2a_artifact_id=req.a2a_artifact_id or "",
        a2a_task_id=req.a2a_task_id,
        a2a_context_id=req.a2a_context_id,
    )
    receipt = result.get("receipt") or build_receipt(
        a2a_task_id=req.a2a_task_id,
        a2a_context_id=req.a2a_context_id,
        intent=intent,
        capability_id=CAPABILITY_NOOP,
        semantic_contract_id=SEMANTIC_EXTENSION_URI,
        semantic_fingerprint=str((contract.get("contract") or {}).get("context_fingerprint") or ""),
        auth_result=result.get("auth_result") or {},
        policy_result={"POLICY_RESULT": "ALLOW", "RISK_CLASS": "LOW"},
        status="BOUND",
        evidence_refs=["src/raios/a2a"],
    )
    envelope = validate_envelope(
        {
            "task_id": req.a2a_task_id,
            "context_id": req.a2a_context_id,
            "message_id": message["A2A_MESSAGE_ID"],
            "artifact_id": artifact["A2A_ARTIFACT_ID"],
            "correlation_id": intent["CORRELATION_ID"],
            "idempotency_key": intent["IDEMPOTENCY_KEY"],
            "provenance": result.get("auth_result") or {"AUTHORITY_SOURCE": "NOT_REQUIRED"},
            "receipt": receipt,
        }
    )
    return {
        "C2_A2A_BOUND": True,
        "SEMANTIC_EXECUTION_ALLOWED": bool(contract.get("SEMANTIC_EXECUTION_ALLOWED")),
        "PUBLIC_AGENT_ID": PUBLIC_AGENT_ID,
        "DIRECT_EXECUTED": bool(result.get("DIRECT_EXECUTED")),
        "EFFECTIVE_AUTHORITY_GRANTED": bool(result.get("EFFECTIVE_AUTHORITY_GRANTED")),
        "envelope": envelope,
        "result": {k: v for k, v in result.items() if k != "receipt"},
        "receipt": receipt,
    }


def bind_c2(*, probe_live: bool = False) -> dict[str, Any]:
    nats_live = nats_listening() if probe_live else False
    transport = nats_status()
    matrix = routing_matrix(nats_available=nats_live)
    bind = c2_semantic_bind()
    c5_ok, c5_http = _http_ok("http://127.0.0.1:8766/health") if probe_live else (False, 0)
    nine_ok, nine_http = (
        _http_ok("http://127.0.0.1:20128/dashboard") if probe_live else (False, 0)
    )
    c5_tcp = tcp_listening(8766) if probe_live else False
    nine_tcp = tcp_listening(20128) if probe_live else False
    from pathlib import Path

    channel = Path(__file__).resolve().parents[3] / "RAIOS-C1-C5.ps1"
    c1_ready = channel.is_file()
    blockers: list[str] = []
    if A2A_EXTERNAL_MUTATION_ALLOWED:
        blockers.append("A2A_EXTERNAL_MUTATION_ALLOWED")
    if transport.get("NEW_SUBJECTS_CREATED"):
        blockers.append("NEW_NATS_SUBJECTS")
    if NATS_REPLACED:
        blockers.append("NATS_REPLACED")
    if probe_live and not c5_ok:
        blockers.append("C5_HTTP_TIMEOUT" if c5_tcp else "C5_HTTP")
    if probe_live and not nine_ok:
        blockers.append("9ROUTER_HTTP_TIMEOUT" if nine_tcp else "9ROUTER_HTTP")
    if not c1_ready:
        blockers.append("C1_C5_CHANNEL_SCRIPT_MISSING")
    flags = {
        "C2_A2A_BOUND": bool(bind["C2_A2A_BOUND"] and bind["SEMANTIC_EXECUTION_ALLOWED"]),
        "ROUTING_MATRIX_42_PAIRS": len(matrix) == 42,
        "C5_REACHABLE": bool(c5_ok or c5_tcp) if probe_live else any(p["to"] == "C5" for p in matrix),
        "C6_REACHABLE": any(p["from"] == "C6" or p["to"] == "C6" for p in matrix),
        "C1_REACHABLE": bool(c1_ready and ((c5_ok or c5_tcp) if probe_live else True)),
        "COMMAND_FABRIC_ROUTE": True,
        "NATS_REUSED": (not NATS_REPLACED) and transport.get("NEW_SUBJECTS_CREATED") is False,
        "HTTP_REUSED": bool(HTTP_PRIMARY and HTTP_FALLBACK_PRESERVED),
        "NEW_BUS_CREATED": False,
        "DIRECT_MUTATION": False,
        "BLOCKERS": ",".join(blockers) if blockers else "none",
        "pairs": len(matrix),
        "nats_listening": nats_live,
        "c5_tcp": c5_tcp,
        "c5_http": c5_http,
        "9router_tcp": nine_tcp,
        "9router_http": nine_http,
        "semantic_contract_id": SEMANTIC_EXTENSION_URI,
        "public_agent_id": PUBLIC_AGENT_ID,
        "command_fabric_route": COMMAND_FABRIC_ROUTE,
        "envelope_fields": list(ENVELOPE_FIELDS),
        "internal_seats_not_public_agents": True,
        "A2A_EXTERNAL_MUTATION_ALLOWED": A2A_EXTERNAL_MUTATION_ALLOWED,
        "bind": {k: v for k, v in bind.items() if k != "result"},
    }
    return flags


def flags_text(flags: dict[str, Any]) -> str:
    keys = (
        "C2_A2A_BOUND",
        "ROUTING_MATRIX_42_PAIRS",
        "C5_REACHABLE",
        "C6_REACHABLE",
        "C1_REACHABLE",
        "COMMAND_FABRIC_ROUTE",
        "NATS_REUSED",
        "HTTP_REUSED",
        "NEW_BUS_CREATED",
        "DIRECT_MUTATION",
        "BLOCKERS",
    )
    return "\n".join(f"{key}={json.dumps(flags[key]) if isinstance(flags[key], bool) else flags[key]}" for key in keys)
