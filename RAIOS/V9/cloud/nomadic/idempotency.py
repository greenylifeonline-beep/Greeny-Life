"""Job retries must be idempotent. Duplicate work is detected, not double-applied."""
from __future__ import annotations

import hashlib
from typing import Any


def key(job_id: str, input_hash: str, op: str = "execute") -> str:
    raw = f"{job_id}|{input_hash}|{op}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class IdempotencyStore:
    def __init__(self) -> None:
        self._done: dict[str, dict[str, Any]] = {}

    def seen(self, idem_key: str) -> bool:
        return idem_key in self._done

    def remember(self, idem_key: str, receipt: dict[str, Any]) -> dict[str, Any]:
        if idem_key in self._done:
            prior = self._done[idem_key]
            return {
                "duplicate": True,
                "applied": False,
                "prior_output_hash": prior.get("output_hash"),
                "idempotency_key": idem_key,
            }
        self._done[idem_key] = dict(receipt)
        return {"duplicate": False, "applied": True, "idempotency_key": idem_key}

    def get(self, idem_key: str) -> dict[str, Any] | None:
        row = self._done.get(idem_key)
        return dict(row) if row else None
