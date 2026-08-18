from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .identity import SCHEMA_VERSION, new_id, utc_now
from .models import (
    CompetencyEvidence,
    CompressionLayer,
    DebtPaymentEvidence,
    DebtState,
    DifferentialOutcome,
    EpistemicState,
    EventType,
    ExpectedLearningValue,
    FailClosed,
    HarvestKind,
    KnowledgeMaturity,
    LearningTrace,
    OriginClass,
    ParticipationMode,
    TeacherDependencyState,
    TeacherStudentDifferential,
    TeacherVerificationStatus,
    TrainingKind,
    TrainingState,
    clamp_unit,
)
from .refs import validate_exchange_ref, validate_refs
from .store import Store
from .transitions import (
    assert_debt_transition,
    assert_maturity_transition,
    assert_not_synthetic_truth_escalation,
    assert_teacher_dep_transition,
    assert_training_transition,
)


ALLOWED_TABLES = {
    "debts": "debt_id",
    "knowledge_objects": "knowledge_id",
    "competency_nodes": "capability_id",
    "competency_proposals": "proposal_id",
    "teacher_dependencies": "capability_id",
    "training_candidates": "candidate_id",
    "harvest_items": "harvest_id",
    "compression_nodes": "node_id",
}


class LearningFabric:
    def __init__(self, db_path: str | Path) -> None:
        self.store = Store(db_path)

    def close(self) -> None:
        self.store.close()

    def _put(self, table: str, key: str, columns: dict[str, Any], payload: dict[str, Any]) -> None:
        pk = ALLOWED_TABLES[table]
        exists = self.store.conn.execute(
            f"SELECT 1 FROM {table} WHERE {pk} = ?",
            (key,),
        ).fetchone()
        columns = dict(columns)
        columns["payload_json"] = json.dumps(payload, sort_keys=True, default=str)
        if exists:
            assignments = ", ".join(f"{col} = ?" for col in columns if col != pk)
            values = [columns[col] for col in columns if col != pk]
            values.append(key)
            self.store.conn.execute(
                f"UPDATE {table} SET {assignments} WHERE {pk} = ?",
                values,
            )
        else:
            cols = list(columns.keys())
            self.store.conn.execute(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                tuple(columns[c] for c in cols),
            )

    def _get(self, table: str, key: str) -> dict[str, Any] | None:
        return self.store.fetch_one(table, ALLOWED_TABLES[table], key)

    def create_learning_trace(
        self,
        task_id: str,
        result_id: str,
        idempotency_key: str,
        decision_summary: str,
        uncertainty: float,
        evidence_basis: list[str] | tuple[str, ...] = (),
        actions_taken: list[str] | tuple[str, ...] = (),
        correction_summary: str = "",
        artifact_refs: list[str] | tuple[str, ...] = (),
        evidence_refs: list[str] | tuple[str, ...] = (),
        experience_refs: list[str] | tuple[str, ...] = (),
        failure_refs: list[str] | tuple[str, ...] = (),
        skill_refs: list[str] | tuple[str, ...] = (),
    ) -> LearningTrace:
        validate_exchange_ref(task_id if task_id.startswith("task://") else f"task://{task_id}")
        validate_exchange_ref(result_id if result_id.startswith("result://") else f"result://{result_id}")
        trace = LearningTrace(
            trace_id=new_id("trace"),
            task_id=task_id if task_id.startswith("task://") else f"task://{task_id}",
            result_id=result_id if result_id.startswith("result://") else f"result://{result_id}",
            idempotency_key=idempotency_key,
            decision_summary=decision_summary,
            uncertainty=clamp_unit(uncertainty, "UNCERTAINTY"),
            created_at=utc_now(),
            schema_version=SCHEMA_VERSION,
            evidence_basis=tuple(evidence_basis),
            actions_taken=tuple(actions_taken),
            correction_summary=correction_summary,
            artifact_refs=tuple(artifact_refs),
            evidence_refs=tuple(evidence_refs),
            experience_refs=tuple(experience_refs),
            failure_refs=tuple(failure_refs),
            skill_refs=tuple(skill_refs),
        ).sealed()
        with self.store.transaction():
            stored = self.store.insert_trace(asdict_trace(trace))
            created = stored["trace_id"] == trace.trace_id
            if created:
                self.store.append_event(EventType.TRACE_CREATED, trace.trace_id, {"task_id": trace.task_id})
            return dict_to_trace(stored)

    def get_trace(self, trace_id: str) -> LearningTrace | None:
        stored = self.store.get_trace(trace_id)
        return dict_to_trace(stored) if stored else None

    def analyze_teacher_student_difference(
        self,
        task_id: str,
        teacher_result_ref: str,
        student_result_ref: str,
        teacher_correct: bool,
        student_correct: bool,
        disagreement: bool = False,
        evidence_refs: list[str] | tuple[str, ...] = (),
        independent_verifier_refs: list[str] | tuple[str, ...] = (),
    ) -> TeacherStudentDifferential:
        validate_exchange_ref(teacher_result_ref)
        validate_exchange_ref(student_result_ref)
        validate_refs(evidence_refs)
        if disagreement:
            outcome = DifferentialOutcome.TEACHER_DISAGREEMENT
        elif teacher_correct and student_correct:
            outcome = DifferentialOutcome.BOTH_RIGHT
        elif (not teacher_correct) and student_correct:
            outcome = DifferentialOutcome.TEACHER_WRONG_STUDENT_RIGHT
        elif teacher_correct and (not student_correct):
            outcome = DifferentialOutcome.TEACHER_RIGHT_STUDENT_WRONG
        else:
            outcome = DifferentialOutcome.BOTH_WRONG
        teacher_error = outcome in {
            DifferentialOutcome.TEACHER_WRONG_STUDENT_RIGHT,
            DifferentialOutcome.BOTH_WRONG,
        }
        status = (
            TeacherVerificationStatus.ERROR_DETECTED
            if teacher_error
            else TeacherVerificationStatus.UNTRUSTED
        )
        if independent_verifier_refs and not teacher_error:
            status = TeacherVerificationStatus.INDEPENDENTLY_VERIFIED
        if disagreement:
            status = TeacherVerificationStatus.CONTRADICTED
        return TeacherStudentDifferential(
            differential_id=new_id("diff"),
            task_id=task_id if task_id.startswith("task://") else f"task://{task_id}",
            teacher_result_ref=teacher_result_ref,
            student_result_ref=student_result_ref,
            outcome=outcome,
            decision_summary=f"Differential outcome {outcome.value}",
            evidence_basis=tuple(evidence_refs),
            actions_taken=("compare_teacher_student_results",),
            correction_summary="Educational evidence only; not automatic truth.",
            uncertainty=0.2 if disagreement else 0.1,
            teacher_verification_status=status,
            evidence_strength=0.4 if not independent_verifier_refs else 0.8,
            contradiction_state="CONTRADICTED" if disagreement or teacher_error else "NONE",
            teacher_error_detected=teacher_error,
            educational_only=True,
            independent_verifier_refs=tuple(independent_verifier_refs),
        )

    def create_learning_debt(
        self,
        task_id: str,
        capability: str,
        knowledge_gap: str,
        teacher: str,
        teacher_artifacts: list[str] | tuple[str, ...] = (),
    ) -> dict[str, Any]:
        validate_refs(teacher_artifacts)
        debt_id = new_id("debt")
        payload = {
            "debt_id": debt_id,
            "task_id": task_id if task_id.startswith("task://") else f"task://{task_id}",
            "capability": capability,
            "knowledge_gap": knowledge_gap,
            "teacher": teacher,
            "teacher_artifacts": list(teacher_artifacts),
            "state": DebtState.OPEN.value,
            "required_practice": True,
            "required_replay": True,
            "required_transfer": True,
            "created_at": utc_now(),
        }
        with self.store.transaction():
            self._put(
                "debts",
                debt_id,
                {
                    "debt_id": debt_id,
                    "task_id": payload["task_id"],
                    "capability": capability,
                    "state": DebtState.OPEN.value,
                    "created_at": payload["created_at"],
                    "updated_at": payload["created_at"],
                },
                payload,
            )
            self.store.append_event(EventType.DEBT_CREATED, debt_id, {"capability": capability})
        return payload

    def transition_debt(self, debt_id: str, nxt: DebtState) -> dict[str, Any]:
        current = self._get("debts", debt_id)
        if not current:
            raise FailClosed("DEBT_NOT_FOUND")
        cur = DebtState(current["state"])
        assert_debt_transition(cur, nxt)
        current["state"] = nxt.value
        current["updated_at"] = utc_now()
        with self.store.transaction():
            self._put(
                "debts",
                debt_id,
                {
                    "debt_id": debt_id,
                    "task_id": current["task_id"],
                    "capability": current["capability"],
                    "state": nxt.value,
                    "created_at": current["created_at"],
                    "updated_at": current["updated_at"],
                },
                current,
            )
            self.store.append_event(
                EventType.DEBT_STATE_CHANGED,
                debt_id,
                {"from": cur.value, "to": nxt.value},
            )
        return current

    def plan_learning_debt_payment(self, debt_id: str) -> dict[str, Any]:
        debt = self._get("debts", debt_id)
        if not debt:
            raise FailClosed("DEBT_NOT_FOUND")
        return {
            "debt_id": debt_id,
            "plan": [
                "complete_required_practice",
                "pass_replay",
                "pass_transfer_test",
                "submit_evidence_refs",
                "accept_competency_validation",
            ],
            "reading_or_observing_insufficient": True,
        }

    def validate_learning_debt_payment(self, debt_id: str, evidence: DebtPaymentEvidence) -> dict[str, Any]:
        debt = self._get("debts", debt_id)
        if not debt:
            raise FailClosed("DEBT_NOT_FOUND")
        validate_refs(evidence.evidence_refs)
        if evidence.reading_only or evidence.observing_only:
            raise FailClosed("DEBT_READING_ONLY_PAYMENT_REJECTED")
        if not evidence.evidence_refs:
            raise FailClosed("DEBT_PAYMENT_EVIDENCE_MISSING")
        if not evidence.required_practice_completed:
            raise FailClosed("DEBT_PRACTICE_INCOMPLETE")
        if not evidence.replay_passed:
            raise FailClosed("DEBT_REPLAY_FAILURE_REJECTED")
        if not evidence.transfer_test_passed:
            raise FailClosed("DEBT_TRANSFER_FAILURE_REJECTED")
        if not evidence.competency_validation_accepted:
            raise FailClosed("DEBT_COMPETENCY_VALIDATION_MISSING")
        if DebtState(debt["state"]) != DebtState.VALIDATION_PENDING:
            # walk legal path if still OPEN for tests that set up evidence after full path
            if DebtState(debt["state"]) != DebtState.VALIDATION_PENDING:
                raise FailClosed("DEBT_NOT_READY_FOR_PAYMENT")
        return self.transition_debt(debt_id, DebtState.PAID)

    def propose_competency_update(
        self,
        capability_id: str,
        proposed_score: float,
        evidence: CompetencyEvidence,
    ) -> dict[str, Any]:
        clamp_unit(proposed_score, "COMPETENCY_SCORE")
        validate_refs(evidence.evidence_refs)
        if (
            evidence.teacher_answer_only
            or evidence.student_read_only
            or evidence.synthetic_repetition_only
            or evidence.llm_claims_learning
            or not (evidence.practice and evidence.replay and evidence.verification and evidence.transfer_tests)
            or not evidence.evidence_refs
        ):
            proposal = {
                "proposal_id": new_id("cprop"),
                "capability_id": capability_id,
                "status": "REJECTED",
                "reason": "COMPETENCY_WITHOUT_EVIDENCE_REJECTED",
                "created_at": utc_now(),
            }
            with self.store.transaction():
                self._put(
                    "competency_proposals",
                    proposal["proposal_id"],
                    {
                        "proposal_id": proposal["proposal_id"],
                        "capability_id": capability_id,
                        "status": "REJECTED",
                        "created_at": proposal["created_at"],
                    },
                    proposal,
                )
                self.store.append_event(EventType.COMPETENCY_UPDATE_REJECTED, proposal["proposal_id"], proposal)
            raise FailClosed("COMPETENCY_WITHOUT_EVIDENCE_REJECTED")
        proposal = {
            "proposal_id": new_id("cprop"),
            "capability_id": capability_id,
            "proposed_score": proposed_score,
            "status": "PROPOSED",
            "evidence_refs": list(evidence.evidence_refs),
            "created_at": utc_now(),
        }
        with self.store.transaction():
            self._put(
                "competency_proposals",
                proposal["proposal_id"],
                {
                    "proposal_id": proposal["proposal_id"],
                    "capability_id": capability_id,
                    "status": "PROPOSED",
                    "created_at": proposal["created_at"],
                },
                proposal,
            )
            self.store.append_event(EventType.COMPETENCY_UPDATE_PROPOSED, proposal["proposal_id"], proposal)
        return proposal

    def validate_competency_update(self, proposal_id: str, accept: bool) -> dict[str, Any]:
        proposal = self._get("competency_proposals", proposal_id)
        if not proposal:
            raise FailClosed("PROPOSAL_NOT_FOUND")
        if proposal["status"] != "PROPOSED":
            raise FailClosed("PROPOSAL_NOT_PENDING")
        if not accept:
            proposal["status"] = "REJECTED"
            with self.store.transaction():
                self._put(
                    "competency_proposals",
                    proposal_id,
                    {
                        "proposal_id": proposal_id,
                        "capability_id": proposal["capability_id"],
                        "status": "REJECTED",
                        "created_at": proposal["created_at"],
                    },
                    proposal,
                )
                self.store.append_event(EventType.COMPETENCY_UPDATE_REJECTED, proposal_id, proposal)
            return proposal
        now = utc_now()
        node = self._get("competency_nodes", proposal["capability_id"]) or {
            "capability_id": proposal["capability_id"],
            "score": 0.0,
            "confidence": 0.0,
        }
        node["score"] = proposal["proposed_score"]
        node["confidence"] = 0.8
        node["updated_at"] = now
        proposal["status"] = "ACCEPTED"
        with self.store.transaction():
            self._put(
                "competency_nodes",
                proposal["capability_id"],
                {
                    "capability_id": proposal["capability_id"],
                    "score": node["score"],
                    "confidence": node["confidence"],
                    "updated_at": now,
                },
                node,
            )
            self._put(
                "competency_proposals",
                proposal_id,
                {
                    "proposal_id": proposal_id,
                    "capability_id": proposal["capability_id"],
                    "status": "ACCEPTED",
                    "created_at": proposal["created_at"],
                },
                proposal,
            )
            self.store.append_event(EventType.COMPETENCY_UPDATE_ACCEPTED, proposal_id, proposal)
        return proposal

    def ingest_knowledge_candidate(
        self,
        claim: str,
        origin_class: OriginClass,
        evidence_refs: list[str] | tuple[str, ...],
        observed_at: str,
        temporal_class: str,
        valid_from: str,
        valid_until: str | None,
        revalidation_policy: str,
        revalidation_due_at: str | None = None,
    ) -> dict[str, Any]:
        validate_refs(evidence_refs)
        knowledge_id = new_id("know")
        payload = {
            "knowledge_id": knowledge_id,
            "claim": claim,
            "origin_class": origin_class.value,
            "maturity": KnowledgeMaturity.SEEN.value,
            "epistemic_state": EpistemicState.UNVERIFIED.value,
            "evidence_refs": list(evidence_refs),
            "temporal_class": temporal_class,
            "observed_at": observed_at,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "freshness": "FRESH",
            "revalidation_due_at": revalidation_due_at,
            "revalidation_policy": revalidation_policy,
            "created_at": utc_now(),
        }
        with self.store.transaction():
            self._put(
                "knowledge_objects",
                knowledge_id,
                {
                    "knowledge_id": knowledge_id,
                    "origin_class": origin_class.value,
                    "maturity": KnowledgeMaturity.SEEN.value,
                    "epistemic_state": EpistemicState.UNVERIFIED.value,
                    "created_at": payload["created_at"],
                    "updated_at": payload["created_at"],
                },
                payload,
            )
            self.store.append_event(EventType.KNOWLEDGE_CREATED, knowledge_id, payload)
        return payload

    def transition_knowledge_maturity(self, knowledge_id: str, nxt: KnowledgeMaturity) -> dict[str, Any]:
        obj = self._get("knowledge_objects", knowledge_id)
        if not obj:
            raise FailClosed("KNOWLEDGE_NOT_FOUND")
        current = KnowledgeMaturity(obj["maturity"])
        assert_maturity_transition(current, nxt)
        obj["maturity"] = nxt.value
        obj["updated_at"] = utc_now()
        with self.store.transaction():
            self._put(
                "knowledge_objects",
                knowledge_id,
                {
                    "knowledge_id": knowledge_id,
                    "origin_class": obj["origin_class"],
                    "maturity": nxt.value,
                    "epistemic_state": obj["epistemic_state"],
                    "created_at": obj["created_at"],
                    "updated_at": obj["updated_at"],
                },
                obj,
            )
            self.store.append_event(
                EventType.KNOWLEDGE_MATURITY_CHANGED,
                knowledge_id,
                {"from": current.value, "to": nxt.value},
            )
        return obj

    def require_revalidation_if_stale(self, knowledge_id: str, now_iso: str) -> dict[str, Any]:
        obj = self._get("knowledge_objects", knowledge_id)
        if not obj:
            raise FailClosed("KNOWLEDGE_NOT_FOUND")
        due = obj.get("revalidation_due_at") or obj.get("valid_until")
        if due and now_iso >= due:
            obj["freshness"] = "STALE"
            obj["epistemic_state"] = EpistemicState.EVIDENCE_BOUNDED.value
            obj["updated_at"] = utc_now()
            with self.store.transaction():
                self._put(
                    "knowledge_objects",
                    knowledge_id,
                    {
                        "knowledge_id": knowledge_id,
                        "origin_class": obj["origin_class"],
                        "maturity": obj["maturity"],
                        "epistemic_state": obj["epistemic_state"],
                        "created_at": obj["created_at"],
                        "updated_at": obj["updated_at"],
                    },
                    obj,
                )
            raise FailClosed("STALE_KNOWLEDGE_REVALIDATION_REQUIRED")
        return obj

    def set_epistemic_state(self, knowledge_id: str, nxt: EpistemicState) -> dict[str, Any]:
        obj = self._get("knowledge_objects", knowledge_id)
        if not obj:
            raise FailClosed("KNOWLEDGE_NOT_FOUND")
        assert_not_synthetic_truth_escalation(obj["origin_class"], EpistemicState(obj["epistemic_state"]), nxt)
        obj["epistemic_state"] = nxt.value
        obj["updated_at"] = utc_now()
        with self.store.transaction():
            self._put(
                "knowledge_objects",
                knowledge_id,
                {
                    "knowledge_id": knowledge_id,
                    "origin_class": obj["origin_class"],
                    "maturity": obj["maturity"],
                    "epistemic_state": nxt.value,
                    "created_at": obj["created_at"],
                    "updated_at": obj["updated_at"],
                },
                obj,
            )
        return obj

    def harvest_historical_learning(
        self,
        source_ref: str,
        items: list[tuple[HarvestKind, str]],
    ) -> list[dict[str, Any]]:
        validate_exchange_ref(source_ref)
        if len(items) >= 3 and len({kind.value for kind, _ in items}) < 3:
            raise FailClosed("RETROSPECTIVE_FACT_INFERENCE_COLLAPSED")
        created = []
        with self.store.transaction():
            for kind, text in items:
                harvest_id = new_id("harvest")
                payload = {
                    "harvest_id": harvest_id,
                    "kind": kind.value,
                    "text": text,
                    "source_ref": source_ref,
                    "created_at": utc_now(),
                }
                self._put(
                    "harvest_items",
                    harvest_id,
                    {
                        "harvest_id": harvest_id,
                        "kind": kind.value,
                        "created_at": payload["created_at"],
                    },
                    payload,
                )
                created.append(payload)
        return created

    def plan_curriculum(self, capability: str, elv: ExpectedLearningValue) -> dict[str, Any]:
        return {
            "capability": capability,
            "expected_learning_value": elv.score(),
            "why_now": "Prioritized by expected learning value, not vendor preference.",
            "components": {
                "recurrence_probability": elv.recurrence_probability,
                "strategic_value": elv.strategic_value,
                "novelty": elv.novelty,
                "generalizability": elv.generalizability,
                "uncertainty": elv.uncertainty,
                "expected_competency_gain": elv.expected_competency_gain,
                "learning_cost": elv.learning_cost,
                "teacher_cost": elv.teacher_cost,
            },
        }

    def calculate_learning_yield(self, work_completed: bool, internal_capability_acquired: bool) -> dict[str, Any]:
        if work_completed and not internal_capability_acquired:
            complete = False
            debt_required = True
        else:
            complete = work_completed and internal_capability_acquired
            debt_required = not internal_capability_acquired
        return {
            "execution_yield": 1.0 if work_completed else 0.0,
            "learning_yield": 1.0 if internal_capability_acquired else 0.0,
            "cognitive_cycle_complete": complete,
            "learning_debt_required": debt_required,
        }

    def select_student_participation_mode(
        self,
        competency: float,
        confidence: float,
        task_difficulty: float,
        risk: float,
        teacher_available: bool,
        expected_learning_value: float,
    ) -> ParticipationMode:
        clamp_unit(competency, "COMPETENCY")
        clamp_unit(confidence, "CONFIDENCE")
        clamp_unit(task_difficulty, "DIFFICULTY")
        clamp_unit(risk, "RISK")
        clamp_unit(expected_learning_value, "ELV")
        if risk >= 0.8 or (not teacher_available and competency < 0.4):
            return ParticipationMode.OBSERVE
        if competency < 0.2:
            return ParticipationMode.PREDICT
        if competency < 0.4:
            return ParticipationMode.ASSISTED_SOLVE
        if competency < 0.55:
            return ParticipationMode.CO_SOLVE
        if competency < 0.7:
            return ParticipationMode.STUDENT_FIRST
        if competency < 0.85 or task_difficulty >= 0.7:
            return ParticipationMode.STUDENT_EXECUTE_TEACHER_VERIFY
        return ParticipationMode.INDEPENDENT

    def record_teacher_task(
        self,
        capability_id: str,
        context_id: str,
        transfer_success: bool,
        verification_failed: bool,
        evidence_refs: list[str] | tuple[str, ...],
    ) -> dict[str, Any]:
        validate_refs(evidence_refs)
        node = self._get("teacher_dependencies", capability_id) or {
            "capability_id": capability_id,
            "state": TeacherDependencyState.TEACHER_SOLVES.value,
            "task_count": 0,
            "distinct_contexts": [],
            "transfer_successes": 0,
            "verification_failures": 0,
            "evidence_count": 0,
        }
        node["task_count"] += 1
        contexts = set(node.get("distinct_contexts") or [])
        contexts.add(context_id)
        node["distinct_contexts"] = sorted(contexts)
        if transfer_success:
            node["transfer_successes"] += 1
        if verification_failed:
            node["verification_failures"] += 1
        node["evidence_count"] += len(evidence_refs)
        node["updated_at"] = utc_now()
        with self.store.transaction():
            self._put(
                "teacher_dependencies",
                capability_id,
                {
                    "capability_id": capability_id,
                    "state": node["state"],
                    "task_count": node["task_count"],
                    "distinct_contexts": len(node["distinct_contexts"]),
                    "transfer_successes": node["transfer_successes"],
                    "verification_failures": node["verification_failures"],
                    "evidence_count": node["evidence_count"],
                    "updated_at": node["updated_at"],
                },
                node,
            )
            self.store.append_event(EventType.TEACHER_DEPENDENCY_CHANGED, capability_id, node)
        return node

    def try_retire_teacher(self, capability_id: str) -> dict[str, Any]:
        node = self._get("teacher_dependencies", capability_id)
        if not node:
            raise FailClosed("TEACHER_DEPENDENCY_NOT_FOUND")
        current = TeacherDependencyState(node["state"])
        if node["task_count"] < 5 or node["evidence_count"] < 5:
            raise FailClosed("TEACHER_EARLY_RETIREMENT_REJECTED")
        if len(node.get("distinct_contexts") or []) < 3 or node["transfer_successes"] < 3:
            raise FailClosed("MULTI_CONTEXT_TRANSFER_REQUIRED")
        fail_rate = node["verification_failures"] / max(node["task_count"], 1)
        if fail_rate > 0.2:
            raise FailClosed("TEACHER_RETIREMENT_VERIFICATION_RATE_UNSAFE")
        if node["evidence_count"] < 5:
            raise FailClosed("TEACHER_RETIREMENT_EVIDENCE_INSUFFICIENT")
        # walk remaining legal path only if already at audit
        if current != TeacherDependencyState.TEACHER_AUDIT_ONLY:
            raise FailClosed("TEACHER_EARLY_RETIREMENT_REJECTED")
        assert_teacher_dep_transition(current, TeacherDependencyState.RETIRED)
        node["state"] = TeacherDependencyState.RETIRED.value
        node["updated_at"] = utc_now()
        with self.store.transaction():
            self._put(
                "teacher_dependencies",
                capability_id,
                {
                    "capability_id": capability_id,
                    "state": node["state"],
                    "task_count": node["task_count"],
                    "distinct_contexts": len(node["distinct_contexts"]),
                    "transfer_successes": node["transfer_successes"],
                    "verification_failures": node["verification_failures"],
                    "evidence_count": node["evidence_count"],
                    "updated_at": node["updated_at"],
                },
                node,
            )
            self.store.append_event(EventType.TEACHER_DEPENDENCY_CHANGED, capability_id, node)
        return node

    def advance_teacher_dependency(self, capability_id: str, nxt: TeacherDependencyState) -> dict[str, Any]:
        node = self._get("teacher_dependencies", capability_id)
        if not node:
            raise FailClosed("TEACHER_DEPENDENCY_NOT_FOUND")
        current = TeacherDependencyState(node["state"])
        assert_teacher_dep_transition(current, nxt)
        node["state"] = nxt.value
        node["updated_at"] = utc_now()
        with self.store.transaction():
            self._put(
                "teacher_dependencies",
                capability_id,
                {
                    "capability_id": capability_id,
                    "state": nxt.value,
                    "task_count": node["task_count"],
                    "distinct_contexts": len(node.get("distinct_contexts") or []),
                    "transfer_successes": node["transfer_successes"],
                    "verification_failures": node["verification_failures"],
                    "evidence_count": node["evidence_count"],
                    "updated_at": node["updated_at"],
                },
                node,
            )
            self.store.append_event(EventType.TEACHER_DEPENDENCY_CHANGED, capability_id, node)
        return node

    def compress(
        self,
        layer: CompressionLayer,
        summary: str,
        source_refs: list[str] | tuple[str, ...],
    ) -> dict[str, Any]:
        validate_refs(source_refs)
        if not source_refs:
            raise FailClosed("COMPRESSION_WITHOUT_PROVENANCE")
        node_id = new_id("cmp")
        payload = {
            "node_id": node_id,
            "layer": layer.value,
            "decision_summary": summary,
            "source_refs": list(source_refs),
            "created_at": utc_now(),
        }
        with self.store.transaction():
            self._put(
                "compression_nodes",
                node_id,
                {
                    "node_id": node_id,
                    "layer": layer.value,
                    "created_at": payload["created_at"],
                },
                payload,
            )
        return payload

    def create_training_candidate(self, kind: TrainingKind, material_ref: str, validated: bool) -> dict[str, Any]:
        validate_exchange_ref(material_ref)
        candidate_id = new_id("train")
        state = TrainingState.VALIDATED if validated else TrainingState.DRAFT
        payload = {
            "candidate_id": candidate_id,
            "kind": kind.value,
            "state": state.value,
            "material_ref": material_ref,
            "created_at": utc_now(),
        }
        with self.store.transaction():
            self._put(
                "training_candidates",
                candidate_id,
                {
                    "candidate_id": candidate_id,
                    "kind": kind.value,
                    "state": state.value,
                    "created_at": payload["created_at"],
                },
                payload,
            )
            self.store.append_event(EventType.TRAINING_CANDIDATE_CREATED, candidate_id, payload)
        return payload

    def promote_training_candidate(self, candidate_id: str) -> dict[str, Any]:
        obj = self._get("training_candidates", candidate_id)
        if not obj:
            raise FailClosed("TRAINING_CANDIDATE_NOT_FOUND")
        current = TrainingState(obj["state"])
        assert_training_transition(current, TrainingState.PROMOTED)
        obj["state"] = TrainingState.PROMOTED.value
        with self.store.transaction():
            self._put(
                "training_candidates",
                candidate_id,
                {
                    "candidate_id": candidate_id,
                    "kind": obj["kind"],
                    "state": obj["state"],
                    "created_at": obj["created_at"],
                },
                obj,
            )
        return obj


