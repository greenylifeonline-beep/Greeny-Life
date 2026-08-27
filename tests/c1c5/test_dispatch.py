"""C1→C5 task-dispatch tests. Deterministic. No LLM/GPU/paid/public listener."""

from __future__ import annotations

import json
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

from raios.a2a.failclosed import AUTH_FAILED, AUTHORITY_REQUIRED, CAPABILITY_UNKNOWN, RISK_POLICY_DENIED
from raios.a2a.ucp_adapter import DryRunUCP
from raios.c1c5.dispatch import dispatch, maybe_dispatch
from raios.c1c5.envelope import SCHEMA_VERSION
from raios.c1c5.identity import STATIC_C1_REF, founder_binding, trusted_founder_contexts

SECRET = "ab" * 32


def _session() -> dict:
    return {
        "session_id": "COR-TEST-C1C5-TASK-01",
        "correlation_id": "COR-TEST-C1C5-TASK-01",
        "founder_secret": SECRET,
    }


def _env(**kw) -> dict:
    base = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "RAIOS-C1-C5-TASK-DISPATCH-01",
        "actor": "C1",
        "target": "C5",
        "mode": "READ_ONLY",
        "intent": "SELF_INSPECT",
        "risk_class": "LOW",
        "writes_allowed": False,
        "correlation_id": "COR-TEST-C1C5-TASK-01",
        "idempotency_key": "idem-c1c5-health-01",
        "requested_capability": "c5.self_inspect.health",
        "parameters": {},
        "authority_context_reference": "COR-TEST-C1C5-TASK-01",
    }
    base.update(kw)
    return base


def _attach_binding(env: dict, session: dict) -> dict:
    out = dict(env)
    ref = str(out.get("authority_context_reference") or session["session_id"])
    out["founder_binding"] = founder_binding(
        secret=session["founder_secret"],
        session_id=ref,
        task_id=str(out.get("task_id") or ""),
        idempotency_key=str(out.get("idempotency_key") or ""),
        correlation_id=str(out.get("correlation_id") or ""),
    )
    return out


def _text(env: dict) -> str:
    return json.dumps(env, ensure_ascii=False)


def _health():
    return {"LIVE": True, "http_status": 200, "body": {"status": "ok", "stub": True}}


