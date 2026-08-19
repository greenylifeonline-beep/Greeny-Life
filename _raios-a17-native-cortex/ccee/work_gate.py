"""D11 Final Work Authorization.

Printed text is never evidence. Only the run supervisor may change this
gate, and only after machine-readable receipts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import FailClosed, canonical_json, sha256_text, utc_now

CLOSED = "CLOSED"
DEGRADED = "DEGRADED_DIAGNOSTIC_ACTIVE"
READY = "READY_FOR_REAL_PROJECT_WORK"
SCHEMA = "raios.d11.work_gate.v1"


class WorkGate:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.is_file():
            self._write(self._body(CLOSED, "NOT_READY_FOR_REAL_PROJECT_WORK", ["UNINITIALIZED"], {}))

    def _body(self, state: str, semantic: str, reasons: list[str], components: dict[str, Any]) -> dict[str, Any]:
        body = {
            "schema": SCHEMA,
            "state": state,
            "semantic": semantic,
            "reasons": reasons,
            "components": components,
            "supervisor": "ccee.run_supervisor",
            "created_at": utc_now(),
            "canonical": False,
        }
        body["sha256"] = sha256_text(canonical_json({k: v for k, v in body.items() if k != "sha256"}))
        return body

    def _write(self, body: dict[str, Any]) -> dict[str, Any]:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(canonical_json(body) + "\n", encoding="utf-8")
        tmp.replace(self.path)
        readback = json.loads(self.path.read_text(encoding="utf-8"))
        if readback.get("sha256") != body.get("sha256"):
            raise FailClosed("WORK_GATE_READBACK_FAILED")
        return readback

    def read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def close(self, reasons: list[str], components: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._write(self._body(CLOSED, "NOT_READY_FOR_REAL_PROJECT_WORK", reasons, components or {}))

    def set_degraded(self, reasons: list[str], components: dict[str, Any]) -> dict[str, Any]:
        return self._write(self._body(DEGRADED, "NOT_READY_FOR_REAL_PROJECT_WORK", reasons, components))

    def open_ready(self, components: dict[str, Any]) -> dict[str, Any]:
        missing = [k for k, v in components.items() if not v]
        if missing:
            raise FailClosed("WORK_GATE_OPEN_FORBIDDEN:" + ",".join(missing))
        return self._write(self._body(READY, READY, [], components))
