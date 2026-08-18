"""D3 Failure Capture Kernel.

Every child/run failure becomes a typed receipt with bytes hashes,
returncode, encoding integrity, and a classifier hint. stdout is never
treated as success.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .certification import EvidenceLedger
from .config import deterministic_id, utc_now
from .process_kernel import KernelObservation


def classify_process_failure(obs: KernelObservation | None, error: str = "") -> str:
    blob = f"{error} {obs.integrity if obs else ''} {obs.stderr if obs else ''}".lower()
    if obs and obs.timed_out:
        return "CHILD_TIMEOUT"
    if "unicodedecode" in blob or (obs and obs.decode_replaced and "ENCODING_INTEGRITY" in error):
        return "UNICODE_DECODE"
    if obs and obs.decode_replaced:
        return "STDOUT_STDERR_INTEGRITY"
    if "none" in blob and ("stdout" in blob or "stderr" in blob):
        return "STREAM_NONE"
    if obs and obs.returncode != 0:
        return "CHILD_EXIT_NONZERO"
    if error:
        return "SECONDARY_EXCEPTION"
    return "UNCLASSIFIED"


class FailureCaptureKernel:
    def __init__(self, ledger: EvidenceLedger) -> None:
        self.ledger = ledger

    def capture(
        self,
        *,
        name: str,
        error: str,
        obs: KernelObservation | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Path:
        family = classify_process_failure(obs, error)
        payload = {
            "capture_id": deterministic_id("failcap", name, family, error[:80]),
            "name": name,
            "error": error,
            "family": family,
            "created_at": utc_now(),
            "observation": obs.to_dict() if obs else None,
            "stdout_never_none": obs is None or obs.stdout is not None,
            "stderr_never_none": obs is None or obs.stderr is not None,
            **(extra or {}),
        }
        return self.ledger.persist_failure(payload)
