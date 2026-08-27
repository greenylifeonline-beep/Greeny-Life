"""Map A2A task/message/artifact identifiers onto RAIOS intent fields. Does not replace existing IDs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def build_intent(
    *,
    a2a_task_id: str,
    a2a_context_id: str,
    actor: str,
    capability_id: str,
    desired_state: dict[str, Any],
    risk_class: str,
    idempotency_key: str,
    target_selector: str = "raios.foundation.local-dry-run",
) -> dict[str, Any]:
    correlation = a2a_context_id or a2a_task_id
    command_id = f"CMD-A2A-{hashlib.sha256(f'{a2a_task_id}:{idempotency_key}'.encode()).hexdigest()[:16]}"
    change_id = f"CHG-A2A-{hashlib.sha256(json.dumps(desired_state, sort_keys=True).encode()).hexdigest()[:16]}"
    return {
        "COMMAND_ID": command_id,
        "CHANGE_ID": change_id,
        "CORRELATION_ID": correlation,
        "IDEMPOTENCY_KEY": idempotency_key,
        "ACTOR": actor,
        "INTENT": capability_id,
        "TARGET_SELECTOR": target_selector,
        "DESIRED_STATE": desired_state,
        "RISK_CLASS": risk_class,
        "CREATED_AT": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "A2A_TASK_ID": a2a_task_id,
        "A2A_CONTEXT_ID": a2a_context_id,
        "secrets": None,
    }


def new_ids() -> tuple[str, str]:
    return str(uuid4()), str(uuid4())


def map_message(*, a2a_message_id: str, a2a_context_id: str, text: str | None = None) -> dict[str, Any]:
    return {
        "A2A_MESSAGE_ID": a2a_message_id,
        "CORRELATION_ID": a2a_context_id,
        "KIND": "A2A_MESSAGE",
        "text": text,
        "secrets": None,
    }


def map_artifact(*, a2a_artifact_id: str, a2a_task_id: str, a2a_context_id: str) -> dict[str, Any]:
    return {
        "A2A_ARTIFACT_ID": a2a_artifact_id,
        "A2A_TASK_ID": a2a_task_id,
        "CORRELATION_ID": a2a_context_id,
        "KIND": "A2A_ARTIFACT",
        "secrets": None,
    }
