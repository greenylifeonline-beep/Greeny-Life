"""In-process event sink for linguistic learning.

GL-DOS has no Python event bus. Project memory
(``intelligence/memory/project-memory.ts``) already implements idempotent
decision appends. This module is a local, replay-safe sink used by the
Cognitive WAL and the Evolution inbox — not a second distributed bus.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    event_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=_utcnow)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventSink:
    """Append-only JSONL sink with in-memory subscribers."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._seen: set[str] = set()
        self._subscribers: list[Callable[[Event], None]] = []
        if self.path and self.path.exists():
            self._seen = {row["event_id"] for row in self._iter_file() if "event_id" in row}

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        self._subscribers.append(callback)

    def emit(self, event: Event) -> bool:
        """Return False when the event_id was already recorded (idempotent)."""
        if event.event_id in self._seen:
            return False
        self._seen.add(event.event_id)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        for callback in self._subscribers:
            callback(event)
        return True

    def replay(self) -> list[Event]:
        events: list[Event] = []
        for row in self._iter_file():
            events.append(
                Event(
                    event_id=row["event_id"],
                    event_type=row["event_type"],
                    payload=row.get("payload") or {},
                    created_at=row.get("created_at") or _utcnow(),
                    schema_version=int(row.get("schema_version") or 1),
                )
            )
        return events

    def _iter_file(self) -> Iterable[dict[str, Any]]:
        if not self.path or not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)
