#!/usr/bin/env python3
"""Certification for A17.14–A23 parallel wave. Inspects persisted state."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
WAVE = ROOT.parents[0] / "_raios-a17-integration-wave" / "src"
for p in (str(SRC), str(WAVE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from raios_parallel import FailClosed, ParallelRuntime  # noqa: E402
from raios_parallel.models import KnowledgeState, LiveStage  # noqa: E402


def _run_unittests():
    native = ROOT.parent / "_raios-a17-native-cortex"
    if str(native) not in sys.path:
        sys.path.insert(0, str(native))
    from ccee.process_kernel import encoding_safe_run

    return encoding_safe_run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
        cwd=ROOT,
        timeout=180.0,
    )


def main() -> int:
    unit = _run_unittests()
    tmp = tempfile.TemporaryDirectory()
    rt = ParallelRuntime(Path(tmp.name) / "cert", repo_root=ROOT.parents[0])
    claims: dict[str, object] = {"UNIT_TESTS": "PASS" if unit.returncode == 0 else "FAIL"}
    if unit.returncode != 0:
        claims["UNIT_STDOUT"] = unit.stdout[-3000:]
        claims["UNIT_STDERR"] = unit.stderr[-3000:]
    try:
        packet = {"contamination_token": "TOK", "lessons": ["l"]}
        sess = rt.live.start_session(capability="cert.cap", teaching_packet=packet)
        rt.live.attempt(sess["session_id"], LiveStage.BASELINE, {"text": "student-first"})
        frozen = rt.live.attempt(sess["session_id"], LiveStage.FREEZE_BASELINE, {})
        claims["A17_14_LIVE_LEARNING_ENGINE"] = (
            "PASS" if frozen["baseline_frozen"] and frozen["state"] == "BASELINE_FROZEN" else "FAIL"
        )
        v = rt.verifier.compare(
            {"correct": True, "claims": ["s"]},
            {"correct": False, "claims": ["t"]},
            provider="DETERMINISTIC",
        )
        row = rt.store.conn.execute("SELECT outcome FROM verifier_results WHERE result_id = ?", (v["result_id"],)).fetchone()
        claims["A17_15_SEMANTIC_VERIFIER"] = "PASS" if row and row["outcome"] == "STUDENT_RIGHT_TEACHER_WRONG" else "FAIL"
        ev = rt.mastery.record(
            "cert.cap",
            {
                "transfer": 0.9,
                "independence": 0.9,
                "teacher_intervention_rate": 0.04,
                "verifier_failure_rate": 0.01,
                "repeated_validations": 5,
                "distinct_transfer_domains": 3,
                "retention_gate": "PASS",
                "regression_gate": "PASS",
                "independent_verification": "PASS",
                "evidence_ref": "e",
            },
        )
        claims["A17_16_MASTERY_ENGINE"] = "PASS" if ev["mastery_scalar_insufficient"] else "FAIL"
        rt.retirement.upsert("teacher:granite4-3b", "cert.cap", "granite4:3b")
        weak = dict(ev["dimensions"])
        rt.mastery.record("cert.weak", {**{k: weak.get(k, 0) for k in weak}, "transfer": 0.1, "evidence_ref": "e"})
        rt.retirement.upsert("teacher:granite4-3b", "cert.weak", "granite4:3b")
        blocked = rt.retirement.evaluate("teacher:granite4-3b", "cert.weak")
        del_reason = None
        try:
            rt.retirement.delete_model("teacher:granite4-3b")
        except FailClosed as exc:
            del_reason = str(exc)
        claims["A17_17_RETIREMENT_ENGINE"] = (
            "PASS" if blocked["decision"] == "BLOCKED_BY_TRANSFER" and del_reason == "AUTO_TEACHER_DELETE_REJECTED" else "FAIL"
        )
        exp = rt.experience.append(
            {
                "task_id": "cert-exp",
                "goal": "g",
                "context": {},
                "hypotheses": [],
                "observations": [],
                "decisions": [],
                "actions": [],
                "tools": [],
                "models": [],
                "providers": [],
                "result": {},
                "tests": [],
                "evidence": ["e"],
                "failures": [],
                "root_causes": [],
                "corrections": [],
                "retest": {},
                "final_outcome": "RECORDED",
                "lessons": ["l"],
                "skills": [],
                "transfer_evidence": [],
                "competency_delta": {},
                "learning_debt": [],
                "knowledge_debt": [],
                "cost": 0,
                "latency": 0,
                "provenance": {},
            }
        )
        claims["A18_EXPERIENCE_PLANE"] = "PASS" if rt.store.conn.execute("SELECT 1 FROM experiences WHERE experience_id=?", (exp["experience_id"],)).fetchone() else "FAIL"
        kn = rt.knowledge.ingest(
            {
                "claim": "c",
                "conditions": [],
                "evidence": [],
                "source": "s",
                "source_version": "1",
                "observed_at": "t",
                "valid_from": "t",
                "valid_until": "t",
                "temporal_class": "standing",
                "authority": "a",
                "confidence": 0.5,
                "examples": [],
                "counterexamples": [],
                "contradictions": [],
                "prerequisites": [],
                "causal_links": [],
                "provenance": {},
                "license": "internal",
                "freshness": "t",
                "maturity": "DISCOVERED",
                "validation_state": "UNVERIFIED",
            }
        )
        for nxt in (
            KnowledgeState.UNDERSTOOD,
            KnowledgeState.LINKED,
            KnowledgeState.PRACTICED,
            KnowledgeState.TRANSFER_TESTED,
            KnowledgeState.VALIDATED,
        ):
            kn = rt.knowledge.transition(kn["knowledge_id"], nxt)
        promo = None
        try:
            rt.knowledge.transition(kn["knowledge_id"], KnowledgeState.CANONICAL)
        except FailClosed as exc:
            promo = str(exc)
        claims["A19_KNOWLEDGE_PLANE"] = "PASS" if promo == "AUTO_CANONICAL_PROMOTION_REJECTED" else "FAIL"
        skill = rt.skills.compile(
            {
                "capability": "c",
                "interface": "i",
                "inputs": [],
                "outputs": [],
                "procedure": ["p"],
                "tool_dependencies": [],
                "source_experiences": [],
                "source_knowledge": [],
                "source_teachers": [],
                "tests": [],
                "transfer_tests": [],
            }
        )
        skill_reason = None
        try:
            rt.skills.auto_activate(skill["skill_id"])
        except FailClosed as exc:
            skill_reason = str(exc)
        claims["A20_SKILL_COMPILER_FOUNDATION"] = (
            "PASS" if skill_reason == "SKILL_CANDIDATE_CANNOT_AUTO_ACTIVATE" else "FAIL"
        )
        adp = rt.factory.create_adapter({"capability": "c"})
        adp_reason = None
        try:
            rt.factory.activate_adapter(adp["adapter_id"])
        except FailClosed as exc:
            adp_reason = str(exc)
        claims["A21_ADAPTER_FACTORY_CONTRACT"] = "PASS" if adp_reason == "ADAPTER_CANNOT_AUTO_PROMOTE" else "FAIL"
        job = rt.scheduler.schedule({"gpu": False, "minutes": 1, "gain": {"capability_gain": 0.2}})
        claims["A22_ELASTIC_COMPUTE_CONTRACT"] = "PASS" if "gpu_value_per_minute" in job else "FAIL"
        mode = rt.maintenance.enter_degraded("SAFE_MINIMUM")
        claims["A23_MAINTENANCE_CONTRACT"] = "PASS" if mode["identity_survived"] else "FAIL"
        claims["PENDING_RUNTIME_VALIDATION"] = True
        claims["SQLITE"] = rt.store.integrity_check()
        claims["EVENT_CHAIN"] = rt.store.verify_event_chain()
        claims["identity"] = rt.store.identity()["organism_id"]
        claims["audit"] = rt.auditor.audit()
        required = [
            "A17_14_LIVE_LEARNING_ENGINE",
            "A17_15_SEMANTIC_VERIFIER",
            "A17_16_MASTERY_ENGINE",
            "A17_17_RETIREMENT_ENGINE",
            "A18_EXPERIENCE_PLANE",
            "A19_KNOWLEDGE_PLANE",
            "A20_SKILL_COMPILER_FOUNDATION",
            "A21_ADAPTER_FACTORY_CONTRACT",
            "A22_ELASTIC_COMPUTE_CONTRACT",
            "A23_MAINTENANCE_CONTRACT",
            "UNIT_TESTS",
        ]
        claims["WAVE_CERTIFICATION"] = "PASS" if all(claims.get(k) == "PASS" for k in required) else "FAIL"
    finally:
        rt.close()
        tmp.cleanup()
    print(json.dumps(claims, indent=2, sort_keys=True, default=str))
    return 0 if claims.get("WAVE_CERTIFICATION") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
