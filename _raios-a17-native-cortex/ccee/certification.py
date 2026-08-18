"""A17.13 forensic repair: fail-closed certification. False PASS is impossible."""
from __future__ import annotations

import json
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any, Callable

from .config import (
    FORBIDDEN_SUCCESS_TOKENS,
    FailClosed,
    assert_not_v9,
    canonical_json,
    contains_forbidden_success,
    deterministic_id,
    sha256_text,
    utc_now,
)

GateFn = Callable[["AssertionRegistry"], Any]


class AssertionRegistry:
    def __init__(self) -> None:
        self.gates: dict[str, dict[str, Any]] = {}

    def require(self, name: str, ok: bool, reason: str = "") -> None:
        self.gates[name] = {"ok": bool(ok), "reason": reason, "mandatory": True, "at": utc_now()}
        if not ok:
            raise FailClosed(f"MANDATORY_GATE_FAILED:{name}:{reason}")

    def observe(self, name: str, ok: bool, reason: str = "") -> None:
        self.gates[name] = {"ok": bool(ok), "reason": reason, "mandatory": False, "at": utc_now()}

    def all_mandatory_passed(self) -> bool:
        mand = [g for g in self.gates.values() if g["mandatory"]]
        return bool(mand) and all(g["ok"] for g in mand)

    def failed(self) -> list[str]:
        return [n for n, g in self.gates.items() if g["mandatory"] and not g["ok"]]


class FalsePassDetector:
    def scan(self, text: str, *, gates_complete: bool) -> None:
        hits = contains_forbidden_success(text)
        if hits and not gates_complete:
            raise FailClosed("FALSE_PASS_DETECTED:" + ",".join(hits))

    def scan_bytes(self, data: bytes, *, gates_complete: bool) -> None:
        self.scan(data.decode("utf-8", errors="replace"), gates_complete=gates_complete)


class ExitCodePropagator:
    def check(self, completed: subprocess.CompletedProcess[str], name: str = "child") -> None:
        if completed.returncode != 0:
            raise FailClosed(f"CHILD_EXIT_NONZERO:{name}:{completed.returncode}")


class EvidenceLedger:
    def __init__(self, evidence_root: str | Path, repo_root: Path | None = None) -> None:
        self.root = Path(evidence_root)
        assert_not_v9(self.root, repo_root)
        for part in ("failures", "successes", "lineage"):
            (self.root / part).mkdir(parents=True, exist_ok=True)

    def persist_failure(self, payload: dict[str, Any]) -> Path:
        return self._write("failures", payload, kind="failure")

    def persist_success(self, payload: dict[str, Any], registry: AssertionRegistry) -> Path:
        if not registry.all_mandatory_passed():
            raise FailClosed("SUCCESS_RECEIPT_FORBIDDEN")
        return self._write("successes", payload, kind="success")

    def _write(self, folder: str, payload: dict[str, Any], kind: str) -> Path:
        body = {**payload, "kind": kind, "created_at": utc_now(), "canonical": False}
        text = canonical_json(body)
        digest = sha256_text(text)
        body["sha256"] = digest
        text = canonical_json(body)
        digest = sha256_text(text)
        body["sha256"] = digest
        path = self.root / folder / f"{kind}-{digest[:16]}.json"
        path.write_text(canonical_json(body), encoding="utf-8")
        lineage = {
            "artifact": str(path),
            "sha256": digest,
            "kind": kind,
            "created_at": body["created_at"],
        }
        (self.root / "lineage" / f"{digest[:16]}.json").write_text(canonical_json(lineage), encoding="utf-8")
        return path

    def has_success(self) -> bool:
        return any((self.root / "successes").glob("success-*.json"))

    def reject_stale_success(self, path: Path, current_run_id: str) -> None:
        if not path.is_file():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("run_id") != current_run_id:
            raise FailClosed("STALE_SUCCESS_RECEIPT")


class FailureAwareRunner:
    def __init__(self, ledger: EvidenceLedger, detector: FalsePassDetector | None = None) -> None:
        self.ledger = ledger
        self.detector = detector or FalsePassDetector()

    def run(self, name: str, fn: GateFn) -> dict[str, Any]:
        registry = AssertionRegistry()
        buf = StringIO()
        try:
            with redirect_stdout(buf):
                result = fn(registry)
            self.detector.scan(buf.getvalue(), gates_complete=registry.all_mandatory_passed())
            if not registry.all_mandatory_passed():
                raise FailClosed("MANDATORY_GATES_INCOMPLETE")
            return {"ok": True, "name": name, "result": result, "stdout": buf.getvalue(), "registry": registry}
        except Exception as exc:
            receipt = {
                "name": name,
                "error": f"{type(exc).__name__}:{exc}",
                "stdout": buf.getvalue(),
                "gates": registry.gates,
            }
            path = self.ledger.persist_failure(receipt)
            self.detector.scan(buf.getvalue(), gates_complete=False)
            raise FailClosed(f"RUN_FAILED:{name}:{exc}:receipt={path.name}") from exc


class AtomicCertificationRunner:
    def __init__(self, ledger: EvidenceLedger) -> None:
        self.ledger = ledger
        self.detector = FalsePassDetector()
        self.propagator = ExitCodePropagator()
        self.aware = FailureAwareRunner(ledger, self.detector)

    def certify(self, name: str, fn: GateFn, run_id: str) -> dict[str, Any]:
        try:
            outcome = self.aware.run(name, fn)
        except FailClosed as exc:
            # success receipt is forbidden; do not emit success tokens
            return {
                "ok": False,
                "overall_status": "FAILED",
                "exit_code": 1,
                "error": str(exc),
                "success_receipt": False,
                "forbidden_tokens_emitted": False,
            }
        success = {
            "name": name,
            "run_id": run_id,
            "gates": outcome["registry"].gates,
            "overall_status": "GATES_SATISFIED",
        }
        path = self.ledger.persist_success(success, outcome["registry"])
        return {
            "ok": True,
            "overall_status": "GATES_SATISFIED",
            "exit_code": 0,
            "success_receipt": str(path),
            "stdout": outcome["stdout"],
        }

    def run_child(self, argv: list[str], cwd: str | Path | None = None, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
        try:
            completed = subprocess.run(
                argv,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            self.ledger.persist_failure({"name": "timeout", "argv": argv, "error": "TIMEOUT"})
            raise FailClosed("CHILD_TIMEOUT") from exc
        self.detector.scan(completed.stdout + completed.stderr, gates_complete=completed.returncode == 0)
        self.propagator.check(completed)
        return completed
