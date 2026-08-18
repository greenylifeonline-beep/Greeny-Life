from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from ccee.arena import Arena  # noqa: E402
from ccee.config import FailClosed, contains_forbidden_success  # noqa: E402
from ccee.engine import CCEE  # noqa: E402
from ccee.first_experiment import diagnose_atomic_failure, run_experiment  # noqa: E402
from ccee.forgetting import Forgetting  # noqa: E402
from ccee.knowledge import KnowledgeMetabolism  # noqa: E402
from ccee.ollama_runtime import OllamaRuntimeManager, OllamaServerError  # noqa: E402
from ccee.structured_inference import StructuredInference  # noqa: E402
from ccee.wal import CognitiveWAL  # noqa: E402


class CCEEFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ccee = CCEE(Path(self.tmp.name) / "ccee", repo_root=REPO)

    def tearDown(self) -> None:
        self.ccee.close()
        self.tmp.cleanup()

    def test_false_pass_impossible(self) -> None:
        self.assertTrue(contains_forbidden_success("status PASS"))
        self.assertFalse(contains_forbidden_success("A18_CCEE_FOUNDATION_PASS"))

    def test_child_failure_propagates(self) -> None:
        with self.assertRaises(FailClosed) as ctx:
            self.ccee.cert.run_child([sys.executable, "-c", "raise SystemExit(1)"])
        self.assertIn("CHILD_EXIT_NONZERO", str(ctx.exception))

    def test_http500_learning_event(self) -> None:
        with self.assertRaises(OllamaServerError):
            raise OllamaServerError(500, "boom")
        self.ccee.bus.emit("OLLAMA_SERVER_ERROR", "test", {"status": 500})
        types = [e.event_type for e in self.ccee.wal.replay()]
        self.assertIn("OLLAMA_SERVER_ERROR", types)
        self.assertEqual(self.ccee.ollama.classify_http(500), "OLLAMA_SERVER_ERROR")

    def test_wal_append(self) -> None:
        ev = self.ccee.wal.append("OBSERVATION", "test", {"n": 1})
        self.assertEqual(ev.canonical, False)
        self.assertTrue(ev.event_hash)

    def test_wal_recovery(self) -> None:
        wal_root = Path(self.tmp.name) / "walrec"
        wal = CognitiveWAL(wal_root, repo_root=REPO)
        ev = wal.append("LESSON", "test", {"n": 9})
        wal.close()
        (wal_root / "cognitive.wal.sqlite").unlink()
        wal2 = CognitiveWAL(wal_root, repo_root=REPO)
        recovered = wal2.get(ev.event_id)
        self.assertEqual(recovered.payload["n"], 9)
        wal2.close()

    def test_wal_dedup(self) -> None:
        a = self.ccee.wal.append("OBSERVATION", "dup", {"k": 1})
        b = self.ccee.wal.append("OBSERVATION", "dup", {"k": 1})
        self.assertEqual(a.event_id, b.event_id)

    def test_checkpoint_restart(self) -> None:
        self.ccee.wal.append("TASK_COMPLETED", "test", {"ok": True})
        saved = self.ccee.checkpoint.save()
        restored = self.ccee.checkpoint.restore()
        self.assertTrue(restored["restored"])
        self.assertGreaterEqual(restored["wal_offset"], saved["wal_offset"])
        self.assertFalse(restored["duplicate_promotion"])

    def test_experience_metabolism(self) -> None:
        ep = self.ccee.metabolism.metabolize(
            {"id": "t1", "intent": "learn"},
            {"ok": False, "failure_score": 1, "success_score": 0, "plan": ["a"]},
            {"lessons": ["hash receipts"], "candidate_skills": ["detector"], "uncertainty": 0.6},
        )
        self.assertGreater(ep["experience_multiplication_factor"], 1)

    def test_curiosity_ranking(self) -> None:
        ranked = self.ccee.curiosity.ingest_signals({"failures": ["e1", "e2"], "uncertainty": ["e3"], "teacher_superiority": ["e4"]})
        self.assertGreaterEqual(ranked[0]["score"], ranked[-1]["score"])
        self.assertTrue(any(m["blocked_auto_experiment"] for m in ranked if m.get("high_risk")))
        self.assertTrue(all(m["auto_execute"] is False for m in ranked))

    def test_curriculum_priority(self) -> None:
        high = self.ccee.curiosity.rank(
            {
                "kind": "failures",
                "refs": ["a"],
                "expected_gain": 0.9,
                "reuse_probability": 0.9,
                "leverage": 0.9,
                "uncertainty": 0.9,
                "failure_reduction": 0.9,
                "teacher_dependency": 0.9,
                "compute_cost": 0.1,
                "risk": 0.1,
            }
        )
        low = self.ccee.curiosity.rank(
            {
                "kind": "uncertainty",
                "refs": ["b"],
                "expected_gain": 0.1,
                "reuse_probability": 0.1,
                "leverage": 0.1,
                "uncertainty": 0.1,
                "failure_reduction": 0.1,
                "teacher_dependency": 0.1,
                "compute_cost": 0.9,
                "risk": 0.2,
            }
        )
        self.ccee.curriculum.queue(high, {"available_compute": 1, "teacher_availability": 1})
        self.ccee.curriculum.queue(low, {"available_compute": 1, "teacher_availability": 1})
        nxt = self.ccee.curriculum.next_mission()
        self.assertEqual(nxt["mission_id"], high["mission_id"])

    def test_failure_imagination(self) -> None:
        imagined = self.ccee.imagination.imagine({"id": "x", "kind": "http_500"}, sandbox=True)
        self.assertGreaterEqual(len(imagined), 12)
        self.assertTrue(all(not i["production_runtime_sabotaged"] for i in imagined))
        with self.assertRaises(FailClosed):
            self.ccee.imagination.imagine({"id": "x", "kind": "http_500"}, sandbox=False)

    def test_replay_schedule(self) -> None:
        planned = self.ccee.replay.plan({"id": "r1"}, "failure", gain=0.9, cost=0.1, spacing="minutes")
        skipped = self.ccee.replay.plan({"id": "r2"}, "high-value", gain=0.01, cost=1.0, spacing="days")
        self.assertIsNotNone(planned)
        self.assertIsNone(skipped)

    def test_teacher_strategy_extraction(self) -> None:
        recs = self.ccee.teachers.extract_from_text(
            "granite4:3b",
            "First break the problem, verify the hash, fail closed, do not emit false pass, then stop.",
        )
        self.assertTrue(recs)
        self.assertTrue(all(not r["memorized_output"] and r["canonical"] is False for r in recs))

    def test_skill_candidate(self) -> None:
        skill = self.ccee.skills.compile(
            {
                "interface": "detect_false_pass(text)->bool",
                "preconditions": ["text"],
                "inputs": ["text"],
                "outputs": ["bool"],
                "procedure": ["scan tokens", "require gates"],
                "invariants": ["no PASS before gates"],
                "negative_controls": ["print PASS then throw"],
                "tests": ["test_11"],
                "rollback": {"enabled": True},
                "failure_modes": ["false pass"],
                "provenance": {"source": "a17.13"},
            }
        )
        self.assertFalse(skill["active"])
        with self.assertRaises(FailClosed):
            self.ccee.skills.compile({"prompt_template": "you are a helper", "interface": "x"})

    def test_zero_llm_candidate(self) -> None:
        rec = self.ccee.skills.zero_llm_candidate("hash_verification", 0.9, 1.0, True, True)
        self.assertTrue(rec["eligible"])
        self.assertFalse(rec["promoted"])

    def test_structured_output_validation(self) -> None:
        rec = self.ccee.structured.parse(
            {
                "assessment": {"ok": True},
                "uncertainty": [],
                "claims": [],
                "evidence_needed": [],
                "plan": [],
                "tool_requests": [],
                "hypotheses": [],
                "skill_candidates": [],
                "learning_signals": [],
                "stop_reason": "done",
            }
        )
        self.assertFalse(rec.execution_authority)

    def test_invalid_model_output_fail_closed(self) -> None:
        with self.assertRaises(FailClosed):
            self.ccee.structured.parse("The model said PASS and ran the tool.")
        with self.assertRaises(FailClosed):
            self.ccee.structured.parse({"assessment": {}, "execution_authority": True, "stop_reason": "x", "uncertainty": [], "claims": [], "evidence_needed": [], "plan": [], "tool_requests": [], "hypotheses": [], "skill_candidates": [], "learning_signals": []})

    def test_causal_hypothesis(self) -> None:
        node = self.ccee.causal.add("DECISION", {"id": "d1"})
        self.assertEqual(node["status"], "CAUSAL_HYPOTHESIS")
        with self.assertRaises(FailClosed):
            self.ccee.causal.claim_true_causality(node["node_id"])

    def test_contradiction(self) -> None:
        rec = self.ccee.contradiction.note({"id": "a", "claim": "PASS allowed"}, {"id": "b", "claim": "PASS forbidden"})
        self.assertEqual(rec["state"], "CONTRADICTED")

    def test_forgetting_non_destructive(self) -> None:
        rec = self.ccee.knowledge.ingest("observation", "stale heuristic")
        forgotten = self.ccee.forgetting.candidate(rec["knowledge_id"], "unused")
        self.assertFalse(forgotten["destroyed"])
        hist = ROOT / "evidence" / "failures" / "HISTORICAL-A17.13.json"
        with self.assertRaises(FailClosed):
            self.ccee.forgetting.destroy(hist)
        self.assertTrue(hist.is_file())

    def test_teacher_not_deleted(self) -> None:
        dep = self.ccee.transfer.teacher_dependency(
            baseline_without_teacher=0.2,
            teacher_assisted=0.8,
            student_after_teaching=0.5,
            unseen_transfer=0.0,
            retention=0.0,
        )
        self.assertTrue(dep["deletion_forbidden"])
        self.assertFalse(dep["retirement_allowed"])

    def test_no_canonical_auto_promotion(self) -> None:
        rec = self.ccee.knowledge.ingest("hypothesis", "maybe")
        with self.assertRaises(FailClosed):
            self.ccee.knowledge.promote_canonical(rec["knowledge_id"])
        arena = Arena()
        cand = arena.compete({"accuracy": 0.5}, {"accuracy": 0.6, "id": "c1"})
        with self.assertRaises(FailClosed):
            arena.advance(cand["candidate_id"], "PROMOTION_REQUESTED")

    def test_resource_governor(self) -> None:
        self.ccee.governor.enter("FOREGROUND_PRIORITY")
        self.assertFalse(self.ccee.governor.allow_background())
        self.assertFalse(self.ccee.governor.allow_high_risk())

    def test_foreground_priority(self) -> None:
        tick = self.ccee.scheduler.tick(foreground_busy=True)
        self.assertEqual(tick["mode"], "FOREGROUND_PRIORITY")
        self.assertFalse(tick["background"])

    def test_learning_metrics(self) -> None:
        self.ccee.metrics.record("ExperienceMultiplicationFactor", 4.0)
        snap = self.ccee.metrics.snapshot()
        self.assertEqual(snap["ExperienceMultiplicationFactor"], 4.0)

    def test_transfer_is_unseen(self) -> None:
        self.ccee.transfer.register_train("train-1")
        with self.assertRaises(FailClosed):
            self.ccee.transfer.register_unseen("train-1")
        self.ccee.transfer.register_unseen("unseen-1")
        rec = self.ccee.transfer.evaluate(
            {"id": "unseen-1", "http": 200, "invalid_semantic": True, "report_integrity": False, "expected": "HTTP_200_INVALID_SEMANTIC"},
            diagnose_atomic_failure,
        )
        self.assertTrue(rec["passed"])
        self.assertFalse(rec["mastery_claimed"])

    def test_retention(self) -> None:
        rec = self.ccee.retention.evaluate("atomic.certification", True, True, 60)
        self.assertEqual(rec["retention"], "RETAINED")
        self.assertFalse(rec["mastery_claimed"])

    def test_no_v9_mutation(self) -> None:
        with self.assertRaises(FailClosed):
            CCEE(REPO / "RAIOS" / "V9" / "ccee-illegal", repo_root=REPO)

    def test_first_live_experiment(self) -> None:
        result = run_experiment(self.ccee, REPO)
        self.assertGreater(result["multiplication"], 1)
        self.assertGreaterEqual(result["counterfactuals"], 12)
        self.assertTrue(result["transfer"]["passed"])
        self.assertFalse(result["mastery_claimed"])
        self.assertFalse(result["teacher_assistance"])

    def test_wal_integrity_sqlite(self) -> None:
        self.ccee.wal.append("OBSERVATION", "int", {"z": 1})
        with self.assertRaises(sqlite3.IntegrityError):
            self.ccee.wal.conn.execute("UPDATE wal_events SET payload_json='{}' WHERE seq=1")


if __name__ == "__main__":
    unittest.main()
