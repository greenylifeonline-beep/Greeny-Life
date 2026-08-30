"""Content addressing. object_id = SHA256(content)."""
from __future__ import annotations

import hashlib


def object_id(content: bytes) -> str:
    if not isinstance(content, (bytes, bytearray)):
        raise TypeError("CONTENT_MUST_BE_BYTES")
    return hashlib.sha256(content).hexdigest()


def object_id_text(text: str) -> str:
    return object_id(text.encode("utf-8"))