def asdict_trace(trace: LearningTrace) -> dict[str, Any]:
    data = dict(trace.__dict__)
    for key, value in list(data.items()):
        if isinstance(value, tuple):
            data[key] = list(value)
        elif hasattr(value, "value"):
            data[key] = value.value
    return data


def dict_to_trace(stored: dict[str, Any]) -> LearningTrace:
    converted = {}
    for key, value in stored.items():
        converted[key] = tuple(value) if isinstance(value, list) else value
    return LearningTrace(**converted)


# Public functional API wrappers expected by the order.

def create_learning_trace(fabric: LearningFabric, **kwargs: Any) -> LearningTrace:
    return fabric.create_learning_trace(**kwargs)


def analyze_teacher_student_difference(fabric: LearningFabric, **kwargs: Any) -> TeacherStudentDifferential:
    return fabric.analyze_teacher_student_difference(**kwargs)


def create_learning_debt(fabric: LearningFabric, **kwargs: Any) -> dict[str, Any]:
    return fabric.create_learning_debt(**kwargs)


def plan_learning_debt_payment(fabric: LearningFabric, debt_id: str) -> dict[str, Any]:
    return fabric.plan_learning_debt_payment(debt_id)


def validate_learning_debt_payment(
    fabric: LearningFabric, debt_id: str, evidence: DebtPaymentEvidence
) -> dict[str, Any]:
    return fabric.validate_learning_debt_payment(debt_id, evidence)


