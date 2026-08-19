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


ALLOWED_OVERALL = {
    "GATES_SATISFIED",
    "FAILED",
    "STRUCTURED",
    "DEGRADED_DIAGNOSTIC_ACTIVE",
}

CERT_CLAIM_KEYS = ("WAVE_CERTIFICATION", "FILE_INTELLIGENCE", "UNIT_TESTS")


def structured_child_allowed(stdout: str, returncode: int) -> bool:
    """JSON claim maps may contain PASS labels. Bare print('PASS') may not."""
    try:
        data = json.loads(stdout.strip())
    except (json.JSONDecodeError, ValueError, TypeError):
        return False
    if not isinstance(data, dict):
        return False
    overall = data.get("overall_status")
    if overall in {"PASS", "SUCCESS", "CERTIFIED", "PROVEN", "COMPLETE"}:
        return False
    coded = data.get("exit_code")
    if coded is not None and int(coded) != int(returncode):
        return False
    if overall in ALLOWED_OVERALL:
        return True
    wave = next((data.get(k) for k in CERT_CLAIM_KEYS if k in data), None)
    if wave == "PASS":
        return int(returncode) == 0
    if wave == "FAIL":
        return int(returncode) != 0
    return False


class AuthoritativeVerdict:
    """Printed text is never authority. One certification model for CCEE."""

    def __init__(self, **fields: Any) -> None:
        self.exit_code = int(fields.get("exit_code") if fields.get("exit_code") is not None else 1)
        self.artifact_exists = bool(fields.get("artifact_exists"))
        self.artifact_valid = bool(fields.get("artifact_valid"))
        self.hash_stable = bool(fields.get("hash_stable"))
        self.tests_ok = bool(fields.get("tests_ok"))
        self.upstream_ok = bool(fields.get("upstream_ok"))
        self.no_critical_contradiction = bool(fields.get("no_critical_contradiction"))
        self.gates_complete = bool(fields.get("gates_complete"))
        self.printed_success_tokens = list(fields.get("printed_success_tokens") or [])
        self.reason = str(fields.get("reason") or "")

    @property
    def ok(self) -> bool:
        if self.printed_success_tokens and not self.gates_complete:
            return False
        return (
            self.exit_code == 0
            and self.artifact_exists
            and self.artifact_valid
            and self.hash_stable
            and self.tests_ok
            and self.upstream_ok
            and self.no_critical_contradiction
            and self.gates_complete
        )

    def overall_status(self) -> str:
        return "GATES_SATISFIED" if self.ok else "FAILED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "overall_status": self.overall_status(),
            "exit_code": 0 if self.ok else (self.exit_code if self.exit_code != 0 else 1),
            "artifact_exists": self.artifact_exists,
            "artifact_valid": self.artifact_valid,
            "hash_stable": self.hash_stable,
            "tests_ok": self.tests_ok,
            "upstream_ok": self.upstream_ok,
            "no_critical_contradiction": self.no_critical_contradiction,
            "gates_complete": self.gates_complete,
            "printed_success_tokens": self.printed_success_tokens,
            "reason": self.reason,
        }


class FalsePassDetector:
    def scan(self, text: str, *, gates_complete: bool) -> None:
        hits = contains_forbidden_success(text)
        if hits and not gates_complete:
            raise FailClosed("FALSE_PASS_DETECTED:" + ",".join(hits))

    def scan_bytes(self, data: bytes, *, gates_complete: bool) -> None:
        self.scan(data.decode("utf-8", errors="replace"), gates_complete=gates_complete)

    def judge_child(self, stdout: str, stderr: str, returncode: int) -> None:
        """Child stdout is never a supervisor PASS. Exit 0 does not complete gates."""
        text = f"{stdout}{stderr}"
        hits = contains_forbidden_success(text)
        if hits and int(returncode) != 0:
            raise FailClosed("FALSE_PASS_DETECTED:PASS")
        if hits and int(returncode) == 0 and not structured_child_allowed(stdout, returncode):
            raise FailClosed("FALSE_PASS_DETECTED:BARE_PASS_EXIT_0")
        if int(returncode) != 0:
            raise FailClosed(f"CHILD_EXIT_NONZERO:child:{returncode}")

    def verdict(self, **fields: Any) -> AuthoritativeVerdict:
        printed = list(fields.get("printed_success_tokens") or contains_forbidden_success(str(fields.get("stdout") or "")))
        verdict = AuthoritativeVerdict(**{**fields, "printed_success_tokens": printed})
        if printed and not verdict.gates_complete:
            raise FailClosed("FALSE_PASS_DETECTED:" + ",".join(printed))
        if verdict.ok is False and fields.get("require_ok"):
            raise FailClosed("AUTHORITATIVE_VERDICT_FAILED:" + (verdict.reason or "incomplete"))
        return verdict


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
        path.write_text(canonical_json(body) + "\n", encoding="utf-8")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if loaded.get("sha256") != digest:
            raise FailClosed("EVIDENCE_READBACK_FAILED")
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
        from .process_kernel import encoding_safe_run

        try:
            obs = encoding_safe_run(argv, cwd=cwd, timeout=timeout)
        except FailClosed as exc:
            self.ledger.persist_failure({"name": "child", "argv": list(argv), "error": str(exc)})
            raise
        completed = obs.as_completed()
        self.detector.judge_child(completed.stdout, completed.stderr, completed.returncode)
        return completed
