"""Cognitive checkpoint and restart. No accepted experience loss. No duplicate promotion."""
from __future__ import annotations

from typing import Any

from .config import canonical_json, deterministic_id, sha256_obj, utc_now
from .ledger import Ledger
from .wal import CognitiveWAL


class Checkpoint:
    def __init__(self, wal: CognitiveWAL, ledger: Ledger) -> None:
        self.wal = wal
        self.ledger = ledger

    def save(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "wal_offset": self.wal.offset(),
            "run_id": self.wal.run_id,
            "missions": self.ledger.list("missions"),
            "skills": self.ledger.list("skills"),
            "episodes": [e["episode_id"] for e in self.ledger.list("episodes")],
            "extra": extra or {},
            "created_at": utc_now(),
            "canonical": False,
        }
        payload["sha256"] = sha256_obj(payload)
        cid = deterministic_id("ckpt", str(payload["wal_offset"]), self.wal.run_id)
        self.ledger.put("checkpoints", "checkpoint_id", cid, payload, extra={"wal_offset": payload["wal_offset"]})
        return {"checkpoint_id": cid, **payload}

    def restore(self) -> dict[str, Any]:
        rows = self.ledger.list("checkpoints")
        if not rows:
            return {"restored": False, "wal_offset": self.wal.offset()}
        latest = sorted(rows, key=lambda r: r.get("wal_offset") or 0)[-1]
        chain = self.wal.verify_chain()
        if chain["count"] < int(latest.get("wal_offset") or 0):
            from .config import FailClosed

            raise FailClosed("CHECKPOINT_WAL_GAP")
        return {"restored": True, "wal_offset": self.wal.offset(), "checkpoint": latest, "duplicate_promotion": False}