def propose_competency_update(
    fabric: LearningFabric, capability_id: str, proposed_score: float, evidence: CompetencyEvidence
) -> dict[str, Any]:
    return fabric.propose_competency_update(capability_id, proposed_score, evidence)


def validate_competency_update(fabric: LearningFabric, proposal_id: str, accept: bool) -> dict[str, Any]:
    return fabric.validate_competency_update(proposal_id, accept)


def ingest_knowledge_candidate(fabric: LearningFabric, **kwargs: Any) -> dict[str, Any]:
    return fabric.ingest_knowledge_candidate(**kwargs)


def transition_knowledge_maturity(
    fabric: LearningFabric, knowledge_id: str, nxt: KnowledgeMaturity
) -> dict[str, Any]:
    return fabric.transition_knowledge_maturity(knowledge_id, nxt)


def harvest_historical_learning(
    fabric: LearningFabric, source_ref: str, items: list[tuple[HarvestKind, str]]
) -> list[dict[str, Any]]:
    return fabric.harvest_historical_learning(source_ref, items)


def plan_curriculum(fabric: LearningFabric, capability: str, elv: ExpectedLearningValue) -> dict[str, Any]:
    return fabric.plan_curriculum(capability, elv)


def calculate_learning_yield(
    fabric: LearningFabric, work_completed: bool, internal_capability_acquired: bool
) -> dict[str, Any]:
    return fabric.calculate_learning_yield(work_completed, internal_capability_acquired)


def select_student_participation_mode(fabric: LearningFabric, **kwargs: Any) -> ParticipationMode:
    return fabric.select_student_participation_mode(**kwargs)
