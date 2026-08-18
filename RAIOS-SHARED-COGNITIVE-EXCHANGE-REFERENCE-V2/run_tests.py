#!/usr/bin/env python3
"""Run Cognitive Exchange V2 tests and emit certification + optional benchmarks."""

from __future__ import annotations

import json
import platform
import sqlite3
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_exchange_v2 import ExchangeV2Tests  # noqa: E402

REQUIRED = [
    "MODULE_IMPORT_PASS",
    "DB_MIGRATION_PASS",
    "OBJECT_ATOMIC_WRITE_PASS",
    "OBJECT_DUPLICATE_CONCURRENCY_PASS",
    "INTERRUPTED_OBJECT_RECOVERY_PASS",
    "ORPHAN_RECONCILIATION_PASS",
    "METADATA_WITHOUT_OBJECT_DETECTED",
    "OBJECT_HASH_TAMPER_DETECTED",
    "PATH_TRAVERSAL_REJECTED",
    "WINDOWS_DRIVE_ESCAPE_REJECTED",
    "UNC_ESCAPE_REJECTED",
    "SYMLINK_OR_JUNCTION_ESCAPE_REJECTED",
    "WINDOWS_CASE_COLLISION_HANDLED",
    "TASK_ILLEGAL_TRANSITION_REJECTED",
    "DUPLICATE_TASK_IDEMPOTENT",
    "RESULT_IDEMPOTENT",
    "HANDOFF_IDEMPOTENT",
    "LEASE_OVERLAP_REJECTED",
    "LEASE_FENCING_PASS",
    "STALE_WORKER_REJECTED",
    "READ_ONLY_VERIFIER_CONCURRENT_PASS",
    "EVENT_APPEND_PASS",
    "EVENT_CHAIN_INTEGRITY_PASS",
    "EVENT_CORRUPTION_DETECTED",
    "REPLAY_PASS",
    "REPLAY_IDEMPOTENCY_PASS",
    "CRASH_REPLAY_PASS",
    "QUARANTINE_ISOLATION_PASS",
    "FTS_TRUST_FILTER_PASS",
    "CONTEXT_CAPSULE_CANONICAL_HASH_PASS",
    "RESTART_PERSISTENCE_PASS",
]


def main() -> int:
    started = time.perf_counter()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(ExchangeV2Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    runtime = time.perf_counter() - started
    names = [name[5:] for name in dir(ExchangeV2Tests) if name.startswith("test_")]
    failed = {
        test.id().split(".")[-1].removeprefix("test_")
        for test, _ in result.failures + result.errors
    }
    named = {name: ("FAIL" if name in failed else "PASS") for name in REQUIRED}
    missing = [name for name in REQUIRED if name not in names]
    from run_benchmarks import run_benchmarks

    benches = run_benchmarks()
    payload = {
        "tests_total": result.testsRun,
        "tests_passed": result.testsRun - len(result.failures) - len(result.errors),
        "tests_failed": len(result.failures) + len(result.errors),
        "exit_code": 0 if result.wasSuccessful() and not missing else 1,
        "runtime_seconds": round(runtime, 4),
        "environment": {
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "sqlite_version": sqlite3.sqlite_version,
            "machine": platform.machine(),
        },
        "required_named_tests": named,
        "required_tests_missing": missing,
        "benchmarks": benches,
        "verdict": (
            "REFERENCE_READY"
            if result.wasSuccessful() and not missing and all(v == "PASS" for v in named.values())
            else "REFERENCE_FAILED"
        ),
    }
    (ROOT / "CERTIFICATION.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
