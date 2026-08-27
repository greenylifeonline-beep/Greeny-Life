"""UCP integration proof: in-process DryRunUCP plus live send/ack. No acquire. No WAL."""

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

from raios.a2a.ucp_adapter import DryRunUCP, EXISTING_CONTROL_PLANE
from raios.c1c5.dispatch import dispatch
from raios.c1c5.envelope import SCHEMA_VERSION
from raios.c1c5.identity import founder_binding
from raios.c1c5.ucp_live import correlated_send_ack

SECRET = "cd" * 32
CORR = "COR-UCP-PROOF-01A"


def _health():
    return {"LIVE": True, "http_status": 200, "body": {"status": "ok"}}


def _session():
    return {"session_id": CORR, "correlation_id": CORR, "founder_secret": SECRET}


def _env():
    env = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "RAIOS-PRECANONICAL-CONTROL-INTEGRATION-PROOF-01A",
        "actor": "C1",
        "target": "C5",
        "mode": "READ_ONLY",
        "intent": "SELF_INSPECT",
        "risk_class": "LOW",
        "writes_allowed": False,
        "correlation_id": CORR,
        "idempotency_key": "idem-ucp-dry-run-01a",
        "requested_capability": "c5.self_inspect.health",
        "parameters": {},
        "authority_context_reference": CORR,
    }
    env["founder_binding"] = founder_binding(
        secret=SECRET,
        session_id=CORR,
        task_id=env["task_id"],
        idempotency_key=env["idempotency_key"],
        correlation_id=CORR,
    )
    return env


class ControlIntegrationTests(unittest.TestCase):
    def test_T11_ONE_COMMAND_DRY_RUN_IDEMPOTENT(self):
        ucp = DryRunUCP()
        tmp = Path(tempfile.mkdtemp(prefix="c1c5-ucp-"))
        session = _session()
        text = json.dumps(_env())
        first = dispatch(text, session=session, ucp=ucp, health=_health, receipt_dir=tmp)
        second = dispatch(text, session=session, ucp=ucp, health=_health, receipt_dir=tmp)
        self.assertEqual(first["UCP_STATUS"], "ACCEPTED_DRY_RUN")
        self.assertEqual(second["UCP_STATUS"], "ALREADY_APPLIED")
        self.assertTrue(second["SECOND_EXECUTION_NO_OP"])
        self.assertFalse(first["CANONICAL_MUTATION"])
        self.assertFalse(first["COMMAND_FABRIC_E2E_PROVEN"])
        self.assertTrue(first["HTTP_PRIMARY"])
        self.assertFalse(first["NATS_PRIMARY"])
        self.assertEqual(first["AUTH"]["AUTHORITY_SOURCE"], "HMAC_FOUNDER_SESSION")
        self.assertEqual(EXISTING_CONTROL_PLANE, ".ai-os/control/RAIOS-CONTROL-PLANE-V1.py")
        self.assertTrue((ROOT / EXISTING_CONTROL_PLANE.replace("/", os.sep)).is_file())
        self.assertIs(type(ucp), DryRunUCP)

    def test_T16_LIVE_UCP_SEND_ACK_NO_LEASE(self):
        live = correlated_send_ack(
            correlation_id=CORR,
            text="harmless READ_ONLY SELF_INSPECT dry-run",
        )
        self.assertTrue(live["SEND_RECEIPT_EXISTS"])
        self.assertTrue(live["ACK_RECEIPT_EXISTS"])
        self.assertTrue(live["INBOX_EXISTS"])
        self.assertEqual(live["CORRELATION_ID"], CORR)
        self.assertEqual(live["ACK_STATUS"], "ACKNOWLEDGED")
        self.assertFalse(live["LEASE_ACQUIRED"])
        self.assertFalse(live["WAL_WRITTEN"])
        self.assertFalse(live["COMMAND_FABRIC_E2E_PROVEN"])
        self.assertFalse(live["UCP_REBUILT"])
        self.assertEqual(live["UCP_IMPLEMENTATION"], EXISTING_CONTROL_PLANE)
