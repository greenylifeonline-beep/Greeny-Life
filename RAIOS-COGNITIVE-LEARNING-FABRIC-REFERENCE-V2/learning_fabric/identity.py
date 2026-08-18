from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any


SCHEMA_VERSION = "learning-fabric.v2"


def utc_now() -> str:
    from datetime import datetime, timezone

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