class C1C5DispatchTests(unittest.TestCase):
    def setUp(self):
        self.ucp = DryRunUCP()
        self.tmp = Path(tempfile.mkdtemp(prefix="c1c5-receipts-"))
        self.session = _session()

    def _go(self, env, **kw):
        bind = kw.pop("bind", True)
        channel_attested = kw.pop("channel_attested", False)
        payload = dict(env)
        if bind and payload.get("authority_context_reference") and not channel_attested:
            payload = _attach_binding(payload, self.session)
        return dispatch(
            _text(payload),
            session=self.session,
            ucp=kw.get("ucp", self.ucp),
            health=kw.get("health", _health),
            receipt_dir=self.tmp,
            persist_receipt=kw.get("persist_receipt", True),
            channel_attested=channel_attested,
        )

    def test_T01_PLAIN_CHAT_NOT_TASK(self):
        self.assertIsNone(maybe_dispatch("نفّذ GL-005 الآن", session=self.session))
        self.assertIsNone(maybe_dispatch('{"hello": "C5"}', session=self.session))
        out = dispatch("plain conversational message", session=self.session)
        self.assertEqual(out["KIND"], "NOT_A_TASK")
        self.assertFalse(out["TASK_BOUND"])
        self.assertFalse(out["PROVEN"])

    def test_T02_MALFORMED_REJECT(self):
        env = _env()
        del env["task_id"]
        out = self._go(env, bind=False)
        self.assertEqual(out["STATUS"], "REJECTED")
        self.assertEqual(out["FAIL_CLOSED"], "TASK_ENVELOPE_MALFORMED")
        self.assertFalse(out["TASK_BOUND"])
        self.assertFalse(out["PROVEN"])

    def test_T03_MISSING_AUTH_REJECT(self):
        out = self._go(_env(authority_context_reference=""), bind=False)
        self.assertEqual(out["FAIL_CLOSED"], AUTH_FAILED)
        out2 = self._go(_env(authority_context_reference="ACTOR=C1"), bind=False)
        self.assertEqual(out2["FAIL_CLOSED"], AUTH_FAILED)

    def test_T04_UNKNOWN_CAPABILITY_REJECT(self):
        out = self._go(_env(requested_capability="c5.mutate.canonical"))
        self.assertEqual(out["FAIL_CLOSED"], CAPABILITY_UNKNOWN)

    def test_T05_WRITES_FALSE_MUTATING_REJECT(self):
        out = self._go(_env(intent="DELETE", writes_allowed=False))
        self.assertEqual(out["FAIL_CLOSED"], RISK_POLICY_DENIED)

    def test_T06_HIGH_RISK_WITHOUT_AUTHORITY_REJECT(self):
        unauth = self._go(_env(risk_class="HIGH", intent="DELETE", authority_context_reference=""), bind=False)
        self.assertEqual(unauth["FAIL_CLOSED"], AUTH_FAILED)
        high = self._go(_env(risk_class="HIGH", intent="SELF_INSPECT"))
        self.assertEqual(high["FAIL_CLOSED"], AUTHORITY_REQUIRED)

    def test_T07_IDEMPOTENCY_NO_OP(self):
        first = self._go(_env())
        self.assertTrue(first["TASK_BOUND"])
        self.assertTrue(first["TOOL_OR_CAPABILITY_INVOKED"])
        self.assertFalse(first["ALREADY_APPLIED"])
        second = self._go(_env())
        self.assertTrue(second["ALREADY_APPLIED"])
        self.assertTrue(second["SECOND_EXECUTION_NO_OP"])
        self.assertFalse(second["TOOL_OR_CAPABILITY_INVOKED"])
        self.assertEqual(second["TASK_ID"], first["TASK_ID"])
        self.assertEqual(second["UCP_STATUS"], "ALREADY_APPLIED")
        self.assertEqual(second["RECEIPT"]["STATUS"], "COMPLETED")
        self.assertEqual(first["RECEIPT_PATH"], second["RECEIPT_PATH"])

    def test_T08_NO_RECEIPT_NOT_PROVEN(self):
        out = self._go(_env(idempotency_key="idem-no-receipt"), persist_receipt=False)
        self.assertTrue(out["TOOL_OR_CAPABILITY_INVOKED"])
        self.assertFalse(out["BOUND_RECEIPT"])
        self.assertFalse(out["PROVEN"])

    def test_T09_POSITIVE_HEALTH_BOUND(self):
        out = self._go(_env())
        self.assertTrue(out["TASK_BOUND"])
        self.assertEqual(out["TASK_ID"], "RAIOS-C1-C5-TASK-DISPATCH-01")
        self.assertEqual(out["CORRELATION_ID"], "COR-TEST-C1C5-TASK-01")
        self.assertTrue(out["POLICY_CHECKED"])
        self.assertEqual(out["POLICY_RESULT"], "ALLOW")
        self.assertTrue(out["UCP_PATH_USED"])
        self.assertTrue(out["TOOL_OR_CAPABILITY_INVOKED"])
        self.assertTrue(out["EXECUTION_COMPLETED"])
        self.assertTrue(out["BOUND_RECEIPT"])
        self.assertTrue(out["PROVEN"])
        self.assertFalse(out["CANONICAL_MUTATION"])
        self.assertFalse(out["WAL_WRITTEN"])
        self.assertFalse(out["COMMAND_FABRIC_E2E_PROVEN"])
        self.assertEqual(out["AUTH"]["AUTHORITY_SOURCE"], "HMAC_FOUNDER_SESSION")
        self.assertTrue(Path(out["RECEIPT_PATH"]).is_file())

    def test_T10_ACTOR_STRING_IS_NOT_AUTHORITY(self):
        self.assertIn("COR-TEST-C1C5-TASK-01", trusted_founder_contexts(session=self.session))
        out = self._go(_env(actor="C1", authority_context_reference="not-a-server-bind"), bind=False)
        self.assertEqual(out["FAIL_CLOSED"], AUTH_FAILED)

    def test_T11_STATIC_C1_IDENTITY_STRING_REJECT(self):
        out = self._go(_env(authority_context_reference=STATIC_C1_REF), bind=False)
        self.assertEqual(out["FAIL_CLOSED"], AUTH_FAILED)
        self.assertFalse(out["TASK_BOUND"])
        self.assertNotIn(STATIC_C1_REF, trusted_founder_contexts(session=self.session))

    def test_T12_SESSION_ID_WITHOUT_HMAC_REJECT(self):
        out = self._go(_env(), bind=False)
        self.assertEqual(out["FAIL_CLOSED"], AUTH_FAILED)
        self.assertFalse(out["TASK_BOUND"])

    def test_T13_WRONG_HMAC_REJECT(self):
        env = _env()
        env["founder_binding"] = "00" * 32
        out = dispatch(
            _text(env),
            session=self.session,
            ucp=self.ucp,
            health=_health,
            receipt_dir=self.tmp,
        )
        self.assertEqual(out["FAIL_CLOSED"], AUTH_FAILED)

    def test_T14_CHANNEL_ATTESTED_IGNORES_STATIC_REF(self):
        out = self._go(_env(authority_context_reference=STATIC_C1_REF), bind=False, channel_attested=True)
        self.assertTrue(out["TASK_BOUND"])
        self.assertEqual(out["AUTH"]["AUTHORITY_SOURCE"], "CHANNEL_ATTESTED_FOUNDER_SESSION")
        self.assertEqual(out["AUTH"]["authority_context_reference"], "COR-TEST-C1C5-TASK-01")
        self.assertTrue(out["PROVEN"])

    def test_T15_HMAC_NOT_REUSABLE_ON_OTHER_TASK(self):
        first = _attach_binding(_env(), self.session)
        stolen = dict(first)
        stolen["task_id"] = "RAIOS-C1-C5-OTHER-TASK"
        stolen["idempotency_key"] = "idem-other-task"
        out = dispatch(
            _text(stolen),
            session=self.session,
            ucp=self.ucp,
            health=_health,
            receipt_dir=self.tmp,
        )
        self.assertEqual(out["FAIL_CLOSED"], AUTH_FAILED)


if __name__ == "__main__":
    unittest.main()
