"""C1→C5 task envelope. Plain chat is not a task."""

from __future__ import annotations

import json
from typing import Any

SCHEMA_VERSION = "raios.c1c5.task-envelope.v1"

REQUIRED_FIELDS = (
    "schema_version",
    "task_id",
    "actor",
    "target",
    "mode",
    "intent",
    "risk_class",
    "writes_allowed",
    "correlation_id",
    "idempotency_key",
    "requested_capability",
    "parameters",
    "authority_context_reference",
)

MALFORMED = "TASK_ENVELOPE_MALFORMED"
NOT_A_TASK = "NOT_A_TASK"


def looks_like_envelope(text: str) -> bool:
    s = (text or "").strip()
    if not s.startswith("{"):
        return False
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return False
    return isinstance(obj, dict) and obj.get("schema_version") == SCHEMA_VERSION


def parse(text: str) -> dict[str, Any] | None:
    if not looks_like_envelope(text):
        return None
    return json.loads(text.strip())


def require_fields(env: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_FIELDS if k not in env]
    if missing:
        raise ValueError(f"{MALFORMED}:missing:{','.join(missing)}")
    if env.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{MALFORMED}:schema")
    if not str(env.get("task_id") or "").strip():
        raise ValueError(f"{MALFORMED}:task_id")
    if not str(env.get("idempotency_key") or "").strip():
        raise ValueError(f"{MALFORMED}:idempotency_key")
    if env.get("parameters") is None or not isinstance(env.get("parameters"), dict):
        raise ValueError(f"{MALFORMED}:parameters")
