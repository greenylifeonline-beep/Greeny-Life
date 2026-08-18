from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"],
    text=True
).strip())

V9 = REPO / "RAIOS" / "V9"

EXPERIENCE_DIR = V9 / "experience" / "automatic"
FAILURE_DIR = V9 / "failures"
SKILL_DIR = V9 / "skills" / "candidates"

for d in (EXPERIENCE_DIR, FAILURE_DIR, SKILL_DIR):
    d.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    loaded = json.loads(tmp.read_text(encoding="utf-8"))
    if loaded != obj:
        raise RuntimeError("ATOMIC_JSON_READBACK_MISMATCH")
    tmp.replace(path)


def environment_snapshot() -> dict[str, Any]:
    def cmd(args: list[str]) -> str | None:
        try:
            return subprocess.check_output(
                args,
                cwd=REPO,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            return None

    return {
        "timestamp": utc_now(),
        "repository": str(REPO),
        "repository_sha": cmd(["git", "rev-parse", "HEAD"]),
        "branch": cmd(["git", "branch", "--show-current"]),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "pid": os.getpid(),
    }


def classify_failure(
    exc: BaseException | None,
    result: Any,
    expected: Any,
) -> tuple[str | None, list[str]]:
    reasons: list[str] = []

    if exc is not None:
        name = type(exc).__name__
        message = str(exc)
        reasons.append(f"{name}: {message}")

        if "zero" in message.lower() and "byte" in message.lower():
            return "ZERO_BYTE_CRITICAL_ARTIFACT", reasons

        if "json" in message.lower():
            return "JSON_CONTRACT_FAILURE", reasons

        return f"EXCEPTION_{name.upper()}", reasons

    if expected is not None and result != expected:
        reasons.append("actual_result_did_not_match_expected_result")
        return "EXPECTED_ACTUAL_MISMATCH", reasons

    return None, reasons


def build_recovery_candidate(
    experience: dict[str, Any],
    failure: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "raios.recovery-skill-candidate.v1",
        "candidate_id": digest({
            "experience": experience["experience_id"],
            "signature": failure["signature"],
        }),
        "source_experience": experience["experience_id"],
        "failure_signature": failure["signature"],
        "status": "REVIEW_REQUIRED",
        "promotion": "FORBIDDEN_WITHOUT_REPLAY_BENCHMARK",
        "candidate_pattern": {
            "detect": failure["signature"],
            "preserve_failure_evidence": True,
            "recover_from_verified_preimage": True,
            "validate_before_replace": True,
            "post_recovery_contract_test": True,
            "rollback_on_failure": True,
        },
        "created_at": utc_now(),
    }


def capture_event(
    *,
    intent: str,
    action: str,
    tool: str,
    input_data: Any = None,
    output_data: Any = None,
    expected_result: Any = None,
    success: bool,
    exception: BaseException | None = None,
    evidence_refs: list[str] | None = None,
    lessons: list[str] | None = None,
    latency_ms: float | None = None,
    pre_state: Any = None,
    post_state: Any = None,
    unresolved_flags: list[str] | None = None,
) -> dict[str, Any]:

    failure_signature, failure_reasons = classify_failure(
        exception,
        output_data,
        expected_result,
    )

    base = {
        "schema": "raios.experience.v2",
        "intent": intent,
        "action": action,
        "tool": tool,
        "environment": environment_snapshot(),
        "input": input_data,
        "expected_result": expected_result,
        "actual_result": output_data,
        "success": success,
        "failure_signature": failure_signature,
        "evidence_refs": evidence_refs or [],
        "lessons": lessons or [],
        "latency_ms": latency_ms,
        "pre_state": pre_state,
        "post_state": post_state,
        "unresolved_flags": unresolved_flags or [],
        "confidence": 1.0 if success else 0.95,
        "replayable": True,
        "captured_at": utc_now(),
    }

    experience_id = digest(base)
    base["experience_id"] = experience_id

    write_json(
        EXPERIENCE_DIR / f"{experience_id}.json",
        base,
    )

    if failure_signature:
        failure = {
            "schema": "raios.failure-signature.v1",
            "failure_id": digest({
                "signature": failure_signature,
                "experience": experience_id,
            }),
            "signature": failure_signature,
            "source_experience": experience_id,
            "reasons": failure_reasons,
            "evidence_refs": evidence_refs or [],
            "status": "ACTIVE",
            "created_at": utc_now(),
        }

        write_json(
            FAILURE_DIR / f"{failure['failure_id']}.json",
            failure,
        )

        candidate = build_recovery_candidate(base, failure)

        write_json(
            SKILL_DIR / f"{candidate['candidate_id']}.json",
            candidate,
        )

    return base


def instrumented_call(
    *,
    intent: str,
    action: str,
    tool: str,
    fn: Callable[[], Any],
    input_data: Any = None,
    expected_result: Any = None,
    evidence_refs: list[str] | None = None,
) -> Any:

    started = time.perf_counter()

    try:
        result = fn()

        latency_ms = round(
            (time.perf_counter() - started) * 1000,
            3,
        )

        capture_event(
            intent=intent,
            action=action,
            tool=tool,
            input_data=input_data,
            output_data=result,
            expected_result=expected_result,
            success=True,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
        )

        return result

    except BaseException as exc:
        latency_ms = round(
            (time.perf_counter() - started) * 1000,
            3,
        )

        capture_event(
            intent=intent,
            action=action,
            tool=tool,
            input_data=input_data,
            output_data=None,
            expected_result=expected_result,
            success=False,
            exception=exc,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
            lessons=[
                "Failure must become reusable negative knowledge.",
                "Recovery must be validated before promotion.",
            ],
            unresolved_flags=[
                traceback.format_exc(limit=5),
            ],
        )

        raise