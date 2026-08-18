"""A18 Experience Intelligence Plane foundations.

Experience is a structured episode with evidence lineage, not a log line.
"""
from __future__ import annotations

from typing import Any

from ..identity import canonical_json, deterministic_id, sha256_obj, utc_now
from ..models import EventType


class ExperiencePlane:
    def __init__(self, store: Any, rkg: Any | None = None) -> None:
        self.store = store
        self.rkg = rkg

    def record(self, episode: dict[str, Any]) -> dict[str, Any]:
        required = (
            "task_id",
            "context",
            "goal",
            "hypothesis",
            "observations",
            "decisions",
            "actions",
            "tools",
            "result",
            "tests",
            "evidence",
            "failures",
            "root_causes",
            "corrections",
            "retest",
            "final_outcome",
            "lessons",
            "skills",
            "transfer_evidence",
            "competency_delta",
            "learning_debt",
            "provenance",
            "confidence",
        )
        missing = [key for key in required if key not in episode]
        if missing:
            from ..identity import FailClosed

            raise FailClosed("EXPERIENCE_MISSING:" + ",".join(missing))
        created_at = episode.get("created_at") or utc_now()
        experience_id = episode.get("experience_id") or deterministic_id("exp", str(episode["task_id"]), sha256_obj(episode)[:16])
        payload = {
            **episode,
            "experience_id": experience_id,
            "created_at": created_at,
            "canonical": False,
            "provider": episode.get("model_provider") or episode.get("provider"),
        }
        digest = sha256_obj(payload)
        payload["content_sha256"] = digest
        with self.store.transaction():
            self.store.conn.execute(
                """
                INSERT INTO experiences(experience_id, task_id, content_sha256, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (experience_id, str(episode["task_id"]), digest, canonical_json(payload), created_at),
            )
            self.store.conn.execute(
                "INSERT INTO experience_fts(experience_id, goal, lesson) VALUES (?, ?, ?)",
                (experience_id, str(episode.get("goal") or ""), " ".join(map(str, episode.get("lessons") or []))),
            )
            self.store.append_event(EventType.EXPERIENCE_RECORDED, experience_id, {"task_id": episode["task_id"], "evidence": episode["evidence"]})
            if self.rkg:
                node = self.rkg.add_node("EXPERIENCE", experience_id, {"task_id": episode["task_id"]})
                for cap in episode.get("capabilities") or []:
                    self.rkg.add_node("CAPABILITY", cap, {})
                    self.rkg.add_edge(experience_id, cap, "OBSERVED_IN")
                for ev in episode.get("evidence") or []:
                    eid = ev if isinstance(ev, str) else ev.get("id") or sha256_obj(ev)[:16]
                    self.rkg.add_node("EVIDENCE", str(eid), {"ref": ev})
                    self.rkg.add_edge(experience_id, str(eid), "VALIDATED_BY")
                for fail in episode.get("failures") or []:
                    fid = fail if isinstance(fail, str) else fail.get("id") or sha256_obj(fail)[:16]
                    self.rkg.add_node("FAILURE", str(fid), {"ref": fail})
                    self.rkg.add_edge(experience_id, str(fid), "FAILED_IN")
                for skill in episode.get("skills") or []:
                    self.rkg.add_node("SKILL", str(skill), {})
                    self.rkg.add_edge(experience_id, str(skill), "LEARNED_FROM")
                _ = node
        return payload

    def record_from_loop(self, run_id: str, task: dict[str, Any], proposal: Any, execution: Any, compiled: Any) -> dict[str, Any]:
        episode = {
            "task_id": task.get("task_id") or task.get("id") or run_id,
            "context": task.get("context") or {"compiled": compiled},
            "goal": task.get("goal") or task.get("intent") or "unspecified",
            "hypothesis": task.get("hypothesis") or "none",
            "observations": task.get("observations") or [],
            "decisions": [{"proposal_id": getattr(proposal, "proposal_id", None)}],
            "actions": [execution] if execution else [],
            "tools": task.get("tools") or [],
            "model_provider": getattr(getattr(proposal, "provider_kind", None), "value", None) or getattr(proposal, "provider_kind", None),
            "result": execution or {"executed": False},
            "tests": task.get("tests") or [],
            "evidence": task.get("evidence") or [f"loop:{run_id}"],
            "failures": task.get("failures") or [],
            "root_causes": task.get("root_causes") or [],
            "corrections": task.get("corrections") or [],
            "retest": task.get("retest") or {},
            "final_outcome": task.get("final_outcome") or "RECORDED",
            "lessons": task.get("lessons") or ["loop-recorded"],
            "skills": task.get("skills") or [],
            "transfer_evidence": task.get("transfer_evidence") or [],
            "competency_delta": task.get("competency_delta") or {},
            "learning_debt": task.get("learning_debt") or [],
            "provenance": {"run_id": run_id, "wave": "a17-integration"},
            "confidence": float(task.get("confidence") or 0.0),
            "capabilities": task.get("capabilities") or [task.get("capability")] if task.get("capability") else [],
        }
        return self.record(episode)
