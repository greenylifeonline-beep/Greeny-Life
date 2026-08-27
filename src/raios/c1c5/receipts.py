"""Bound task receipts. Reuses Command Fabric receipt directory; not a second WAL."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .receipt_identity import producer_receipt_identity

ROOT = Path(__file__).resolve().parents[3]
RECEIPT_DIR = ROOT / ".ai-os" / "receipts" / "command-fabric" / "c1c5-task"
EXISTING_RECEIPT_ROOT = ".ai-os/receipts/command-fabric"


def receipt_path(idempotency_key: str, *, directory: Path | None = None) -> Path:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
    base = directory or RECEIPT_DIR
    return base / f"{digest}.receipt.json"


def persist(receipt: dict[str, Any], *, directory: Path | None = None) -> Path:
    path = receipt_path(str(receipt["IDEMPOTENCY_KEY"]), directory=directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load(idempotency_key: str, *, directory: Path | None = None) -> dict[str, Any] | None:
    path = receipt_path(idempotency_key, directory=directory)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(
    *,
    env: dict[str, Any],
    auth: dict[str, Any],
    policy: dict[str, Any],
    ucp: dict[str, Any],
    capability: dict[str, Any] | None,
    status: str,
) -> dict[str, Any]:
    ident = producer_receipt_identity(
        message_id=env.get("message_id") if isinstance(env.get("message_id"), str) else None,
        task_id=env.get("task_id"),
        correlation_id=env.get("correlation_id"),
        idempotency_key=env.get("idempotency_key"),
    )
    return {
        "schema": "raios.c1c5.task-receipt.v1",
        "receipt_id": ident["receipt_id"],
        "message_id": ident["message_id"],
        "RECEIPT_ID_EQUALS_MESSAGE_ID": ident["RECEIPT_ID_EQUALS_MESSAGE_ID"],
        "RECEIPT_ID_SOURCE": ident["RECEIPT_ID_SOURCE"],
        "TASK_ID": env.get("task_id"),
        "CORRELATION_ID": env.get("correlation_id"),
        "IDEMPOTENCY_KEY": env.get("idempotency_key"),
        "ACTOR_BOUND": auth.get("PRINCIPAL"),
        "AUTHORITY_SOURCE": auth.get("AUTHORITY_SOURCE"),
        "TARGET": env.get("target"),
        "REQUESTED_CAPABILITY": env.get("requested_capability"),
        "AUTH_RESULT": {
            "EFFECTIVE_AUTHORITY": True,
            "AUTHORITY_SOURCE": auth.get("AUTHORITY_SOURCE"),
            "PRINCIPAL": auth.get("PRINCIPAL"),
        },
        "POLICY_RESULT": policy.get("POLICY_RESULT"),
        "RISK_CLASS": policy.get("RISK_CLASS"),
        "UCP_STATUS": ucp.get("STATUS"),
        "UCP_NO_OP": ucp.get("NO_OP"),
        "CAPABILITY_INVOKED": bool(capability and capability.get("INVOKED")),
        "STATUS": status,
        "TIMESTAMP": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "EVIDENCE_REFS": [EXISTING_RECEIPT_ROOT, "src/raios/a2a/ucp_adapter.py"],
        "WAL_WRITTEN": False,
        "CANONICAL_MUTATION": False,
    }


def is_bound(path: Path | None) -> bool:
    return bool(path and path.is_file())
