#!/usr/bin/env python3
"""Run the Learning Fabric V2 reference tests and emit a certification record."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_learning_fabric_v2 import LearningFabricV2Tests  # noqa: E402

REQUIRED = [
    "MODULE_IMPORTS_PASS",
    "DATACLASS_CONSTRUCTION_PASS",
    "IMMUTABLE_TRACE_PASS",
    "TRACE_IDEMPOTENCY_PASS",
    "ILLEGAL_DEBT_TRANSITION_REJECTED",
    "DEBT_READING_ONLY_PAYMENT_REJECTED",
    "DEBT_TRANSFER_FAILURE_REJECTED",
    "COMPETENCY_WITHOUT_EVIDENCE_REJECTED",
    "TEACHER_WRONG_STUDENT_RIGHT",
    "TEACHER_RIGHT_STUDENT_WRONG",
    "BOTH_WRONG",
    "TEACHER_DISAGREEMENT",
    "SYNTHETIC_TRUTH_ESCALATION_REJECTED",
    "STALE_KNOWLEDGE_REVALIDATION_REQUIRED",
    "KNOWLEDGE_ILLEGAL_MATURITY_JUMP_REJECTED",
    "RETROSPECTIVE_FACT_INFERENCE_SEPARATION",
    "TEACHER_EARLY_RETIREMENT_REJECTED",
    "MULTI_CONTEXT_TRANSFER_REQUIRED",
    "COGNITIVE_COMPRESSION_PROVENANCE_PRESERVED",
    "DATABASE_TRANSACTION_ROLLBACK_PASS",
    "RESTART_PERSISTENCE_PASS",
    "IDEMPOTENT_REPLAY_PASS",
]


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(LearningFabricV2Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    names = [
        name[5:]
        for name in dir(LearningFabricV2Tests)
        if name.startswith("test_")
    ]
    failed = {
        (test.id().split(".")[-1].removeprefix("test_"))
        for test, _ in result.failures + result.errors
    }
    named = {name: ("FAIL" if name in failed else "PASS") for name in REQUIRED}
    missing = [name for name in REQUIRED if name not in names]
    payload = {
        "tests_total": result.testsRun,
        "tests_passed": result.testsRun - len(result.failures) - len(result.errors),
        "tests_failed": len(result.failures) + len(result.errors),
        "required_named_tests": named,
        "required_tests_missing": missing,
        "package_import_pass": named.get("MODULE_IMPORTS_PASS") == "PASS",
        "database_migration_pass": named.get("RESTART_PERSISTENCE_PASS") == "PASS",
        "learning_debt_gate_pass": named.get("ILLEGAL_DEBT_TRANSITION_REJECTED") == "PASS"
        and named.get("DEBT_READING_ONLY_PAYMENT_REJECTED") == "PASS"
        and named.get("DEBT_TRANSFER_FAILURE_REJECTED") == "PASS",
        "competency_gate_pass": named.get("COMPETENCY_WITHOUT_EVIDENCE_REJECTED") == "PASS",
        "epistemic_gate_pass": named.get("KNOWLEDGE_ILLEGAL_MATURITY_JUMP_REJECTED") == "PASS"
        and named.get("STALE_KNOWLEDGE_REVALIDATION_REQUIRED") == "PASS",
        "synthetic_governance_pass": named.get("SYNTHETIC_TRUTH_ESCALATION_REJECTED") == "PASS",
        "retrospective_harvest_pass": named.get("RETROSPECTIVE_FACT_INFERENCE_SEPARATION") == "PASS",
        "dependency_decay_pass": named.get("TEACHER_EARLY_RETIREMENT_REJECTED") == "PASS"
        and named.get("MULTI_CONTEXT_TRANSFER_REQUIRED") == "PASS",
    }
    payload["verdict"] = (
        "REFERENCE_READY"
        if result.wasSuccessful() and not missing and all(v == "PASS" for v in named.values())
        else "REFERENCE_FAILED"
    )
    out = ROOT / "CERTIFICATION.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["verdict"] == "REFERENCE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
