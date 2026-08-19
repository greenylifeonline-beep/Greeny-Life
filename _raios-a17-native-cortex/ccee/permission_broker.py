"""Permission Broker + Approval Envelope + Permission Leasing.

LOW-risk read/test/evidence leases are granted. HIGH/CRITICAL and
canonical mutation stay fail-closed until D11 READY plus human approval.
Reuses Exchange V2 lease vocabulary without duplicating CAS authority.
"""
from __future__ import annotations

from typing import Any

from .config import FailClosed, deterministic_id, utc_now
from .ledger import Ledger
from .work_gate import READY, WorkGate

LOW = "LOW"
HIGH = "HIGH"
CRITICAL = "CRITICAL"


class PermissionBroker:
    def __init__(self, ledger: Ledger, gate: WorkGate) -> None:
        self.ledger = ledger
        self.gate = gate

    def request_lease(
        self,
        *,
        scope: list[str],
        duration_s: int,
        risk: str,
        purpose: str,
        mutating: bool = False,
    ) -> dict[str, Any]:
        if risk not in {LOW, HIGH, CRITICAL}:
            raise FailClosed(f"UNKNOWN_RISK:{risk}")
        if mutating and risk == LOW:
            raise FailClosed("MUTATION_IS_NOT_LOW_RISK")
        if risk in {HIGH, CRITICAL} or mutating:
            state = self.gate.read().get("state")
            if state == READY and mutating:
                raise FailClosed("HUMAN_APPROVAL_REQUIRED")
            raise FailClosed("LEASE_DENIED:" + risk)
        lease = {
            "lease_id": deterministic_id("lease", purpose, ",".join(scope)),
            "scope": scope,
            "duration_s": int(duration_s),
            "risk": risk,
            "purpose": purpose,
            "mutating": False,
            "state": "GRANTED",
            "created_at": utc_now(),
            "envelope": "raios.approval-envelope.v1",
        }
        self.ledger.put(
            "knowledge",
            "knowledge_id",
            lease["lease_id"],
            lease,
            extra={"state": "VALIDATED", "kind": "permission_lease"},
        )
        return lease
