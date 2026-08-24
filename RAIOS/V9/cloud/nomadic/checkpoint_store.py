"""Resumable checkpoints. A stolen job continues from the last durable step."""
from __future__ import annotations

from typing import Any


class CheckpointStore:
    def __init__(self) -> None:
        self._rows: dict[str, list[dict[str, Any]]] = {}

    def save(self, job_id: str, seq: int, state: dict[str, Any]) -> dict[str, Any]:
        row = {"job_id": job_id, "seq": int(seq), "state": dict(state)}
        self._rows.setdefault(job_id, []).append(row)
        return {"ok": True, "job_id": job_id, "seq": seq, "resumable": True}

    def latest(self, job_id: str) -> dict[str, Any] | None:
        rows = self._rows.get(job_id) or []
        return dict(rows[-1]) if rows else None

    def resume(self, job_id: str) -> dict[str, Any]:
        last = self.latest(job_id)
        if last is None:
            return {"ok": False, "reason": "NO_CHECKPOINT", "job_id": job_id, "seq": 0, "state": {}}
        return {
            "ok": True,
            "reason": "RESUMED",
            "job_id": job_id,
            "seq": last["seq"],
            "state": dict(last["state"]),
        }
