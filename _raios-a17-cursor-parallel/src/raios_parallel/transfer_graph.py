"""Teacher capability transfer graph."""
from __future__ import annotations

from typing import Any

from .identity import canonical_json, utc_now


class TransferGraph:
    def __init__(self, store: Any, mastery: Any, retirement: Any) -> None:
        self.store = store
        self.mastery = mastery
        self.retirement = retirement

    def build(self) -> dict[str, Any]:
        rows = self.store.conn.execute("SELECT * FROM teacher_capability").fetchall()
        nodes: list[dict[str, Any]] = []
        for row in rows:
            evaluation = self.mastery.evaluate(row["capability"])
            dep = self.mastery.teacher_dependency(row["capability"])
            ret = self.retirement.evaluate(row["teacher_id"], row["capability"])
            dims = evaluation["dimensions"]
            nodes.append(
                {
                    "teacher": row["teacher_id"],
                    "capability": row["capability"],
                    "source_observations": self._obs(row["teacher_id"]),
                    "teacher_unique_value": bool(row["unique_capability"]),
                    "raios_current_score": dims.get("knowledge"),
                    "transfer_score": dims.get("transfer"),
                    "retention_score": dims.get("retention"),
                    "teacher_dependency": dep["dependent"],
                    "retirement_state": ret["decision"],
                    "lifecycle": row["lifecycle"],
                    "evidence_refs": dims.get("evidence_refs") or [],
                    "skill_refs": self._refs("skills", "capability", row["capability"]),
                    "training_refs": self._refs("training", None, None),
                }
            )
        graph = {
            "generated_at": utc_now(),
            "edges_model": "Teacher→Capability→Lesson→Skill→TransferTest→StudentEvidence→Mastery→RetirementState",
            "nodes": nodes,
            "canonical": False,
        }
        return graph

    def write(self, path: Any) -> dict[str, Any]:
        graph = self.build()
        path.write_text(canonical_json(graph), encoding="utf-8")
        return graph

    def _obs(self, teacher_id: str) -> list[str]:
        rows = self.store.conn.execute(
            "SELECT observation_id FROM observations WHERE teacher_id = ?", (teacher_id,)
        ).fetchall()
        return [r["observation_id"] for r in rows]

    def _refs(self, table: str, col: str | None, value: str | None) -> list[str]:
        if col and value:
            rows = self.store.conn.execute(f"SELECT payload_json FROM {table} WHERE {col} = ?", (value,)).fetchall()
        else:
            rows = self.store.conn.execute(f"SELECT payload_json FROM {table}").fetchall()
        import json

        out = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            out.append(payload.get("skill_id") or payload.get("candidate_id") or "")
        return [x for x in out if x]
