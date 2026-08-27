"""Receipt/evidence mapping. Reuses Command Fabric receipt concept; does not create a second WAL."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

EXISTING_RECEIPT_DIR = ".ai-os/receipts/command-fabric"


def build_receipt(
    *,
    a2a_task_id: str,
    a2a_context_id: str,
    intent: dict[str, Any],
    capability_id: str,
    semantic_contract_id: str,
    semantic_fingerprint: str,
    auth_result: dict[str, Any],
    policy_result: dict[str, Any],
    status: str,
    evidence_refs: list[str],
    pre_hash: str = "NOT_APPLICABLE",
    post_hash: str = "NOT_APPLICABLE",
    rollback: bool = False,
) -> dict[str, Any]:
    return {
        "A2A_TASK_ID": a2a_task_id,
        "A2A_CONTEXT_ID": a2a_context_id,
        "COMMAND_ID": intent.get("COMMAND_ID"),
        "CHANGE_ID": intent.get("CHANGE_ID"),
        "CORRELATION_ID": intent.get("CORRELATION_ID"),
        "ACTOR": intent.get("ACTOR"),
        "AGENT_ID": intent.get("ACTOR"),
        "CAPABILITY_ID": capability_id,
        "SEMANTIC_CONTRACT_ID": semantic_contract_id,
        "SEMANTIC_FINGERPRINT": semantic_fingerprint,
        "AUTH_RESULT": auth_result,
        "POLICY_RESULT": policy_result.get("POLICY_RESULT"),
        "RISK_CLASS": policy_result.get("RISK_CLASS"),
        "TARGET": intent.get("TARGET_SELECTOR"),
        "PRE_STATE_HASH": pre_hash,
        "ACTION": intent.get("INTENT"),
        "POST_STATE_HASH": post_hash,
        "STATUS": status,
        "TIMESTAMP": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "EVIDENCE_REFS": evidence_refs,
        "ROLLBACK_AVAILABLE": rollback,
    }
