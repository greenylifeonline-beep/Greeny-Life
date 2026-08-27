"""Command execution lease adapter over existing command-fabric leases.

Reuses `.ai-os/state/command-fabric/leases`. Not LOCKS.json. Not a second registry.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
EXISTING_LEASES = ROOT / ".ai-os" / "state" / "command-fabric" / "leases"
EXISTING_LOCKS_JSON = ROOT / ".ai-os" / "state" / "LOCKS.json"

LEASE_CONFLICT = "LEASE_CONFLICT"
LEASE_UNKNOWN = "LEASE_UNKNOWN"
LEASE_EXPIRED = "LEASE_EXPIRED"
WRONG_OWNER = "WRONG_OWNER_RELEASE_DENIED"
LEASE_FAIL_CLOSED = "LEASE_FAIL_CLOSED"

SCHEMA = "raios.write-lease.v2"


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(t: datetime | None = None) -> str:
    return (t or _utc()).isoformat()


def _parse(v: str) -> datetime:
    try:
        rec = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)
    if rec.tzinfo is None:
        rec = rec.replace(tzinfo=timezone.utc)
    return rec


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _atomic(path: Path, obj: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    raw = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(raw, encoding="utf-8")
    tmp.replace(path)
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


class CommandLeaseAdapter:
    """Minimal wrapper around existing write-lease files."""

    def __init__(self, leases_dir: Path | None = None) -> None:
        self.leases_dir = Path(leases_dir) if leases_dir else EXISTING_LEASES
        self.leases_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, lease_id: str) -> Path:
        return self.leases_dir / f"{lease_id}.json"

    def _all(self) -> list[dict[str, Any]]:
        rows = []
        for p in self.leases_dir.glob("*.json"):
            x = _load(p)
            if x:
                rows.append(x)
        return rows

    def active_on_scope(self, scope: str) -> dict[str, Any] | None:
        now = _utc()
        for x in self._all():
            if x.get("scope") != scope:
                continue
            if x.get("state") != "ACTIVE":
                continue
            if _parse(str(x.get("expires_at") or "")) <= now:
                continue
            return x
        return None

    def acquire(
        self,
        *,
        owner: str,
        scope: str,
        task_id: str,
        correlation_id: str,
        capability: str,
        resource_or_target: str,
        idempotency_key: str,
        provenance_ref: str,
        ttl_seconds: int = 120,
        head: str = "",
    ) -> dict[str, Any]:
        existing = self.active_on_scope(scope)
        if existing:
            same_task = existing.get("task_id") == task_id and existing.get("idempotency_key") == idempotency_key
            if existing.get("owner") == owner and same_task:
                out = dict(existing)
                out["IDEMPOTENT_REACQUIRE"] = True
                out["ok"] = True
                return out
            return {
                "ok": False,
                "code": LEASE_CONFLICT,
                "existing_lease_id": existing.get("lease_id"),
                "existing_owner": existing.get("owner"),
                "existing_task_id": existing.get("task_id"),
            }
        t = _utc()
        epoch = int(t.timestamp() * 1_000_000)
        lid = f"L-{epoch}-{uuid.uuid4().hex[:8]}"
        rec = {
            "schema": SCHEMA,
            "lease_id": lid,
            "fence_token": epoch,
            "owner": owner,
            "owner_identity": owner,
            "scope": scope,
            "task_id": task_id,
            "correlation_id": correlation_id,
            "capability": capability,
            "resource_or_target": resource_or_target,
            "idempotency_key": idempotency_key,
            "provenance_ref": provenance_ref,
            "acquired_at": _iso(t),
            "issued_at": _iso(t),
            "expires_at": _iso(t + timedelta(seconds=max(0, int(ttl_seconds)))),
            "state": "ACTIVE",
            "fail_closed": True,
            "head": head,
            "LEASE_ACQUIRE_IS_AUTHORITY_GRANT": False,
        }
        _atomic(self._path(lid), rec)
        out = dict(rec)
        out["ok"] = True
        out["IDEMPOTENT_REACQUIRE"] = False
        return out

    def validate(self, lease_id: str, *, owner: str | None = None) -> dict[str, Any]:
        rec = _load(self._path(lease_id))
        if not rec:
            return {"ok": False, "code": LEASE_UNKNOWN}
        if rec.get("state") != "ACTIVE":
            return {"ok": False, "code": rec.get("state") or LEASE_FAIL_CLOSED, "lease": rec}
        if _parse(str(rec.get("expires_at") or "")) <= _utc():
            return {"ok": False, "code": LEASE_EXPIRED, "lease": rec}
        if owner is not None and rec.get("owner") != owner:
            return {"ok": False, "code": WRONG_OWNER, "lease": rec}
        return {"ok": True, "lease": rec}

    def renew(self, lease_id: str, *, owner: str, ttl_seconds: int = 120) -> dict[str, Any]:
        v = self.validate(lease_id, owner=owner)
        if not v.get("ok"):
            return v
        rec = dict(v["lease"])
        rec["expires_at"] = _iso(_utc() + timedelta(seconds=int(ttl_seconds)))
        rec["renewed_at"] = _iso()
        _atomic(self._path(lease_id), rec)
        return {"ok": True, "lease": rec}

    def release(self, lease_id: str, *, owner: str) -> dict[str, Any]:
        rec = _load(self._path(lease_id))
        if not rec:
            return {"ok": False, "code": LEASE_UNKNOWN}
        if rec.get("owner") != owner:
            return {"ok": False, "code": WRONG_OWNER}
        rec["state"] = "RELEASED"
        rec["released_at"] = _iso()
        _atomic(self._path(lease_id), rec)
        return {"ok": True, "lease": rec, "PROVENANCE_ERASED": False}

    def expire(self, lease_id: str) -> dict[str, Any]:
        rec = _load(self._path(lease_id))
        if not rec:
            return {"ok": False, "code": LEASE_UNKNOWN}
        rec["state"] = "EXPIRED"
        rec["expired_at"] = _iso()
        _atomic(self._path(lease_id), rec)
        return {"ok": True, "lease": rec}

    def uses_existing_lease_dir(self) -> bool:
        return self.leases_dir.resolve() == EXISTING_LEASES.resolve()

    def uses_locks_json(self) -> bool:
        return False
