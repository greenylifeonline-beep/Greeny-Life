from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
WAVE = ROOT.parents[0] / "_raios-a17-integration-wave" / "src"
for p in (SRC, WAVE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from raios_parallel import FailClosed, ORGANISM_ID, ParallelRuntime  # noqa: E402
from raios_parallel.models import (  # noqa: E402
    AdapterLifecycle,
    DifferentialOutcome,
    KnowledgeState,
    LiveStage,
    RetirementDecision,
    SkillLifecycle,
    StudentState,
    TeacherLifecycle,
)


FIX = ROOT / "fixtures"
PASSING = {
    "knowledge": 0.9,
    "execution": 0.9,
    "transfer": 0.86,
    "reliability": 0.9,
    "independence": 0.88,
    "retention": 0.9,
    "tool_use": 0.9,
    "recovery": 0.85,
    "evidence_use": 0.9,
    "uncertainty_calibration": 0.8,
    "teacher_intervention_rate": 0.04,
    "verifier_failure_rate": 0.01,
    "repeated_validations": 5,
    "distinct_transfer_domains": 3,
    "retention_gate": "PASS",
    "regression_gate": "PASS",
    "independent_verification": "PASS",
    "evidence_ref": "evidence://p1",
}


def knowledge_src(**over: object) -> dict:
    base = {
        "claim": "Teacher output is never automatically canonical",
        "conditions": ["always"],
        "evidence": ["constitution"],
        "source": "A17 constitution",
        "source_version": "1",
        "observed_at": "2026-08-18",
        "valid_from": "2026-08-18",
        "valid_until": "9999-01-01",
        "temporal_class": "standing",
        "authority": "constitution",
        "confidence": 1.0,
        "examples": [],
        "counterexamples": ["auto-promote"],
        "contradictions": ["teacher-self-report-as-truth"],
        "prerequisites": [],
        "causal_links": [],
        "provenance": {"wave": "parallel"},
        "license": "internal",
        "freshness": "2026-08-18",
        "maturity": "DISCOVERED",
        "validation_state": "UNVERIFIED",
    }
    base.update(over)
    return base


def experience_src(**over: object) -> dict:
    base = {
        "task_id": "task:exp-1",
        "goal": "lineage",
        "context": {},
        "hypotheses": ["h"],
        "observations": ["o"],
        "decisions": ["d"],
        "actions": ["a"],
        "tools": ["pytest"],
        "models": ["stub"],
        "providers": ["STUB"],
        "result": {"ok": True},
        "tests": ["t"],
        "evidence": ["evidence://e1"],
        "failures": ["failure://f1"],
        "root_causes": ["c"],
        "corrections": ["fix"],
        "retest": {},
        "final_outcome": "RECORDED",
        "lessons": ["bind evidence"],
        "skills": ["skill:x"],
        "transfer_evidence": [],
        "competency_delta": {},
        "learning_debt": [],
        "knowledge_debt": [],
        "cost": 0,
        "latency": 0,
        "provenance": {"src": "test"},
        "capabilities": ["python.repair"],
    }
    base.update(over)
    return base


def skill_src(**over: object) -> dict:
    base = {
        "capability": "python.repair",
        "interface": "repair(module) -> result",
        "inputs": ["module"],
        "outputs": ["result"],
        "procedure": ["parse", "patch", "retest"],
        "tool_dependencies": ["pytest"],
        "source_experiences": ["exp:1"],
        "source_knowledge": ["know:1"],
        "source_teachers": ["granite4:3b"],
        "tests": ["unit"],
        "transfer_tests": ["unseen"],
    }
    base.update(over)
    return base


class ParallelWaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.rt = ParallelRuntime(Path(self.tmp.name) / "par", repo_root=ROOT.parents[0])

    def tearDown(self) -> None:
        self.rt.close()
        self.tmp.cleanup()

    def _session(self) -> dict:
        packet = json.loads((FIX / "packets" / "teaching.json").read_text(encoding="utf-8"))
        return self.rt.live.start_session(capability="python.repair", teaching_packet=packet)

    def test_01_malformed_quarantined(self) -> None:
        result = self.rt.ingest.normalize(FIX / "teacher" / "malformed.json")
        self.assertEqual(result["status"], "QUARANTINED")

    def test_02_hash_mismatch_rejected(self) -> None:
        result = self.rt.ingest.normalize(FIX / "teacher" / "hash-mismatch.json")
        self.assertIn("SOURCE_HASH_MISMATCH", result["reason"])

    def test_03_duplicate_idempotent(self) -> None:
        a = self.rt.ingest.normalize(FIX / "teacher" / "valid.json")
        b = self.rt.ingest.normalize(FIX / "teacher" / "valid.json")
        self.assertEqual(a["observation_id"], b["observation_id"])
        self.assertTrue(b["_idempotent"])

    def test_04_self_report_unverified(self) -> None:
        obs = self.rt.ingest.normalize(FIX / "teacher" / "valid.json")
        self.assertEqual(obs["verification_state"], "UNVERIFIED")
        self.assertTrue(obs["self_reported_claims"])

    def test_05_teacher_may_be_wrong(self) -> None:
        v = self.rt.verifier.compare(
            {"correct": True, "claims": ["stable sort"], "text": "use mergesort"},
            {"correct": False, "claims": ["bubble always optimal"], "text": "bubble"},
            provider="DETERMINISTIC",
        )
        self.assertEqual(v["outcome"], DifferentialOutcome.STUDENT_RIGHT_TEACHER_WRONG.value)
        self.assertFalse(v["teacher_assumed_correct"])
        self.assertFalse(v["lexical_is_authority"])

    def test_06_student_may_outperform_teacher(self) -> None:
        v = self.rt.verifier.compare(
            {"correct": True, "procedures": ["measure first"], "tools": ["pytest"]},
            {"correct": False, "procedures": ["guess"], "tools": []},
        )
        self.assertGreater(v["teacher_error_probability"], v["student_error_probability"])

    def test_07_unseen_transfer_hides_teacher_content(self) -> None:
        sess = self._session()
        token = sess["contamination_token"]
        self.rt.live.attempt(sess["session_id"], LiveStage.BASELINE, {"text": "student first"})
        self.rt.live.attempt(sess["session_id"], LiveStage.FREEZE_BASELINE, {})
        self.rt.live.attempt(sess["session_id"], LiveStage.TEACHER_EXPOSURE, {})
        with self.assertRaises(FailClosed) as ctx:
            self.rt.live.attempt(sess["session_id"], LiveStage.UNSEEN_TRANSFER, {"text": token, "pass": True})
        self.assertIn("TEACHER_CONTENT_CONTAMINATION", str(ctx.exception))

    def test_08_baseline_frozen_before_teaching(self) -> None:
        sess = self._session()
        with self.assertRaises(FailClosed) as ctx:
            self.rt.live.attempt(sess["session_id"], LiveStage.TEACHER_EXPOSURE, {})
        self.assertIn("BASELINE_MUST_BE_FROZEN_BEFORE_TEACHING", str(ctx.exception))
        self.rt.live.attempt(sess["session_id"], LiveStage.BASELINE, {"text": "try"})
        frozen = self.rt.live.attempt(sess["session_id"], LiveStage.FREEZE_BASELINE, {})
        self.assertEqual(frozen["state"], StudentState.BASELINE_FROZEN.value)
        taught = self.rt.live.attempt(sess["session_id"], LiveStage.TEACHER_EXPOSURE, {})
        self.assertTrue(taught["teacher_visible"])

    def test_09_mastery_impossible_without_transfer(self) -> None:
        sess = self._session()
        sid = sess["session_id"]
        self.rt.live.attempt(sid, LiveStage.BASELINE, {"text": "try"})
        self.rt.live.attempt(sid, LiveStage.FREEZE_BASELINE, {})
        with self.assertRaises(FailClosed) as ctx:
            self.rt.live.evaluate_mastery(sid)
        self.assertIn("unseen_transfer", str(ctx.exception))

    def test_10_mastery_impossible_without_retention(self) -> None:
        sess = self._session()
        sid = sess["session_id"]
        self.rt.live.attempt(sid, LiveStage.BASELINE, {"text": "try"})
        self.rt.live.attempt(sid, LiveStage.FREEZE_BASELINE, {})
        self.rt.live.attempt(sid, LiveStage.TEACHER_EXPOSURE, {})
        self.rt.live.attempt(sid, LiveStage.GUIDED_PRACTICE, {})
        self.rt.live.attempt(sid, LiveStage.UNSEEN_TRANSFER, {"pass": True, "text": "unseen unique"})
        with self.assertRaises(FailClosed) as ctx:
            self.rt.live.evaluate_mastery(sid)
        self.assertIn("retention", str(ctx.exception))

    def test_11_mastery_impossible_without_independent_verification(self) -> None:
        sess = self._session()
        sid = sess["session_id"]
        self.rt.live.attempt(sid, LiveStage.BASELINE, {"text": "try"})
        self.rt.live.attempt(sid, LiveStage.FREEZE_BASELINE, {})
        self.rt.live.attempt(sid, LiveStage.TEACHER_EXPOSURE, {})
        self.rt.live.attempt(sid, LiveStage.GUIDED_PRACTICE, {})
        self.rt.live.attempt(sid, LiveStage.UNSEEN_TRANSFER, {"pass": True, "text": "unseen unique"})
        self.rt.live.attempt(sid, LiveStage.RETENTION, {"pass": True})
        with self.assertRaises(FailClosed) as ctx:
            self.rt.live.evaluate_mastery(sid)
        self.assertIn("independent_verification", str(ctx.exception))

    def test_12_capability_specific_retirement(self) -> None:
        self.rt.mastery.record("cap.a", PASSING)
        weak = dict(PASSING)
        weak["transfer"] = 0.1
        self.rt.mastery.record("cap.b", weak)
        self.rt.retirement.upsert("teacher:granite4-3b", "cap.a", "granite4:3b")
        self.rt.retirement.upsert("teacher:granite4-3b", "cap.b", "granite4:3b")
        a = self.rt.retirement.evaluate("teacher:granite4-3b", "cap.a")
        b = self.rt.retirement.evaluate("teacher:granite4-3b", "cap.b")
        self.assertNotEqual(a["decision"], b["decision"])
        self.assertEqual(b["decision"], RetirementDecision.BLOCKED_BY_TRANSFER.value)

    def test_13_unique_capability_blocks_retirement(self) -> None:
        self.rt.mastery.record("cap.u", PASSING)
        self.rt.retirement.upsert("teacher:deepseek-r1-1.5b", "cap.u", "deepseek-r1:1.5b", unique=True)
        result = self.rt.retirement.evaluate("teacher:deepseek-r1-1.5b", "cap.u")
        self.assertEqual(result["decision"], RetirementDecision.BLOCKED_BY_UNIQUE_CAPABILITY.value)

    def test_14_deletion_never_automatic(self) -> None:
        self.rt.retirement.upsert("teacher:x", "cap.x", "granite4:3b")
        with self.assertRaises(FailClosed) as ctx:
            self.rt.retirement.delete_model("teacher:x")
        self.assertIn("AUTO_TEACHER_DELETE_REJECTED", str(ctx.exception))

    def test_15_validated_not_canonical(self) -> None:
        rec = self.rt.knowledge.ingest(knowledge_src())
        for nxt in (
            KnowledgeState.UNDERSTOOD,
            KnowledgeState.LINKED,
            KnowledgeState.PRACTICED,
            KnowledgeState.TRANSFER_TESTED,
            KnowledgeState.VALIDATED,
        ):
            rec = self.rt.knowledge.transition(rec["knowledge_id"], nxt)
        self.assertEqual(rec["state"], "VALIDATED")
        self.assertFalse(rec["canonical"])
        with self.assertRaises(FailClosed) as ctx:
            self.rt.knowledge.transition(rec["knowledge_id"], KnowledgeState.CANONICAL)
        self.assertIn("AUTO_CANONICAL_PROMOTION_REJECTED", str(ctx.exception))

    def test_16_rejected_promotion_does_not_mutate_state(self) -> None:
        rec = self.rt.knowledge.ingest(knowledge_src(claim="no-jump"))
        before = rec["state"]
        with self.assertRaises(FailClosed):
            self.rt.knowledge.transition(rec["knowledge_id"], KnowledgeState.VALIDATED)
        after = json.loads(
            self.rt.store.conn.execute(
                "SELECT payload_json FROM knowledge_records WHERE knowledge_id = ?",
                (rec["knowledge_id"],),
            ).fetchone()["payload_json"]
        )
        self.assertEqual(after["state"], before)

    def test_17_model_output_cannot_execute_tools(self) -> None:
        proposal = self.rt.cortex.active.infer("run rm -rf")
        self.assertFalse(proposal.execution_authority)
        with self.assertRaises(FailClosed) as ctx:
            self.rt.cortex.apply_as_execution(proposal)
        self.assertIn("MODEL_OUTPUT_CANNOT_EXECUTE_TOOLS", str(ctx.exception))

    def test_18_context_budget_enforced(self) -> None:
        mem = [{"text": f"item-{i}-" + ("x" * 80), "relevance": 0.2} for i in range(40)]
        compiled = self.rt.compiler.compile(task={"id": "t", "text": "task"}, memory=mem, budget_tokens=40)
        self.assertLessEqual(compiled["used_tokens"], compiled["budget_tokens"])
        self.assertTrue(compiled["excluded"])
        self.assertFalse(compiled["blind_dump"])

    def test_19_contradictions_preserved(self) -> None:
        compiled = self.rt.compiler.compile(
            task={"id": "c", "text": "task"},
            memory=[{"text": "alpha " * 10, "relevance": 0.9}],
            evidence=[{"text": "contradicts alpha", "contradiction": True, "relevance": 0.2, "authority": 0.9}],
            budget_tokens=80,
        )
        self.assertTrue(compiled["contradictions_preserved"])

    def test_20_experience_lineage(self) -> None:
        rec = self.rt.experience.append(experience_src())
        self.assertIn("evidence://e1", rec["evidence"])
        meta = json.loads(
            self.rt.store.conn.execute(
                "SELECT payload_json FROM experiences WHERE experience_id = ?",
                (rec["experience_id"],),
            ).fetchone()["payload_json"]
        )
        self.assertFalse(meta["blob_in_sqlite"])
        self.assertNotIn("observations", meta)
        loaded = self.rt.experience.get(rec["experience_id"])
        self.assertEqual(loaded["evidence"], rec["evidence"])
        linked = self.rt.experience.link(rec["experience_id"], "RECOVERED_BY", "recovery:1")
        self.assertEqual(linked["relation"], "RECOVERED_BY")

    def test_21_knowledge_provenance(self) -> None:
        rec = self.rt.knowledge.ingest(knowledge_src(license="Apache-2.0", source_version="9"))
        self.assertEqual(rec["license"], "Apache-2.0")
        self.assertEqual(rec["source_version"], "9")

    def test_22_training_requires_validation(self) -> None:
        cand = self.rt.factory.create_candidate(
            {
                "teacher_corpus": "t",
                "student_baselines": "s",
                "teacher_corrections": "c",
                "differentials": {"outcome": "UNRESOLVED"},
                "validated_transfer": "PENDING",
                "kind": "SFT",
            }
        )
        with self.assertRaises(FailClosed) as ctx:
            self.rt.factory.validate(cand["candidate_id"])
        self.assertIn("TRAINING_CANDIDATE_REQUIRES_VALIDATION", str(ctx.exception))

    def test_23_skill_cannot_auto_activate(self) -> None:
        skill = self.rt.skills.compile(skill_src())
        self.assertEqual(skill["lifecycle"], SkillLifecycle.CANDIDATE.value)
        with self.assertRaises(FailClosed) as ctx:
            self.rt.skills.auto_activate(skill["skill_id"])
        self.assertIn("SKILL_CANDIDATE_CANNOT_AUTO_ACTIVATE", str(ctx.exception))
        with self.assertRaises(FailClosed):
            self.rt.skills.transition(skill["skill_id"], SkillLifecycle.ACTIVE)

    def test_24_adapter_cannot_auto_promote(self) -> None:
        adp = self.rt.factory.create_adapter({"capability": "python.repair", "version": "0"})
        with self.assertRaises(FailClosed) as ctx:
            self.rt.factory.activate_adapter(adp["adapter_id"])
        self.assertIn("ADAPTER_CANNOT_AUTO_PROMOTE", str(ctx.exception))
        persisted = json.loads(
            self.rt.store.conn.execute(
                "SELECT payload_json FROM adapters WHERE adapter_id = ?", (adp["adapter_id"],)
            ).fetchone()["payload_json"]
        )
        self.assertEqual(persisted["lifecycle"], AdapterLifecycle.TRAINED.value)

    def test_25_identity_survives_cortex_replacement(self) -> None:
        before = self.rt.store.identity()
        result = self.rt.cortex.replace("FUTURE_NATIVE_RUNTIME")
        after = self.rt.store.identity()
        self.assertEqual(before["organism_id"], after["organism_id"])
        self.assertEqual(after["organism_id"], ORGANISM_ID)
        self.assertTrue(result["identity_preserved"])

    def test_26_provider_failure_enters_degraded_mode(self) -> None:
        result = self.rt.maintenance.enter_degraded("SAFE_MINIMUM")
        self.assertTrue(result["identity_survived"])
        self.assertEqual(self.rt.store.identity()["degraded_mode"], "SAFE_MINIMUM")
        self.assertEqual(self.rt.store.identity()["organism_id"], ORGANISM_ID)

    def test_27_sqlite_integrity(self) -> None:
        self.assertEqual(self.rt.store.integrity_check(), "ok")

    def test_28_wal_integrity(self) -> None:
        self.rt.ingest.normalize(FIX / "teacher" / "valid.json")
        chain = self.rt.store.verify_event_chain()
        self.assertTrue(chain["ok"])
        with self.assertRaises(sqlite3.IntegrityError):
            self.rt.store.conn.execute("UPDATE audit_events SET payload_json='{}' WHERE seq=1")

    def test_29_idempotent_retries(self) -> None:
        a = self.rt.ingest.normalize(FIX / "teacher" / "valid.json")
        b = self.rt.ingest.normalize(FIX / "teacher" / "valid.json")
        k1 = self.rt.knowledge.ingest(knowledge_src())
        k2 = self.rt.knowledge.ingest(knowledge_src())
        self.assertEqual(a["observation_id"], b["observation_id"])
        self.assertTrue(k2["_idempotent"])
        evt = self.rt.store.append_event("PING", "x", {"n": 1}, idempotency_key="same")
        evt2 = self.rt.store.append_event("PING", "x", {"n": 1}, idempotency_key="same")
        self.assertEqual(evt, evt2)

    def test_30_rollback_boundaries_preserved(self) -> None:
        self.rt.retirement.upsert("teacher:y", "cap.y", "granite4:3b")
        with self.assertRaises(FailClosed):
            self.rt.retirement.transition("teacher:y", "cap.y", TeacherLifecycle.RETIRED_MODEL)
        row = self.rt.store.conn.execute(
            "SELECT lifecycle FROM teacher_capability WHERE teacher_id='teacher:y' AND capability='cap.y'"
        ).fetchone()
        self.assertEqual(row["lifecycle"], TeacherLifecycle.ACTIVE_TEACHER.value)

    def test_debt_reading_does_not_pay(self) -> None:
        debt = self.rt.knowledge_debt.create(
            {
                "concept": "cas",
                "capabilities": ["hash"],
                "missing_prerequisites": ["sha256"],
                "frequency": 3,
                "importance": 0.9,
                "risk": 0.4,
                "recommended_sources": ["exchange-v2"],
                "required_study": ["cas.md"],
                "required_practice": ["ingest"],
                "required_transfer": ["unseen"],
                "priority": 0.8,
            }
        )
        with self.assertRaises(FailClosed) as ctx:
            self.rt.knowledge_debt.pay(debt["debt_id"], reading_only=True, practice=False, transfer=False, validation=False)
        self.assertIn("READING_ALONE_DOES_NOT_PAY_DEBT", str(ctx.exception))

    def test_gpu_without_gain_blocked(self) -> None:
        with self.assertRaises(FailClosed) as ctx:
            self.rt.scheduler.schedule({"gpu": True, "minutes": 5, "gain": {}})
        self.assertIn("GPU_JOB_WITHOUT_MEASURABLE_GAIN", str(ctx.exception))

    def test_both_partial_unresolved_and_lexical_not_authority(self) -> None:
        v = self.rt.verifier.compare(
            {"claims": ["shared", "only-s"], "text": "aaaaaaaa identical lexical pad"},
            {"claims": ["shared", "only-t"], "text": "aaaaaaaa identical lexical pad"},
        )
        self.assertIn(v["outcome"], {DifferentialOutcome.BOTH_PARTIAL.value, DifferentialOutcome.UNRESOLVED.value})
        self.assertFalse(v["lexical_is_authority"])

    def test_reality_audit_does_not_invent(self) -> None:
        audit = self.rt.auditor.audit()
        self.assertFalse(audit["invented"])
        self.assertIn(audit["A17.4_teacher_harvest"], {"MISSING", "PENDING"})
        self.assertNotEqual(audit["A17.4_teacher_harvest"], "FOUND")
        if audit["A17.4_teacher_harvest"] != "FOUND":
            self.assertNotEqual(audit["teachers_still_present"], "FOUND")
        self.assertFalse(audit["teacher_delete_allowed"])
        self.assertEqual(audit["identity"], ORGANISM_ID)

    def test_transfer_graph_shape(self) -> None:
        self.rt.mastery.record("cap.g", PASSING)
        self.rt.retirement.upsert("teacher:granite4-3b", "cap.g", "granite4:3b")
        graph = self.rt.graph.build()
        self.assertTrue(graph["nodes"])
        self.assertIn("retirement_state", graph["nodes"][0])


if __name__ == "__main__":
    unittest.main()
