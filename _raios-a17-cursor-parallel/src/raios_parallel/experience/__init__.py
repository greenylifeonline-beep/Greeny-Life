"""A18 Experience intelligence plane."""
from __future__ import annotations

from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now

REQUIRED = (
    "task_id",
    "goal",
    "context",
    "hypotheses",
    "observations",
    "decisions",
    "actions",
    "tools",
    "models",
    "providers",
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
    "knowledge_debt",
    "cost",
    "latency",
    "provenance",
)


class ExperienceStore:
    def __init__(self, store: Any, rkg: Any | None = None) -> None:
        self.store = store
        self.rkg = rkg

    def append(self, episode: dict[str, Any]) -> dict[str, Any]:
        missing = [k for k in REQUIRED if k not in episode]
        if missing:
            raise FailClosed("EXPERIENCE_MISSING:" + ",".join(missing))
        experience_id = episode.get("experience_id") or deterministic_id("exp", str(episode["task_id"]))
        payload = {**episode, "experience_id": experience_id, "created_at": episode.get("created_at") or utc_now(), "canonical": False}
        digest = self.store.put_bytes(canonical_json(payload).encode("utf-8"))
        payload["content_sha256"] = digest
        meta = {
            "experience_id": experience_id,
            "task_id": str(episode["task_id"]),
            "content_sha256": digest,
            "goal": episode.get("goal"),
            "created_at": payload["created_at"],
            "canonical": False,
            "blob_in_sqlite": False,
        }
        self.store.conn.execute(
            "INSERT INTO experiences(experience_id, task_id, content_sha256, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (experience_id, str(episode["task_id"]), digest, canonical_json(meta), payload["created_at"]),
        )
        self.store.conn.execute(
            "INSERT INTO experience_fts(experience_id, goal, lesson) VALUES (?, ?, ?)",
            (experience_id, str(episode.get("goal") or ""), " ".join(map(str, episode.get("lessons") or []))),
        )
        self.store.append_event("EXPERIENCE_RECORDED", experience_id, {"task_id": episode["task_id"]})
        if self.rkg:
            self.rkg.add_node("EXPERIENCE", experience_id, {"task_id": episode["task_id"]})
            for cap in episode.get("capabilities") or []:
                self.rkg.add_node("CAPABILITY", cap, {})
                self.rkg.add_edge(experience_id, cap, "OBSERVED_IN")
            for ev in episode.get("evidence") or []:
                eid = ev if isinstance(ev, str) else str(ev)
                self.rkg.add_node("EVIDENCE", eid[:80], {})
                self.rkg.add_edge(experience_id, eid[:80], "VALIDATED_BY")
            for skill in episode.get("skills") or []:
                self.rkg.add_node("SKILL", str(skill), {})
                self.rkg.add_edge(experience_id, str(skill), "LEARNED_FROM")
            for fail in episode.get("failures") or []:
                fid = fail if isinstance(fail, str) else str(fail)[:80]
                self.rkg.add_node("FAILURE", fid, {})
                self.rkg.add_edge(experience_id, fid, "FAILED_IN")
        return payload

    def get(self, experience_id: str) -> dict[str, Any]:
        import json

        row = self.store.conn.execute(
            "SELECT content_sha256, payload_json FROM experiences WHERE experience_id = ?", (experience_id,)
        ).fetchone()
        if not row:
            raise FailClosed("EXPERIENCE_UNKNOWN")
        blob = self.store.cas.read(row["content_sha256"])
        payload = json.loads(blob.decode("utf-8"))
        payload["content_sha256"] = row["content_sha256"]
        return payload

    def query(self, task_id: str | None = None) -> list[dict[str, Any]]:
        if task_id:
            rows = self.store.conn.execute(
                "SELECT experience_id FROM experiences WHERE task_id = ?", (task_id,)
            ).fetchall()
        else:
            rows = self.store.conn.execute("SELECT experience_id FROM experiences").fetchall()
        return [self.get(r["experience_id"]) for r in rows]

    def search(self, text: str) -> list[dict[str, Any]]:
        rows = self.store.conn.execute(
            "SELECT experience_id, goal FROM experience_fts WHERE experience_fts MATCH ? LIMIT 50",
            (text,),
        ).fetchall()
        return [dict(r) for r in rows]

    def link(self, experience_id: str, relation: str, target: str) -> dict[str, Any]:
        if not self.rkg:
            raise FailClosed("RKG_UNBOUND")
        return self.rkg.add_edge(experience_id, target, relation)

    def replay_candidate(self, experience_id: str) -> dict[str, Any]:
        rec = self.get(experience_id)
        return {"kind": "replay_candidate", "experience_id": experience_id, "canonical": False, "source": rec["task_id"]}

    def compress_candidate(self, experience_id: str) -> dict[str, Any]:
        rec = self.get(experience_id)
        return {
            "kind": "compress_candidate",
            "experience_id": experience_id,
            "lesson": rec.get("lessons"),
            "raw_omitted": True,
            "canonical": False,
        }
