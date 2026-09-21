from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TRACE_FIELDS = (
    "seat",
    "task_id",
    "provider",
    "model_id",
    "deployment_location",
    "request_class",
    "privacy_class",
    "input_tokens",
    "output_tokens",
    "latency_ms",
    "cost_estimate",
    "fallback_reason",
    "canonical_head",
    "response_hash",
)

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(authorization\s*[:=]\s*bearer\s+)\S+"),
    re.compile(r"(?i)\b(bearer\s+)\S+"),
    re.compile(r"(?i)\b(api[_-]?key\s*[:=]\s*)\S+"),
    re.compile(r"(?i)\b(token\s*[:=]\s*)\S+"),
    re.compile(r"(?i)\b(secret\s*[:=]\s*)\S+"),
    re.compile(r"(?i)\b(password\s*[:=]\s*)\S+"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9_\-]+"),
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            key_l = str(key).casefold()
            if any(s in key_l for s in ("api_key", "authorization", "bearer", "token", "secret", "password")):
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_secrets(item)
        return out
    if isinstance(value, list):
        return [redact_secrets(x) for x in value]
    if isinstance(value, str):
        text = value
        for pattern in _SECRET_PATTERNS:
            if pattern.groups:
                text = pattern.sub(r"\1[REDACTED]", text)
            else:
                text = pattern.sub("[REDACTED]", text)
        return text
    return value


def response_hash(text: str | None) -> str:
    raw = (text or "").encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


def append_call_trace(repo: Path, record: dict[str, Any]) -> Path:
    path = repo / ".ai-os" / "receipts" / "ai-gateway" / "call-traces.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {field: record.get(field) for field in TRACE_FIELDS}
    row["schema"] = "raios.ai-gateway.call-trace.v1"
    row["recorded_at"] = utc()
    for extra in ("ok", "decision", "dispatch_executed", "http_status", "error"):
        if extra in record:
            row[extra] = record[extra]
    safe = redact_secrets(row)
    text = json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
    if any(tok in text.casefold() for tok in ("sk-", "bearer ", "api_key=")):
        # Fail closed: never persist something that still looks like a secret.
        text = json.dumps(redact_secrets({**safe, "sanitized": True}), ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text + "\n")
    return path
