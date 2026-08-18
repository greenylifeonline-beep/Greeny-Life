from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learning_fabric import (  # noqa: E402
    SCHEMA_VERSION,
    CompetencyEvidence,
    DebtPaymentEvidence,
    DebtState,
    ExpectedLearningValue,
    FailClosed,
    HarvestKind,
    KnowledgeMaturity,
    LearningFabric,
    LearningTrace,
    OriginClass,
    ParticipationMode,
    TrainingKind,
    analyze_teacher_student_difference,
    calculate_learning_yield,
    create_learning_debt,
    create_learning_trace,
    harvest_historical_learning,
    ingest_knowledge_candidate,
    plan_curriculum,
    plan_learning_debt_payment,
    propose_competency_update,
    select_student_participation_mode,
    transition_knowledge_maturity,
    validate_competency_update,
    validate_learning_debt_payment,
)
from learning_fabric.models import (  # noqa: E402
    CompressionLayer,
    DifferentialOutcome,
    EpistemicState,
    TeacherDependencyState,
    TeacherVerificationStatus,
)
from learning_fabric.store import Store  # noqa: E402


EVIDENCE = ("evidence://practice-1",)
ARTIFACT = "artifact://sha256/" + ("a" * 64)
RESULT_T = "result://teacher-1"
RESULT_S = "result://student-1"


