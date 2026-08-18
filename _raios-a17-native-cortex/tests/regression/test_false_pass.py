from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from ccee.certification import (  # noqa: E402
    AssertionRegistry,
    AtomicCertificationRunner,
    EvidenceLedger,
    FailClosed,
    FalsePassDetector,
)
from ccee.config import contains_forbidden_success  # noqa: E402
from ccee.ollama_runtime import OllamaServerError  # noqa: E402


def _runner(tmp: Path) -> AtomicCertificationRunner:
    return AtomicCertificationRunner(EvidenceLedger(tmp / "evidence", repo_root=REPO))


class FalsePassRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runner = _runner(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _failed(self, name, fn):
        result = self.runner.certify(name, fn, run_id="run-test")
        self.assertFalse(result["ok"])
        self.assertEqual(result["overall_status"], "FAILED")
        self.assertNotEqual(result["exit_code"], 0)
        self.assertFalse(result["success_receipt"])
        stdout = str(result.get("stdout") or "") + str(result.get("error") or "")
        self.assertFalse(contains_forbidden_success(stdout) and result["ok"])
        failures = list((self.root / "evidence" / "failures").glob("failure-*.json"))
        self.assertTrue(failures)
        successes = list((self.root / "evidence" / "successes").glob("success-*.json"))
        self.assertFalse(successes)
        return result

    def test_01_undefined_variable(self) -> None:
        def fn(reg: AssertionRegistry):
            return missing_name  # noqa: F821

        self._failed("undefined", fn)

    def test_02_missing_file(self) -> None:
        def fn(reg: AssertionRegistry):
            Path("/tmp/ccee-does-not-exist-a18").read_text(encoding="utf-8")

        self._failed("missing_file", fn)

    def test_03_child_exit_1(self) -> None:
        def fn(reg: AssertionRegistry):
            self.runner.run_child([sys.executable, "-c", "raise SystemExit(1)"])

        self._failed("child", fn)

    def test_04_http_500(self) -> None:
        def fn(reg: AssertionRegistry):
            raise OllamaServerError(500, "upstream")

        result = self._failed("http500", fn)
        self.assertIn("OLLAMA_SERVER_ERROR", result["error"])

    def test_05_malformed_json(self) -> None:
        def fn(reg: AssertionRegistry):
            json.loads("{")

        self._failed("json", fn)

    def test_06_hash_mismatch(self) -> None:
        def fn(reg: AssertionRegistry):
            from ccee.config import require_sha256

            require_sha256("deadbeef")

        self._failed("hash", fn)

    def test_07_model_missing(self) -> None:
        def fn(reg: AssertionRegistry):
            raise FailClosed("MODEL_MISSING:qwen3.6:35b-a3b")

        self._failed("model", fn)

    def test_08_ollama_unavailable(self) -> None:
        def fn(reg: AssertionRegistry):
            raise FailClosed("OLLAMA_UNAVAILABLE:connection refused")

        self._failed("ollama", fn)

    def test_09_timeout(self) -> None:
        def fn(reg: AssertionRegistry):
            self.runner.run_child([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2)

        self._failed("timeout", fn)

    def test_10_invalid_report(self) -> None:
        def fn(reg: AssertionRegistry):
            report = {"Draft": True}
            reg.require("ResponseHash", "ResponseHash" in report)
            reg.require("Final", "Final" in report)

        self._failed("report", fn)

    def test_11_exception_after_partial_pass(self) -> None:
        def fn(reg: AssertionRegistry):
            print("PASS")
            raise RuntimeError("boom-after-partial")

        result = self._failed("partial", fn)
        self.assertIn("FALSE_PASS_DETECTED", result["error"])

    def test_12_stale_success_receipt(self) -> None:
        def fn(reg: AssertionRegistry):
            path = self.root / "evidence" / "successes" / "stale.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"run_id": "old"}), encoding="utf-8")
            self.runner.ledger.reject_stale_success(path, "run-test")

        self._failed("stale", fn)

    def test_false_pass_impossible_on_success_path(self) -> None:
        def fn(reg: AssertionRegistry):
            reg.require("ResponseHash", True)
            reg.require("Final", True)
            return {"Final": True, "ResponseHash": "abc"}

        result = self.runner.certify("ok-path", fn, run_id="run-test")
        self.assertTrue(result["ok"])
        self.assertEqual(result["overall_status"], "GATES_SATISFIED")
        self.assertFalse(contains_forbidden_success(result["overall_status"]))


if __name__ == "__main__":
    unittest.main()
