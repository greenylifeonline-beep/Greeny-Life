"""Unified Control Plane dry-run adapter. A2A has no independent mutation authority."""

from __future__ import annotations

from typing import Any

from .failclosed import UNIFIED_CONTROL_PLANE_UNAVAILABLE, FailClosed
from .flags import A2A_EXTERNAL_MUTATION_ALLOWED

EXISTING_CONTROL_PLANE = ".ai-os/control/RAIOS-CONTROL-PLANE-V1.py"


class DryRunUCP:
    """In-process dry-run. Does not acquire live leases or start a second fabric."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.applied: dict[str, dict[str, Any]] = {}

    def submit(self, intent: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            raise FailClosed(UNIFIED_CONTROL_PLANE_UNAVAILABLE)
        if A2A_EXTERNAL_MUTATION_ALLOWED:
            raise FailClosed("RISK_POLICY_DENIED", "external-mutation-flag-must-remain-false")
        key = intent["IDEMPOTENCY_KEY"]
        existing = self.applied.get(key)
        desired = intent.get("DESIRED_STATE") or {}
        if existing is not None:
            if existing.get("DESIRED_STATE") == desired:
                return {"STATUS": "ALREADY_APPLIED", "NO_OP": True, "intent": existing, "EXECUTED": False}
            return {"STATUS": "ALREADY_APPLIED", "NO_OP": True, "intent": existing, "EXECUTED": False}
        record = dict(intent)
        record["UCP_MODE"] = "DRY_RUN"
        record["EXECUTED"] = False
        self.applied[key] = record
        return {"STATUS": "ACCEPTED_DRY_RUN", "NO_OP": False, "intent": record, "EXECUTED": False}
