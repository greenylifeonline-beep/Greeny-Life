"""Canonical sensory contracts for NeuroLingua.

Assimilated from retired local multimodal experiments. This module declares
portable semantics only: it does not start a microphone daemon, FastAPI,
Ollama, Whisper, or a second bus.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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


@dataclass(frozen=True)
class AudioFrame:
    frame_id: str
    timestamp: str
    pcm: bytes
    sample_rate: int
    speech: bool


class UtteranceSegmenter:
    """Backend-neutral utterance boundary logic.

    Speech detection is supplied by the caller. This preserves the proven
    pre-roll/end-silence/max-duration semantics without binding a microphone,
    sounddevice, or WebRTC VAD into the canonical runtime.
    """

    def __init__(self, *, frame_ms: int = 30, pre_roll_ms: int = 300, end_silence_ms: int = 600, max_seconds: int = 30) -> None:
        if frame_ms not in (10, 20, 30):
            raise ValueError("UNSUPPORTED_FRAME_MS")
        self.frame_ms = frame_ms
        self.pre_roll_frames = max(1, pre_roll_ms // frame_ms)
        self.end_silence_frames = max(1, end_silence_ms // frame_ms)
        self.max_frames = max(1, int(max_seconds * 1000 / frame_ms))
        self.pre_roll: collections.deque[bytes] = collections.deque(maxlen=self.pre_roll_frames)
        self.active = False
        self.frames: list[bytes] = []
        self.silence = 0

    def push(self, pcm: bytes, *, speech: bool) -> bytes | None:
        if not self.active:
            self.pre_roll.append(pcm)
            if speech:
                self.active = True
                self.frames = list(self.pre_roll)
                self.pre_roll.clear()
                self.silence = 0
            return None

        self.frames.append(pcm)
        self.silence = 0 if speech else self.silence + 1
        if self.silence < self.end_silence_frames and len(self.frames) < self.max_frames:
            return None
        result = b"".join(self.frames)
        self.active = False
        self.frames = []
        self.silence = 0
        return result


class FasterWhisperAdapter:
    """Optional STT adapter; construction is fail-closed when backend is absent."""

    _cache: dict[tuple[str, str, str], Any] = {}
    _lock = threading.Lock()

    def __init__(self, model_name: str | None = None, device: str | None = None, compute_type: str | None = None) -> None:
        self.model_name = model_name or os.getenv("RAIOS_STT_MODEL", "small")
        self.device = device or os.getenv("RAIOS_STT_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv("RAIOS_STT_COMPUTE", "int8")
        self.capability = SensoryCapability(name="HEARING_STT")
        self._model: Any = None
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as exc:
            self.capability = SensoryCapability(name="HEARING_STT", reason=f"BACKEND_UNAVAILABLE::{type(exc).__name__}")
            return
        key = (self.model_name, self.device, self.compute_type)
        try:
            with self._lock:
                if key not in self._cache:
                    self._cache[key] = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
                self._model = self._cache[key]
            self.capability = SensoryCapability(
                name="HEARING_STT",
                available=True,
                backend="faster-whisper",
                reason=None,
                metadata={"model": self.model_name, "device": self.device, "compute_type": self.compute_type},
            )
        except Exception as exc:
            self.capability = SensoryCapability(name="HEARING_STT", reason=f"BACKEND_BIND_FAILED::{type(exc).__name__}")

    def transcribe(self, wav: str | Path, language: str | None = None) -> dict[str, Any]:
        if not self.capability.available or self._model is None:
            return {"ok": False, "reason": self.capability.reason or "NOT_PROVEN", "text": "", "segments": []}
        kwargs: dict[str, Any] = {
            "beam_size": 5,
            "vad_filter": False,
            "word_timestamps": True,
            "condition_on_previous_text": True,
        }
        if language and language != "auto":
            kwargs["language"] = language
        segments, info = self._model.transcribe(str(wav), **kwargs)
        out: list[dict[str, Any]] = []
        for segment in segments:
            words = [
                {"start": w.start, "end": w.end, "word": w.word, "probability": w.probability}
                for w in (segment.words or [])
            ]
            out.append({"start": segment.start, "end": segment.end, "text": segment.text, "words": words})
        return {
            "ok": True,
            "text": " ".join(str(row["text"]).strip() for row in out).strip(),
            "language": getattr(info, "language", None),
            "language_probability": getattr(info, "language_probability", None),
            "duration": getattr(info, "duration", None),
            "segments": out,
        }


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
    "MICROPHONE_DAEMON_NE_SENSORY_CONTRACT",
    "SEGMENTATION_NE_SPEECH_DETECTION",
    "MULTIMODAL_DECLARATION_NE_LIVE_MULTIMODAL_RUNTIME",
)
