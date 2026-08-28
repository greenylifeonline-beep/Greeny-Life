"""Canonical governed task-submission seam for RAIOS.

registered task
→ semantic task/capability authorization
→ authenticated submission
→ existing Command Fabric

No second scheduler, task store, UCP, transport, lease system, receipt
system, or mutation authority is introduced here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from raios.command_fabric import execute as command_execute
from raios.command_fabric.lease import CommandLeaseAdapter
from raios.a2a.ucp_adapter import DryRunUCP


TASKS_STATE = Path(".ai-os/state/TASKS.json")

EXECUTABLE_STATES = {
    "READY",
    "IN_PROGRESS",
    "ACTIVE",
}

C5_READ_ONLY_CAPABILITIES = {
    "c5.self_inspect.health",
}

C5_ALLOWED_SCOPES = {
    ".ai-os",
    "intelligence",
    "governance",
    "brains",
}


class TaskSubmissionError(RuntimeError):
    pass


@dataclass(frozen=True)
class OrchestrationTask:
    task_id: str
    correlation_id: str
    idempotency_key: str
    target: str
    requested_capability: str
    authenticated_principal_ref: str
    authority_context_reference: str
    submitting_agent: str = "chatgpt-main-brain"

    def as_envelope(self) -> dict[str, str]:
        return {
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "idempotency_key": self.idempotency_key,
            "target": self.target,
            "requested_capability": self.requested_capability,
            "authenticated_principal_ref": self.authenticated_principal_ref,
            "authority_context_reference": self.authority_context_reference,
        }


def _load_tasks(tasks_path: Path = TASKS_STATE) -> Any:
    if not tasks_path.is_file():
        raise TaskSubmissionError(f"TASK_REGISTRY_NOT_FOUND:{tasks_path}")

    return json.loads(tasks_path.read_text(encoding="utf-8-sig"))


def _find_task_record(node: Any, task_id: str) -> Mapping[str, Any] | None:
    if isinstance(node, Mapping):
        direct = None

        for key in ("task_id", "TASK_ID", "id", "ID"):
            if key in node and str(node[key]) == task_id:
                direct = node
                break

        if direct is not None:
            return direct

        for value in node.values():
            found = _find_task_record(value, task_id)
            if found is not None:
                return found

    elif isinstance(node, list):
        for value in node:
            found = _find_task_record(value, task_id)
            if found is not None:
                return found

    return None


def get_registered_task(
    task_id: str,
    tasks_path: Path = TASKS_STATE,
) -> Mapping[str, Any] | None:
    if not task_id:
        return None

    return _find_task_record(_load_tasks(tasks_path), task_id)


def task_is_registered(
    task_id: str,
    tasks_path: Path = TASKS_STATE,
) -> bool:
    return get_registered_task(task_id, tasks_path) is not None


def authorize_task_capability(
    task: OrchestrationTask,
    *,
    tasks_path: Path = TASKS_STATE,
) -> dict[str, Any]:
    record = get_registered_task(task.task_id, tasks_path)

    if record is None:
        raise TaskSubmissionError(f"TASK_NOT_REGISTERED:{task.task_id}")

    status = str(
        record.get("status")
        or record.get("state")
        or ""
    ).upper()

    if status not in EXECUTABLE_STATES:
        raise TaskSubmissionError(
            f"TASK_NOT_EXECUTABLE:{task.task_id}:{status}"
        )

    allowed_agents = {
        str(value)
        for value in record.get("allowed_agents", [])
    }

    if allowed_agents and task.submitting_agent not in allowed_agents:
        raise TaskSubmissionError(
            f"SUBMITTING_AGENT_NOT_ALLOWED:{task.submitting_agent}"
        )

    scope = {
        str(value)
        for value in record.get("scope", [])
    }

    if (
        task.target == "C5"
        and task.requested_capability in C5_READ_ONLY_CAPABILITIES
    ):
        if not scope.intersection(C5_ALLOWED_SCOPES):
            raise TaskSubmissionError(
                f"TASK_SCOPE_NOT_AUTHORIZED:"
                f"{task.task_id}:{task.requested_capability}"
            )

        return {
            "AUTHORIZED": True,
            "TASK_ID": task.task_id,
            "TASK_STATUS": status,
            "TARGET": task.target,
            "CAPABILITY": task.requested_capability,
            "SUBMITTING_AGENT": task.submitting_agent,
            "MATCHED_SCOPE": sorted(
                scope.intersection(C5_ALLOWED_SCOPES)
            ),
            "RISK_CLASS": "LOW",
            "MODE": "READ_ONLY",
        }

    raise TaskSubmissionError(
        f"TASK_CAPABILITY_BINDING_NOT_DEFINED:"
        f"{task.task_id}:{task.target}:{task.requested_capability}"
    )


def submit_authenticated_task(
    task: OrchestrationTask,
    *,
    session: Mapping[str, Any],
    leases: CommandLeaseAdapter,
    transport: Any | None = None,
    ucp: DryRunUCP | None = None,
    health: Callable[[], dict[str, Any]] | None = None,
    nats_available: bool = True,
    force_duplicate_delivery: bool = False,
    ttl_seconds: int = 120,
    executor: Callable[..., dict[str, Any]] = command_execute,
) -> dict[str, Any]:
    if not task.task_id:
        raise TaskSubmissionError("TASK_ID_REQUIRED")

    if not task.correlation_id:
        raise TaskSubmissionError("CORRELATION_ID_REQUIRED")

    if not task.idempotency_key:
        raise TaskSubmissionError("IDEMPOTENCY_KEY_REQUIRED")

    if not task.authenticated_principal_ref:
        raise TaskSubmissionError(
            "AUTHENTICATED_PRINCIPAL_REQUIRED"
        )

    if not task.authority_context_reference:
        raise TaskSubmissionError(
            "AUTHORITY_CONTEXT_REQUIRED"
        )

    authorization = authorize_task_capability(task)

    if not session:
        raise TaskSubmissionError("AUTHENTICATED_SESSION_REQUIRED")

    result = executor(
        env=task.as_envelope(),
        session=dict(session),
        leases=leases,
        transport=transport,
        ucp=ucp or DryRunUCP(),
        health=health,
        nats_available=nats_available,
        force_duplicate_delivery=force_duplicate_delivery,
        ttl_seconds=ttl_seconds,
    )

    return {
        "schema": "raios.orchestration.task-submission.v1",
        "task_id": task.task_id,
        "registered_task": True,
        "semantic_authorization": authorization,
        "authenticated_submission": True,
        "delegated_to_command_fabric": True,
        "second_task_store": False,
        "second_scheduler": False,
        "second_transport": False,
        "second_ucp": False,
        "second_lease_system": False,
        "second_receipt_system": False,
        "result": result,
    }

