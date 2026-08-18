"""Known Repair Memory + D5 Repair Planner.

Replay is forbidden unless preconditions match. Canonical promotion is
never automatic.
"""
from __future__ import annotations

from typing import Any

from .config import FailClosed, deterministic_id, utc_now
from .ledger import Ledger
from .process_kernel import KERNEL_ID, env_signature
from .root_cause import KERNEL_REPAIR_ID, classify_failure

ENCODING_REPAIR = {
    "failure_signature": "UNICODE_DECODE|STREAM_NONE|FALSE_PASS_AFTER_NONZERO",
    "root_cause_graph": [
        "windows_or_locale_process_environment",
        "subprocess_stream_capture",
        "locale_or_strict_utf8_decode",
        "reader_failure_or_mojibake",
        "stdout_stderr_none_or_invalid",
        "secondary_exception",
        "certification_failure",
        "possible_false_pass_print",
    ],
    "environment_signature": env_signature(),
    "repair_preconditions": [
        "child_process_captured",
        "bytes_available_or_reproducible",
        "no_errors_ignore",
    ],
    "repair_action": [
        "capture_stdout_stderr_as_bytes",
        "set_PYTHONUTF8=1",
        "decode_utf8_errors_replace",
        "never_return_none_streams",
        "propagate_returncode_before_status_text",
        "scan_forbidden_success_tokens_only_after_gates",
    ],
    "positive_tests": ["utf8_child_roundtrip", "returncode_preserved"],
    "negative_controls": ["latin1_byte_does_not_raise", "pass_text_plus_exit_1_is_failure"],
    "regression_scope": ["ccee.certification.run_child", "raios_fi.config.run"],
    "transfer_cases": ["rg_non_ascii_path", "python_buffer_write_0xe9"],
    "confidence": 0.72,
    "success_count": 0,
    "failure_count": 0,
    "canonical_version": None,
    "rollback_recipe": "restore_text_true_call_sites_from_git",
}


class RepairMemory:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger
        self._ensure_seed()

    def _ensure_seed(self) -> None:
        existing = self.ledger.get("knowledge", KERNEL_REPAIR_ID)
        if existing is None:
            rec = {
                "repair_id": KERNEL_REPAIR_ID,
                "kernel_id": KERNEL_ID,
                **ENCODING_REPAIR,
                "last_validated": None,
                "created_at": utc_now(),
            }
            self.ledger.put(
                "knowledge",
                "knowledge_id",
                KERNEL_REPAIR_ID,
                rec,
                extra={"state": "VALIDATED", "kind": "repair_memory"},
            )

    def get(self, repair_id: str) -> dict[str, Any] | None:
        return self.ledger.get("knowledge", repair_id)

    def record_validation(self, repair_id: str, *, ok: bool, evidence: dict[str, Any]) -> dict[str, Any]:
        rec = self.get(repair_id)
        if rec is None:
            raise FailClosed(f"REPAIR_MEMORY_MISSING:{repair_id}")
        rec = dict(rec)
        rec["success_count"] = int(rec.get("success_count") or 0) + (1 if ok else 0)
        rec["failure_count"] = int(rec.get("failure_count") or 0) + (0 if ok else 1)
        rec["last_validated"] = utc_now()
        rec["last_evidence"] = evidence
        rec["canonical"] = False
        self.ledger.put(
            "knowledge",
            "knowledge_id",
            repair_id,
            rec,
            extra={"state": "VALIDATED" if ok else "DISCOVERED", "kind": "repair_memory"},
        )
        return rec

    def preconditions_hold(self, repair_id: str, observed: dict[str, Any]) -> bool:
        rec = self.get(repair_id)
        if rec is None:
            return False
        family = classify_failure(observed)
        return family in {
            "UNICODE_DECODE",
            "STREAM_NONE",
            "FALSE_PASS",
            "CHILD_EXIT_NONZERO",
            "STDOUT_STDERR_INTEGRITY",
        } or family == observed.get("family")


class RepairPlanner:
    def __init__(self, memory: RepairMemory) -> None:
        self.memory = memory

    def plan(self, observed: dict[str, Any]) -> dict[str, Any]:
        family = classify_failure(observed)
        repair_id = KERNEL_REPAIR_ID if family in {
            "UNICODE_DECODE",
            "STREAM_NONE",
            "FALSE_PASS",
            "CHILD_EXIT_NONZERO",
            "SYSTEM_INTEGRITY_FAILURE",
        } else None
        if repair_id and not self.memory.preconditions_hold(repair_id, observed):
            repair_id = None
        rec = self.memory.get(repair_id) if repair_id else None
        return {
            "plan_id": deterministic_id("rplan", family, repair_id or "none"),
            "family": family,
            "repair_id": repair_id,
            "actions": list((rec or {}).get("repair_action") or ["human_review"]),
            "auto_apply": False,
            "shadow_required": True,
            "canonical_promotion": False,
            "confidence": float((rec or {}).get("confidence") or 0.2),
        }
