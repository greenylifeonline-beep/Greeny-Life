"""Every completed task becomes an experience episode and multiple learning objects."""
from __future__ import annotations

from typing import Any

from .config import deterministic_id, sha256_obj, utc_now
from .event_bus import EventBus
from .ledger import Ledger
from .schemas import ExperienceEpisode


class ExperienceMetabolism:
    def __init__(self, ledger: Ledger, bus: EventBus) -> None:
        self.ledger = ledger
        self.bus = bus

    def metabolize(self, task: dict[str, Any], result: dict[str, Any], extras: dict[str, Any] | None = None) -> dict[str, Any]:
        extra = extras or {}
        episode_id = deterministic_id("exp", str(task.get("id") or "task"), sha256_obj(result)[:12])
        episode = ExperienceEpisode(
            episode_id=episode_id,
            input=task.get("input") or task,
            context=task.get("context") or {},
            intent=task.get("intent") or task.get("goal") or "unknown",
            plan=result.get("plan") or task.get("plan") or [],
            actions=list(extra.get("actions") or result.get("actions") or []),
            tool_calls=list(extra.get("tool_calls") or []),
            model_calls=list(extra.get("model_calls") or []),
            observations=list(extra.get("observations") or []),
            decisions=list(extra.get("decisions") or []),
            result=result,
            success_score=float(result.get("success_score") or (1.0 if result.get("ok") else 0.0)),
            failure_score=float(result.get("failure_score") or (0.0 if result.get("ok") else 1.0)),
            latency=float(extra.get("latency") or 0.0),
            compute_cost=float(extra.get("compute_cost") or 0.0),
            teacher_used=bool(result.get("teacher_used")),
            recovery_used=bool(extra.get("recovery_used")),
            uncertainty=float(extra.get("uncertainty") or 0.5),
            lessons=list(extra.get("lessons") or []),
            candidate_skills=list(extra.get("candidate_skills") or []),
            counterfactuals=list(extra.get("counterfactuals") or []),
        )
        objects: list[dict[str, Any]] = []
        dumped = episode.model_dump()
        objects.append({"kind": "episode", "id": episode_id})
        if episode.failure_score > 0:
            hid = deterministic_id("hyp", episode_id, "failure")
            objects.append({"kind": "hypothesis", "id": hid})
            self.bus.emit("HYPOTHESIS", "metabolism", {"episode_id": episode_id, "hypothesis": "failure has a recoverable signature", "tested": False}, causal_parent_ids=[])
            self.bus.emit("TASK_FAILED", "metabolism", {"episode_id": episode_id, "result": result})
        if episode.lessons:
            for lesson in episode.lessons:
                lid = deterministic_id("les", episode_id, str(lesson))
                objects.append({"kind": "lesson", "id": lid})
                self.bus.emit("LESSON", "metabolism", {"episode_id": episode_id, "lesson": lesson})
        if episode.candidate_skills:
            for skill in episode.candidate_skills:
                sid = deterministic_id("skc", episode_id, str(skill))
                objects.append({"kind": "skill_candidate", "id": sid})
                self.bus.emit("SKILL_CANDIDATE", "metabolism", {"episode_id": episode_id, "skill": skill})
        objects.append({"kind": "self_critique", "id": deterministic_id("crit", episode_id)})
        self.bus.emit("SELF_CRITIQUE", "metabolism", {"episode_id": episode_id, "uncertainty": episode.uncertainty})
        objects.append({"kind": "observation", "id": deterministic_id("obs", episode_id)})
        self.bus.emit("OBSERVATION", "metabolism", {"episode_id": episode_id, "result_ok": result.get("ok")})
        factor = len(objects) / 1.0
        dumped["experience_multiplication_factor"] = factor
        dumped["created_at"] = utc_now()
        dumped["canonical"] = False
        self.ledger.put("episodes", "episode_id", episode_id, dumped, extra={"content_sha256": sha256_obj(dumped)})
        return dumped
