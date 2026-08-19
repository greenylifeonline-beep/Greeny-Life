"""D10 governed executor bridge.

Reuses permission leases, D1 kernel, CognitiveTurn envelope, and Exchange
V2 task/lease vocabulary. Does not duplicate the Communication Fabric.
Does not open WORK_GATE. Does not log credentials.
"""
from __future__ import annotations

import os
import shutil
from typing import Any

from .config import FailClosed, canonical_json, deterministic_id, sha256_obj, utc_now
from .cursor_probe import probe_clients
from .process_kernel import encoding_safe_run
from .work_gate import READY

STATES = (
    "CREATED",
    "ADMITTED",
    "LEASED",
    "ACK",
    "RUNNING",
    "VERIFYING",
    "COMPLETED",
    "FAILED",
    "BLOCKED",
    "PERMISSION_DENIED",
)

# Reuse Exchange V2 lease words without importing that package (ChatGPT fabric track).
LEASE_MODE_READ_VERIFY = "READ_VERIFY"
LEASE_MODE_WRITE = "WRITE"


def discover_executors() -> dict[str, Any]:
    probe = probe_clients()
    gh = shutil.which("gh")
    copilot = shutil.which("copilot")
    gh_copilot = {"available": False, "returncode": None, "stderr_sha256": None, "reason": "GH_MISSING"}
    gh_version = None
    if gh:
        ver = encoding_safe_run([gh, "--version"], timeout=15.0)
        gh_version = {
            "returncode": ver.returncode,
            "stdout_sha256": ver.stdout_sha256,
            "integrity": ver.integrity,
            "preview": ver.stdout.splitlines()[:3],
        }
        help_obs = encoding_safe_run([gh, "copilot", "--help"], timeout=15.0)
        unknown = "unknown command" in (help_obs.stderr + help_obs.stdout).lower()
        gh_copilot = {
            "available": help_obs.returncode == 0 and not unknown,
            "returncode": help_obs.returncode,
            "stdout_sha256": help_obs.stdout_sha256,
            "stderr_sha256": help_obs.stderr_sha256,
            "reason": None if help_obs.returncode == 0 and not unknown else "GH_COPILOT_SUBCOMMAND_UNAVAILABLE",
            "invocation": "gh copilot" if help_obs.returncode == 0 and not unknown else None,
        }
    secret_keys = [k for k in os.environ if any(s in k.upper() for s in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"))]
    return {
        "cursor": probe,
        "gh_path": gh,
        "gh_version": gh_version,
        "copilot_which": copilot,
        "gh_copilot": gh_copilot,
        "credential_env_names_redacted": True,
        "credential_env_count": len(secret_keys),
        "created_at": utc_now(),
        "invocation_authorized": False,
    }


class GovernedExecutorBridge:
    def __init__(self, broker: Any, gate: Any, bus: Any, ledger: Any) -> None:
        self.broker = broker
        self.gate = gate
        self.bus = bus
        self.ledger = ledger

    def _idempotency_key(self, envelope: dict[str, Any]) -> str:
        return deterministic_id(
            "exid",
            str(envelope.get("task_id") or ""),
            str(envelope.get("attempt") or 1),
            str(envelope.get("intent") or ""),
            str(envelope.get("target") or ""),
        )

    def dispatch(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if envelope.get("execution_authority") is True:
            raise FailClosed("MODEL_OUTPUT_HAS_NO_AUTHORITY")
        mutating = bool(envelope.get("mutating"))
        risk = str(envelope.get("risk") or ("HIGH" if mutating else "LOW"))
        target = str(envelope.get("target") or "cursor")
        intent = str(envelope.get("intent") or "observe")
        task_id = str(envelope.get("task_id") or "GL-EX")
        attempt = int(envelope.get("attempt") or 1)
        correlation_id = str(envelope.get("correlation_id") or deterministic_id("corr", task_id, str(attempt)))
        key = self._idempotency_key({**envelope, "task_id": task_id, "attempt": attempt, "intent": intent, "target": target})
        existing = self.ledger.get("knowledge", key)
        if existing and existing.get("kind") == "executor_receipt":
            return existing

        states = ["CREATED"]
        self.bus.emit("TASK_RECEIVED", "executor_bridge", {"task_id": task_id, "correlation_id": correlation_id, "target": target})
        states.append("ADMITTED")

        if mutating or risk in {"HIGH", "CRITICAL"}:
            receipt = self._receipt(
                envelope,
                correlation_id,
                key,
                states + ["PERMISSION_DENIED"],
                ok=False,
                reason="LEASE_DENIED_OR_HUMAN_APPROVAL_REQUIRED",
                lease=None,
                discovery=discover_executors(),
            )
            try:
                self.broker.request_lease(
                    scope=list(envelope.get("permission_scope") or ["executor observe"]),
                    duration_s=int(envelope.get("deadline_s") or 600),
                    risk=risk if risk in {"LOW", "HIGH", "CRITICAL"} else "HIGH",
                    purpose=f"{task_id}:{intent}",
                    mutating=mutating,
                )
            except FailClosed as exc:
                receipt["result"]["error"] = str(exc)
            self._persist(key, receipt)
            self.bus.emit("TASK_FAILED", "executor_bridge", {"task_id": task_id, "reason": receipt["result"]["reason"]})
            return receipt

        lease = self.broker.request_lease(
            scope=list(envelope.get("permission_scope") or ["executor observe", "cli version probe"]),
            duration_s=int(envelope.get("deadline_s") or 600),
            risk="LOW",
            purpose=f"{task_id}:{intent}",
            mutating=False,
        )
        states.extend(["LEASED", "ACK"])
        self.bus.emit("TOOL_CALL", "executor_bridge", {"state": "ACK", "lease_id": lease["lease_id"], "correlation_id": correlation_id})
        states.append("RUNNING")
        discovery = discover_executors()
        gate_state = self.gate.read().get("state")
        if gate_state == READY:
            # READY still does not auto-invoke mutating tools. Observe-only version probe is the allowed action.
            action = "observe_only_despite_ready"
        else:
            action = "observe_only_work_gate_not_ready"

        files_touched: list[str] = []
        tests: dict[str, Any] = {"ran": False, "reason": "OBSERVE_ONLY"}
        states.append("VERIFYING")
        states.append("COMPLETED")
        receipt = self._receipt(
            envelope,
            correlation_id,
            key,
            states,
            ok=True,
            reason=action,
            lease=lease,
            discovery=discovery,
            extra={
                "files_touched": files_touched,
                "tests": tests,
                "lease_mode": LEASE_MODE_READ_VERIFY,
                "work_gate": gate_state,
                "permanent_permission": False,
                "credentials_exposed": False,
            },
        )
        # Observe-only is not a supervisor PASS. ok means envelope completed without mutation.
        receipt["overall_status"] = "STRUCTURED"
        receipt["canonical"] = False
        self._persist(key, receipt)
        self.bus.emit("TASK_COMPLETED", "executor_bridge", {"task_id": task_id, "correlation_id": correlation_id, "mutating": False})
        return receipt

    def _receipt(
        self,
        envelope: dict[str, Any],
        correlation_id: str,
        key: str,
        states: list[str],
        *,
        ok: bool,
        reason: str,
        lease: dict[str, Any] | None,
        discovery: dict[str, Any],
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = {
            "schema": "raios.executor-receipt.v1",
            "kind": "executor_receipt",
            "receipt_id": key,
            "correlation_id": correlation_id,
            "causal_parent": envelope.get("causal_parent"),
            "task_id": envelope.get("task_id"),
            "attempt": envelope.get("attempt") or 1,
            "actor": envelope.get("actor") or "RAIOS",
            "target": envelope.get("target") or "cursor",
            "intent": envelope.get("intent"),
            "states": states,
            "lease": {"lease_id": lease["lease_id"], "state": lease.get("state"), "mode": LEASE_MODE_READ_VERIFY} if lease else None,
            "discovery": discovery,
            "result": {"ok": ok, "reason": reason, **(extra or {})},
            "overall_status": "STRUCTURED" if ok else "FAILED",
            "created_at": utc_now(),
            "canonical": False,
        }
        body["sha256"] = sha256_obj({k: v for k, v in body.items() if k != "sha256"})
        return body

    def _persist(self, key: str, receipt: dict[str, Any]) -> None:
        self.ledger.put(
            "knowledge",
            "knowledge_id",
            key,
            receipt,
            extra={"state": "DISCOVERED", "kind": "executor_receipt"},
        )
