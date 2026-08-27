"""Live harmless NATS canary. Uses existing RAIOS_FABRIC stream. Does not rebuild NATS."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))

from raios.a2a.ucp_adapter import DryRunUCP, EXISTING_CONTROL_PLANE
from raios.c1c5 import capabilities, identity, receipts
from raios.command_fabric.lease import CommandLeaseAdapter
from raios.command_fabric.route import select_transport
from raios_transport.nats_provider import NatsJetStreamProvider
from raios_transport.provider import FabricConfig

TASK = "RAIOS-COMMAND-FABRIC-E2E-CANARY-01"
CORR = "COR-CF-NATS-CANARY-01"
IDEMP = "idem-cf-nats-canary-01"
CAP = "c5.self_inspect.health"
TARGET = "C5"
DURABLE_EXISTING = "fabric-commands-C5"
SEAL = ROOT / ".ai-os" / "reports" / "command-fabric" / "RAIOS-COMMAND-FABRIC-E2E-SEAL-01"


def _secret_session() -> dict[str, Any]:
    return {"session_id": CORR, "correlation_id": CORR, "founder_secret": "cf" * 32}


async def _stream_get(provider: NatsJetStreamProvider, stream: str, seq: int) -> dict[str, Any] | None:
    js = provider.js
    if js is None or not seq:
        return None
    raw = None
    try:
        raw = await js.get_msg(stream, seq)
    except TypeError:
        try:
            raw = await js.get_msg(name=stream, seq=seq)
        except Exception:
            raw = None
    except Exception:
        raw = None
    if raw is None:
        return None
    body: dict[str, Any] = {}
    data = getattr(raw, "data", None)
    if data:
        try:
            body = json.loads(data.decode("utf-8"))
        except Exception:
            body = {}
    return {
        "stream_seq": str(getattr(raw, "seq", seq) or seq),
        "subject": getattr(raw, "subject", None),
        "packet_id": body.get("packet_id"),
        "correlation_id": body.get("correlation_id"),
        "kind": "JETSTREAM_GET_MSG",
        "envelope_schema": body.get("schema"),
    }


async def _canary_once(*, replay: bool, ucp: DryRunUCP) -> dict[str, Any]:
    session = _secret_session()
    env = {
        "task_id": TASK,
        "actor": "C1",
        "target": TARGET,
        "correlation_id": CORR,
        "idempotency_key": IDEMP,
        "requested_capability": CAP,
        "authority_context_reference": session["session_id"],
        "message_id": f"MSG-CF-CANARY-{uuid.uuid4().hex[:8]}",
    }
    env["founder_binding"] = identity.founder_binding(
        secret=session["founder_secret"],
        session_id=session["session_id"],
        task_id=TASK,
        idempotency_key=IDEMP,
        correlation_id=CORR,
    )
    auth = identity.bind_founder(
        actor="C1",
        authority_context_reference=session["session_id"],
        env=env,
        session=session,
        founder_binding_hex=env["founder_binding"],
    )
    route = select_transport(target=TARGET, nats_available=True)
    ucp_result = ucp.submit(
        {
            "IDEMPOTENCY_KEY": IDEMP,
            "DESIRED_STATE": {"task_id": TASK, "capability": CAP},
            "COMMAND_ID": TASK,
        }
    )
    replay = replay or bool(ucp_result.get("NO_OP") or ucp_result.get("STATUS") == "ALREADY_APPLIED")
    leases = CommandLeaseAdapter()
    owner = str(auth["PRINCIPAL"])
    lease = leases.acquire(
        owner=owner,
        scope=f"{TARGET}:{CAP}",
        task_id=TASK,
        correlation_id=CORR,
        capability=CAP,
        resource_or_target=TARGET,
        idempotency_key=IDEMP,
        provenance_ref="RAIOS-COMMAND-FABRIC-E2E-CLOSEOUT-WAVE-01",
        ttl_seconds=60,
    )
    if not lease.get("ok"):
        return {
            "STATUS": "REJECTED",
            "EXACT_MISSING_SEGMENT": "LEASE_ACQUIRE",
            "lease": lease,
            "COMMAND_FABRIC_E2E_PROVEN": False,
            "NATS_PRIMARY": False,
        }
    cfg = FabricConfig()
    provider = NatsJetStreamProvider(cfg, runtime_id="C2-CF-CANARY", role_id="C2")
    rel: dict[str, Any] = {"ok": False, "code": "NOT_RELEASED"}
    invoked = None
    pub: dict[str, Any] = {}
    res_pub: dict[str, Any] = {}
    delivery = None
    health: dict[str, Any] = {}
    try:
        await provider.connect()
        health = await provider.health()
        packet_id = hashlib.sha256(f"{TASK}:{IDEMP}".encode()).hexdigest()[:24]
        envelope = {
            "schema": "raios.cross-host-packet.v1",
            "logical_route": "commands/C5",
            "receiver_runtime": "C5",
            "target": TARGET,
            "correlation_id": CORR,
            "packet_id": packet_id,
            "payload": {"capability": CAP, "mode": "READ_ONLY"},
            "nats_msg_id": f"raios:cmd:{TASK}:{IDEMP}",
        }
        pub = await provider.publish_idempotent_with_reconcile(envelope)
        seq = int(pub.get("SEQUENCE") or 0)
        delivery = await _stream_get(provider, cfg.stream, seq)
        if delivery is None:
            last = await provider.last_on_route("commands/C5")
            if last and last.get("packet_id") == packet_id:
                delivery = {
                    "stream_seq": last.get("_stream_seq"),
                    "packet_id": last.get("packet_id"),
                    "correlation_id": last.get("correlation_id"),
                    "kind": "JETSTREAM_GET_LAST_MSG",
                }
        if delivery and delivery.get("packet_id") and delivery.get("packet_id") != packet_id:
            delivery = {**delivery, "PACKET_MISMATCH": True}
        status = "IDEMPOTENT_REPLAY" if replay else "COMPLETED"
        if not replay:
            invoked = capabilities.invoke(CAP)
            live = bool((invoked.get("result") or {}).get("LIVE"))
            status = "COMPLETED" if live else "COMPLETED_TARGET_UNREACHABLE"
            result_env = {
                "schema": "raios.c5-routed-response.v1",
                "correlation_id": CORR,
                "payload": {"capability": CAP, "LIVE": live, "mode": "READ_ONLY"},
                "packet_id": hashlib.sha256(f"{TASK}:{IDEMP}:result".encode()).hexdigest()[:24],
                "nats_msg_id": f"raios:result:{TASK}:{IDEMP}",
            }
            res_pub = await provider.publish_idempotent_with_reconcile(result_env)
        else:
            status = "ALREADY_APPLIED"
            invoked = None
        receipt = receipts.build(
            env=env,
            auth=auth,
            policy={"POLICY_RESULT": "ALLOW", "RISK_CLASS": "LOW"},
            ucp=ucp_result,
            capability=invoked,
            status=status,
        )
        receipt_path = receipts.persist(receipt)
        rel = leases.release(str(lease["lease_id"]), owner=owner)
        sha = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        packet_ok = bool(delivery) and not delivery.get("PACKET_MISMATCH")
        nats_primary = route["selected_transport"] == "NATS" and bool(pub.get("STORED"))
        e2e = bool(
            health.get("ok")
            and nats_primary
            and packet_ok
            and lease.get("ok")
            and rel.get("ok")
            and receipt.get("receipt_id")
            and (status in {"COMPLETED", "IDEMPOTENT_REPLAY", "ALREADY_APPLIED"})
        )
        missing = None
        if not e2e:
            if not health.get("ok"):
                missing = "NATS_HEALTH"
            elif not pub.get("STORED"):
                missing = "NATS_PUBLISH"
            elif not packet_ok:
                missing = "NATS_JETSTREAM_DELIVERY"
            elif not rel.get("ok"):
                missing = "LEASE_RELEASE"
            else:
                missing = "INCOMPLETE_CHAIN"
        return {
            "task_id": TASK,
            "correlation_id": CORR,
            "command_id": TASK,
            "idempotency_key": IDEMP,
            "authenticated_principal_ref": auth.get("PRINCIPAL"),
            "authority_result": auth.get("AUTHORITY_SOURCE"),
            "UCP_STATUS": ucp_result.get("STATUS"),
            "UCP_IMPLEMENTATION": EXISTING_CONTROL_PLANE,
            "lease_id": lease.get("lease_id"),
            "lease_acquire_result": "ACQUIRED" if not lease.get("IDEMPOTENT_REACQUIRE") else "IDEMPOTENT_REACQUIRE",
            "lease_owner": lease.get("owner"),
            "lease_scope": lease.get("scope"),
            "lease_expiry": lease.get("expires_at"),
            "lease_release_result": "RELEASED" if rel.get("ok") else rel.get("code"),
            "selected_transport": route["selected_transport"],
            "fallback_transport": route["fallback_transport"],
            "nats_subject": f"{cfg.subject_root}.commands.C5",
            "nats_result_subject": f"{cfg.subject_root}.results.{CORR}",
            "stream": cfg.stream,
            "consumer": DURABLE_EXISTING,
            "publish_ack_or_delivery_ref": pub.get("SEQUENCE") or (delivery or {}).get("stream_seq"),
            "NATS_HEALTH": health,
            "PUBLISH": {k: pub.get(k) for k in ("STORED", "SEQUENCE", "DUPLICATE_FLAG", "MSG_ID")},
            "RESULT_PUBLISH": {k: res_pub.get(k) for k in ("STORED", "SEQUENCE", "DUPLICATE_FLAG", "MSG_ID") if res_pub},
            "DELIVERY": delivery,
            "target": TARGET,
            "adapter": "scripts/ai-os/raios_transport/nats_provider.py",
            "capability": CAP,
            "target_execution_result": invoked,
            "result_fingerprint": {
                "publish_seq": pub.get("SEQUENCE"),
                "delivery_seq": (delivery or {}).get("stream_seq"),
                "receipt_sha256": sha,
            },
            "receipt_id": receipt.get("receipt_id"),
            "message_id": receipt.get("message_id") or env["message_id"],
            "receipt_sha256": sha,
            "receipt_path": str(receipt_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "STATUS": status,
            "CAPABILITY_INVOKED": bool(invoked and invoked.get("INVOKED")),
            "COMMAND_FABRIC_E2E_PROVEN": e2e,
            "EXACT_MISSING_SEGMENT": missing,
            "NATS_PRIMARY": nats_primary,
            "NATS_AT_LEAST_ONCE": True,
            "RAIOS_IDEMPOTENCY": True,
            "EXACTLY_ONCE_CLAIMED": False,
        }
    finally:
        if not rel.get("ok"):
            try:
                leases.release(str(lease["lease_id"]), owner=owner)
            except Exception:
                pass
        await provider.close()


async def run() -> dict[str, Any]:
    ucp = DryRunUCP()
    first = await _canary_once(replay=False, ucp=ucp)
    second = await _canary_once(replay=True, ucp=ucp)
    return {"first": first, "second": second}


def main() -> int:
    out = asyncio.run(run())
    SEAL.mkdir(parents=True, exist_ok=True)
    path = SEAL / "LIVE-CANARY-RAW.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "first": out["first"].get("STATUS"),
                "second": out["second"].get("STATUS"),
                "e2e": out["first"].get("COMMAND_FABRIC_E2E_PROVEN"),
                "missing": out["first"].get("EXACT_MISSING_SEGMENT"),
                "seq": (out["first"].get("PUBLISH") or {}).get("SEQUENCE"),
                "path": str(path),
            },
            indent=2,
        )
    )
    return 0 if out["first"].get("COMMAND_FABRIC_E2E_PROVEN") else 1


if __name__ == "__main__":
    raise SystemExit(main())
