"""A17.16 empirical mastery engine with 10 dimensions."""
from __future__ import annotations

import json
from typing import Any

from ..identity import clamp_unit, canonical_json, utc_now
from ..models import DEFAULT_MASTERY_THRESHOLDS, MASTERY_DIMENSIONS, MasteryRecord


class MasteryEngine:
    def __init__(self, store: Any, thresholds: dict[str, Any] | None = None) -> None:
        self.store = store
        self.thresholds = dict(DEFAULT_MASTERY_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    def record(self, capability_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
        current = self.get(capability_id)
        for dim in MASTERY_DIMENSIONS:
            if dim in metrics:
                setattr(current, dim, clamp_unit(float(metrics[dim]), dim.upper()))
        for rate in ("teacher_intervention_rate", "verifier_failure_rate"):
            if rate in metrics:
                setattr(current, rate, clamp_unit(float(metrics[rate]), rate.upper()))
        for key in ("repeated_validations", "distinct_transfer_domains"):
            if key in metrics:
                setattr(current, key, int(metrics[key]))
        for gate in ("retention_gate", "regression_gate", "independent_verification"):
            if gate in metrics:
                setattr(current, gate, str(metrics[gate]))
        if metrics.get("evidence_ref"):
            current.evidence_refs.append(str(metrics["evidence_ref"]))
        current.updated_at = utc_now()
        payload = current.as_dict()
        self.store.conn.execute(
            """
            INSERT INTO competency(capability_id, payload_json, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(capability_id) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
            """,
            (capability_id, canonical_json(payload), current.updated_at),
        )
        self.store.append_event("COMPETENCY_UPDATED", capability_id, {"updated_at": current.updated_at})
        return self.evaluate(capability_id)

    def get(self, capability_id: str) -> MasteryRecord:
        row = self.store.conn.execute(
            "SELECT payload_json FROM competency WHERE capability_id = ?", (capability_id,)
        ).fetchone()
        if not row:
            return MasteryRecord(capability_id=capability_id)
        data = json.loads(row["payload_json"])
        fields = set(MasteryRecord.__dataclass_fields__)
        return MasteryRecord(**{k: v for k, v in data.items() if k in fields})

    def evaluate(self, capability_id: str) -> dict[str, Any]:
        rec = self.get(capability_id)
        gates = {
            "unseen_transfer": rec.transfer >= float(self.thresholds["unseen_transfer"]),
            "independent_success": rec.independence >= float(self.thresholds["independent_success"]),
            "teacher_intervention": rec.teacher_intervention_rate <= float(self.thresholds["teacher_intervention"]),
            "verifier_failure": rec.verifier_failure_rate <= float(self.thresholds["verifier_failure"]),
            "distinct_transfer_domains": rec.distinct_transfer_domains >= int(self.thresholds["distinct_transfer_domains"]),
            "repeated_validations": rec.repeated_validations >= int(self.thresholds["repeated_validations"]),
            "retention": rec.retention_gate == "PASS",
            "regression": rec.regression_gate == "PASS",
            "independent_verification": rec.independent_verification == "PASS",
        }
        return {
            "capability_id": capability_id,
            "dimensions": rec.as_dict(),
            "gates": gates,
            "empirical_mastery": all(gates.values()),
            "mastery_scalar_insufficient": True,
            "thresholds": dict(self.thresholds),
            "canonical": False,
        }

    def status(self, capability_id: str) -> dict[str, Any]:
        evaluation = self.evaluate(capability_id)
        return {**evaluation, "gaps": [k for k, ok in evaluation["gates"].items() if not ok]}

    def teacher_dependency(self, capability_id: str) -> dict[str, Any]:
        rec = self.get(capability_id)
        dependent = rec.teacher_intervention_rate > float(self.thresholds["teacher_intervention"])
        return {
            "capability_id": capability_id,
            "dependent": dependent,
            "teacher_intervention_rate": rec.teacher_intervention_rate,
            "state": "TEACHER_DEPENDENT" if dependent else "STUDENT_INDEPENDENT",
        }

    def capability_gap(self, capability_id: str) -> dict[str, Any]:
        status = self.status(capability_id)
        return {"capability_id": capability_id, "gaps": status["gaps"], "canonical": False}

    def retention_status(self, capability_id: str) -> dict[str, Any]:
        rec = self.get(capability_id)
        return {"capability_id": capability_id, "retention_gate": rec.retention_gate, "retention": rec.retention}

    def transfer_status(self, capability_id: str) -> dict[str, Any]:
        rec = self.get(capability_id)
        return {
            "capability_id": capability_id,
            "transfer": rec.transfer,
            "domains": rec.distinct_transfer_domains,
            "pass": rec.transfer >= float(self.thresholds["unseen_transfer"]),
        }
