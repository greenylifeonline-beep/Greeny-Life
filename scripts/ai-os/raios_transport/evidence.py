"""Durable Command Fabric completion evidence. Files only. No SQLite. No WAL."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None


class CompletionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.complete_dir = root / "complete"
        self.inflight_dir = root / "inflight"
        self.nonce_dir = root / "nonces"
        for d in (self.complete_dir, self.inflight_dir, self.nonce_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _key(self, packet_id: str, corr: str) -> str:
        return f"{packet_id}__{corr}"

    def complete_path(self, packet_id: str, corr: str) -> Path:
        return self.complete_dir / f"{self._key(packet_id, corr)}.json"

    def inflight_path(self, packet_id: str, corr: str) -> Path:
        return self.inflight_dir / f"{self._key(packet_id, corr)}.json"

    def nonce_path(self, nonce: str) -> Path:
        return self.nonce_dir / f"{nonce}.json"

    def get_complete(self, packet_id: str, corr: str) -> dict[str, Any] | None:
        return _load(self.complete_path(packet_id, corr))

    def nonce_seen(self, nonce: str) -> bool:
        return self.nonce_path(nonce).exists()

    def mark_nonce(self, nonce: str, packet_id: str, corr: str) -> None:
        if not nonce:
            return
        _atomic(self.nonce_path(nonce), {"nonce": nonce, "packet_id": packet_id, "correlation_id": corr, "at": utc()})

    def begin(self, packet_id: str, corr: str, nonce: str) -> dict[str, Any]:
        rec = {"packet_id": packet_id, "correlation_id": corr, "nonce": nonce, "started_at": utc()}
        _atomic(self.inflight_path(packet_id, corr), rec)
        self.mark_nonce(nonce, packet_id, corr)
        return rec

    def inflight(self, packet_id: str, corr: str) -> dict[str, Any] | None:
        return _load(self.inflight_path(packet_id, corr))

    def finish(self, packet_id: str, corr: str, outputs: dict[str, Any], executed: bool) -> dict[str, Any]:
        rec = {
            "schema": "raios.fabric-completion.v1",
            "packet_id": packet_id,
            "correlation_id": corr,
            "completed_at": utc(),
            "executed": executed,
            "execution_count": 1 if executed else 0,
            "outputs": outputs,
        }
        existing = self.get_complete(packet_id, corr)
        if existing:
            rec["execution_count"] = int(existing.get("execution_count") or 0)
            rec["executed"] = False
            rec["outputs"] = existing.get("outputs") or outputs
            rec["replayed"] = True
            return existing
        _atomic(self.complete_path(packet_id, corr), rec)
        inflight = self.inflight_path(packet_id, corr)
        if inflight.exists():
            inflight.unlink()
        return rec
