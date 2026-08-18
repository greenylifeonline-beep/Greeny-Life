from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from ccee.config import FailClosed, contains_forbidden_success, authoritative_exit  # noqa: E402
from ccee.engine import CCEE  # noqa: E402
from ccee.first_experiment import diagnose_atomic_failure  # noqa: E402
from ccee.process_kernel import encoding_safe_run  # noqa: E402
from ccee.root_cause import classify_failure  # noqa: E402
from ccee.work_gate import CLOSED, DEGRADED  # noqa: E402


class NervousSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ccee = CCEE(Path(self.tmp.name) / "ccee", repo_root=REPO)

    def tearDown(self) -> None:
        self.ccee.close()
        self.tmp.cleanup()

    def test_d1_never_returns_none_on_invalid_utf8(self) -> None:
        obs = encoding_safe_run(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xe9\\n')"]
        )
        self.assertIsNotNone(obs.stdout)
        self.assertIsNotNone(obs.stderr)
        self.assertTrue(obs.decode_replaced)
        self.assertEqual(obs.integrity, "DECODE_REPLACED")
        with self.assertRaises(UnicodeDecodeError):
            subprocess.run(
                [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xe9\\n')"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
            )

    def test_d7_pass_plus_exit_1_is_not_success(self) -> None:
        with self.assertRaises(FailClosed) as ctx:
            self.ccee.cert.run_child([sys.executable, "-c", "print('PASS'); raise SystemExit(1)"])
        self.assertIn("FALSE_PASS", str(ctx.exception))
        self.assertFalse(contains_forbidden_success(str(ctx.exception)) and "GATES_SATISFIED" in str(ctx.exception))

    def test_d4_false_pass_not_shadowed_by_responsehash(self) -> None:
        family = diagnose_atomic_failure(
            {
                "signatures": ["missing_ResponseHash", "false_PASS_after_failure"],
                "printed_pass": True,
                "failed": True,
                "child_exit": 1,
            }
        )
        self.assertEqual(family, "FALSE_PASS")
        self.assertEqual(classify_failure({"http": 200, "invalid_semantic": True, "report_integrity": False}), "HTTP_200_INVALID_SEMANTIC")

    def test_d11_work_gate_stays_closed_without_cortex(self) -> None:
        ns = self.ccee.nervous.certify_self(Path(self.tmp.name) / "lab")
        self.assertTrue(ns["lab"]["executed"])
        self.assertNotEqual(ns["boot"]["gate"]["state"], "READY_FOR_REAL_PROJECT_WORK")
        self.assertIn(ns["boot"]["gate"]["state"], {CLOSED, DEGRADED})
        self.assertFalse(ns["mastery_claimed"])
        with self.assertRaises(FailClosed):
            self.ccee.nervous.broker.request_lease(
                scope=["RAIOS/V9"],
                duration_s=10,
                risk="HIGH",
                purpose="canonical",
                mutating=True,
            )

    def test_d10_cursor_invoke_forbidden(self) -> None:
        with self.assertRaises(FailClosed):
            self.ccee.nervous.supervisor.invoke_cursor("repair")

    def test_d2_supervisor_is_authoritative(self) -> None:
        boot = self.ccee.nervous.supervisor.evaluate_boot(
            {
                "process_kernel": True,
                "run_supervisor": True,
                "failure_capture": True,
                "anti_false_pass": True,
                "work_gate": True,
                "experience_capture": True,
                "shadow_lab": True,
                "main_cortex": False,
                "shared_state": True,
                "memory": True,
                "permission_system": True,
            }
        )
        self.assertEqual(boot["overall_status"], "DEGRADED_DIAGNOSTIC_ACTIVE")
        self.assertNotEqual(boot["gate"]["state"], "READY_FOR_REAL_PROJECT_WORK")

    def test_d7_zero_exit_is_not_coerced_to_one(self) -> None:
        self.assertEqual(authoritative_exit(0), 0)
        self.assertEqual(authoritative_exit(None), 1)
        self.assertEqual(authoritative_exit(2), 2)


if __name__ == "__main__":
    unittest.main()
