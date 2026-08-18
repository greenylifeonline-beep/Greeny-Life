"""Curiosity engine. Ranked learning opportunities. High-risk never auto-executes."""
from __future__ import annotations

from typing import Any

from .config import EPSILON, canonical_json, deterministic_id, utc_now
from .ledger import Ledger


class CuriosityEngine:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger
        self.rankings: list[dict[str, Any]] = []

    def ingest_signals(self, signals: dict[str, list[str]]) -> list[dict[str, Any]]:
        missions = []
        for kind, refs in signals.items():
            if not refs:
                continue
            missions.append(
                self.rank(
                    {
                        "kind": kind,
                        "refs": refs,
                        "expected_gain": min(1.0, 0.2 + 0.1 * len(refs)),
                        "reuse_probability": 0.6 if kind in {"failures", "skill_opportunities"} else 0.3,
                        "leverage": 0.8 if kind == "failures" else 0.4,
                        "uncertainty": 0.7 if kind == "uncertainty" else 0.4,
                        "failure_reduction": 0.9 if kind == "failures" else 0.2,
                        "teacher_dependency": 0.5 if kind == "teacher_superiority" else 0.2,
                        "compute_cost": 0.2,
                        "risk": 0.9 if kind == "teacher_superiority" else 0.2,
                    }
                )
            )
        self.rankings = sorted(missions, key=lambda m: m["score"], reverse=True)
        for item in self.rankings:
            self.ledger.put("missions", "mission_id", item["mission_id"], item, extra={"state": item["state"], "score": item["score"]})
        return self.rankings

    def rank(self, opp: dict[str, Any]) -> dict[str, Any]:
        score = (
            float(opp["expected_gain"])
            * float(opp["reuse_probability"])
            * float(opp["leverage"])
            * float(opp["uncertainty"])
            * float(opp["failure_reduction"])
            * float(opp["teacher_dependency"])
            / max(float(opp["compute_cost"]) * float(opp["risk"]), EPSILON)
        )
        high_risk = float(opp["risk"]) >= 0.8
        mission = {
            **opp,
            "mission_id": deterministic_id("miss", opp["kind"], canonical_json(opp.get("refs") or [])),
            "score": score,
            "state": "DISCOVERED",
            "auto_execute": False,
            "high_risk": high_risk,
            "blocked_auto_experiment": high_risk,
            "created_at": utc_now(),
        }
        return mission
