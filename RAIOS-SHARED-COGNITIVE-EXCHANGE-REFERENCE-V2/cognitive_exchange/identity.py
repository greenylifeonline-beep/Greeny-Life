from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "cognitive-exchange.v2"
SCHEMA_MAJOR = 2
SCHEMA_MINOR = 0


class FailClosed(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_obj(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def new_id(prefix: str) -> str:
    return f"{prefix}:{uuid.uuid4().hex}"


def parse_schema_version(value: str) -> tuple[int, int]:
    if not isinstance(value, str) or not value:
        raise FailClosed("SCHEMA_VERSION_MISSING")
    marker = ".v"
    if marker not in value:
        raise FailClosed(f"UNKNOWN_SCHEMA_VERSION:{value}")
    tail = value.rsplit(marker, 1)[-1]
    parts = tail.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError as exc:
        raise FailClosed(f"UNKNOWN_SCHEMA_VERSION:{value}") from exc
    return major, minor


def assert_compatible_schema(value: str) -> None:
    major, _minor = parse_schema_version(value)
    if major != SCHEMA_MAJOR:
        raise FailClosed(f"INCOMPATIBLE_SCHEMA_MAJOR:{value}")
    if major == SCHEMA_MAJOR and parse_schema_version(value)[1] > SCHEMA_MINOR:
        # Forward-minor unknown: fail closed unless an explicit migration exists.
        raise FailClosed(f"UNMIGRATED_SCHEMA_MINOR:{value}")