class LearningFabricV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "fabric.sqlite")
        self.fabric = LearningFabric(self.db_path)

    def tearDown(self) -> None:
        self.fabric.close()
        self.tmp.cleanup()

    def _trace_kwargs(self, key: str = "idem-1") -> dict:
        return {
            "task_id": "task://task-1",
            "result_id": "result://result-1",
            "idempotency_key": key,
            "decision_summary": "Selected practice-then-verify path",
            "uncertainty": 0.2,
            "evidence_basis": ("evidence://basis-1",),
            "actions_taken": ("compare_outputs",),
            "correction_summary": "No private chain-of-thought stored",
            "artifact_refs": (ARTIFACT,),
            "evidence_refs": EVIDENCE,
            "experience_refs": ("experience://exp-1",),
            "failure_refs": ("failure://fail-1",),
            "skill_refs": ("skill://skill-1",),
        }

    def _walk_debt(self, debt_id: str) -> None:
        for state in (
            DebtState.ASSIGNED,
            DebtState.STUDYING,
            DebtState.PRACTICING,
            DebtState.REPLAY_PENDING,
            DebtState.VALIDATION_PENDING,
        ):
            self.fabric.transition_debt(debt_id, state)

    def _valid_payment(self) -> DebtPaymentEvidence:
        return DebtPaymentEvidence(
            required_practice_completed=True,
            replay_passed=True,
            transfer_test_passed=True,
            competency_validation_accepted=True,
            evidence_refs=EVIDENCE,
        )

    def test_MODULE_IMPORTS_PASS(self) -> None:
        import learning_fabric.identity as identity
        import learning_fabric.models as models
        import learning_fabric.refs as refs
        import learning_fabric.services as services
        import learning_fabric.store as store
        import learning_fabric.transitions as transitions

        self.assertTrue(identity.SCHEMA_VERSION)
        self.assertTrue(models.LearningTrace)
        self.assertTrue(refs.validate_exchange_ref)
        self.assertTrue(services.LearningFabric)
        self.assertTrue(store.Store)
        self.assertTrue(transitions.assert_debt_transition)

    def test_DATACLASS_CONSTRUCTION_PASS(self) -> None:
        trace = LearningTrace(
            trace_id="trace:x",
            task_id="task://t",
            result_id="result://r",
            idempotency_key="k",
            decision_summary="summary",
            uncertainty=0.1,
            created_at="2026-08-18T00:00:00+00:00",
            evidence_refs=EVIDENCE,
        ).sealed()
        self.assertEqual(trace.schema_version, SCHEMA_VERSION)
        self.assertTrue(trace.content_sha256)
        elv = ExpectedLearningValue(
            recurrence_probability=0.5,
            strategic_value=0.5,
            novelty=0.5,
            generalizability=0.5,
            uncertainty=0.5,
            expected_competency_gain=0.5,
            learning_cost=0.2,
            teacher_cost=0.2,
        )
        self.assertGreater(elv.score(), 0)
        evidence = CompetencyEvidence(
            practice=True,
            replay=True,
            verification=True,
            transfer_tests=True,
            evidence_refs=EVIDENCE,
        )
        self.assertTrue(evidence.practice)

    def test_IMMUTABLE_TRACE_PASS(self) -> None:
        trace = create_learning_trace(self.fabric, **self._trace_kwargs())
        with self.assertRaises(FrozenInstanceError):
            trace.decision_summary = "mutated"  # type: ignore[misc]
        with self.assertRaises(sqlite3.IntegrityError):
            self.fabric.store.conn.execute(
                "UPDATE traces SET payload_json=? WHERE trace_id=?",
                ("{}", trace.trace_id),
            )

    def test_TRACE_IDEMPOTENCY_PASS(self) -> None:
        first = create_learning_trace(self.fabric, **self._trace_kwargs("same-key"))
        second = create_learning_trace(self.fabric, **self._trace_kwargs("same-key"))
        self.assertEqual(first.trace_id, second.trace_id)
        self.assertEqual(first.content_sha256, second.content_sha256)
        conflict = self._trace_kwargs("same-key")
        conflict["decision_summary"] = "different observable summary"
        with self.assertRaises(FailClosed) as ctx:
            create_learning_trace(self.fabric, **conflict)
        self.assertIn("IDEMPOTENCY_KEY_PAYLOAD_CONFLICT", str(ctx.exception))

    def test_ILLEGAL_DEBT_TRANSITION_REJECTED(self) -> None:
        debt = create_learning_debt(
            self.fabric,
            task_id="task://debt-1",
            capability="cap.alpha",
            knowledge_gap="missing transfer",
            teacher="teacher-a",
            teacher_artifacts=(ARTIFACT,),
        )
        with self.assertRaises(FailClosed) as ctx:
            self.fabric.transition_debt(debt["debt_id"], DebtState.PAID)
        self.assertIn("ILLEGAL_DEBT_TRANSITION", str(ctx.exception))

    def test_DEBT_READING_ONLY_PAYMENT_REJECTED(self) -> None:
        debt = create_learning_debt(
            self.fabric,
            task_id="task://debt-2",
            capability="cap.beta",
            knowledge_gap="gap",
            teacher="teacher-a",
        )
        self._walk_debt(debt["debt_id"])
        plan = plan_learning_debt_payment(self.fabric, debt["debt_id"])
        self.assertTrue(plan["reading_or_observing_insufficient"])
        with self.assertRaises(FailClosed) as ctx:
            validate_learning_debt_payment(
                self.fabric,
                debt["debt_id"],
                DebtPaymentEvidence(
                    required_practice_completed=True,
                    replay_passed=True,
                    transfer_test_passed=True,
                    competency_validation_accepted=True,
                    evidence_refs=EVIDENCE,
                    reading_only=True,
                ),
            )
        self.assertEqual(str(ctx.exception), "DEBT_READING_ONLY_PAYMENT_REJECTED")

    def test_DEBT_TRANSFER_FAILURE_REJECTED(self) -> None:
        debt = create_learning_debt(
            self.fabric,
            task_id="task://debt-3",
            capability="cap.gamma",
            knowledge_gap="gap",
            teacher="teacher-a",
        )
        self._walk_debt(debt["debt_id"])
        with self.assertRaises(FailClosed) as ctx:
            validate_learning_debt_payment(
                self.fabric,
                debt["debt_id"],
                DebtPaymentEvidence(
                    required_practice_completed=True,
                    replay_passed=True,
                    transfer_test_passed=False,
                    competency_validation_accepted=True,
                    evidence_refs=EVIDENCE,
                ),
            )
        self.assertEqual(str(ctx.exception), "DEBT_TRANSFER_FAILURE_REJECTED")

    def test_COMPETENCY_WITHOUT_EVIDENCE_REJECTED(self) -> None:
        cases = [
            CompetencyEvidence(True, True, True, True, EVIDENCE, teacher_answer_only=True),
            CompetencyEvidence(True, True, True, True, EVIDENCE, student_read_only=True),
            CompetencyEvidence(True, True, True, True, EVIDENCE, synthetic_repetition_only=True),
            CompetencyEvidence(True, True, True, True, EVIDENCE, llm_claims_learning=True),
            CompetencyEvidence(False, True, True, True, EVIDENCE),
        ]
        for evidence in cases:
            with self.assertRaises(FailClosed) as ctx:
                propose_competency_update(self.fabric, "cap.delta", 0.9, evidence)
            self.assertEqual(str(ctx.exception), "COMPETENCY_WITHOUT_EVIDENCE_REJECTED")

    def test_TEACHER_WRONG_STUDENT_RIGHT(self) -> None:
        diff = analyze_teacher_student_difference(
            self.fabric,
            task_id="task://diff-1",
            teacher_result_ref=RESULT_T,
            student_result_ref=RESULT_S,
            teacher_correct=False,
            student_correct=True,
            evidence_refs=EVIDENCE,
            independent_verifier_refs=("evidence://verifier-1",),
        )
        self.assertEqual(diff.outcome, DifferentialOutcome.TEACHER_WRONG_STUDENT_RIGHT)
        self.assertTrue(diff.teacher_error_detected)
        self.assertTrue(diff.educational_only)
        self.assertEqual(diff.teacher_verification_status, TeacherVerificationStatus.ERROR_DETECTED)

    def test_TEACHER_RIGHT_STUDENT_WRONG(self) -> None:
        diff = analyze_teacher_student_difference(
            self.fabric,
            task_id="task://diff-2",
            teacher_result_ref=RESULT_T,
            student_result_ref=RESULT_S,
            teacher_correct=True,
            student_correct=False,
            evidence_refs=EVIDENCE,
        )
        self.assertEqual(diff.outcome, DifferentialOutcome.TEACHER_RIGHT_STUDENT_WRONG)
        self.assertFalse(diff.teacher_error_detected)
        self.assertEqual(diff.teacher_verification_status, TeacherVerificationStatus.UNTRUSTED)

    def test_BOTH_WRONG(self) -> None:
        diff = analyze_teacher_student_difference(
            self.fabric,
            task_id="task://diff-3",
            teacher_result_ref=RESULT_T,
            student_result_ref=RESULT_S,
            teacher_correct=False,
            student_correct=False,
            evidence_refs=EVIDENCE,
        )
        self.assertEqual(diff.outcome, DifferentialOutcome.BOTH_WRONG)
        self.assertTrue(diff.teacher_error_detected)

    def test_TEACHER_DISAGREEMENT(self) -> None:
        diff = analyze_teacher_student_difference(
            self.fabric,
            task_id="task://diff-4",
            teacher_result_ref=RESULT_T,
            student_result_ref="result://teacher-2",
            teacher_correct=True,
            student_correct=True,
            disagreement=True,
            evidence_refs=EVIDENCE,
        )
        self.assertEqual(diff.outcome, DifferentialOutcome.TEACHER_DISAGREEMENT)
        self.assertEqual(diff.contradiction_state, "CONTRADICTED")
        self.assertEqual(diff.teacher_verification_status, TeacherVerificationStatus.CONTRADICTED)

    def test_SYNTHETIC_TRUTH_ESCALATION_REJECTED(self) -> None:
        obj = ingest_knowledge_candidate(
            self.fabric,
            claim="synthetic claim",
            origin_class=OriginClass.SYNTHETIC,
            evidence_refs=EVIDENCE,
            observed_at="2026-01-01T00:00:00+00:00",
            temporal_class="EPHEMERAL",
            valid_from="2026-01-01T00:00:00+00:00",
            valid_until="2026-12-31T00:00:00+00:00",
            revalidation_policy="require_independent_evidence",
        )
        with self.assertRaises(FailClosed) as ctx:
            self.fabric.set_epistemic_state(obj["knowledge_id"], EpistemicState.VERIFIED)
        self.assertEqual(str(ctx.exception), "SYNTHETIC_TRUTH_ESCALATION_REJECTED")

    def test_STALE_KNOWLEDGE_REVALIDATION_REQUIRED(self) -> None:
        obj = ingest_knowledge_candidate(
            self.fabric,
            claim="time-bound claim",
            origin_class=OriginClass.REAL,
            evidence_refs=EVIDENCE,
            observed_at="2020-01-01T00:00:00+00:00",
            temporal_class="VOLATILE",
            valid_from="2020-01-01T00:00:00+00:00",
            valid_until="2021-01-01T00:00:00+00:00",
            revalidation_policy="revalidate_after_valid_until",
            revalidation_due_at="2021-01-01T00:00:00+00:00",
        )
        with self.assertRaises(FailClosed) as ctx:
            self.fabric.require_revalidation_if_stale(obj["knowledge_id"], "2026-08-18T00:00:00+00:00")
        self.assertEqual(str(ctx.exception), "STALE_KNOWLEDGE_REVALIDATION_REQUIRED")

    def test_KNOWLEDGE_ILLEGAL_MATURITY_JUMP_REJECTED(self) -> None:
        obj = ingest_knowledge_candidate(
            self.fabric,
            claim="real claim",
            origin_class=OriginClass.REAL,
            evidence_refs=EVIDENCE,
            observed_at="2026-08-18T00:00:00+00:00",
            temporal_class="DURABLE",
            valid_from="2026-08-18T00:00:00+00:00",
            valid_until=None,
            revalidation_policy="on_contradiction",
        )
        with self.assertRaises(FailClosed) as ctx:
            transition_knowledge_maturity(self.fabric, obj["knowledge_id"], KnowledgeMaturity.MASTERED)
        self.assertIn("ILLEGAL_MATURITY_JUMP", str(ctx.exception))

    def test_RETROSPECTIVE_FACT_INFERENCE_SEPARATION(self) -> None:
        items = harvest_historical_learning(
            self.fabric,
            "experience://history-1",
            [
                (HarvestKind.OBSERVED_FACT, "The test failed at step 3"),
                (HarvestKind.DERIVED_INFERENCE, "Step 3 likely lacks a guard"),
                (HarvestKind.UNVERIFIED_HYPOTHESIS, "A retry policy may fix it"),
            ],
        )
        kinds = {item["kind"] for item in items}
        self.assertEqual(
            kinds,
            {
                HarvestKind.OBSERVED_FACT.value,
                HarvestKind.DERIVED_INFERENCE.value,
                HarvestKind.UNVERIFIED_HYPOTHESIS.value,
            },
        )
        with self.assertRaises(FailClosed):
            harvest_historical_learning(
                self.fabric,
                "experience://history-2",
                [
                    (HarvestKind.OBSERVED_FACT, "a"),
                    (HarvestKind.OBSERVED_FACT, "b"),
                    (HarvestKind.OBSERVED_FACT, "c"),
                ],
            )

    def test_TEACHER_EARLY_RETIREMENT_REJECTED(self) -> None:
        self.fabric.record_teacher_task(
            "cap.teacher",
            "ctx-1",
            transfer_success=True,
            verification_failed=False,
            evidence_refs=EVIDENCE,
        )
        with self.assertRaises(FailClosed) as ctx:
            self.fabric.try_retire_teacher("cap.teacher")
        self.assertEqual(str(ctx.exception), "TEACHER_EARLY_RETIREMENT_REJECTED")

    def test_MULTI_CONTEXT_TRANSFER_REQUIRED(self) -> None:
        for i in range(5):
            self.fabric.record_teacher_task(
                "cap.transfer",
                "same-context",
                transfer_success=False,
                verification_failed=False,
                evidence_refs=EVIDENCE,
            )
        with self.assertRaises(FailClosed) as ctx:
            self.fabric.try_retire_teacher("cap.transfer")
        self.assertEqual(str(ctx.exception), "MULTI_CONTEXT_TRANSFER_REQUIRED")

    def test_COGNITIVE_COMPRESSION_PROVENANCE_PRESERVED(self) -> None:
        raw = self.fabric.compress(CompressionLayer.RAW_EXPERIENCE, "raw episode", EVIDENCE)
        pattern = self.fabric.compress(
            CompressionLayer.PATTERN, "pattern", (f"evidence://{raw['node_id']}",) + EVIDENCE
        )
        abstraction = self.fabric.compress(
            CompressionLayer.ABSTRACTION, "abstraction", tuple(pattern["source_refs"])
        )
        knowledge = self.fabric.compress(
            CompressionLayer.KNOWLEDGE_SKILL, "skill", tuple(abstraction["source_refs"])
        )
        archive = self.fabric.compress(
            CompressionLayer.COLD_ARCHIVE, "archive", tuple(knowledge["source_refs"])
        )
        self.assertIn(EVIDENCE[0], archive["source_refs"])
        with self.assertRaises(FailClosed):
            self.fabric.compress(CompressionLayer.PATTERN, "orphan", ())

    def test_DATABASE_TRANSACTION_ROLLBACK_PASS(self) -> None:
        debt_id = "debt:rollback"
        try:
            with self.fabric.store.transaction():
                self.fabric.store.conn.execute(
                    "INSERT INTO debts(debt_id, task_id, capability, state, payload_json, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (debt_id, "task://t", "cap.rollback", "OPEN", "{}", "t", "t"),
                )
                raise FailClosed("INTENTIONAL_ROLLBACK")
        except FailClosed as exc:
            self.assertEqual(str(exc), "INTENTIONAL_ROLLBACK")
        row = self.fabric.store.conn.execute(
            "SELECT 1 FROM debts WHERE debt_id = ?",
            (debt_id,),
        ).fetchone()
        self.assertIsNone(row)

    def test_RESTART_PERSISTENCE_PASS(self) -> None:
        trace = create_learning_trace(self.fabric, **self._trace_kwargs("persist-key"))
        debt = create_learning_debt(
            self.fabric,
            task_id="task://persist",
            capability="cap.persist",
            knowledge_gap="gap",
            teacher="teacher-a",
        )
        self.fabric.close()
        restarted = LearningFabric(self.db_path)
        loaded = restarted.get_trace(trace.trace_id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.content_sha256, trace.content_sha256)
        self.assertEqual(restarted.store.schema_version(), 1)
        self.assertEqual(restarted.store.logical_schema_version(), SCHEMA_VERSION)
        self.assertEqual(restarted._get("debts", debt["debt_id"])["state"], DebtState.OPEN.value)
        restarted.close()
        self.fabric = LearningFabric(self.db_path)

    def test_IDEMPOTENT_REPLAY_PASS(self) -> None:
        first = create_learning_trace(self.fabric, **self._trace_kwargs("replay-key"))
        self.fabric.close()
        restarted = LearningFabric(self.db_path)
        second = create_learning_trace(restarted, **self._trace_kwargs("replay-key"))
        self.assertEqual(first.trace_id, second.trace_id)
        events = [
            row["event_type"]
            for row in restarted.store.list_events()
            if row["event_type"] == "TRACE_CREATED"
        ]
        self.assertEqual(len(events), 1)
        restarted.close()
        self.fabric = LearningFabric(self.db_path)

    def test_DEBT_PAYMENT_ACCEPTED_WITH_FULL_EVIDENCE(self) -> None:
        debt = create_learning_debt(
            self.fabric,
            task_id="task://debt-paid",
            capability="cap.paid",
            knowledge_gap="gap",
            teacher="teacher-a",
        )
        self._walk_debt(debt["debt_id"])
        paid = validate_learning_debt_payment(self.fabric, debt["debt_id"], self._valid_payment())
        self.assertEqual(paid["state"], DebtState.PAID.value)

    def test_COMPETENCY_ACCEPTED_WITH_FULL_EVIDENCE(self) -> None:
        proposal = propose_competency_update(
            self.fabric,
            "cap.ready",
            0.72,
            CompetencyEvidence(
                practice=True,
                replay=True,
                verification=True,
                transfer_tests=True,
                evidence_refs=EVIDENCE,
            ),
        )
        accepted = validate_competency_update(self.fabric, proposal["proposal_id"], True)
        self.assertEqual(accepted["status"], "ACCEPTED")
        node = self.fabric._get("competency_nodes", "cap.ready")
        self.assertEqual(node["score"], 0.72)

    def test_TRAINING_CANDIDATE_GATE(self) -> None:
        draft = self.fabric.create_training_candidate(
            TrainingKind.SFT, "artifact://sha256/" + ("b" * 64), validated=False
        )
        with self.assertRaises(FailClosed):
            self.fabric.promote_training_candidate(draft["candidate_id"])
        validated = self.fabric.create_training_candidate(
            TrainingKind.TRANSFER, "artifact://sha256/" + ("c" * 64), validated=True
        )
        promoted = self.fabric.promote_training_candidate(validated["candidate_id"])
        self.assertEqual(promoted["state"], "PROMOTED")

    def test_CURRICULUM_AND_PARTICIPATION_AND_YIELD(self) -> None:
        elv = ExpectedLearningValue(0.8, 0.7, 0.4, 0.6, 0.3, 0.5, 0.2, 0.1)
        plan = plan_curriculum(self.fabric, "cap.curriculum", elv)
        self.assertIn("expected_learning_value", plan)
        mode = select_student_participation_mode(
            self.fabric,
            competency=0.9,
            confidence=0.8,
            task_difficulty=0.2,
            risk=0.1,
            teacher_available=True,
            expected_learning_value=0.4,
        )
        self.assertEqual(mode, ParticipationMode.INDEPENDENT)
        yield_info = calculate_learning_yield(self.fabric, True, False)
        self.assertTrue(yield_info["learning_debt_required"])
        self.assertFalse(yield_info["cognitive_cycle_complete"])

    def test_LEGAL_MATURITY_WALK_AND_EPISTEMIC_STATES(self) -> None:
        obj = ingest_knowledge_candidate(
            self.fabric,
            claim="verified real claim",
            origin_class=OriginClass.REAL,
            evidence_refs=EVIDENCE,
            observed_at="2026-08-18T00:00:00+00:00",
            temporal_class="DURABLE",
            valid_from="2026-08-18T00:00:00+00:00",
            valid_until=None,
            revalidation_policy="on_contradiction",
        )
        current = KnowledgeMaturity.SEEN
        for nxt in (
            KnowledgeMaturity.UNDERSTOOD,
            KnowledgeMaturity.CONNECTED,
            KnowledgeMaturity.PRACTICED,
            KnowledgeMaturity.VALIDATED,
            KnowledgeMaturity.TRANSFERABLE,
            KnowledgeMaturity.MASTERED,
        ):
            obj = transition_knowledge_maturity(self.fabric, obj["knowledge_id"], nxt)
            current = nxt
        self.assertEqual(current, KnowledgeMaturity.MASTERED)
        bounded = self.fabric.set_epistemic_state(obj["knowledge_id"], EpistemicState.EVIDENCE_BOUNDED)
        verified = self.fabric.set_epistemic_state(bounded["knowledge_id"], EpistemicState.VERIFIED)
        self.assertEqual(verified["epistemic_state"], EpistemicState.VERIFIED.value)

    def test_AUDIT_EVENTS_APPEND_ONLY(self) -> None:
        create_learning_trace(self.fabric, **self._trace_kwargs("audit-key"))
        events = self.fabric.store.list_events()
        types = {event["event_type"] for event in events}
        self.assertIn("TRACE_CREATED", types)
        with self.assertRaises(sqlite3.IntegrityError):
            self.fabric.store.conn.execute("DELETE FROM audit_events")


if __name__ == "__main__":
    unittest.main()
