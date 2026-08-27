"""Receipt identity compatibility. Does not mutate historical receipts or rerun live UCP."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("NO_LLM_CALLS", "true")

from raios.c1c5.receipt_identity import interpret_receipt_id, producer_receipt_identity
from raios.c1c5.receipts import build

HIST_ACK = (
    ROOT
    / ".ai-os"
    / "receipts"
    / "command-fabric"
    / "MSG-1787844821137190-c621b602.C2-OBS.ack.receipt.json"
)
HIST_ACK_SHA256 = "c2fa2d061fc1125d11adaf49adedcb061fabc0d19fc0008dfdb65e85c0e9ccff"
HIST_C5 = ROOT / ".ai-os" / "receipts" / "command-fabric" / "c1c5-task" / "415717063d4bdd51caba7583.receipt.json"
HIST_C5_SHA256 = "a289ce8e28817259b333994c9a061b66cb81d4c7afba8293707aadb20fa56342"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReceiptIdentityTests(unittest.TestCase):
    def test_MESSAGE_ID_COMPAT_ALIAS_NE_NEW_RECEIPT(self):
        raw = HIST_ACK.read_bytes()
        hist = json.loads(raw.decode("utf-8-sig"))
        self.assertNotIn("receipt_id", hist)
        self.assertEqual(hist["message_id"], "MSG-1787844821137190-c621b602")
        self.assertEqual(interpret_receipt_id(hist), hist["message_id"])
        self.assertEqual(_sha256(HIST_ACK), HIST_ACK_SHA256)
        produced = producer_receipt_identity(
            message_id=hist["message_id"],
            correlation_id="COR-UCP-PROOF-01A",
            task_id="RAIOS-C1-C5-TASK-DISPATCH-01A-LIVE-03",
        )
        self.assertEqual(produced["receipt_id"], hist["message_id"])
        self.assertEqual(produced["message_id"], hist["message_id"])
        self.assertTrue(produced["RECEIPT_ID_EQUALS_MESSAGE_ID"])
        self.assertNotEqual(produced, hist)
        self.assertEqual(_sha256(HIST_ACK), HIST_ACK_SHA256)
        self.assertEqual(HIST_ACK.read_bytes(), raw)

    def test_RECEIPT_ID_BOUND_TO_TASK_AND_CORRELATION(self):
        env = {
            "task_id": "RAIOS-C1-C5-TASK-DISPATCH-01",
            "correlation_id": "COR-TEST-C1C5-TASK-01",
            "idempotency_key": "idem-c1c5-health-01",
            "target": "C5",
            "requested_capability": "c5.self_inspect.health",
            "message_id": "MSG-TEST-RECEIPT-ID-01",
        }
        receipt = build(
            env=env,
            auth={"PRINCIPAL": "C1@AG", "AUTHORITY_SOURCE": "HMAC_FOUNDER_SESSION"},
            policy={"POLICY_RESULT": "ALLOW", "RISK_CLASS": "LOW"},
            ucp={"STATUS": "ACCEPTED_DRY_RUN", "NO_OP": False},
            capability={"INVOKED": True},
            status="COMPLETED",
        )
        self.assertEqual(receipt["receipt_id"], "MSG-TEST-RECEIPT-ID-01")
        self.assertEqual(receipt["message_id"], "MSG-TEST-RECEIPT-ID-01")
        self.assertTrue(receipt["RECEIPT_ID_EQUALS_MESSAGE_ID"])
        self.assertEqual(receipt["TASK_ID"], "RAIOS-C1-C5-TASK-DISPATCH-01")
        self.assertEqual(receipt["CORRELATION_ID"], "COR-TEST-C1C5-TASK-01")
        self.assertEqual(_sha256(HIST_C5), HIST_C5_SHA256)
        hist_c5 = json.loads(HIST_C5.read_text(encoding="utf-8-sig"))
        self.assertNotIn("receipt_id", hist_c5)
        self.assertIsNone(interpret_receipt_id(hist_c5))


if __name__ == "__main__":
    unittest.main()
