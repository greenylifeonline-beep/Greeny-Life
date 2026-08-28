"""NATS JetStream TransportProvider. Subject mapping is provider-internal."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import nats
import nats.errors
import nats.js.api as jsapi
import nats.js.errors
from nats.js.api import AckPolicy, ConsumerConfig, DeliverPolicy, StreamConfig

from raios_transport.packet import sha256_bytes
from raios_transport.provider import (
    FabricConfig,
    IncomingMessage,
    LogicalRoute,
    TransportProvider,
    derive_logical_route,
    parse_logical_route,
    runtime_key,
    wire_envelope,
)


def is_timeout(exc: BaseException) -> bool:
    return isinstance(exc, (nats.errors.TimeoutError, asyncio.TimeoutError, TimeoutError))


class PullSubscription:
    def __init__(self, provider: "NatsJetStreamProvider", sub: Any, route: LogicalRoute) -> None:
        self._provider = provider
        self._sub = sub
        self.route = route

    async def fetch(self, n: int = 1, timeout: float = 5.0) -> list[IncomingMessage]:
        try:
            raws = await self._sub.fetch(n, timeout=timeout)
        except nats.errors.TimeoutError:
            return []
        out: list[IncomingMessage] = []
        for msg in raws:
            out.append(self._provider._wrap(msg, self.route))
        return out


class NatsJetStreamProvider(TransportProvider):
    def __init__(self, config: FabricConfig, *, runtime_id: str = "", role_id: str = "TRANSPORT") -> None:
        self.config = config
        self.transport_id = "nats-jetstream-fabric"
        self.runtime_id = runtime_id
        self.role_id = role_id
        self.nc = None
        self.js = None
        self._inbox: dict[str, Any] = {}
        self._core_sub = None

    def _subject(self, route: LogicalRoute) -> str:
        key = runtime_key(route.key) if route.kind != "results" else route.key
        return f"{self.config.subject_root}.{route.kind}.{key}"

    def _wrap(self, msg: Any, route: LogicalRoute) -> IncomingMessage:
        receipt_id = str(uuid.uuid4())
        self._inbox[receipt_id] = msg
        md = getattr(msg, "metadata", None)
        seq = getattr(md, "sequence", None) if md else None
        delivery = getattr(md, "num_delivered", None) if md else None
        body = json.loads(msg.data.decode("utf-8")) if msg.data else {}
        return IncomingMessage(
            envelope=body,
            receipt_id=receipt_id,
            delivery_count=int(delivery or 1),
            stream_seq=str(getattr(seq, "stream", None)) if seq else None,
            logical_route=route.path,
        )

    async def connect(self) -> None:
        self.nc = await nats.connect(
            self.config.nats_url,
            name=self.runtime_id or self.transport_id,
            allow_reconnect=True,
            max_reconnect_attempts=-1,
            reconnect_time_wait=2,
            connect_timeout=5,
            ping_interval=20,
            max_outstanding_pings=5,
        )
        self.js = self.nc.jetstream()
        try:
            await self.js.add_stream(
                StreamConfig(
                    name=self.config.stream,
                    subjects=[f"{self.config.subject_root}.>"],
                    retention="limits",
                    storage="file",
                    max_msgs=10000,
                    max_bytes=32_000_000,
                )
            )
        except Exception:
            await self.js.stream_info(self.config.stream)

    async def health(self) -> dict[str, Any]:
        connected = bool(self.nc and self.nc.is_connected and not self.nc.is_closed)
        js_ok = False
        if connected and self.js:
            try:
                await self.js.stream_info(self.config.stream)
                js_ok = True
            except Exception:
                js_ok = False
        return {
            "ok": connected and js_ok,
            "transport_id": self.transport_id,
            "runtime_id": self.runtime_id,
            "role_id": self.role_id,
            "NATS_CONNECTED": connected,
            "JETSTREAM_AVAILABLE": js_ok,
            "stream": self.config.stream,
        }

    async def publish(self, envelope: dict[str, Any]) -> str:
        rec = await self.publish_idempotent_with_reconcile(envelope)
        if not rec.get("STORED"):
            raise RuntimeError("PUBLISH_FAILED")
        return str(rec.get("SEQUENCE") or "")

    async def subscribe(self, logical_route: str, durable: str | None = None) -> PullSubscription:
        route = parse_logical_route(logical_route)
        subject = self._subject(route)
        name = durable or f"fabric-{route.kind}-{runtime_key(route.key)}"
        # Exact-subject filter only. Never subscribe to raios.fabric.> or RAIOS_BENCH.
        sub = await self.js.pull_subscribe(
            subject,
            durable=name,
            config=ConsumerConfig(
                durable_name=name,
                ack_policy=AckPolicy.EXPLICIT,
                deliver_policy=DeliverPolicy.ALL,
                filter_subject=subject,
                max_deliver=5,
                ack_wait=self.config.ack_wait_seconds,
            ),
        )
        return PullSubscription(self, sub, route)

    async def request(self, envelope: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
        payload = json.dumps(wire_envelope(envelope), ensure_ascii=False).encode("utf-8")
        msg = await self.nc.request(f"{self.config.subject_root}.core.request", payload, timeout=timeout)
        return json.loads(msg.data.decode("utf-8"))

    async def reply(self, request_id: str, envelope: dict[str, Any]) -> None:
        msg = self._inbox.get(request_id)
        if msg is None or not getattr(msg, "reply", None):
            raise RuntimeError("REQUEST_NOT_FOUND")
        await msg.respond(json.dumps(wire_envelope(envelope), ensure_ascii=False).encode("utf-8"))

    async def ack(self, receipt_id: str) -> None:
        msg = self._inbox.pop(receipt_id, None)
        if msg is None:
            return
        await msg.ack()

    async def nack(self, receipt_id: str, reason: str | None = None) -> None:
        msg = self._inbox.pop(receipt_id, None)
        if msg is None:
            return
        await msg.nak(delay=2.0)

    async def close(self) -> None:
        if not self.nc or self.nc.is_closed:
            return
        try:
            await asyncio.wait_for(self.nc.drain(), timeout=2.0)
        except Exception:
            try:
                await self.nc.close()
            except Exception:
                pass

    async def consumer_pending(self, durable: str) -> int:
        info = await self.js.consumer_info(self.config.stream, durable)
        return int(getattr(info, "num_pending", 0) or 0)

    async def last_on_route(self, logical_route: str) -> dict[str, Any] | None:
        subject = self._subject(parse_logical_route(logical_route))
        try:
            raw = await self.js.get_last_msg(self.config.stream, subject)
        except (nats.js.errors.NotFoundError, nats.js.errors.Error):
            return None
        if not raw.data:
            return None
        body = json.loads(raw.data.decode("utf-8"))
        body["_stream_seq"] = str(raw.seq)
        return body

    async def reconcile_stored(self, subject: str, packet_id: str, corr: str, schema: str, payload_sha: str):
        await self.nc.flush(timeout=2.0)
        try:
            raw = await self.js.get_last_msg(self.config.stream, subject)
        except Exception:
            return None
        if raw.subject != subject or not raw.data:
            return None
        try:
            stored = json.loads(raw.data.decode("utf-8"))
        except Exception:
            return None
        if stored.get("schema") != schema:
            return None
        if stored.get("packet_id") != packet_id or stored.get("correlation_id") != corr:
            return None
        if sha256_bytes(raw.data) != payload_sha:
            return None
        return raw

    async def publish_idempotent_with_reconcile(self, envelope: dict[str, Any]) -> dict[str, Any]:
        route = derive_logical_route(envelope)
        subject = self._subject(route)
        wire = wire_envelope(envelope)
        packet_id = str(wire.get("packet_id") or "")
        corr = str(wire.get("correlation_id") or "")
        schema = str(wire.get("schema") or "")
        kind = route.kind.rstrip("s") if route.kind.endswith("s") else route.kind
        if route.kind == "acks":
            kind = "ack"
        elif route.kind == "results":
            kind = "result"
        elif route.kind == "receipts":
            kind = "receipt"
        elif route.kind == "commands":
            kind = "cmd"
        msg_id = str(envelope.get("nats_msg_id") or f"raios:{kind}:{packet_id}:{corr}")
        payload = json.dumps(wire, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        payload_sha = sha256_bytes(payload)
        headers = {jsapi.Header.MSG_ID: msg_id}
        out = {
            "MSG_ID": msg_id,
            "PUBLISH_ATTEMPTED": True,
            "PUBACK_RECEIVED": False,
            "STORED": False,
            "RECONCILED": False,
            "AMBIGUOUS_COMMIT_RECONCILED": False,
            "RETRY_ATTEMPTED": False,
            "IDEMPOTENT_RETRY_RECONCILED": False,
            "DUPLICATE_FLAG": None,
            "SEQUENCE": None,
            "PAYLOAD_SHA256": payload_sha,
            "LOGICAL_ROUTE": route.path,
        }

        async def try_publish():
            return await self.js.publish(
                subject,
                payload,
                timeout=self.config.js_puback_timeout,
                stream=self.config.stream,
                headers=headers,
            )

        try:
            ack = await try_publish()
            out["PUBACK_RECEIVED"] = True
            out["STORED"] = True
            out["SEQUENCE"] = str(ack.seq)
            out["DUPLICATE_FLAG"] = ack.duplicate
            return out
        except Exception as e:
            if not is_timeout(e):
                raise

        raw = await self.reconcile_stored(subject, packet_id, corr, schema, payload_sha)
        if raw is not None:
            out["STORED"] = True
            out["RECONCILED"] = True
            out["AMBIGUOUS_COMMIT_RECONCILED"] = True
            out["SEQUENCE"] = str(raw.seq)
            return out

        out["RETRY_ATTEMPTED"] = True
        try:
            ack = await try_publish()
            out["PUBACK_RECEIVED"] = True
            out["STORED"] = True
            out["SEQUENCE"] = str(ack.seq)
            out["DUPLICATE_FLAG"] = ack.duplicate
            return out
        except Exception as e:
            if not is_timeout(e):
                raise

        raw = await self.reconcile_stored(subject, packet_id, corr, schema, payload_sha)
        if raw is not None:
            out["STORED"] = True
            out["RECONCILED"] = True
            out["AMBIGUOUS_COMMIT_RECONCILED"] = True
            out["IDEMPOTENT_RETRY_RECONCILED"] = True
            out["SEQUENCE"] = str(raw.seq)
            return out
        return out
