from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from ccee.config import FailClosed  # noqa: E402
from ccee.engine import CCEE  # noqa: E402
from ccee.process_kernel import encoding_safe_run  # noqa: E402
from ccee.repair_memory import RepairMemory  # noqa: E402
from ccee.root_cause import FALSE_PASS_REPAIR_ID, KERNEL_REPAIR_ID, diagnose  # noqa: E402
from ccee.shadow_lab import LIFECYCLE, ShadowRepairLab  # noqa: E402
from ccee.training_loop import LiveCognitiveLoop  # noqa: E402


class DiagnosticHardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ccee = CCEE(Path(self.tmp.name) / "ccee", repo_root=REPO)

    def tearDown(self) -> None:
        self.ccee.close()
        self.tmp.cleanup()

    def test_false_pass_graph_distinguishes_root_from_secondary(self) -> None:
        obs = encoding_safe_run([sys.executable, "-c", "print('PASS'); raise SystemExit(1)"])
        graph = diagnose(self.ccee.causal, obs, printed_pass=True)
        self.assertEqual(graph["family"], "FALSE_PASS")
        self.assertIn("ROOT_CAUSE", graph["kinds"])
        self.assertIn("SECONDARY_FAILURE", graph["kinds"])
        self.assertIn("ASSERTION", graph["kinds"])
        self.assertNotEqual(graph["root_cause"], graph["secondary_failure"])
        self.assertGreaterEqual(graph["confidence"], 0.5)
        self.assertTrue(graph["evidence"])
        self.assertFalse(graph["tested"])
        rels = {e["relation"] for e in graph["edges"]}
        self.assertTrue({"CAUSED", "TRIGGERED", "CONTRADICTS", "PROPAGATED_TO"} & rels)

    def test_encoding_graph_not_used_for_timeout(self) -> None:
        graph = diagnose(self.ccee.causal, None, error="timeout waiting for child", printed_pass=False)
        self.assertEqual(graph["family"], "TIMEOUT")
        self.assertEqual(graph["root_cause"], "child_timeout")
        self.assertNotIn("implicit_locale_subprocess_decode", [self.ccee.causal.nodes[n]["payload"]["id"] for n in graph["nodes"]])

    def test_integrity_shadow_lifecycle(self) -> None:
        lab = ShadowRepairLab().run_integrity_session(Path(self.tmp.name) / "integrity")
        self.assertTrue(lab["executed"])
        self.assertTrue(lab["repair_success"])
        self.assertTrue(lab["transfer_success"])
        self.assertEqual(lab["regression_count"], 0)
        self.assertFalse(lab["canonical_promotion"])
        self.assertEqual(set(lab["stages"]), set(LIFECYCLE))

    def test_repair_memory_matches_false_pass_not_encoding(self) -> None:
        memory = RepairMemory(self.ccee.ledger)
        matched = memory.match({"printed_pass": True, "failed": True, "child_exit": 1})
        self.assertIsNotNone(matched)
        self.assertEqual(matched["repair_id"], FALSE_PASS_REPAIR_ID)
        self.assertFalse(matched["replay_authorized"])
        enc = memory.match({"decode_replaced": True, "integrity": "DECODE_REPLACED"})
        self.assertEqual(enc["repair_id"], KERNEL_REPAIR_ID)

    def test_false_pass_plan_requires_shadow(self) -> None:
        plan = self.ccee.nervous.planner.plan({"printed_pass": True, "failed": True, "child_exit": 1})
        self.assertEqual(plan["repair_id"], FALSE_PASS_REPAIR_ID)
        self.assertTrue(plan["shadow_required"])
        self.assertFalse(plan["auto_apply"])
        self.assertFalse(plan["canonical_promotion"])

    def test_gl_fp_uses_print_pass_strategy(self) -> None:
        loop = LiveCognitiveLoop(self.ccee, REPO)
        turn = loop.ask_raios(task_id="GL-FP-TEST", intent="hunt false PASS")
        self.assertEqual((turn.get("result") or {}).get("strategy"), "naive_print_pass")
        self.assertTrue(turn["action_taken"])

    def test_unknown_edge_fail_closed(self) -> None:
        with self.assertRaises(FailClosed):
            self.ccee.causal.add("SYMPTOM", {"id": "x"}, parent=None, relation="NOT_AN_EDGE")


if __name__ == "__main__":
    unittest.main()
