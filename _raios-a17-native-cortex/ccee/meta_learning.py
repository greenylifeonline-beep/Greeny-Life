"""Meta-learning produces policy candidates. It does not mutate production policy."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import FailClosed, deterministic_id, utc_now


class MetaLearning:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def record(self, mission: dict[str, Any]) -> dict[str, Any]:
        rec = {
            "meta_id": deterministic_id("meta", str(mission.get("mission_id") or mission)),
            "teaching_method": mission.get("teaching_method") or "unknown",
            "teacher": mission.get("teacher"),
            "examples": mission.get("examples") or [],
            "counterexamples": mission.get("counterexamples") or [],
            "practice_count": int(mission.get("practice_count") or 0),
            "time_to_transfer": float(mission.get("time_to_transfer") or 0),
            "retention": mission.get("retention"),
            "compute_cost": float(mission.get("compute_cost") or 0),
            "success": bool(mission.get("success")),
            "created_at": utc_now(),
        }
        self.records.append(rec)
        return rec

    def policy_candidates(self) -> list[dict[str, Any]]:
        by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for rec in self.records:
            by_method[str(rec["teaching_method"])].append(rec)
        out = []
        for method, rows in by_method.items():
            wins = sum(1 for r in rows if r["success"])
            out.append(
                {
                    "candidate_id": deterministic_id("pol", method),
                    "teaching_method": method,
                    "success_rate": wins / max(len(rows), 1),
                    "production_policy_modified": False,
                    "kind": "POLICY_CANDIDATE",
                }
            )
        return out

    def apply_to_production(self) -> None:
        raise FailClosed("META_LEARNING_CANNOT_MODIFY_PRODUCTION_POLICY")
