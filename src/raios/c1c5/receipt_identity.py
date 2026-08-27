"""Receipt identity compatibility. Historical files are not mutated.

Historical command-fabric receipts used message_id only.
New producers emit receipt_id and message_id with an explicit relationship.
"""

from __future__ import annotations

import hashlib
from typing import Any


def interpret_receipt_id(obj: dict[str, Any] | None) -> str | None:
    """Compatibility: receipt_id := message_id when receipt_id is absent."""
    if not isinstance(obj, dict):
        return None
    rid = str(obj.get("receipt_id") or "").strip()
    if rid:
        return rid
    mid = str(obj.get("message_id") or "").strip()
    return mid or None


def producer_receipt_identity(
    *,
    message_id: str | None = None,
    task_id: str | None = None,
    correlation_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Identity fields for new receipts. Does not rewrite historical bytes."""
    mid = str(message_id or "").strip() or None
    if mid:
        rid = mid
        source = "MESSAGE_ID"
    else:
        key = str(idempotency_key or "").strip()
        rid = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24] if key else None
        source = "IDEMPOTENCY_DIGEST_24"
    return {
        "receipt_id": rid,
        "message_id": mid,
        "RECEIPT_ID_EQUALS_MESSAGE_ID": bool(mid) and rid == mid,
        "RECEIPT_ID_SOURCE": source,
        "TASK_ID": task_id,
        "CORRELATION_ID": correlation_id,
    }
