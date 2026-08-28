# Canonical local fabric bridge tests. Phase A. No C5 LLM calls.
from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

from nats.js.api import DeliverPolicy, Header

from raios_transport.evidence import CompletionStore
from raios_transport.local_bridge import LocalFabricBridge
from raios_transport.nats_provider import NatsJetStreamProvider
from raios_transport.packet import (
    build_packet,
    deterministic_msg_id,
    validate_packet,
)
from raios_transport.provider import FabricConfig, parse_logical_route, runtime_key


TOKEN = "stage04-test-token-not-a-secret-aaaaaaaa"


def _cfg(tmp: Path) -> FabricConfig:
    return FabricConfig(
        evidence_root=tmp / "evidence",
        token_path=tmp / "fabric.token",
        hmac_token=TOKEN,
        health_path=tmp / "health.json",
    )


class FakeAck:
    def __init__(self, seq: int, duplicate: bool = False) -> None:
        self.seq = seq
        self.duplicate = duplicate


class FakeRaw:
    def __init__(self, subject: str, data: bytes, seq: int) -> None:
        self.subject = subject
        self.data = data
        self.seq = seq


class FakeJS:
    def __init__(self) -> None:
        self.store: dict[str, tuple[int, bytes, str, str | None]] = {}
        self.seq = 0
        self.timeouts_left = 0

    async def publish(self, subject, payload, timeout=10, stream=None, headers=None):
        if self.timeouts_left > 0:
            self.timeouts_left -= 1
            raise TimeoutError("simulated puback timeout")
        msg_id = None
        if headers:
            msg_id = headers.get(Header.MSG_ID) or headers.get("Nats-Msg-Id")
        existing = self.store.get(subject)
        if existing and existing[3] == msg_id and existing[1] == payload:
            return FakeAck(existing[0], duplicate=True)
        self.seq += 1
        self.store[subject] = (self.seq, payload, subject, msg_id)
        return FakeAck(self.seq, duplicate=False)

    async def get_last_msg(self, stream, subject):
        if subject not in self.store:
            raise RuntimeError("not found")
        seq, data, subj, _mid = self.store[subject]
        return FakeRaw(subj, data, seq)

    async def stream_info(self, name):
        return {"name": name, "seq": self.seq}


class FakeNC:
    is_connected = True
    is_closed = False

    async def flush(self, timeout=2):
        return None


class RecProvider:
    def __init__(self) -> None:
        self.pubs: list[dict] = []
        self.nc = None
        self.js = None

    async def publish_idempotent_with_reconcile(self, envelope):
        self.pubs.append(envelope)
        return {
            "STORED": True,
            "SEQUENCE": str(len(self.pubs)),
            "PUBACK_RECEIVED": True,
            "AMBIGUOUS_COMMIT_RECONCILED": False,
        }

    async def health(self):
        return {"NATS_CONNECTED": False, "JETSTREAM_AVAILABLE": False}


class RouteTests(unittest.TestCase):
    def test_parse_and_runtime_key(self):
        r = parse_logical_route("commands/C5@AG")
        self.assertEqual(r.kind, "commands")
        self.assertEqual(r.key, "C5@AG")
        self.assertEqual(runtime_key("C5@AG"), "C5AG")
        self.assertEqual(runtime_key("C2@AG"), "C2AG")

    def test_required_kinds(self):
        for kind in ("commands", "results", "receipts", "events", "health", "failures"):
            parse_logical_route(f"{kind}/x")

    def test_reject_blank(self):
        with self.assertRaises(ValueError):
            parse_logical_route("commands/")


class PacketTests(unittest.TestCase):
    def test_valid_and_bind_fields(self):
        pkt = build_packet(
            token=TOKEN,
            actor="C2",
            target="C5-PUBLIC",
            payload={"action": "RETURN_RUNTIME_IDENTITY", "mutation": False},
            sender_runtime="C2@AG",
            receiver_runtime="C5@AG",
            role_id="C2",
        )
        self.assertEqual(validate_packet(pkt, TOKEN, {"C1", "C2", "C5"}), "OK")
        self.assertNotEqual(pkt["packet_id"], pkt["correlation_id"])
        self.assertTrue(pkt["nonce"])
        self.assertTrue(pkt["issued_at"])
        self.assertTrue(pkt["expires_at"])

    def test_bad_signature(self):
        pkt = build_packet(
            token=TOKEN,
            actor="C2",
            target="C5-PUBLIC",
            payload={"x": 1},
            sender_runtime="C2@AG",
            receiver_runtime="C5@AG",
            role_id="C2",
        )
        pkt["payload"] = {"x": 2}
        self.assertEqual(validate_packet(pkt, TOKEN, {"C2"}), "INVALID_SCHEMA")

    def test_replay_and_expiry(self):
        pkt = build_packet(
            token=TOKEN,
            actor="C5",
            target="C2",
            payload={"action": "RETURN_RUNTIME_IDENTITY"},
            sender_runtime="C5@AG",
            receiver_runtime="C2@AG",
            role_id="C5",
        )
        seen = {pkt["nonce"]}
        self.assertEqual(validate_packet(pkt, TOKEN, {"C5"}, seen), "REPLAY")
        pkt2 = build_packet(
            token=TOKEN,
            actor="C5",
            target="C2",
            payload={},
            sender_runtime="C5@AG",
            receiver_runtime="C2@AG",
            role_id="C5",
            expires_seconds=-1,
        )
        self.assertEqual(validate_packet(pkt2, TOKEN, {"C5"}), "EXPIRED")

    def test_msg_id_deterministic(self):
        a = deterministic_msg_id("ack", "pkt-1", "corr-1")
        b = deterministic_msg_id("ack", "pkt-1", "corr-1")
        self.assertEqual(a, b)
        self.assertEqual(a, "raios:ack:pkt-1:corr-1")


