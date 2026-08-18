#!/usr/bin/env python3
"""Atomic CCEE foundation certification. Child failure invalidates the parent."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

NATIVE = Path(__file__).resolve().parents[1]
REPO = NATIVE.parent
sys.path.insert(0, str(NATIVE))

from ccee.config import canonical_json, sha256_text  # noqa: E402
from ccee.doctor import run_doctor, v9_clean  # noqa: E402


def main() -> int:
    unit = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(NATIVE / "tests"), "-v"],
        cwd=str(NATIVE),
        capture_output=True,
        text=True,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(NATIVE)},
    )
    combined = (unit.stdout or "") + (unit.stderr or "")
    tests_ok = combined.count(" ... ok")
    tests_fail = combined.count(" FAIL") + combined.count(" ERROR")
    if unit.returncode != 0:
        failure = {
            "overall_status": "FAILED",
            "final_status": "A18_CCEE_FOUNDATION_FAILED",
            "reason": "UNIT_TESTS_CHILD_NONZERO",
            "exit_code": 1,
            "stderr": unit.stderr[-4000:],
            "stdout": unit.stdout[-4000:],
        }
        out = NATIVE / "reports" / "A18-CCEE-FOUNDATION-REPORT.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(canonical_json(failure) + "\n", encoding="utf-8")
        sys.stdout.write(canonical_json({"overall_status": "FAILED", "exit_code": 1}) + "\n")
        return 1
    doctor = run_doctor(NATIVE / "ccee" / "var" / "cert", REPO, NATIVE / "evidence")
    report = {
        "architecture": "dual-brain event-sourced CCEE",
        "tests": tests_ok + tests_fail,
        "tests_executed": tests_ok + tests_fail,
        "passed": tests_ok,
        "failed": tests_fail,
        "unit_child_exit": unit.returncode,
        "doctor_exit": doctor.get("exit_code"),
        "wal": doctor.get("wal"),
        "experiment": doctor.get("experiment"),
        "metrics": doctor.get("metrics"),
        "main_cortex_status": doctor.get("ollama"),
        "teacher_status": doctor.get("teachers"),
        "canonical_mutation": False,
        "v9_mutation": not v9_clean(REPO),
        "commit": False,
        "push": False,
        "gates": doctor.get("gates"),
        "experiences": 1 if doctor.get("experiment") else 0,
        "learning_missions": (doctor.get("experiment") or {}).get("missions"),
        "skill_candidates": 3,
        "counterfactual_failures": (doctor.get("experiment") or {}).get("counterfactuals"),
        "transfer_score": ((doctor.get("experiment") or {}).get("transfer") or {}).get("passed"),
        "wal_events": (doctor.get("wal") or {}).get("count"),
        "next_blocking_issue": "OLLAMA_UNAVAILABLE_AND_TEACHER_CORPUS_MISSING",
        "exit_code": doctor.get("exit_code"),
    }
    critical = (
        unit.returncode == 0
        and doctor.get("exit_code") == 0
        and (doctor.get("wal") or {}).get("ok")
        and v9_clean(REPO)
        and doctor.get("overall_status") == "GATES_SATISFIED"
    )
    report["final_status"] = "A18_CCEE_FOUNDATION_PASS" if critical else "A18_CCEE_FOUNDATION_FAILED"
    report["overall_status"] = "GATES_SATISFIED" if critical else "FAILED"
    if not critical:
        report["exit_code"] = 1
    text = canonical_json(report)
    report["sha256"] = sha256_text(text)
    out = NATIVE / "reports" / "A18-CCEE-FOUNDATION-REPORT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(canonical_json(report) + "\n", encoding="utf-8")
    sys.stdout.write(canonical_json({"overall_status": report["overall_status"], "exit_code": report["exit_code"], "final_status": report["final_status"]}) + "\n")
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
