"""Leases expire so another worker can fail over. Not Cognitive WAL. Not C5."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class Lease:
    job_id: str
    worker_id: str
    expires_at: float
    token: str
    released: bool = False

    def alive(self, now: float | None = None) -> bool:
        if self.released:
            return False
        return (now if now is not None else time.time()) < self.expires_at


class LeaseManager:
    def __init__(self, ttl_s: float = 30.0) -> None:
        self.ttl_s = float(ttl_s)
        self._leases: dict[str, Lease] = {}
        self._seq = 0

    def claim(self, job_id: str, worker_id: str, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        current = self._leases.get(job_id)
        if current and current.alive(now) and current.worker_id != worker_id:
            return {
                "ok": False,
                "reason": "LEASE_HELD",
                "holder": current.worker_id,
                "expires_at": current.expires_at,
            }
        self._seq += 1
        lease = Lease(
            job_id=job_id,
            worker_id=worker_id,
            expires_at=now + self.ttl_s,
            token=f"lease-{self._seq}-{job_id}",
        )
        self._leases[job_id] = lease
        return {
            "ok": True,
            "reason": "CLAIMED" if current is None else "FAILOVER_CLAIM",
            "lease": {
                "job_id": job_id,
                "worker_id": worker_id,
                "token": lease.token,
                "expires_at": lease.expires_at,
            },
        }

    def holder(self, job_id: str, now: float | None = None) -> str | None:
        now = time.time() if now is None else now
        lease = self._leases.get(job_id)
        if lease and lease.alive(now):
            return lease.worker_id
        return None

    def expired(self, job_id: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        lease = self._leases.get(job_id)
        if lease is None:
            return True
        return not lease.alive(now)

    def release(self, job_id: str, worker_id: str) -> dict[str, Any]:
        lease = self._leases.get(job_id)
        if lease is None or lease.worker_id != worker_id:
            return {"ok": False, "reason": "NOT_HOLDER"}
        lease.released = True
        return {"ok": True, "reason": "RELEASED", "job_id": job_id, "worker_id": worker_id}

    def stealable(self, now: float | None = None) -> list[str]:
        now = time.time() if now is None else now
        out: list[str] = []
        for job_id, lease in self._leases.items():
            if not lease.alive(now) and not lease.released:
                out.append(job_id)
        return out
