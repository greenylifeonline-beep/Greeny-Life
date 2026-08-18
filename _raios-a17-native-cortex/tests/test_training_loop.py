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
from ccee.schemas import CognitiveTurn  # noqa: E402
from ccee.training_loop import LiveCognitiveLoop  # noqa: E402


class TrainingLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ccee = CCEE(Path(self.tmp.name) / "ccee", repo_root=REPO)
        self.loop = LiveCognitiveLoop(self.ccee, REPO)

    def tearDown(self) -> None:
        self.ccee.close()
        self.tmp.cleanup()

    def test_turn_has_no_execution_authority(self) -> None:
        with self.assertRaises(FailClosed):
            CognitiveTurn(task_id="t", actor="RAIOS", intent="x", execution_authority=True)

    def test_raios_executes_search_not_prose(self) -> None:
        turn = self.loop.ask_raios(task_id="GL-ENC-TEST", intent="find unsafe subprocess callers")
        self.assertEqual(turn["actor"], "RAIOS")
        self.assertTrue(turn["action_taken"])
        self.assertIn("rg", str(turn["action_taken"]))
        self.assertFalse(turn["execution_authority"])
        self.assertGreaterEqual(len((turn["result"] or {}).get("hits") or []), 0)

    def test_identical_retry_forbidden(self) -> None:
        self.loop.ask_raios(task_id="GL-DUP", intent="x", strategy="naive_repo_rg")
        with self.assertRaises(FailClosed) as ctx:
            self.loop.ask_raios(task_id="GL-DUP", intent="x", strategy="naive_repo_rg")
        self.assertIn("IDENTICAL_RETRY_FORBIDDEN", str(ctx.exception))

    def test_three_attempts_then_block_or_adapt(self) -> None:
        t1 = self.loop.ask_raios(task_id="GL-THREE", intent="x")
        t2 = self.loop.ask_raios(task_id="GL-THREE", intent="x")
        t3 = self.loop.ask_raios(task_id="GL-THREE", intent="x")
        self.assertEqual(t1["attempt"], 1)
        self.assertEqual(t2["attempt"], 2)
        self.assertEqual(t3["attempt"], 3)
        blocked = self.loop.ask_raios(task_id="GL-THREE", intent="x")
        self.assertEqual(blocked["queue"], "BLOCKED")
        self.assertIn("MAX_ATTEMPTS", str(blocked["failure_class"]))

    def test_critic_persists_teacher_event(self) -> None:
        self.loop.ask_raios(task_id="GL-CRIT", intent="x")
        critique = self.loop.critique(
            task_id="GL-CRIT",
            scores={
                "diagnosis_accuracy": 0.4,
                "root_cause_quality": 0.5,
                "evidence_quality": 0.6,
                "plan_quality": 0.5,
                "tool_selection": 0.7,
                "execution_success": 0.7,
                "verification_quality": 0.3,
                "risk_awareness": 0.6,
                "efficiency": 0.4,
                "confidence_calibration": 0.4,
                "learning_quality": 0.3,
                "transfer_success": 0.0,
            },
            missed=["archive_filter"],
            supplied=["exclude archive"],
            notes=["naive search includes archive"],
        )
        self.assertEqual(critique["actor"], "CURSOR")
        self.assertTrue(critique["teacher_used"])
        types = [e.event_type for e in self.ccee.wal.replay()]
        self.assertIn("TEACHER_CRITIQUE", types)

    def test_continuity_review_written(self) -> None:
        review = self.loop.continuity_review()
        self.assertEqual(review["schema"], "raios.session-start-cognitive-review.v1")
        self.assertTrue(Path(review["path"]).is_file())
        self.assertIsInstance(review["BLOCKERS"], list)

    def test_attempts_restore_from_ledger(self) -> None:
        self.loop.ask_raios(task_id="GL-REST", intent="x")
        again = LiveCognitiveLoop(self.ccee, REPO)
        self.assertEqual(again._attempts["GL-REST"], 1)


if __name__ == "__main__":
    unittest.main()
