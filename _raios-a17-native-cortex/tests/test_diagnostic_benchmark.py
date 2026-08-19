"""C14 diagnostic benchmark. Printed PASS is never the score."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from ccee.certification import AtomicCertificationRunner, EvidenceLedger, FailClosed, FalsePassDetector  # noqa: E402
from ccee.engine import CCEE  # noqa: E402
from ccee.process_kernel import encoding_safe_run  # noqa: E402
from ccee.root_cause import classify_failure, diagnose  # noqa: E402


CASES = (
    ("encoding", {"decode_replaced": True, "integrity": "DECODE_REPLACED"}, "UNICODE_DECODE"),
    ("missing_file", {"missing_final": True}, "MISSING_FINAL"),
    ("stale_artifact", {"evidence_sha": "dead", "failed": True}, "REPORT_INTEGRITY"),
    ("bad_json", {"failed": True, "child_exit": 1, "signatures": ["json"]}, "CHILD_EXIT_NONZERO"),
    ("timeout", {"timeout": True}, "TIMEOUT"),
    ("subprocess_nonzero", {"child_exit": 2, "failed": True}, "CHILD_EXIT_NONZERO"),
    ("false_pass", {"printed_pass": True, "failed": True, "child_exit": 1}, "FALSE_PASS"),
    ("model_unavailable", {"model": "missing", "failed": True}, "MODEL_UNAVAILABLE"),
    ("tool_unavailable", {"tool": "rg", "unavailable": True}, "TOOL_UNAVAILABLE"),
    ("permission", {"permission_denied": True}, "PERMISSION_DENIED"),
)


class DiagnosticBenchmark(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ccee = CCEE(Path(self.tmp.name) / "ccee", repo_root=REPO)
        self.runner = AtomicCertificationRunner(EvidenceLedger(Path(self.tmp.name) / "ev", repo_root=REPO))
        self.hits = 0

    def tearDown(self) -> None:
        self.ccee.close()
        self.tmp.cleanup()

    def test_root_cause_accuracy(self) -> None:
        correct = 0
        for name, payload, expected in CASES:
            family = classify_failure(payload)
            if family == expected:
                correct += 1
            else:
                self.fail(f"{name}: got {family} expected {expected}")
        self.assertEqual(correct, len(CASES))

    def test_false_pass_attempt_blocked(self) -> None:
        detector = FalsePassDetector()
        with self.assertRaises(FailClosed):
            detector.judge_child("PASS\n", "", 1)
        with self.assertRaises(FailClosed):
            detector.judge_child("PASS\n", "", 0)

    def test_missing_executable(self) -> None:
        with self.assertRaises(FailClosed):
            encoding_safe_run(["raios-definitely-missing-binary-41f5"])

    def test_duplicate_event_dedup(self) -> None:
        a = self.ccee.wal.append("OBSERVATION", "bench", {"k": 1}, idempotency_key="dup-bench")
        b = self.ccee.wal.append("OBSERVATION", "bench", {"k": 1}, idempotency_key="dup-bench")
        self.assertEqual(a.event_id, b.event_id)

    def test_graph_has_evidence(self) -> None:
        obs = encoding_safe_run([sys.executable, "-c", "print('PASS'); raise SystemExit(1)"])
        graph = diagnose(self.ccee.causal, obs, printed_pass=True)
        self.assertTrue(graph["evidence"])
        self.assertEqual(graph["family"], "FALSE_PASS")


if __name__ == "__main__":
    unittest.main()
