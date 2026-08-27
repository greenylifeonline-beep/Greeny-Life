"""Command-fabric delta tests CF001-CF024. Does not replay A2A/C1C5/C7 historical suites."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("NO_LLM_CALLS", "true")

from raios.a2a.ucp_adapter import DryRunUCP, EXISTING_CONTROL_PLANE
from raios.c1c5.identity import founder_binding
from raios.command_fabric.fake_transport import FakeFabricTransport
from raios.command_fabric.lease import (
    EXISTING_LEASES,
    EXISTING_LOCKS_JSON,
    LEASE_CONFLICT,
    LEASE_EXPIRED,
    LEASE_UNKNOWN,
    WRONG_OWNER,
    CommandLeaseAdapter,
)
from raios.command_fabric.pipeline import STREAM, SUBJECT_ROOT, execute
from raios.command_fabric.route import HTTP_FALLBACK, NATS, select_transport

SECRET = "ef" * 32
CORR = "COR-CF-E2E-01"
TASK = "RAIOS-COMMAND-FABRIC-E2E-CLOSEOUT-WAVE-01"


def _session() -> dict:
    return {"session_id": CORR, "correlation_id": CORR, "founder_secret": SECRET}


def _env(**kw) -> dict:
    env = {
        "task_id": TASK,
        "actor": "C1",
        "target": "C5",
        "correlation_id": CORR,
        "idempotency_key": "idem-cf-e2e-01",
        "requested_capability": "c5.self_inspect.health",
        "authority_context_reference": CORR,
        "message_id": "MSG-CF-TEST-01",
    }
    env.update(kw)
    env["founder_binding"] = founder_binding(
        secret=SECRET,
        session_id=CORR,
        task_id=str(env["task_id"]),
        idempotency_key=str(env["idempotency_key"]),
        correlation_id=str(env["correlation_id"]),
    )
    return env


def _health():
    return {"LIVE": True, "http_status": 200, "body": {"status": "ONLINE", "stub": True}}


class ControlFabricDeltaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cf-leases-"))
        self.leases = CommandLeaseAdapter(self.tmp)
        self.ucp = DryRunUCP()
        self.transport = FakeFabricTransport()
        self.session = _session()

    def _run(self, env=None, **kw):
        return execute(
            env=env or _env(),
            session=self.session,
            leases=self.leases,
            transport=kw.get("transport", self.transport),
            ucp=kw.get("ucp", self.ucp),
            health=kw.get("health", _health),
            nats_available=kw.get("nats_available", True),
            force_duplicate_delivery=kw.get("force_duplicate_delivery", False),
            ttl_seconds=kw.get("ttl_seconds", 120),
        )

    def test_CF001_NATS_SELECTED_AS_PRIMARY_FOR_SUPPORTED_TARGET(self):
        r = select_transport(target="C5", nats_available=True)
        self.assertEqual(r["selected_transport"], NATS)
        self.assertEqual(r["fallback_transport"], HTTP_FALLBACK)

    def test_CF002_HTTP_REMAINS_FALLBACK(self):
        r = select_transport(target="C5", nats_available=True)
        self.assertEqual(r["fallback_transport"], HTTP_FALLBACK)
        self.assertTrue(r["HTTP_FALLBACK_PRESERVED"])

    def test_CF003_AUTHORITY_DENIED_BEFORE_LEASE(self):
        env = _env()
        env["founder_binding"] = "00" * 32
        out = self._run(env)
        self.assertEqual(out["FAIL_CLOSED"], "AUTH_FAILED")
        self.assertFalse(out["LEASE_ACQUIRED"])
        self.assertEqual(len(list(self.tmp.glob("*.json"))), 0)

    def test_CF004_VALID_AUTHORITY_CAN_ACQUIRE_LEASE(self):
        out = self._run()
        self.assertTrue(out["ok"])
        self.assertTrue(out["LEASE_ID"])
        self.assertIn(out["LEASE_ACQUIRE_RESULT"], {"ACQUIRED", "IDEMPOTENT_REACQUIRE"})

    def test_CF005_SINGLE_ACTIVE_LEASE(self):
        a = self.leases.acquire(
            owner="C1@AG",
            scope="C5:c5.self_inspect.health",
            task_id=TASK,
            correlation_id=CORR,
            capability="c5.self_inspect.health",
            resource_or_target="C5",
            idempotency_key="idem-a",
            provenance_ref="t",
        )
        b = self.leases.acquire(
            owner="OTHER",
            scope="C5:c5.self_inspect.health",
            task_id="OTHER-TASK",
            correlation_id="COR-X",
            capability="c5.self_inspect.health",
            resource_or_target="C5",
            idempotency_key="idem-b",
            provenance_ref="t",
        )
        self.assertTrue(a["ok"])
        self.assertFalse(b["ok"])
        self.assertEqual(b["code"], LEASE_CONFLICT)

    def test_CF006_CONFLICTING_TASK_LEASE_DENIED(self):
        self.leases.acquire(
            owner="C1@AG",
            scope="C5:cap",
            task_id="T-A",
            correlation_id=CORR,
            capability="cap",
            resource_or_target="C5",
            idempotency_key="idem-a",
            provenance_ref="t",
        )
        other = self.leases.acquire(
            owner="C1@AG",
            scope="C5:cap",
            task_id="T-B",
            correlation_id=CORR,
            capability="cap",
            resource_or_target="C5",
            idempotency_key="idem-b",
            provenance_ref="t",
        )
        self.assertFalse(other["ok"])
        self.assertEqual(other["code"], LEASE_CONFLICT)

    def test_CF007_SAME_TASK_IDEMPOTENT_REACQUIRE(self):
        first = self.leases.acquire(
            owner="C1@AG",
            scope="C5:cap",
            task_id=TASK,
            correlation_id=CORR,
            capability="cap",
            resource_or_target="C5",
            idempotency_key="idem-same",
            provenance_ref="t",
        )
        second = self.leases.acquire(
            owner="C1@AG",
            scope="C5:cap",
            task_id=TASK,
            correlation_id=CORR,
            capability="cap",
            resource_or_target="C5",
            idempotency_key="idem-same",
            provenance_ref="t",
        )
        self.assertEqual(first["lease_id"], second["lease_id"])
        self.assertTrue(second["IDEMPOTENT_REACQUIRE"])

    def test_CF008_EXPIRED_LEASE_NOT_ACTIVE(self):
        rec = self.leases.acquire(
            owner="C1@AG",
            scope="C5:cap",
            task_id=TASK,
            correlation_id=CORR,
            capability="cap",
            resource_or_target="C5",
            idempotency_key="idem-exp",
            provenance_ref="t",
        )
        self.leases.expire(rec["lease_id"])
        v = self.leases.validate(rec["lease_id"])
        self.assertFalse(v["ok"])
        self.assertEqual(v["code"], "EXPIRED")
        self.assertIsNone(self.leases.active_on_scope("C5:cap"))

    def test_CF009_WRONG_OWNER_RELEASE_DENIED(self):
        rec = self.leases.acquire(
            owner="C1@AG",
            scope="C5:cap",
            task_id=TASK,
            correlation_id=CORR,
            capability="cap",
            resource_or_target="C5",
            idempotency_key="idem-own",
            provenance_ref="t",
        )
        rel = self.leases.release(rec["lease_id"], owner="INTRUDER")
        self.assertFalse(rel["ok"])
        self.assertEqual(rel["code"], WRONG_OWNER)

    def test_CF010_VALID_OWNER_RELEASE_ALLOWED(self):
        rec = self.leases.acquire(
            owner="C1@AG",
            scope="C5:cap",
            task_id=TASK,
            correlation_id=CORR,
            capability="cap",
            resource_or_target="C5",
            idempotency_key="idem-rel",
            provenance_ref="t",
        )
        rel = self.leases.release(rec["lease_id"], owner="C1@AG")
        self.assertTrue(rel["ok"])
        self.assertFalse(rel["PROVENANCE_ERASED"])
        self.assertTrue(self.leases._path(rec["lease_id"]).is_file())

    def test_CF011_DUPLICATE_NATS_DELIVERY_NO_DUPLICATE_EFFECT(self):
        first = self._run(force_duplicate_delivery=True)
        self.assertEqual(first["STATUS"], "COMPLETED")
        self.assertTrue(first["CAPABILITY_INVOKED"])
        second = self._run()
        self.assertEqual(second["STATUS"], "ALREADY_APPLIED")
        self.assertFalse(second["CAPABILITY_INVOKED"])
        self.assertGreaterEqual(first["DELIVERY_COUNT"], 1)
        self.assertFalse(first["EXACTLY_ONCE_CLAIMED"])

    def test_CF012_TASK_ID_BOUND(self):
        out = self._run()
        self.assertEqual(out["TASK_ID"], TASK)
        self.assertEqual(out["RECEIPT"]["TASK_ID"], TASK)

    def test_CF013_CORRELATION_ID_BOUND(self):
        out = self._run()
        self.assertEqual(out["CORRELATION_ID"], CORR)
        self.assertEqual(out["RECEIPT"]["CORRELATION_ID"], CORR)

    def test_CF014_IDEMPOTENCY_KEY_BOUND(self):
        out = self._run()
        self.assertEqual(out["IDEMPOTENCY_KEY"], "idem-cf-e2e-01")
        self.assertEqual(out["RECEIPT"]["IDEMPOTENCY_KEY"], "idem-cf-e2e-01")

    def test_CF015_NATS_ACK_OR_DELIVERY_EVIDENCE_BOUND(self):
        out = self._run()
        self.assertTrue(out["publish_ack_or_delivery_ref"])
        self.assertTrue(self.transport.acked)
        self.assertEqual(out["stream"], STREAM)

    def test_CF016_TARGET_RESULT_BOUND(self):
        out = self._run()
        self.assertTrue(out["TARGET_EXECUTION"]["result"]["LIVE"])

    def test_CF017_RECEIPT_BOUND(self):
        out = self._run()
        self.assertTrue(out["RECEIPT"]["receipt_id"])
        self.assertEqual(out["RECEIPT"]["STATUS"], "COMPLETED")

    def test_CF018_RECEIPT_ID_AND_MESSAGE_ID_COMPATIBLE(self):
        out = self._run()
        self.assertEqual(out["receipt_id"], out["message_id"])
        self.assertTrue(out["RECEIPT"]["RECEIPT_ID_EQUALS_MESSAGE_ID"])
        self.assertTrue(out["RECEIPT_ID_COMPATIBLE"])

    def test_CF019_HTTP_FALLBACK_POLICY_DETERMINISTIC(self):
        down = select_transport(target="C5", nats_available=False)
        self.assertEqual(down["selected_transport"], HTTP_FALLBACK)
        self.assertEqual(down["route_reason"], "NATS_UNAVAILABLE_HTTP_FALLBACK")
        other = select_transport(target="C7-CLOUD-SANDBOX", nats_available=True)
        self.assertEqual(other["selected_transport"], HTTP_FALLBACK)

    def test_CF020_NO_SECOND_LOCK_REGISTRY(self):
        prod = CommandLeaseAdapter()
        self.assertEqual(prod.leases_dir.resolve(), EXISTING_LEASES.resolve())
        self.assertFalse(prod.uses_locks_json())
        self.assertTrue(EXISTING_LOCKS_JSON.name == "LOCKS.json")
        self.assertNotEqual(EXISTING_LEASES.resolve(), EXISTING_LOCKS_JSON.resolve())

    def test_CF021_NO_SECOND_EVENT_BUS(self):
        out = self._run()
        self.assertFalse(out["SECOND_EVENT_BUS"])
        self.assertEqual(out["EXISTING_NATS_PROVIDER"], "scripts/ai-os/raios_transport/nats_provider.py")
        self.assertTrue(out["nats_subject"].startswith(SUBJECT_ROOT))

    def test_CF022_NO_SECOND_UCP(self):
        out = self._run()
        self.assertFalse(out["SECOND_UCP"])
        self.assertEqual(out["UCP_IMPLEMENTATION"], EXISTING_CONTROL_PLANE)

    def test_CF023_NO_EXACTLY_ONCE_CLAIM(self):
        out = self._run()
        self.assertFalse(out["EXACTLY_ONCE_CLAIMED"])
        self.assertTrue(out["NATS_AT_LEAST_ONCE"])
        self.assertTrue(out["RAIOS_IDEMPOTENCY"])

    def test_CF024_UNKNOWN_LEASE_FAILS_CLOSED(self):
        v = self.leases.validate("L-does-not-exist")
        self.assertFalse(v["ok"])
        self.assertEqual(v["code"], LEASE_UNKNOWN)
        rel = self.leases.release("L-does-not-exist", owner="C1@AG")
        self.assertFalse(rel["ok"])
        self.assertEqual(rel["code"], LEASE_UNKNOWN)


if __name__ == "__main__":
    unittest.main()
