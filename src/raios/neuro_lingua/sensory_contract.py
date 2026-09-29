"""Canonical sensory contracts for NeuroLingua.

Assimilated from retired local multimodal experiments. This module declares
semantics only: it does not start audio, Ollama, Whisper, FastAPI, or a second bus.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class SensoryEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    modality: str = "TEXT"
    source: str = "HUMAN"
    language: str = "auto"
    partial: bool = False
    final: bool = True
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: str = field(default_factory=utc)

    def canonical(self) -> dict[str, Any]:
        row = asdict(self)
        row["content_hash"] = stable_hash(row)
        return row


@dataclass
class CognitiveTurn:
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sensory_events: list[dict[str, Any]] = field(default_factory=list)
    user_text: str = ""
    language: str = "auto"
    context: list[dict[str, Any]] = field(default_factory=list)
    response_text: str = ""
    state: str = "RECEIVED"
    created_at: str = field(default_factory=utc)
    completed_at: str | None = None


@dataclass(frozen=True)
class SensoryCapability:
    name: str
    available: bool = False
    backend: str | None = None
    reason: str | None = "NOT_PROVEN"
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_lightweight_language(text: str) -> str:
    if not text:
        return "unknown"
    letters = sum(1 for c in text if c.isalpha())
    arabic = sum(1 for c in text if 0x0600 <= ord(c) < 0x0700)
    if letters and arabic / letters > 0.25:
        return "ar"
    if any(c in "æøåÆØÅ" for c in text):
        return "no"
    return "auto"


LAWS = (
    "SENSORY_CONTRACT_NE_RUNTIME",
    "BACKEND_ABSENT_NE_AVAILABLE",
    "LOCAL_OLLAMA_NE_MAIN_CORTEX",
    "WHISPER_ADAPTER_NE_HEARING_PROOF",
    "AUDIO_DEVICE_NE_ACTIVE_HEARING",
    "MULTIMODAL_DECLARATION_NE_LIVE_MULTIMODAL_RUNTIME",
)
