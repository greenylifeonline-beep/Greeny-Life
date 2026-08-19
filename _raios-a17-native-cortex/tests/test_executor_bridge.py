from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
import sys

sys.path.insert(0, str(ROOT))

from ccee.config import FailClosed  # noqa: E402
from ccee.engine import CCEE  # noqa: E402
from ccee.executor_bridge import discover_executors  # noqa: E402
from ccee.training_loop import LiveCognitiveLoop  # noqa: E402


class ExecutorBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ccee = CCEE(Path(self.tmp.name) / "ccee", repo_root=REPO)

    def tearDown(self) -> None:
        self.ccee.close()
        self.tmp.cleanup()

    def test_discover_does_not_authorize_invocation(self) -> None:
        disc = discover_executors()
        self.assertFalse(disc["invocation_authorized"])
        self.assertTrue(disc["credential_env_names_redacted"])
        self.assertNotIn("token", str(disc).lower() + str(disc.get("gh_copilot")))

    def test_observe_dispatch_completes_without_mutation(self) -> None:
        receipt = self.ccee.nervous.executor.dispatch(
            {
                "task_id": "GL-EX-TEST",
                "attempt": 1,
                "actor": "RAIOS",
                "target": "cursor",
                "intent": "observe",
                "mutating": False,
                "risk": "LOW",
                "permission_scope": ["cli version probe"],
            }
        )
        self.assertEqual(receipt["schema"], "raios.executor-receipt.v1")
        self.assertEqual(receipt["overall_status"], "STRUCTURED")
        self.assertIn("ACK", receipt["states"])
        self.assertIn("COMPLETED", receipt["states"])
        self.assertEqual(receipt["result"]["files_touched"], [])
        self.assertFalse(receipt["result"]["permanent_permission"])
        self.assertFalse(receipt["result"]["credentials_exposed"])
        self.assertNotEqual(receipt["result"].get("work_gate"), "READY_FOR_REAL_PROJECT_WORK")

    def test_mutating_dispatch_denied(self) -> None:
        receipt = self.ccee.nervous.executor.dispatch(
            {
                "task_id": "GL-EX-MUT",
                "intent": "patch",
                "mutating": True,
                "risk": "HIGH",
                "target": "cursor",
            }
        )
        self.assertEqual(receipt["overall_status"], "FAILED")
        self.assertIn("PERMISSION_DENIED", receipt["states"])

    def test_idempotent_observe(self) -> None:
        env = {"task_id": "GL-EX-DUP", "attempt": 1, "intent": "observe", "mutating": False, "target": "gh"}
        a = self.ccee.nervous.executor.dispatch(env)
        b = self.ccee.nervous.executor.dispatch(env)
        self.assertEqual(a["receipt_id"], b["receipt_id"])
        self.assertEqual(a["sha256"], b["sha256"])

    def test_execution_authority_fail_closed(self) -> None:
        with self.assertRaises(FailClosed):
            self.ccee.nervous.executor.dispatch({"task_id": "x", "execution_authority": True, "mutating": False})

    def test_supervisor_repair_still_forbidden(self) -> None:
        with self.assertRaises(FailClosed):
            self.ccee.nervous.supervisor.invoke_cursor("repair")

    def test_gl_ex_strategy(self) -> None:
        loop = LiveCognitiveLoop(self.ccee, REPO)
        turn = loop.ask_raios(task_id="GL-EX-LOOP", intent="discover executors")
        self.assertEqual((turn.get("result") or {}).get("strategy"), "which_executors")
        self.assertTrue(turn["action_taken"])


if __name__ == "__main__":
    unittest.main()
