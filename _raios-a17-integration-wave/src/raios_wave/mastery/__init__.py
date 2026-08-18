"""A17.7 Mastery / transfer / competency engine.

Mastery is multi-dimensional. A single scalar is never sufficient for
retirement or canonical promotion.
"""
from __future__ import annotations

import json
from typing import Any

from ..identity import canonical_json, utc_now
from ..models import DEFAULT_MASTERY_THRESHOLDS, CompetencyRecord, EventType


class MasteryEngine:
    def __init__(self, store: Any, thresholds: dict[str, Any] | None = None) -> None:
        self.store = store
        self.thresholds = dict(DEFAULT_MASTERY_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    def get(self, capability_id: str) -> CompetencyRecord:
        row = self.store.conn.execute(
            "SELECT payload_json FROM competency WHERE capability_id = ?",
            (capability_id,),
        ).fetchone()
        if not row:
            return CompetencyRecord(capability_id=capability_id).clamped()
        data = json.loads(row["payload_json"])
        return CompetencyRecord(**{k: v for k, v in data.items() if k in CompetencyRecord.__dataclass_fields__}).clamped()

    def record_evaluation(self, capability_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
        current = self.get(capability_id)
        for field in (
            "knowledge_score",
            "execution_score",
            "transfer_score",
            "reliability_score",
            "independence_score",
            "retention_score",
            "teacher_intervention_rate",
            "verifier_failure_rate",
        ):
            if field in metrics:
                setattr(current, field, float(metrics[field]))
        if "repeated_validations" in metrics:
            current.repeated_validations = int(metrics["repeated_validations"])
        if "distinct_transfer_domains" in metrics:
            current.distinct_transfer_domains = int(metrics["distinct_transfer_domains"])
        if metrics.get("evidence_ref"):
            current.evidence_refs.append(str(metrics["evidence_ref"]))
        if metrics.get("failure_ref"):
            current.failure_refs.append(str(metrics["failure_ref"]))
        if metrics.get("skill_ref"):
            current.skill_refs.append(str(metrics["skill_ref"]))
        if metrics.get("learning_debt_ref"):
            current.learning_debt_refs.append(str(metrics["learning_debt_ref"]))
        current.last_validation = str(metrics.get("last_validation") or utc_now())
        current.regression_gate = str(metrics.get("regression_gate") or current.regression_gate)
        current.retention_gate = str(metrics.get("retention_gate") or current.retention_gate)
        current.updated_at = utc_now()
        current.clamped()
        payload = current.as_dict()
        with self.store.transaction():
            self.store.conn.execute(
                """
                INSERT INTO competency(
                    capability_id, knowledge_score, execution_score, transfer_score,
                    reliability_score, independence_score, retention_score,
                    teacher_intervention_rate, verifier_failure_rate,
                    repeated_validations, distinct_transfer_domains,
                    regression_gate, retention_gate, payload_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(capability_id) DO UPDATE SET
                    knowledge_score=excluded.knowledge_score,
                    execution_score=excluded.execution_score,
                    transfer_score=excluded.transfer_score,
                    reliability_score=excluded.reliability_score,
                    independence_score=excluded.independence_score,
                    retention_score=excluded.retention_score,
                    teacher_intervention_rate=excluded.teacher_intervention_rate,
                    verifier_failure_rate=excluded.verifier_failure_rate,
                    repeated_validations=excluded.repeated_validations,
                    distinct_transfer_domains=excluded.distinct_transfer_domains,
                    regression_gate=excluded.regression_gate,
                    retention_gate=excluded.retention_gate,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    current.capability_id,
                    current.knowledge_score,
                    current.execution_score,
                    current.transfer_score,
                    current.reliability_score,
                    current.independence_score,
                    current.retention_score,
                    current.teacher_intervention_rate,
                    current.verifier_failure_rate,
                    current.repeated_validations,
                    current.distinct_transfer_domains,
                    current.regression_gate,
                    current.retention_gate,
                    canonical_json(payload),
                    current.updated_at,
                ),
            )
            self.store.append_event(EventType.COMPETENCY_UPDATED, capability_id, {"last_validation": current.last_validation})
        return self.evaluate(capability_id)

    def evaluate(self, capability_id: str) -> dict[str, Any]:
        rec = self.get(capability_id)
        gates = {
            "unseen_transfer": rec.transfer_score >= float(self.thresholds["unseen_transfer"]),
            "independent_success": rec.independence_score >= float(self.thresholds["independent_success"]),
            "teacher_intervention": rec.teacher_intervention_rate <= float(self.thresholds["teacher_intervention"]),
            "verifier_failure": rec.verifier_failure_rate <= float(self.thresholds["verifier_failure"]),
            "distinct_transfer_domains": rec.distinct_transfer_domains >= int(self.thresholds["distinct_transfer_domains"]),
            "repeated_validations": rec.repeated_validations >= int(self.thresholds["repeated_validations"]),
            "regression_gate": rec.regression_gate == "PASS",
            "retention_gate": rec.retention_gate == "PASS",
        }
        scalar = (
            rec.knowledge_score
            + rec.execution_score
            + rec.transfer_score
            + rec.reliability_score
            + rec.independence_score
            + rec.retention_score
        ) / 6.0
        return {
            "capability_id": capability_id,
            "dimensions": rec.as_dict(),
            "gates": gates,
            "mastery_scalar_insufficient": True,
            "scalar_mean": scalar,
            "empirical_mastery": all(gates.values()),
            "thresholds": dict(self.thresholds),
            "canonical": False,
        }

    def competency_status(self, capability_id: str) -> dict[str, Any]:
        evaluation = self.evaluate(capability_id)
        rec = self.get(capability_id)
        return {
            **evaluation,
            "teacher_dependency": rec.teacher_intervention_rate > float(self.thresholds["teacher_intervention"]),
            "gaps": [name for name, ok in evaluation["gates"].items() if not ok],
        }

    def teacher_dependency(self, capability_id: str) -> dict[str, Any]:
        rec = self.get(capability_id)
        dependent = rec.teacher_intervention_rate > float(self.thresholds["teacher_intervention"])
        return {
            "capability_id": capability_id,
            "teacher_intervention_rate": rec.teacher_intervention_rate,
            "independence_score": rec.independence_score,
            "dependent": dependent,
            "state": "TEACHER_DEPENDENT" if dependent else "STUDENT_INDEPENDENT",
        }

    def capability_gap(self, capability_id: str) -> dict[str, Any]:
        status = self.competency_status(capability_id)
        return {
            "capability_id": capability_id,
            "gaps": status["gaps"],
            "recommended_action": "KEEP_TEACHER" if status["gaps"] else "EVALUATE_RETIREMENT",
            "canonical": False,
        }
