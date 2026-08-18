from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
FIXTURES = ROOT / "fixtures" / "teacher-harvest"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from raios_wave import CORTEX_IS_IDENTITY, FailClosed, ORGANISM_ID, WaveRuntime  # noqa: E402
from raios_wave.cortex import CortexProviderKind  # noqa: E402
from raios_wave.models import (  # noqa: E402
    AuthorityState,
    DifferentialOutcome,
    KnowledgeState,
    RetirementDecision,
    TeacherLifecycle,
    TrainingKind,
    VerificationState,
)


PASSING = {
    "knowledge_score": 0.91,
    "execution_score": 0.90,
    "transfer_score": 0.86,
    "reliability_score": 0.92,
    "independence_score": 0.88,
    "retention_score": 0.90,
    "teacher_intervention_rate": 0.04,
    "verifier_failure_rate": 0.01,
    "repeated_validations": 5,
    "distinct_transfer_domains": 3,
    "regression_gate": "PASS",
    "retention_gate": "PASS",
    "evidence_ref": "evidence://pass-1",
}


def knowledge_source(**overrides: object) -> dict:
    base = {
        "claim": "SQLite WAL is a durability mechanism, not a truth claim",
        "conditions": ["local sqlite", "single writer preferred"],
        "evidence": ["exchange-v2-cas"],
        "source": "RAIOS-SHARED-COGNITIVE-EXCHANGE-REFERENCE-V2/README.md",
        "version": "v2",
        "date": "2026-08-18",
        "temporal_validity": "while-schema-v2",
        "authority": "reference-package",
        "confidence": 0.7,
        "examples": ["crash-safe ingest"],
        "counterexamples": ["treating FTS hits as truth"],
        "contradictions": ["FTS retrieval is not verification"],
        "prerequisites": ["content addressing"],
        "causal_links": ["hash verify -> fail closed"],
        "provenance": {"package": "cognitive-exchange-v2"},
        "license": "internal-reference",
        "freshness": "2026-08-18",
    }
    base.update(overrides)
    return base


class IntegrationWaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.rt = WaveRuntime(Path(self.tmp.name) / "wave", repo_root=ROOT.parents[0])

    def tearDown(self) -> None:
        self.rt.close()
        self.tmp.cleanup()

    def test_01_malformed_teacher_artifact_quarantined(self) -> None:
        result = self.rt.normalizer.normalize_artifact(FIXTURES / "malformed")
        self.assertEqual(result["status"], "QUARANTINED")
        row = self.rt.store.conn.execute("SELECT COUNT(*) AS n FROM quarantined_artifacts").fetchone()
        self.assertGreaterEqual(row["n"], 1)

    def test_02_duplicate_artifact_idempotent(self) -> None:
        first = self.rt.normalizer.normalize_artifact(FIXTURES / "valid" / "meta.json")
        second = self.rt.normalizer.normalize_artifact(FIXTURES / "valid" / "meta.json")
        self.assertEqual(first["observation_id"], second["observation_id"])
        self.assertTrue(second.get("_idempotent"))
        count = self.rt.store.conn.execute("SELECT COUNT(*) AS n FROM observations").fetchone()["n"]
        self.assertEqual(count, 1)

    def test_03_source_hash_mismatch_rejected(self) -> None:
        result = self.rt.normalizer.normalize_artifact(FIXTURES / "hash-mismatch" / "meta.json")
        self.assertEqual(result["status"], "QUARANTINED")
        self.assertIn("SOURCE_HASH_MISMATCH", result["reason"])

    def test_04_teacher_self_report_remains_unverified(self) -> None:
        obs = self.rt.normalizer.normalize_artifact(FIXTURES / "valid" / "meta.json")
        self.assertEqual(obs["verification_state"], VerificationState.UNVERIFIED.value)
        self.assertEqual(obs["self_report_authority"], "LOWER_THAN_EMPIRICAL")
        self.assertFalse(obs["canonical"])
        self.assertTrue(obs["self_reported_claims"])

    def test_05_teacher_can_be_wrong(self) -> None:
        teacher = json.loads((FIXTURES / "teacher-wrong" / "teacher.json").read_text(encoding="utf-8"))
        student = json.loads((FIXTURES / "student-better" / "student.json").read_text(encoding="utf-8"))
        diff = self.rt.differential.compare(student, teacher)
        self.assertEqual(diff["outcome"], DifferentialOutcome.STUDENT_RIGHT_TEACHER_WRONG.value)
        self.assertFalse(diff["teacher_assumed_correct"])
        self.assertIn("TEACHER_MARKED_INCORRECT", diff["teacher_error_possibility"])

    def test_06_student_can_outperform_teacher(self) -> None:
        teacher = json.loads((FIXTURES / "teacher-wrong" / "teacher.json").read_text(encoding="utf-8"))
        student = json.loads((FIXTURES / "student-better" / "student.json").read_text(encoding="utf-8"))
        diff = self.rt.differential.compare(student, teacher)
        self.assertEqual(diff["outcome"], DifferentialOutcome.STUDENT_RIGHT_TEACHER_WRONG.value)
        self.assertTrue(diff["teacher_missed"])

    def test_07_differential_preserves_uncertainty(self) -> None:
        diff = self.rt.differential.compare(
            {"task_id": "t1", "capability": "c1", "claims": ["a"], "uncertainties": ["maybe"]},
            {"task_id": "t1", "capability": "c1", "claims": ["b"], "uncertainties": ["unknown"]},
        )
        self.assertEqual(diff["outcome"], DifferentialOutcome.UNRESOLVED.value)
        self.assertIn("NO_INDEPENDENT_VERIFIER", diff["open_uncertainty"])
        self.assertTrue(diff["open_uncertainty"])

    def test_08_validated_is_not_canonical(self) -> None:
        rec = self.rt.knowledge.ingest(knowledge_source())
        for nxt in (
            KnowledgeState.UNDERSTOOD,
            KnowledgeState.LINKED,
            KnowledgeState.PRACTICED,
            KnowledgeState.TRANSFER_TESTED,
            KnowledgeState.VALIDATED,
        ):
            rec = self.rt.knowledge.transition(rec["knowledge_id"], nxt)
        self.assertEqual(rec["state"], KnowledgeState.VALIDATED.value)
        self.assertFalse(rec["canonical"])
        self.assertEqual(rec["authority_state"], AuthorityState.VALIDATED.value)
        with self.assertRaises(FailClosed) as ctx:
            self.rt.knowledge.transition(rec["knowledge_id"], KnowledgeState.CANONICAL)
        self.assertIn("AUTO_CANONICAL_PROMOTION_REJECTED", str(ctx.exception))
        persisted = json.loads(
            self.rt.store.conn.execute(
                "SELECT payload_json FROM knowledge_records WHERE knowledge_id = ?",
                (rec["knowledge_id"],),
            ).fetchone()["payload_json"]
        )
        self.assertEqual(persisted["state"], KnowledgeState.VALIDATED.value)
        self.assertEqual(persisted["canonical"], False)

    def test_09_retirement_fails_without_unseen_transfer(self) -> None:
        metrics = dict(PASSING)
        metrics["transfer_score"] = 0.2
        self.rt.mastery.record_evaluation("cap.transfer", metrics)
        self.rt.retirement.upsert_teacher_capability("teacher:granite4-3b", "cap.transfer", "granite4:3b")
        result = self.rt.retirement.evaluate("teacher:granite4-3b", "cap.transfer")
        self.assertEqual(result["decision"], RetirementDecision.BLOCKED_BY_TRANSFER.value)
        self.assertIn("unseen_transfer", result["blockers"])
        self.assertFalse(result["auto_delete"])

    def test_10_retirement_fails_without_retention(self) -> None:
        metrics = dict(PASSING)
        metrics["retention_gate"] = "FAIL"
        self.rt.mastery.record_evaluation("cap.retain", metrics)
        self.rt.retirement.upsert_teacher_capability("teacher:granite4-3b", "cap.retain", "granite4:3b")
        result = self.rt.retirement.evaluate("teacher:granite4-3b", "cap.retain")
        self.assertEqual(result["decision"], RetirementDecision.BLOCKED_BY_RETENTION.value)
        self.assertFalse(result["model_deleted"])

    def test_11_retirement_fails_with_verifier_regression(self) -> None:
        metrics = dict(PASSING)
        metrics["verifier_failure_rate"] = 0.4
        metrics["regression_gate"] = "FAIL"
        self.rt.mastery.record_evaluation("cap.reg", metrics)
        self.rt.retirement.upsert_teacher_capability("teacher:qwen2.5-coder-3b", "cap.reg", "qwen2.5-coder:3b")
        result = self.rt.retirement.evaluate("teacher:qwen2.5-coder-3b", "cap.reg")
        self.assertEqual(result["decision"], RetirementDecision.BLOCKED_BY_REGRESSION.value)

    def test_12_retirement_is_capability_specific(self) -> None:
        self.rt.mastery.record_evaluation("cap.alpha", PASSING)
        weak = dict(PASSING)
        weak["transfer_score"] = 0.1
        self.rt.mastery.record_evaluation("cap.beta", weak)
        self.rt.retirement.upsert_teacher_capability("teacher:deepseek-r1-1.5b", "cap.alpha", "deepseek-r1:1.5b")
        self.rt.retirement.upsert_teacher_capability("teacher:deepseek-r1-1.5b", "cap.beta", "deepseek-r1:1.5b")
        alpha = self.rt.retirement.evaluate("teacher:deepseek-r1-1.5b", "cap.alpha")
        beta = self.rt.retirement.evaluate("teacher:deepseek-r1-1.5b", "cap.beta")
        self.assertTrue(alpha["capability_specific"])
        self.assertNotEqual(alpha["decision"], beta["decision"])
        self.assertEqual(beta["decision"], RetirementDecision.BLOCKED_BY_TRANSFER.value)

    def test_13_model_deletion_is_never_automatic(self) -> None:
        self.rt.retirement.upsert_teacher_capability("teacher:granite4-3b", "cap.x", "granite4:3b")
        with self.assertRaises(FailClosed) as ctx:
            self.rt.retirement.delete_model("teacher:granite4-3b")
        self.assertIn("AUTO_TEACHER_DELETE_REJECTED", str(ctx.exception))
        with self.assertRaises(FailClosed) as ctx2:
            self.rt.retirement.delete_model("teacher:granite4-3b", approval_token="GOVERNED:human-1")
        self.assertIn("MODEL_DELETION_REMAINS_EXTERNAL", str(ctx2.exception))

    def test_14_cortex_output_cannot_directly_mutate_canonical_state(self) -> None:
        proposal = self.rt.cortex.active.infer("mutate canonical identity")
        self.assertFalse(proposal.execution_authority)
        with self.assertRaises(FailClosed) as ctx:
            self.rt.cortex.apply_proposal_as_canonical(proposal)
        self.assertIn("DIRECT_CANONICAL_MUTATION_REJECTED", str(ctx.exception))
        with self.assertRaises(FailClosed):
            self.rt.tools.execute({"tool": "write", "target": "canonical/identity", "mutate": True}, authorized=True)

    def test_15_cortex_replacement_preserves_identity_contract(self) -> None:
        before = self.rt.store.identity()
        result = self.rt.cortex.replace(CortexProviderKind.FUTURE_LOCAL_RUNTIME)
        after = self.rt.store.identity()
        self.assertEqual(before["organism_id"], after["organism_id"])
        self.assertEqual(after["organism_id"], ORGANISM_ID)
        self.assertTrue(result["identity_preserved"])
        self.assertFalse(result["cortex_is_identity"])
        self.assertFalse(CORTEX_IS_IDENTITY)
        self.assertFalse(after.get("cortex_is_identity"))

    def test_16_context_compiler_obeys_budget(self) -> None:
        items = [{"text": f"memory-item-{i}-" + ("x" * 80), "priority": 0.2, "relevance": 0.2} for i in range(40)]
        compiled = self.rt.compiler.compile(task={"id": "budget", "text": "task"}, memory=items, budget_tokens=50)
        self.assertLessEqual(compiled["used_tokens"], compiled["budget_tokens"])
        self.assertTrue(compiled["excluded"])
        self.assertFalse(compiled["blind_dump"])

    def test_17_context_compiler_includes_contradictions_when_relevant(self) -> None:
        compiled = self.rt.compiler.compile(
            task={"id": "contra", "text": "task"},
            memory=[{"text": "alpha " * 20, "priority": 0.9, "relevance": 0.9}],
            evidence=[
                {
                    "text": "this contradicts the prior claim about alpha",
                    "contradiction": True,
                    "priority": 0.1,
                    "relevance": 0.9,
                    "authority": 0.8,
                }
            ],
            budget_tokens=80,
            include_contradictions=True,
        )
        self.assertTrue(any(row.get("contradiction") for row in compiled["included"]))

    def test_18_experience_preserves_evidence_lineage(self) -> None:
        episode = {
            "task_id": "task:exp-1",
            "context": {"k": "v"},
            "goal": "record lineage",
            "hypothesis": "evidence is linked",
            "observations": ["o1"],
            "decisions": ["d1"],
            "actions": ["a1"],
            "tools": ["pytest"],
            "model_provider": "stub-cortex",
            "result": {"ok": True},
            "tests": ["t1"],
            "evidence": ["evidence://abc", {"id": "evidence://def", "kind": "log"}],
            "failures": [{"id": "failure://f1", "msg": "boom"}],
            "root_causes": ["missed hash"],
            "corrections": ["bind hash"],
            "retest": {"pass": True},
            "final_outcome": "RECORDED",
            "lessons": ["bind evidence"],
            "skills": ["skill:hash-bind"],
            "transfer_evidence": ["other-domain"],
            "competency_delta": {"hash.binding": 0.1},
            "learning_debt": [],
            "provenance": {"src": "fixture"},
            "confidence": 0.4,
            "capabilities": ["hash.binding"],
        }
        rec = self.rt.experience.record(episode)
        self.assertEqual(rec["evidence"][0], "evidence://abc")
        edges = self.rt.rkg.neighbors(rec["experience_id"])
        relations = {row["relation"] for row in edges}
        self.assertIn("VALIDATED_BY", relations)
        self.assertIn("FAILED_IN", relations)
        self.assertIn("OBSERVED_IN", relations)

    def test_19_knowledge_candidate_preserves_source_version_license(self) -> None:
        rec = self.rt.knowledge.ingest(knowledge_source(license="Apache-2.0", version="3.1"))
        self.assertEqual(rec["source"], knowledge_source()["source"])
        self.assertEqual(rec["version"], "3.1")
        self.assertEqual(rec["license"], "Apache-2.0")
        self.assertFalse(rec["canonical"])

    def test_20_training_candidate_requires_validation(self) -> None:
        with self.assertRaises(FailClosed) as missing:
            self.rt.training.create(kind=TrainingKind.SFT, record={"teacher_source": "t"})
        self.assertIn("TRAINING_CANDIDATE_MISSING", str(missing.exception))
        draft = self.rt.training.create(
            kind=TrainingKind.CODE_REPAIR,
            record={
                "teacher_source": "granite4:3b",
                "student_baseline": "broken",
                "teacher_output": "patch",
                "differential": {"outcome": "UNRESOLVED"},
                "evidence": ["e1"],
                "validation_result": "PENDING",
                "transfer_result": "PENDING",
                "capability": "python.repair",
            },
        )
        with self.assertRaises(FailClosed) as ctx:
            self.rt.training.promote_validated(draft["candidate_id"])
        self.assertIn("TRAINING_CANDIDATE_REQUIRES_VALIDATION", str(ctx.exception))
        with self.assertRaises(FailClosed):
            self.rt.training.create(
                kind=TrainingKind.SFT,
                record={
                    "teacher_source": "t",
                    "student_baseline": "s",
                    "teacher_output": "o",
                    "differential": {},
                    "evidence": [],
                    "validation_result": "PASS",
                    "transfer_result": "PASS",
                    "copy_teacher_blindly": True,
                },
            )

    def test_21_skill_candidate_is_not_canonical(self) -> None:
        result = self.rt.skills.ingest_external("SkillX", {"title": "parse-patch-retest", "capability": "python.repair"})
        self.assertFalse(result["canonical"])
        cand = result["candidates"][0]
        self.assertEqual(cand["kind"], "SKILL_CANDIDATE")
        self.assertFalse(cand["canonical"])
        with self.assertRaises(FailClosed) as ctx:
            self.rt.skills.promote_canonical(cand["candidate_id"])
        self.assertIn("SKILL_CANDIDATE_IS_NOT_CANONICAL", str(ctx.exception))

    def test_22_sqlite_integrity(self) -> None:
        self.rt.normalizer.normalize_artifact(FIXTURES / "valid" / "meta.json")
        self.assertEqual(self.rt.store.integrity_check(), "ok")

    def test_23_wal_event_integrity(self) -> None:
        self.rt.normalizer.normalize_artifact(FIXTURES / "valid" / "meta.json")
        chain = self.rt.store.verify_event_chain()
        self.assertTrue(chain["ok"])
        self.assertGreater(chain["count"], 0)
        with self.assertRaises(sqlite3.IntegrityError):
            self.rt.store.conn.execute("UPDATE audit_events SET payload_json = '{}' WHERE seq = 1")

    def test_24_idempotent_retry(self) -> None:
        a = self.rt.normalizer.normalize_artifact(FIXTURES / "valid" / "meta.json")
        b = self.rt.normalizer.normalize_artifact(FIXTURES / "valid" / "meta.json")
        k1 = self.rt.knowledge.ingest(knowledge_source())
        k2 = self.rt.knowledge.ingest(knowledge_source())
        self.assertEqual(a["observation_id"], b["observation_id"])
        self.assertEqual(k1["knowledge_id"], k2["knowledge_id"])
        self.assertTrue(k2["_idempotent"])

    def test_25_rejected_transition_does_not_mutate_authoritative_state(self) -> None:
        rec = self.rt.knowledge.ingest(knowledge_source(claim="no jump"))
        before = rec["state"]
        with self.assertRaises(FailClosed) as ctx:
            self.rt.knowledge.transition(rec["knowledge_id"], KnowledgeState.VALIDATED)
        self.assertIn("ILLEGAL_KNOWLEDGE_STATE", str(ctx.exception))
        after = json.loads(
            self.rt.store.conn.execute(
                "SELECT payload_json FROM knowledge_records WHERE knowledge_id = ?",
                (rec["knowledge_id"],),
            ).fetchone()["payload_json"]
        )
        self.assertEqual(after["state"], before)
        self.rt.retirement.upsert_teacher_capability("teacher:x", "cap.z", "granite4:3b")
        with self.assertRaises(FailClosed):
            self.rt.retirement.transition("teacher:x", "cap.z", TeacherLifecycle.RETIRED_MODEL)
        row = self.rt.store.conn.execute(
            "SELECT lifecycle FROM teacher_capability WHERE teacher_id = ? AND capability = ?",
            ("teacher:x", "cap.z"),
        ).fetchone()
        self.assertEqual(row["lifecycle"], TeacherLifecycle.ACTIVE_TEACHER.value)

    def test_loop_model_output_is_not_execution_authority(self) -> None:
        result = self.rt.loop.run({"task_id": "loop-1", "goal": "safe", "budget_tokens": 128}, authorize_tools=False)
        self.assertFalse(result["model_output_is_execution_authority"])
        self.assertFalse(result["direct_canonical_mutation"])
        stages = {row["stage"]: row for row in result["stages"]}
        self.assertEqual(stages["TOOL_AUTHORITY"]["status"], "BLOCKED")
        self.assertEqual(stages["TOOL_AUTHORITY"]["reason"], "MODEL_OUTPUT_IS_NOT_EXECUTION_AUTHORITY")

    def test_v9_mutation_rejected(self) -> None:
        with self.assertRaises(FailClosed):
            self.rt.v9.write_identity({"hack": True})
        with self.assertRaises(FailClosed):
            self.rt.memory.claim_authority("eidetic")

    def test_a17_4_consumption_pending(self) -> None:
        status = self.rt.a174.status()
        self.assertEqual(status["A17_4_REAL_DATA_CONSUMPTION"], "PENDING")

    def test_knowledge_debt_distinct_and_frequency(self) -> None:
        first = self.rt.knowledge_debt.create(
            concept="content-addressing",
            record={"importance": 0.9, "missing_prerequisites": ["hashing"], "priority": 0.8},
        )
        second = self.rt.knowledge_debt.encounter("content-addressing")
        self.assertTrue(first["distinct_from_learning_debt"])
        self.assertEqual(second["frequency"], 2)

    def test_student_wrong_teacher_right(self) -> None:
        diff = self.rt.differential.compare(
            {"task_id": "t2", "capability": "c2", "correct": False, "claims": ["wrong"]},
            {"task_id": "t2", "capability": "c2", "correct": True, "claims": ["right"], "procedures": ["p1"]},
        )
        self.assertEqual(diff["outcome"], DifferentialOutcome.STUDENT_WRONG_TEACHER_RIGHT.value)
        self.assertIn("KnowledgeCandidate", diff["candidates"])
        self.assertFalse(diff["canonical"])

    def test_both_partial_and_both_correct_different(self) -> None:
        partial = self.rt.differential.compare(
            {"task_id": "t3", "capability": "c3", "claims": ["shared", "only-student"], "procedures": ["s"]},
            {"task_id": "t3", "capability": "c3", "claims": ["shared", "only-teacher"], "procedures": ["t"]},
            independent_verifier={"student": None, "teacher": None},
        )
        self.assertIn(partial["outcome"], {DifferentialOutcome.BOTH_PARTIAL.value, DifferentialOutcome.UNRESOLVED.value})
        both = self.rt.differential.compare(
            {"task_id": "t4", "capability": "c4", "correct": True, "claims": ["ok"], "procedures": ["a"]},
            {"task_id": "t4", "capability": "c4", "correct": True, "claims": ["ok"], "procedures": ["b"]},
        )
        self.assertEqual(both["outcome"], DifferentialOutcome.BOTH_CORRECT_DIFFERENT.value)

    def test_cli_mastery_and_identity(self) -> None:
        from raios_wave.cli import main

        self.rt.mastery.record_evaluation("cli.cap", PASSING)
        rc = main(["--root", str(self.rt.root), "competency-status", "cli.cap"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
