"""Archive states. Never delete. Preserve path, hash, reason, replacement, evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from raios_fi.config import sha256_bytes
from raios_fi.store import Store

ArchiveState = Literal["ACTIVE", "REFERENCE", "SUPERSEDED", "ARCHIVED", "QUARANTINED"]


@dataclass(frozen=True)
class ArchiveRecord:
    original_path: str
    sha256: str
    version: str
    state: ArchiveState
    reason: str
    replacement: str | None
    evidence: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArchiveEngine:
    def __init__(self, store: Store) -> None:
        self.store = store

    def record(
        self,
        path: Path,
        state: ArchiveState,
        reason: str,
        *,
        version: str = "unknown",
        replacement: str | None = None,
        evidence: str = "",
    ) -> ArchiveRecord:
        h = sha256_bytes(path.read_bytes()) if path.is_file() else sha256_bytes(str(path).encode())
        rec = ArchiveRecord(
            original_path=str(path),
            sha256=h,
            version=version,
            state=state,
            reason=reason,
            replacement=replacement,
            evidence=evidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.insert_archive(rec.to_dict())
        return rec
