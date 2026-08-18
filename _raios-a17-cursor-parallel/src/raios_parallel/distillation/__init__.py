"""A21 adapter / distillation factory contracts. Isolated test data only. No training."""
from __future__ import annotations

import json
from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import AdapterLifecycle, TrainingLifecycle
from ..transitions import assert_adapter, assert_training

GATES = ("data_provenance", "license", "quality", "dedupe", "contamination", "transfer_evidence", "regression", "rollback")
CANDIDATE_KINDS = (
    "teacher_corpus",
    "student_baselines",
    "teacher_corrections",
    "differentials",
    "validated_transfer",
    "preference_pairs",
    "failure_recovery",
    "architecture_decisions",
    "tool_use_trajectories",
    "SFT",
    "DPO",
)


class DistillationFactory:
    def __init__(self, store: Any, governance: Any) -> None:
        self.store = store
        self.governance = governance

    def create_candidate(self, record: dict[str, Any]) -> dict[str, Any]:
        required = (
            "teacher_corpus", "student_baselines", "teacher_corrections", "differentials",
            "validated_transfer", "kind",
        )
        missing = [k for k in required if k not in record]
        if missing:
            raise FailClosed("TRAINING_CANDIDATE_MISSING:" + ",".join(missing))
        if record.get("copy_teacher_blindly"):
            raise FailClosed("BLIND_TEACHER_COPY_REJECTED")
        if record["kind"] not in CANDIDATE_KINDS:
            raise FailClosed(f"UNKNOWN_TRAINING_KIND:{record['kind']}")
        if record.get("train_now") and not record.get("isolated_test_data"):
            raise FailClosed("TRAINING_NOT_AUTHORIZED")
        candidate_id = deterministic_id("train", str(record["kind"]), canonical_json(record.get("differentials")))
        payload = {
            **record,
            "candidate_id": candidate_id,
            "lifecycle": TrainingLifecycle.CANDIDATE.value,
            "gates": {g: bool(record.get("gates", {}).get(g)) for g in GATES},
            "cortex_target_family": "Qwen",
            "cortex_is_identity": False,
            "canonical": False,
        }
        self.store.conn.execute(
            "INSERT INTO training(candidate_id, lifecycle, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (candidate_id, payload["lifecycle"], canonical_json(payload), utc_now(), utc_now()),
        )
        return payload

    def validate(self, candidate_id: str) -> dict[str, Any]:
        payload = self._load("training", "candidate_id", candidate_id)
        if payload.get("validated_transfer") not in {True, "PASS", "pass"}:
            raise FailClosed("TRAINING_CANDIDATE_REQUIRES_VALIDATION")
        return self._train_transition(candidate_id, TrainingLifecycle.FILTERED)

    def _train_transition(self, candidate_id: str, nxt: TrainingLifecycle, promote: bool = False) -> dict[str, Any]:
        payload = self._load("training", "candidate_id", candidate_id)
        snapshot = payload["lifecycle"]
        try:
            assert_training(TrainingLifecycle(payload["lifecycle"]), nxt, promote=promote)
        except FailClosed:
            after = self._load("training", "candidate_id", candidate_id)
            if after["lifecycle"] != snapshot:
                raise FailClosed("REJECTED_TRANSITION_MUTATED_STATE")
            raise
        payload["lifecycle"] = nxt.value
        payload["updated_at"] = utc_now()
        self.store.conn.execute(
            "UPDATE training SET lifecycle = ?, payload_json = ?, updated_at = ? WHERE candidate_id = ?",
            (payload["lifecycle"], canonical_json(payload), payload["updated_at"], candidate_id),
        )
        return payload

    def promote_training(self, candidate_id: str) -> None:
        self.governance.reject("AUTO_PROMOTE_ADAPTER", {"candidate_id": candidate_id})

    def create_adapter(self, record: dict[str, Any]) -> dict[str, Any]:
        adapter_id = deterministic_id("adp", str(record.get("capability") or "cap"), str(record.get("version") or "0"))
        payload = {
            **record,
            "adapter_id": adapter_id,
            "lifecycle": AdapterLifecycle.TRAINED.value,
            "cortex_target": "qwen3.6:35b-a3b",
            "identity_bound": False,
            "canonical": False,
        }
        self.store.conn.execute(
            "INSERT INTO adapters(adapter_id, lifecycle, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (adapter_id, payload["lifecycle"], canonical_json(payload), utc_now(), utc_now()),
        )
        return payload

    def promote_adapter(self, adapter_id: str, *, governed: bool = False) -> dict[str, Any]:
        if not governed:
            self.governance.reject("AUTO_PROMOTE_ADAPTER", {"adapter_id": adapter_id})
        payload = self._load("adapters", "adapter_id", adapter_id)
        assert_adapter(AdapterLifecycle(payload["lifecycle"]), AdapterLifecycle.SHADOW, promote=False)
        payload["lifecycle"] = AdapterLifecycle.SHADOW.value
        self.store.conn.execute(
            "UPDATE adapters SET lifecycle = ?, payload_json = ?, updated_at = ? WHERE adapter_id = ?",
            (payload["lifecycle"], canonical_json(payload), utc_now(), adapter_id),
        )
        return payload

    def activate_adapter(self, adapter_id: str) -> None:
        self.governance.reject("AUTO_PROMOTE_ADAPTER", {"adapter_id": adapter_id})

    def _load(self, table: str, key: str, value: str) -> dict[str, Any]:
        row = self.store.conn.execute(f"SELECT payload_json FROM {table} WHERE {key} = ?", (value,)).fetchone()
        if not row:
            raise FailClosed(f"{table.upper()}_UNKNOWN")
        return json.loads(row["payload_json"])
