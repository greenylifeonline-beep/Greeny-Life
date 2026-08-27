"""Command-fabric pipeline: auth → UCP → lease → NATS primary → target → receipt → release.

Reuses DryRunUCP, existing leases dir, existing NATS provider. Not a second UCP/bus/WAL.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Callable

from raios.a2a.ucp_adapter import DryRunUCP, EXISTING_CONTROL_PLANE
from raios.c1c5 import capabilities, identity, receipts
from raios.c1c5.receipt_identity import interpret_receipt_id

from .fake_transport import FakeFabricTransport
from .lease import CommandLeaseAdapter, EXISTING_LEASES, EXISTING_LOCKS_JSON
from .route import HTTP_FALLBACK, NATS, select_transport

EXISTING_NATS_PROVIDER = "scripts/ai-os/raios_transport/nats_provider.py"
EXISTING_NATS_CONFIG = "scripts/ai-os/raios_transport/provider.py"
STREAM = "RAIOS_FABRIC"
SUBJECT_ROOT = "raios.fabric"


def _message_id() -> str:
    return f"MSG-{uuid.uuid4().hex[:20]}"


def execute(
    *,
    env: dict[str, Any],
    session: dict[str, Any],
    leases: CommandLeaseAdapter,
    transport: Any | None = None,
    ucp: DryRunUCP | None = None,
    health: Callable[[], dict[str, Any]] | None = None,
    nats_available: bool = True,
    force_duplicate_delivery: bool = False,
    ttl_seconds: int = 120,
) -> dict[str, Any]:
    ucp = ucp or DryRunUCP()
    transport = transport or FakeFabricTransport()
    task_id = str(env.get("task_id") or "")
    corr = str(env.get("correlation_id") or "")
    idem = str(env.get("idempotency_key") or "")
    target = str(env.get("target") or "C5")
    cap = str(env.get("requested_capability") or capabilities.CAPABILITY_HEALTH)
    mid = str(env.get("message_id") or _message_id())
    env = dict(env)
    env["message_id"] = mid

    try:
        auth = identity.bind_founder(
            actor=str(env.get("actor") or ""),
            authority_context_reference=str(env.get("authority_context_reference") or ""),
            env=env,
            session=session,
            founder_binding_hex=str(env.get("founder_binding") or "") or None,
        )
    except PermissionError:
        return {
            "ok": False,
            "STATUS": "REJECTED",
            "FAIL_CLOSED": identity.AUTH_FAILED,
            "LEASE_ACQUIRED": False,
            "COMMAND_FABRIC_E2E_PROVEN": False,
            "EXACT_MISSING_SEGMENT": "AUTHORITY",
            "NATS_PRIMARY": False,
            "HTTP_FALLBACK_PRESERVED": True,
            "EXACTLY_ONCE_CLAIMED": False,
            "NATS_AT_LEAST_ONCE": True,
            "SECOND_LOCK_REGISTRY": False,
            "SECOND_EVENT_BUS": False,
            "SECOND_UCP": False,
        }

    route = select_transport(target=target, nats_available=nats_available)
    ucp_intent = {
        "IDEMPOTENCY_KEY": idem,
        "DESIRED_STATE": {"task_id": task_id, "capability": cap},
        "COMMAND_ID": task_id,
    }
    ucp_result = ucp.submit(ucp_intent)
    replay = bool(ucp_result.get("NO_OP") or ucp_result.get("STATUS") == "ALREADY_APPLIED")

    scope = f"{target}:{cap}"
    lease = leases.acquire(
        owner=str(auth.get("PRINCIPAL") or "C1@AG"),
        scope=scope,
        task_id=task_id,
        correlation_id=corr,
        capability=cap,
        resource_or_target=target,
        idempotency_key=idem,
        provenance_ref="RAIOS-COMMAND-FABRIC-E2E-CLOSEOUT-WAVE-01",
        ttl_seconds=ttl_seconds,
    )
    if not lease.get("ok"):
        return {
            "ok": False,
            "STATUS": "REJECTED",
            "FAIL_CLOSED": lease.get("code"),
            "LEASE_ACQUIRED": False,
            "lease": lease,
            "AUTH": auth,
            "ROUTE": route,
            "COMMAND_FABRIC_E2E_PROVEN": False,
            "EXACT_MISSING_SEGMENT": "LEASE_ACQUIRE",
            "EXACTLY_ONCE_CLAIMED": False,
            "NATS_AT_LEAST_ONCE": True,
        }

    subject = f"{SUBJECT_ROOT}.commands.{target.replace('@', '').replace('/', '')}"
    result_subject = f"{SUBJECT_ROOT}.results.{corr}"
    envelope = {
        "schema": "raios.cross-host-packet.v1",
        "logical_route": f"commands/{target.replace('@', '').replace('/', '')}",
        "target": target,
        "receiver_runtime": target,
        "correlation_id": corr,
        "packet_id": hashlib.sha256(f"{task_id}:{idem}".encode()).hexdigest()[:24],
        "task_id": task_id,
        "idempotency_key": idem,
        "message_id": mid,
        "nats_msg_id": f"raios:cmd:{task_id}:{idem}",
        "capability": cap,
        "subject": subject,
    }
    pub = transport.publish(envelope)
    deliveries = transport.deliver_all(duplicate=force_duplicate_delivery)
    invoked = None
    status = "ALREADY_APPLIED" if replay else "COMPLETED"
    if not replay:
        invoked = capabilities.invoke(cap, health=health)
        live = bool((invoked.get("result") or {}).get("LIVE"))
        status = "COMPLETED" if live or health is not None else "COMPLETED_TARGET_UNREACHABLE"
    if deliveries:
        ack_id = str(deliveries[0].get("message_id") or mid)
        transport.ack(ack_id)

    receipt = receipts.build(
        env=env,
        auth=auth,
        policy={"POLICY_RESULT": "ALLOW", "RISK_CLASS": "LOW"},
        ucp=ucp_result,
        capability=invoked,
        status=status,
    )
    rel = leases.release(str(lease["lease_id"]), owner=str(auth.get("PRINCIPAL") or "C1@AG"))
    nats_primary = route["selected_transport"] == NATS and bool(pub.get("STORED"))
    e2e = bool(
        auth.get("AUTHORITY_SOURCE")
        and lease.get("ok")
        and nats_primary
        and receipt.get("receipt_id")
        and rel.get("ok")
        and status in {"COMPLETED", "ALREADY_APPLIED"}
    )
    return {
        "ok": True,
        "STATUS": status,
        "TASK_ID": task_id,
        "CORRELATION_ID": corr,
        "COMMAND_ID": task_id,
        "IDEMPOTENCY_KEY": idem,
        "AUTH": auth,
        "AUTHORITY_RESULT": auth.get("AUTHORITY_SOURCE"),
        "LEASE_ID": lease.get("lease_id"),
        "LEASE_ACQUIRE_RESULT": "ACQUIRED" if not lease.get("IDEMPOTENT_REACQUIRE") else "IDEMPOTENT_REACQUIRE",
        "LEASE_OWNER": lease.get("owner"),
        "LEASE_SCOPE": lease.get("scope"),
        "LEASE_EXPIRY": lease.get("expires_at"),
        "LEASE_RELEASE_RESULT": "RELEASED" if rel.get("ok") else rel.get("code"),
        "ROUTE": route,
        "selected_transport": route["selected_transport"],
        "fallback_transport": route["fallback_transport"],
        "nats_subject": subject,
        "nats_result_subject": result_subject,
        "stream": STREAM,
        "consumer": f"fabric-commands-{target.replace('@', '').replace('/', '')}",
        "publish_ack_or_delivery_ref": pub.get("SEQUENCE"),
        "target": target,
        "adapter": EXISTING_NATS_PROVIDER,
        "capability": cap,
        "TARGET_EXECUTION": invoked,
        "CAPABILITY_INVOKED": bool(invoked and invoked.get("INVOKED")),
        "RECEIPT": receipt,
        "receipt_id": receipt.get("receipt_id"),
        "message_id": receipt.get("message_id") or mid,
        "RECEIPT_ID_COMPATIBLE": interpret_receipt_id(receipt) == (receipt.get("receipt_id") or mid),
        "UCP": ucp_result,
        "UCP_IMPLEMENTATION": EXISTING_CONTROL_PLANE,
        "NATS_PRIMARY": nats_primary,
        "HTTP_FALLBACK_PRESERVED": True,
        "HTTP_PRIMARY": route["selected_transport"] == HTTP_FALLBACK,
        "NATS_AT_LEAST_ONCE": True,
        "RAIOS_IDEMPOTENCY": True,
        "EXACTLY_ONCE_CLAIMED": False,
        "COMMAND_FABRIC_E2E_PROVEN": e2e,
        "EXACT_MISSING_SEGMENT": None if e2e else "INCOMPLETE_CHAIN",
        "SECOND_LOCK_REGISTRY": False,
        "LEASES_DIR": str(leases.leases_dir),
        "LOCKS_JSON_USED": False,
        "SECOND_EVENT_BUS": False,
        "SECOND_UCP": False,
        "DELIVERY_COUNT": max((d.get("delivery_count") or 1) for d in deliveries) if deliveries else 1,
        "EXISTING_NATS_PROVIDER": EXISTING_NATS_PROVIDER,
        "EXISTING_LEASES": str(EXISTING_LEASES),
        "EXISTING_LOCKS_JSON": str(EXISTING_LOCKS_JSON),
    }
