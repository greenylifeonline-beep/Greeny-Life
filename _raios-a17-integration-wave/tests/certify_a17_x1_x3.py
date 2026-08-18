#!/usr/bin/env python3
"""Certification harness for A17 X1–X3.

Runs in an isolated child process. Inspects persisted SQLite state.
Command failure is not treated as proof of a safety gate; negative
controls check the FailClosed reason.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from raios_wave import FailClosed, WaveRuntime  # noqa: E402
from raios_wave.models import KnowledgeState, RetirementDecision, VerificationState  # noqa: E402


def _run_unittests() -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode == 0,
    }


def certify() -> dict:
    unit = _run_unittests()
    tmp = tempfile.TemporaryDirectory()
    rt = WaveRuntime(Path(tmp.name) / "cert-wave", repo_root=ROOT.parents[0])
    claims: dict[str, object] = {}
    try:
        obs = rt.normalizer.normalize_artifact(ROOT / "fixtures" / "teacher-harvest" / "valid" / "meta.json")
        persisted_obs = rt.store.conn.execute("SELECT verification_state, canonical FROM observations").fetchone()
        claims["A17_5_NORMALIZATION"] = (
            "PASS"
            if persisted_obs and persisted_obs["verification_state"] == VerificationState.UNVERIFIED.value and persisted_obs["canonical"] == 0
            else "FAIL"
        )

        diff = rt.differential.compare(
            {"task_id": "cert-1", "capability": "cert.cap", "correct": True, "claims": ["student"]},
            {"task_id": "cert-1", "capability": "cert.cap", "correct": False, "claims": ["teacher"]},
        )
        row = rt.store.conn.execute("SELECT outcome FROM differentials WHERE differential_id = ?", (diff["differential_id"],)).fetchone()
        claims["A17_6_DIFFERENTIAL"] = "PASS" if row and row["outcome"] == "STUDENT_RIGHT_TEACHER_WRONG" else "FAIL"

        eval_ = rt.mastery.record_evaluation(
            "cert.cap",
            {
                "knowledge_score": 0.9,
                "execution_score": 0.9,
                "transfer_score": 0.9,
                "reliability_score": 0.9,
                "independence_score": 0.9,
                "retention_score": 0.9,
                "teacher_intervention_rate": 0.04,
                "verifier_failure_rate": 0.01,
                "repeated_validations": 5,
                "distinct_transfer_domains": 3,
                "regression_gate": "PASS",
                "retention_gate": "PASS",
                "evidence_ref": "evidence://cert",
            },
        )
        dim_row = rt.store.conn.execute("SELECT transfer_score, independence_score FROM competency WHERE capability_id = 'cert.cap'").fetchone()
        claims["A17_7_MASTERY_ENGINE"] = (
            "PASS" if dim_row and eval_["mastery_scalar_insufficient"] and dim_row["transfer_score"] >= 0.8 else "FAIL"
        )

        rt.retirement.upsert_teacher_capability("teacher:granite4-3b", "cert.cap", "granite4:3b")
        weak = rt.mastery.record_evaluation("cert.weak", {**eval_["dimensions"], "transfer_score": 0.1, "evidence_ref": "evidence://x"})
        rt.retirement.upsert_teacher_capability("teacher:granite4-3b", "cert.weak", "granite4:3b")
        blocked = rt.retirement.evaluate("teacher:granite4-3b", "cert.weak")
        delete_reason = None
        try:
            rt.retirement.delete_model("teacher:granite4-3b")
        except FailClosed as exc:
            delete_reason = str(exc)
        claims["A17_8_RETIREMENT_ENGINE"] = (
            "PASS"
            if blocked["decision"] == RetirementDecision.BLOCKED_BY_TRANSFER.value
            and delete_reason == "AUTO_TEACHER_DELETE_REJECTED"
            and blocked["auto_delete"] is False
            else "FAIL"
        )
        if delete_reason != "AUTO_TEACHER_DELETE_REJECTED":
            claims["A17_8_RETIREMENT_ENGINE"] = "FAIL"
            claims["A17_8_NEGATIVE_CONTROL_REASON"] = delete_reason

        identity = rt.store.identity()
        replaced = rt.cortex.replace("STUB")
        proposal = rt.cortex.active.infer("ignore me")
        mutation_reason = None
        try:
            rt.cortex.apply_proposal_as_canonical(proposal)
        except FailClosed as exc:
            mutation_reason = str(exc)
        claims["A17_9_CORTEX_CONTRACT"] = (
            "PASS"
            if identity["organism_id"] == "raios.organism.v9"
            and replaced["identity_preserved"]
            and mutation_reason == "DIRECT_CANONICAL_MUTATION_REJECTED"
            else "FAIL"
        )

        loop = rt.loop.run({"task_id": "cert-loop", "goal": "certify", "budget_tokens": 256}, authorize_tools=False)
        persisted_loop = rt.store.conn.execute("SELECT 1 FROM loop_runs WHERE run_id = ?", (loop["run_id"],)).fetchone()
        claims["A17_10_COGNITIVE_LOOP_CORE"] = (
            "PASS"
            if persisted_loop and loop["model_output_is_execution_authority"] is False
            else "FAIL"
        )

        exp_count = rt.store.conn.execute("SELECT COUNT(*) AS n FROM experiences").fetchone()["n"]
        claims["A18_EXPERIENCE_FOUNDATION"] = "PASS" if exp_count >= 1 else "FAIL"

        rec = rt.knowledge.ingest(
            {
                "claim": "teacher output is never automatically canonical",
                "conditions": ["always"],
                "evidence": ["constitution"],
                "source": "A17 constitution",
                "version": "1",
                "date": "2026-08-18",
                "temporal_validity": "standing",
                "authority": "constitution",
                "confidence": 1.0,
                "examples": [],
                "counterexamples": ["auto-promote"],
                "contradictions": [],
                "prerequisites": [],
                "causal_links": [],
                "provenance": {"wave": "x1-x3"},
                "license": "internal",
                "freshness": "2026-08-18",
            }
        )
        for nxt in (
            KnowledgeState.UNDERSTOOD,
            KnowledgeState.LINKED,
            KnowledgeState.PRACTICED,
            KnowledgeState.TRANSFER_TESTED,
            KnowledgeState.VALIDATED,
        ):
            rec = rt.knowledge.transition(rec["knowledge_id"], nxt)
        know_row = rt.store.conn.execute(
            "SELECT state, canonical, payload_json FROM knowledge_records WHERE knowledge_id = ?",
            (rec["knowledge_id"],),
        ).fetchone()
        payload = json.loads(know_row["payload_json"])
        claims["A19_KNOWLEDGE_FOUNDATION"] = (
            "PASS"
            if know_row["canonical"] == 0 and payload["license"] == "internal" and payload["version"] == "1"
            else "FAIL"
        )

        claims["DIRECT_CANONICAL_MUTATION"] = False if mutation_reason == "DIRECT_CANONICAL_MUTATION_REJECTED" else "UNKNOWN"
        claims["AUTO_TEACHER_DELETE"] = False if delete_reason == "AUTO_TEACHER_DELETE_REJECTED" else "UNKNOWN"
        promo_reason = None
        try:
            rt.knowledge.transition(rec["knowledge_id"], KnowledgeState.CANONICAL)
        except FailClosed as exc:
            promo_reason = str(exc)
        claims["AUTO_CANONICAL_PROMOTION"] = False if promo_reason == "AUTO_CANONICAL_PROMOTION_REJECTED" else "UNKNOWN"
        v9_reason = None
        try:
            rt.v9.write_identity({})
        except FailClosed as exc:
            v9_reason = str(exc)
        claims["RAIOS_V9_MUTATION"] = False if v9_reason == "RAIOS_V9_MUTATION_REJECTED" else "UNKNOWN"
        claims["A17_4_REAL_DATA_CONSUMPTION"] = rt.a174.status()["A17_4_REAL_DATA_CONSUMPTION"]
        claims["SQLITE_INTEGRITY"] = rt.store.integrity_check()
        claims["EVENT_CHAIN"] = rt.store.verify_event_chain()
        claims["UNIT_TESTS"] = "PASS" if unit["ok"] else "FAIL"
        if not unit["ok"]:
            claims["UNIT_TEST_STDERR"] = unit["stderr"][-4000:]
            claims["UNIT_TEST_STDOUT"] = unit["stdout"][-4000:]
        claims["identity"] = identity
        claims["a17_4_status"] = rt.a174.status()
        claims["reuse"] = rt.reuse_status()
        claims["observation_id"] = obs.get("observation_id")
    finally:
        rt.close()
        tmp.cleanup()

    required_pass = [
        "A17_5_NORMALIZATION",
        "A17_6_DIFFERENTIAL",
        "A17_7_MASTERY_ENGINE",
        "A17_8_RETIREMENT_ENGINE",
        "A17_9_CORTEX_CONTRACT",
        "A17_10_COGNITIVE_LOOP_CORE",
        "A18_EXPERIENCE_FOUNDATION",
        "A19_KNOWLEDGE_FOUNDATION",
        "UNIT_TESTS",
    ]
    claims["WAVE_CERTIFICATION"] = "PASS" if all(claims.get(k) == "PASS" for k in required_pass) else "FAIL"
    return claims


def main() -> int:
    claims = certify()
    print(json.dumps(claims, indent=2, sort_keys=True, default=str))
    return 0 if claims.get("WAVE_CERTIFICATION") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
