"""UCP integration proof: C1 task envelope submits to existing DryRunUCP only."""

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


def _health():
    return {"LIVE": True, "http_status": 200, "body": {"status": "ok"}}


class ControlIntegrationTests(unittest.TestCase):
    def test_T11_ONE_COMMAND_DRY_RUN_IDEMPOTENT(self):
        ucp = DryRunUCP()
        tmp = Path(tempfile.mkdtemp(prefix="c1c5-ucp-"))
        session = {"session_id": "COR-UCP-PROOF-01", "correlation_id": "COR-UCP-PROOF-01"}
        env = {
            "schema_version": SCHEMA_VERSION,
            "task_id": "RAIOS-PRECANONICAL-CONTROL-INTEGRATION-PROOF-01",
            "actor": "C1",
            "target": "C5",
            "mode": "READ_ONLY",
            "intent": "SELF_INSPECT",
            "risk_class": "LOW",
            "writes_allowed": False,
            "correlation_id": "COR-UCP-PROOF-01",
            "idempotency_key": "idem-ucp-dry-run-01",
            "requested_capability": "c5.self_inspect.health",
            "parameters": {},
            "authority_context_reference": "COR-UCP-PROOF-01",
        }
        text = json.dumps(env)
        first = dispatch(text, session=session, ucp=ucp, health=_health, receipt_dir=tmp)
        second = dispatch(text, session=session, ucp=ucp, health=_health, receipt_dir=tmp)
        self.assertEqual(first["UCP_STATUS"], "ACCEPTED_DRY_RUN")
        self.assertEqual(second["UCP_STATUS"], "ALREADY_APPLIED")
        self.assertTrue(second["SECOND_EXECUTION_NO_OP"])
        self.assertFalse(first["CANONICAL_MUTATION"])
        self.assertFalse(first["COMMAND_FABRIC_E2E_PROVEN"])
        self.assertTrue(first["HTTP_PRIMARY"])
        self.assertFalse(first["NATS_PRIMARY"])
        self.assertEqual(EXISTING_CONTROL_PLANE, ".ai-os/control/RAIOS-CONTROL-PLANE-V1.py")
        self.assertTrue((ROOT / EXISTING_CONTROL_PLANE.replace("/", os.sep)).is_file())
        self.assertIs(type(ucp), DryRunUCP)