class ProviderMappingTests(unittest.IsolatedAsyncioTestCase):
    async def test_exact_filter_not_wildcard_not_bench(self):
        captured: dict = {}

        class JS:
            async def pull_subscribe(self, subj, durable=None, config=None):
                captured["subj"] = subj
                captured["filter"] = config.filter_subject
                captured["deliver"] = config.deliver_policy
                return object()

        p = NatsJetStreamProvider(FabricConfig())
        p.js = JS()
        await p.subscribe("commands/C5@AG", durable="fabric-cmd-C5AG")
        self.assertEqual(captured["subj"], "raios.fabric.commands.C5AG")
        self.assertEqual(captured["filter"], "raios.fabric.commands.C5AG")
        self.assertNotIn("bench", captured["subj"])
        self.assertNotEqual(captured["subj"], "raios.fabric.>")
        self.assertEqual(captured["deliver"], DeliverPolicy.ALL)

    async def test_results_are_correlation_scoped(self):
        captured: dict = {}

        class JS:
            async def pull_subscribe(self, subj, durable=None, config=None):
                captured["subj"] = subj
                captured["durable"] = durable
                captured["filter"] = config.filter_subject
                return object()

        p = NatsJetStreamProvider(FabricConfig())
        p.js = JS()
        corr = "corr-" + uuid.uuid4().hex[:12]
        await p.subscribe(f"results/{corr}", durable=f"obs-res-{corr}")
        self.assertEqual(captured["subj"], f"raios.fabric.results.{corr}")
        self.assertEqual(captured["durable"], f"obs-res-{corr}")
        self.assertEqual(captured["filter"], captured["subj"])


class IdempotencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_msg_id_does_not_create_duplicate_logical(self):
        p = NatsJetStreamProvider(FabricConfig())
        p.js = FakeJS()
        p.nc = FakeNC()
        env = {
            "schema": "raios.message-ack.v1",
            "packet_id": "pkt-idem",
            "correlation_id": "corr-idem",
            "logical_route": "acks/C5@AG",
            "actor": "C5@AG",
        }
        a = await p.publish_idempotent_with_reconcile(env)
        b = await p.publish_idempotent_with_reconcile(env)
        self.assertTrue(a["STORED"])
        self.assertTrue(b["STORED"])
        self.assertEqual(a["SEQUENCE"], b["SEQUENCE"])
        self.assertTrue(b["DUPLICATE_FLAG"])

    async def test_ambiguous_puback_reconcile(self):
        p = NatsJetStreamProvider(FabricConfig())
        js = FakeJS()
        p.js = js
        p.nc = FakeNC()
        env = {
            "schema": "raios.message-ack.v1",
            "packet_id": "pkt-amb",
            "correlation_id": "corr-amb",
            "logical_route": "acks/C2@AG",
            "actor": "C2@AG",
        }
        first = await p.publish_idempotent_with_reconcile(env)
        self.assertTrue(first["PUBACK_RECEIVED"])
        js.timeouts_left = 2
        second = await p.publish_idempotent_with_reconcile(env)
        self.assertTrue(second["STORED"])
        self.assertTrue(second["RECONCILED"] or second["AMBIGUOUS_COMMIT_RECONCILED"] or second["DUPLICATE_FLAG"] is True)


class DuplicateExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_handler_runs_once(self):
        tmp = Path(tempfile.mkdtemp())
        cfg = _cfg(tmp)
        calls = {"n": 0}

        def c5_post(text, timeout=60):
            calls["n"] += 1
            return 200, {"status": "OK", "model": "test", "wal_written": False}

        bridge = LocalFabricBridge(cfg, c5_post=c5_post, provider=RecProvider())
        pkt = build_packet(
            token=TOKEN,
            actor="C2",
            target="C5-PUBLIC",
            payload={"action": "RETURN_RUNTIME_IDENTITY", "mutation": False},
            sender_runtime="C2@AG",
            receiver_runtime="C5@AG",
            role_id="C2",
        )
        a = await bridge.handle_command(pkt)
        b = await bridge.handle_command(pkt)
        self.assertEqual(a["disposition"], "executed")
        self.assertEqual(b["disposition"], "replayed")
        self.assertTrue(b["duplicate_execution_prevented"])
        self.assertEqual(calls["n"], 1)
        self.assertEqual(bridge._executions, 1)


class LiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_publish_subscribe_roundtrip(self):
        p = NatsJetStreamProvider(FabricConfig(hmac_token=TOKEN), runtime_id="stage04-test")
        await p.connect()
        try:
            h = await p.health()
            self.assertTrue(h["NATS_CONNECTED"])
            self.assertTrue(h["JETSTREAM_AVAILABLE"])
            self.assertEqual(h["stream"], "RAIOS_FABRIC")
            tag = uuid.uuid4().hex[:8]
            route = f"health/TESTSTAGE04-{tag}"
            env = {
                "schema": "raios.message.v1",
                "packet_id": "pkt-" + tag,
                "correlation_id": "corr-" + tag,
                "logical_route": route,
                "runtime": "TEST",
            }
            seq = await p.publish(env)
            self.assertTrue(seq)
            sub = await p.subscribe(route, durable=f"t-health-{tag}")
            got = []
            for _ in range(10):
                got = await sub.fetch(1, timeout=2)
                if got:
                    break
            self.assertTrue(got)
            self.assertEqual(got[0].envelope.get("packet_id"), "pkt-" + tag)
            await p.ack(got[0].receipt_id)
        finally:
            await p.close()


if __name__ == "__main__":
    unittest.main()
