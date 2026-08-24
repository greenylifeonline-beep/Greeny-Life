"""Append-only job ledger. Not Cognitive WAL."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Job:
    job_id: str
    op: str
    payload: dict[str, Any]
    input_hash: str
    status: str = "QUEUED"
    worker_id: str | None = None
    created_at: str = field(default_factory=utc)

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "op": self.op,
            "payload": self.payload,
            "input_hash": self.input_hash,
            "status": self.status,
            "worker_id": self.worker_id,
            "created_at": self.created_at,
        }


class JobLedger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.jobs: dict[str, Job] = {}
        if path and path.is_file():
            self._load()

    def _load(self) -> None:
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            job = Job(
                job_id=row["job_id"],
                op=row["op"],
                payload=row.get("payload") or {},
                input_hash=row["input_hash"],
                status=row.get("status") or "QUEUED",
                worker_id=row.get("worker_id"),
                created_at=row.get("created_at") or utc(),
            )
            self.jobs[job.job_id] = job

    def _append(self, job: Job) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(job.as_dict(), ensure_ascii=False) + "\n")

    def enqueue(self, job_id: str, op: str, payload: dict[str, Any]) -> Job:
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        job = Job(job_id=job_id, op=op, payload=payload, input_hash=sha256_bytes(blob))
        self.jobs[job_id] = job
        self._append(job)
        return job

    def get(self, job_id: str) -> Job:
        return self.jobs[job_id]

    def queued(self) -> list[Job]:
        return [j for j in self.jobs.values() if j.status == "QUEUED"]

    def set_status(self, job_id: str, status: str, worker_id: str | None = None) -> Job:
        job = self.jobs[job_id]
        job.status = status
        if worker_id is not None:
            job.worker_id = worker_id
        self._append(job)
        return job
