"""Local-first Cognitive WAL.

Fast linguistic observations enter DISCOVERED without a remote ACK.
Replay is idempotent on ``event_id``. Canonical promotion is explicit and
cannot skip VALIDATED.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from raios.events import Event, EventSink
from raios.knowledge_state import KnowledgeState, assert_transition


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_event_id(event_type: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"event_type": event_type, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class LinguisticLearningEvent:
    event_id: str
    event_type: str
    payload: dict[str, Any]
    knowledge_state: KnowledgeState = KnowledgeState.DISCOVERED
    created_at: str = field(default_factory=utcnow)
    schema_version: int = 1
    source: str = "neuro_lingua"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "knowledge_state": self.knowledge_state.value,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "LinguisticLearningEvent":
        return cls(
            event_id=row["event_id"],
            event_type=row["event_type"],
            payload=row.get("payload") or {},
            knowledge_state=KnowledgeState(row.get("knowledge_state") or "DISCOVERED"),
            created_at=row.get("created_at") or utcnow(),
            schema_version=int(row.get("schema_version") or 1),
            source=row.get("source") or "neuro_lingua",
        )


class CognitiveWAL:
    """Append-only JSONL log. Local durability only; no remote ACK."""

    def __init__(self, path: Path, *, sink: EventSink | None = None) -> None:
        self.path = path
        self.sink = sink or EventSink()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, LinguisticLearningEvent] = {}
        for event in self.replay():
            self._index[event.event_id] = event

    def append(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        event_id: str | None = None,
        knowledge_state: KnowledgeState = KnowledgeState.DISCOVERED,
    ) -> tuple[LinguisticLearningEvent, bool]:
        """Append an observation.

        Returns ``(event, inserted)``. ``inserted`` is False on idempotent replay.
        Direct CANONICAL appends are rejected.
        """
        if knowledge_state is KnowledgeState.CANONICAL:
            raise ValueError(
                "Cognitive WAL will not append CANONICAL observations. "
                "Use promote() after VALIDATED under durability policy."
            )
        eid = event_id or stable_event_id(event_type, payload)
        if eid in self._index:
            return self._index[eid], False
        event = LinguisticLearningEvent(
            event_id=eid,
            event_type=event_type,
            payload=payload,
            knowledge_state=knowledge_state,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        self._index[eid] = event
        self.sink.emit(
            Event(
                event_id=eid,
                event_type=event_type,
                payload={"knowledge_state": knowledge_state.value, **payload},
            )
        )
        return event, True

    def promote(
        self,
        event_id: str,
        target: KnowledgeState,
        *,
        allow_canonical: bool = False,
        validation_evidence: dict[str, Any] | None = None,
    ) -> LinguisticLearningEvent:
        current = self._index.get(event_id)
        if current is None:
            raise KeyError(f"Unknown WAL event {event_id}")
        assert_transition(current.knowledge_state, target)
        if target is KnowledgeState.CANONICAL and not allow_canonical:
            raise ValueError(
                "Canonical promotion is governed by RAIOS durability policy "
                "and requires allow_canonical=True plus validation evidence."
            )
        if target is KnowledgeState.CANONICAL and not validation_evidence:
            raise ValueError("CANONICAL promotion requires validation_evidence.")
        current.knowledge_state = target
        if validation_evidence:
            current.payload = {
                **current.payload,
                "validation_evidence": validation_evidence,
            }
        self._rewrite()
        return current

    def get(self, event_id: str) -> LinguisticLearningEvent | None:
        return self._index.get(event_id)

    def replay(self) -> list[LinguisticLearningEvent]:
        events: list[LinguisticLearningEvent] = []
        seen: set[str] = set()
        for row in self._iter():
            event = LinguisticLearningEvent.from_dict(row)
            if event.event_id in seen:
                continue
            seen.add(event.event_id)
            events.append(event)
        return events

    def by_state(self, state: KnowledgeState) -> list[LinguisticLearningEvent]:
        return [event for event in self._index.values() if event.knowledge_state is state]

    def _iter(self) -> Iterable[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def _rewrite(self) -> None:
        tmp = self.path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            for event in self._index.values():
                handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        tmp.replace(self.path)
