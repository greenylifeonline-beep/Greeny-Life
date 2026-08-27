"""AG execution of C7 donor suite v1.1 via staging runner."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / ".ai-os" / "staging" / "rif-c7-integration" / "ag-runner"
if str(RUNNER) not in sys.path:
    sys.path.insert(0, str(RUNNER))

from run_suite import run_all  # noqa: E402


class RIFDonorSuiteV11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_all()

    def test_all_defined_tests_executed(self):
        self.assertEqual(self.report["TESTS_DISCOVERED"], 56)
        self.assertEqual(self.report["TESTS_EXECUTED"], 56)
        self.assertEqual(self.report["TESTS_FAIL"], 0)
        self.assertEqual(self.report["TESTS_ERROR"], 0)
        self.assertEqual(self.report["TESTS_PASS"], 56)
        self.assertFalse(self.report["C7_TEST_EXECUTION_PROVEN"])
        self.assertTrue(self.report["AG_TEST_EXECUTION_PROVEN"])
        self.assertFalse(self.report["WAL_WRITTEN"])


if __name__ == "__main__":
    unittest.main()
