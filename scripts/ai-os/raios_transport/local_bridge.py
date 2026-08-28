"""RAIOS-FABRIC-BRIDGE@AG — transport service, not actor authority."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from raios_transport.evidence import CompletionStore
from raios_transport.nats_provider import NatsJetStreamProvider
from raios_transport.packet import ensure_hmac_token, sha256_bytes, utc, validate_packet
from raios_transport.provider import FabricConfig, IncomingMessage

SERVICE_ID = "RAIOS-FABRIC-BRIDGE@AG"
C5_CHAT_DEFAULT = "http://127.0.0.1:8766/api/chat"


def git_head(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception:
        return ""


def get_json(url: str, timeout: float = 8.0) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", errors="replace"))


def post_c5(url: str, text: str, timeout: float = 60.0) -> tuple[int, dict]:
    body = json.dumps(
        {
            "text": text,
            "language": "en",
            "training_mode": False,
            "task_id": "RAIOS-FABRIC-LOCAL",
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8", errors="replace"))
        except Exception:
            payload = {"error": str(e)}
        return e.code, payload


def load_user_router(tree: Path):
    path = tree / ".ai-os" / "control" / "RAIOS-USER-ROUTER-V1.py"
    spec = importlib.util.spec_from_file_location("raios_user_router", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class HandlerUnavailable(Exception):
    pass


class LocalFabricBridge:
    def __init__(
        self,
        config: FabricConfig,
        *,
        c5_post: Callable[..., tuple[int, dict]] | None = None,
        c2_dispatch: Callable[..., dict] | None = None,
        provider: NatsJetStreamProvider | None = None,
    ) -> None:
        self.config = config
        self.token = ensure_hmac_token(config.token_path, config.hmac_token)
        self.store = CompletionStore(config.evidence_root)
        self.provider = provider or NatsJetStreamProvider(config, runtime_id=SERVICE_ID, role_id="TRANSPORT")
        self._c5_post = c5_post
        self._c2_dispatch = c2_dispatch
        self._router = None
        self._stop = asyncio.Event()
        self._started = time.monotonic()
        self.last_error = ""
        self.head = git_head(config.tree_root)
        self._executions = 0

    def _c5_available(self) -> bool:
        try:
            status, body = get_json(self.config.c5_health, timeout=5)
            return status == 200 and body.get("status") == "ONLINE"
        except Exception:
            return False

    def _c2_available(self) -> bool:
        try:
            router = self._router or load_user_router(self.config.tree_root)
            self._router = router
            return bool(router.local_worker_present("C2-OBS"))
        except Exception:
            return False

    def write_health(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        nh = {"NATS_CONNECTED": False, "JETSTREAM_AVAILABLE": False}
        try:
            if self.provider.nc:
                nh = asyncio.get_event_loop().run_until_complete(self.provider.health()) if False else nh
        except Exception:
            pass
        rec = {
            "SERVICE": SERVICE_ID,
            "RUNTIME": SERVICE_ID,
            "NATS_CONNECTED": bool(self.provider.nc and self.provider.nc.is_connected),
            "JETSTREAM_AVAILABLE": bool(self.provider.js),
            "C5_ROUTE_AVAILABLE": self._c5_available(),
            "C2_ROUTE_AVAILABLE": self._c2_available(),
            "LAST_ERROR": self.last_error,
            "UPTIME": round(time.monotonic() - self._started, 3),
            "HEAD": self.head,
            "HTTP_PRIMARY": True,
            "NATS_SHADOW": True,
            "NATS_PRIMARY": False,
            "at": utc(),
        }
        if extra:
            rec.update(extra)
        self.config.health_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.health_path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        return rec

    async def write_health_async(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        nats_health = await self.provider.health() if self.provider.js or self.provider.nc else {}
        rec = {
            "SERVICE": SERVICE_ID,
            "RUNTIME": SERVICE_ID,
            "NATS_CONNECTED": bool(nats_health.get("NATS_CONNECTED")),
            "JETSTREAM_AVAILABLE": bool(nats_health.get("JETSTREAM_AVAILABLE")),
            "C5_ROUTE_AVAILABLE": self._c5_available(),
            "C2_ROUTE_AVAILABLE": self._c2_available(),
            "LAST_ERROR": self.last_error,
            "UPTIME": round(time.monotonic() - self._started, 3),
            "HEAD": self.head,
            "HTTP_PRIMARY": True,
            "NATS_SHADOW": True,
            "NATS_PRIMARY": False,
            "at": utc(),
        }
        if extra:
            rec.update(extra)
        self.config.health_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.health_path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        return rec

    def _target_bind(self, packet: dict[str, Any]) -> bool:
        target = packet.get("target")
        recv = packet.get("receiver_runtime")
        actor = packet.get("actor")
        send = packet.get("sender_runtime")
        if target == "C5-PUBLIC":
            return recv == "C5@AG" and actor == "C2" and send == "C2@AG"
        if target == "C2":
            return recv == "C2@AG" and actor == "C5" and send == "C5@AG"
        return False

    async def _publish_outputs(self, runtime: str, corr: str, ack: dict, result: dict, receipt: dict) -> dict[str, Any]:
        ack["logical_route"] = f"acks/{runtime}"
        result["logical_route"] = f"results/{corr}"
        receipt["logical_route"] = f"receipts/{runtime}"
        ack_rec = await self.provider.publish_idempotent_with_reconcile(ack)
        res_rec = await self.provider.publish_idempotent_with_reconcile(result)
        rcp_rec = await self.provider.publish_idempotent_with_reconcile(receipt)
        return {"ack": ack_rec, "result": res_rec, "receipt": rcp_rec}

    async def _dispatch_c5(self, packet: dict[str, Any]) -> dict[str, Any]:
        if not self._c5_available() and self._c5_post is None:
            raise HandlerUnavailable("C5_UNAVAILABLE")
        text = (
            "MISSION_ID=RAIOS-FABRIC-LOCAL ACTION=RETURN_RUNTIME_IDENTITY "
            "MUTATION=false TRAINING_MODE=false. Observe only. Do not claim runtime_id as self-proof."
        )
        poster = self._c5_post or (lambda t, timeout=60: post_c5(self.config.c5_chat, t, timeout))
        status, resp = await asyncio.to_thread(poster, text, self.config.http_timeout_seconds)
        if status != 200:
            raise HandlerUnavailable(f"C5_HTTP_{status}")
        if isinstance(resp, dict) and resp.get("wal_written"):
            raise RuntimeError("WAL_WRITTEN")
        if self._c5_post is None and (not isinstance(resp, dict) or resp.get("status") != "OK"):
            raise HandlerUnavailable("C5_NOT_OK")
        return {"http_status": status, "response": resp}

    async def _dispatch_c2(self, packet: dict[str, Any], corr: str) -> dict[str, Any]:
        if self._c2_dispatch:
            return await asyncio.to_thread(self._c2_dispatch, packet, corr)
        router = self._router or load_user_router(self.config.tree_root)
        self._router = router
        text = (
            "MISSION_ID=RAIOS-FABRIC-LOCAL ACTION=RETURN_RUNTIME_IDENTITY "
            "MUTATION=false TRAINING_MODE=false SOURCE=C5@AG TARGET=C2@AG"
        )

        def _run() -> dict:
            routed = router.route_one("C5@AG", "C2", text, correlation=corr)
            mid = routed.get("message_id")
            ack = router.cp("ack", mid, "C2@AG") if mid else None
            return {"routed": routed, "control_ack": ack}

        out = await asyncio.to_thread(_run)
        routed = out["routed"]
        if not routed.get("message_id"):
            raise HandlerUnavailable("C2_HANDLER")
        if routed.get("wal_written"):
            raise RuntimeError("WAL_WRITTEN")
        return out

    async def handle_command(self, packet: dict[str, Any]) -> dict[str, Any]:
        packet_id = str(packet.get("packet_id") or "")
        corr = str(packet.get("correlation_id") or "")
        existing = self.store.get_complete(packet_id, corr)
        if existing:
            outputs = existing.get("outputs") or {}
            if outputs.get("ack"):
                await self._publish_outputs(
                    packet.get("receiver_runtime") or "",
                    corr,
                    dict(outputs["ack"]),
                    dict(outputs["result"]),
                    dict(outputs["receipt"]),
                )
            return {"disposition": "replayed", "duplicate_execution_prevented": True, "complete": existing}

        inflight = self.store.inflight(packet_id, corr)
        if inflight:
            return {"disposition": "in_flight", "duplicate_execution_prevented": True}

        auth = validate_packet(packet, self.token, set(self.config.allowed_actors), set())
        if auth == "EXPIRED":
            return {"disposition": "expired", "reason": auth}
        if auth != "OK":
            return {"disposition": "rejected", "reason": auth}
        if packet.get("target") == "C5-FOUNDER":
            return {"disposition": "rejected", "reason": "C5_FOUNDER_FAIL_CLOSED"}
        if not self._target_bind(packet):
            return {"disposition": "rejected", "reason": "TARGET_BIND"}
        if self.store.nonce_seen(str(packet.get("nonce") or "")):
            return {"disposition": "in_flight", "duplicate_execution_prevented": True}

        self.store.begin(packet_id, corr, str(packet.get("nonce") or ""))
        runtime = str(packet.get("receiver_runtime") or "")
        head = self.head
        try:
            if packet.get("target") == "C5-PUBLIC":
                dispatched = await self._dispatch_c5(packet)
                self._executions += 1
                c5_resp = dispatched.get("response") or {}
                ack = {
                    "schema": "raios.message-ack.v1",
                    "message_id": packet.get("message_id"),
                    "packet_id": packet_id,
                    "correlation_id": corr,
                    "actor": "C5@AG",
                    "status": "ACKNOWLEDGED",
                    "at": utc(),
                    "head": head,
                }
                result = {
                    "schema": "raios.c5-routed-response.v1",
                    "message_id": packet.get("message_id"),
                    "packet_id": packet_id,
                    "correlation_id": corr,
                    "target": "C5@AG",
                    "http_status": dispatched.get("http_status"),
                    "status": c5_resp.get("status"),
                    "cortex_request_id": c5_resp.get("cortex_request_id"),
                    "model": c5_resp.get("model"),
                    "wal_written": False,
                    "identity_source": "C1_ASSIGNMENT+RUNTIME_BIND+LIVE_PROCESS",
                    "runtime": "C5@AG",
                    "role": "C5",
                    "at": utc(),
                }
                receipt = {
                    "schema": "raios.user-route-receipt.v1",
                    "event": "RETURNED",
                    "message_id": packet.get("message_id"),
                    "packet_id": packet_id,
                    "correlation_id": corr,
                    "target": "C5@AG",
                    "at": utc(),
                    "ack": ack,
                    "response_sha256": sha256_bytes(
                        json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    ),
                    "return_path": "results/" + corr,
                    "durable": True,
                }
            elif packet.get("target") == "C2":
                dispatched = await self._dispatch_c2(packet, corr)
                self._executions += 1
                routed = dispatched["routed"]
                ack = {
                    "schema": "raios.message-ack.v1",
                    "message_id": routed.get("message_id"),
                    "packet_id": packet_id,
                    "correlation_id": corr,
                    "actor": "C2@AG",
                    "status": "ACKNOWLEDGED",
                    "at": utc(),
                    "head": head,
                    "control_ack": dispatched.get("control_ack"),
                }
                result = {
                    "schema": "raios.message.v1",
                    "message_id": routed.get("message_id"),
                    "packet_id": packet_id,
                    "correlation_id": corr,
                    "target": "C2@AG",
                    "status": routed.get("status"),
                    "handler": "RAIOS-USER-ROUTER-V1.route_one + RAIOS-CONTROL-PLANE-V1 send/ack",
                    "identity_source": "C1_ASSIGNMENT+C2@AG_SESSION",
                    "runtime": "C2@AG",
                    "role": "C2",
                    "wal_written": False,
                    "at": utc(),
                }
                receipt = {
                    "schema": "raios.user-route-receipt.v1",
                    "event": "RETURNED",
                    "message_id": routed.get("message_id"),
                    "packet_id": packet_id,
                    "correlation_id": corr,
                    "target": "C2@AG",
                    "at": utc(),
                    "ack": ack,
                    "response_sha256": sha256_bytes(
                        json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    ),
                    "return_path": "results/" + corr,
                    "durable": True,
                }
            else:
                return {"disposition": "rejected", "reason": "UNKNOWN_TARGET"}
        except HandlerUnavailable as e:
            self.last_error = str(e)
            inflight_path = self.store.inflight_path(packet_id, corr)
            if inflight_path.exists():
                inflight_path.unlink()
            raise
        pubs = await self._publish_outputs(runtime, corr, ack, result, receipt)
        complete = self.store.finish(
            packet_id,
            corr,
            {"ack": ack, "result": result, "receipt": receipt, "publish": pubs},
            executed=True,
        )
        return {"disposition": "executed", "complete": complete, "publish": pubs, "duplicate_execution_prevented": True}

    async def _handle_incoming(self, incoming: IncomingMessage) -> None:
        packet = incoming.envelope
        try:
            rec = await self.handle_command(packet)
        except HandlerUnavailable:
            await self.provider.nack(incoming.receipt_id, "HANDLER_UNAVAILABLE")
            return
        except Exception as e:
            self.last_error = f"{type(e).__name__}::{e}"
            await self.provider.nack(incoming.receipt_id, self.last_error)
            return
        if rec.get("disposition") == "in_flight":
            await self.provider.nack(incoming.receipt_id, "IN_FLIGHT")
            return
        await self.provider.ack(incoming.receipt_id)

    async def connect_with_retry(self) -> None:
        delay = 2.0
        while not self._stop.is_set():
            try:
                await self.provider.connect()
                self.last_error = ""
                return
            except Exception as e:
                self.last_error = f"NATS_CONNECT::{type(e).__name__}"
                try:
                    await self.write_health_async()
                except Exception:
                    pass
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                    return
                except asyncio.TimeoutError:
                    delay = min(delay * 2, 30.0)

    async def run(self) -> None:
        await self.connect_with_retry()
        cmd_c5 = await self.provider.subscribe("commands/C5@AG", durable="fabric-cmd-C5AG")
        cmd_c2 = await self.provider.subscribe("commands/C2@AG", durable="fabric-cmd-C2AG")
        await self.write_health_async()
        last_health = time.monotonic()
        while not self._stop.is_set():
            for sub in (cmd_c5, cmd_c2):
                try:
                    msgs = await sub.fetch(1, timeout=1.0)
                except Exception as e:
                    if self.provider.nc and self.provider.nc.is_connected:
                        self.last_error = f"FETCH::{type(e).__name__}"
                    msgs = []
                for incoming in msgs:
                    await self._handle_incoming(incoming)
            if time.monotonic() - last_health > 5:
                await self.write_health_async()
                last_health = time.monotonic()
            if self.provider.nc and self.provider.nc.is_closed:
                await self.connect_with_retry()
                cmd_c5 = await self.provider.subscribe("commands/C5@AG", durable="fabric-cmd-C5AG")
                cmd_c2 = await self.provider.subscribe("commands/C2@AG", durable="fabric-cmd-C2AG")

    def stop(self) -> None:
        self._stop.set()


async def amain() -> int:
    config = FabricConfig()
    log = Path(r"C:\ProgramData\RAIOS\transport\logs\fabric-bridge.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    bridge = LocalFabricBridge(config)
    try:
        log.write_text("starting " + utc() + "\n", encoding="utf-8")
        await bridge.run()
    except asyncio.CancelledError:
        bridge.stop()
    except Exception as e:
        rec = f"{type(e).__name__}::{e}"
        bridge.last_error = rec
        try:
            log.write_text(rec + "\n", encoding="utf-8")
            await bridge.write_health_async()
        except Exception:
            pass
        raise
    finally:
        await bridge.provider.close()
    return 0


def main() -> int:
    if any(a in ("--health", "health") for a in __import__("sys").argv[1:]):
        path = FabricConfig().health_path
        if path.exists():
            print(path.read_text(encoding="utf-8"), end="")
            return 0
        print(json.dumps({"NATS_CONNECTED": False, "LAST_ERROR": "NO_HEALTH_FILE"}))
        return 2
    return asyncio.run(amain())


if __name__ == "__main__":
    raise SystemExit(main())
