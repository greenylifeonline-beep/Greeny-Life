from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .schema import KnowledgeState


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "RAIOS" / "V9" / "runtime" / "cognitive_event_bus.py").exists():
            return parent
    return Path.cwd()


def _load_event_bus():
    root = _repo_root()
    runtime = root / "RAIOS" / "V9" / "runtime"
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    import cognitive_event_bus as bus  # type: ignore

    return bus


class ExistingCognitiveWALWriter:
    """Adapter over RAIOS/V9/runtime/cognitive_event_bus.emit. Not a second WAL."""

    def __init__(self):
        self.bus = None
        self.unavailable_reason: str | None = None
        try:
            self.bus = _load_event_bus()
        except Exception as exc:
            self.unavailable_reason = f"{type(exc).__name__}:{exc}"

    @property
    def wal_path(self) -> str | None:
        if self.bus is None:
            return None
        return str(getattr(self.bus, "WAL_FILE", None))

    def append_learning(
        self,
        intent: str,
        payload: dict[str, Any],
        *,
        knowledge_state: KnowledgeState = KnowledgeState.DISCOVERED,
        actor: str = "RAIOS.NEUROLINGUA",
    ) -> dict[str, Any]:
        if knowledge_state is KnowledgeState.CANONICAL:
            raise ValueError("DIRECT_CANONICAL_PROMOTION_FORBIDDEN")
        if self.bus is None:
            return {
                "status": "WAL_UNAVAILABLE",
                "wal_appended": False,
                "reason": self.unavailable_reason,
                "knowledge_state": knowledge_state.value,
            }
        metadata = {
            **payload,
            "knowledge_state": knowledge_state.value,
            "subsystem": "neuro_lingua",
            "remote_ack_required": False,
        }
        built = self.bus.build_event(
            event_type="LEARNING",
            actor=actor,
            intent=intent,
            success=True,
            metadata=metadata,
            confidence=payload.get("confidence"),
        )
        result = self.bus.emit_event(built, materialize=True)
        return {
            "status": result.get("status"),
            "wal_appended": bool(result.get("wal_appended")),
            "event_id": result.get("event_id"),
            "knowledge_state": knowledge_state.value,
            "wal_path": self.wal_path,
            "materialized": result.get("materialized"),
        }
