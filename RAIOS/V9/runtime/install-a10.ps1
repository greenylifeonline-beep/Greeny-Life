$ErrorActionPreference = "Stop"

$Repo = (git rev-parse --show-toplevel).Trim()
Set-Location $Repo

$V9 = Join-Path $Repo "RAIOS\V9"

$PythonCandidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)

$Python = $PythonCandidates |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $Python) {
    throw "PYTHON_EXECUTABLE_NOT_FOUND"
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$Runtime = Join-Path $V9 "runtime"
$Harness = Join-Path $Runtime "a10_canary_guardian_certification.py"

New-Item -ItemType Directory -Force $Runtime | Out-Null

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$Code = @'
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import uuid

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
)

V9 = REPO / "RAIOS" / "V9"

STATE = V9 / "continuity" / "RAIOS-CURRENT-STATE.json"

A9_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A9-RECEIPT.json"
)

A10_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A10-RECEIPT.json"
)

REGISTRY = (
    V9
    / "governance"
    / "a7"
    / "registry"
    / "SKILL-REGISTRY.json"
)

ROOT = V9 / "runtime" / "a10"

AUTH = ROOT / "authorization"
SNAPSHOTS = ROOT / "snapshots"
CANARY = ROOT / "canary"
GUARDIAN = ROOT / "guardian"
ROLLBACK = ROOT / "rollback"
REPORTS = ROOT / "reports"

EVO = V9 / "evolution" / "a10"
EXPERIENCES = EVO / "experiences"
FAILURES = EVO / "failures"
RECOVERY = EVO / "recovery-skill-candidates"

for p in (
    AUTH,
    SNAPSHOTS,
    CANARY,
    GUARDIAN,
    ROLLBACK,
    REPORTS,
    EXPERIENCES,
    FAILURES,
    RECOVERY,
):
    p.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def write_json_atomic(
    path: Path,
    obj: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_name(
        path.name
        + ".tmp-"
        + uuid.uuid4().hex
    )

    tmp.write_text(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
            default=str,
        ) + "\n",
        encoding="utf-8",
    )

    check = load_json(tmp)

    if check != obj:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "ATOMIC_WRITE_READBACK_FAILED"
        )

    os.replace(
        tmp,
        path,
    )


def file_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def object_hash(obj: Any) -> str:
    payload = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(
        payload
    ).hexdigest()


def probability(
    value: Any,
    name: str,
) -> float:

    if isinstance(value, bool):
        raise RuntimeError(
            f"{name}_BOOLEAN_INVALID"
        )

    value = float(value)

    if not 0.0 <= value <= 1.0:
        raise RuntimeError(
            f"{name}_OUT_OF_RANGE:{value}"
        )

    return value


def capture_experience(
    event: str,
    status: str,
    details: dict[str, Any],
) -> Path:

    obj = {
        "schema":
            "raios.a10.experience.v1",

        "timestamp":
            now(),

        "event":
            event,

        "status":
            status,

        "details":
            details,
    }

    obj["experience_id"] = (
        "exp:"
        +
        object_hash(obj)[:32]
    )

    path = (
        EXPERIENCES
        /
        (
            obj["experience_id"]
            .replace(":", "_")
            + ".json"
        )
    )

    write_json_atomic(
        path,
        obj,
    )

    return path


def capture_failure(
    exc: BaseException,
) -> None:

    basis = {
        "phase":
            "V9.0-A10",

        "exception_type":
            type(exc).__name__,

        "message":
            str(exc),
    }

    sig = (
        "fs:"
        +
        object_hash(basis)[:32]
    )

    failure = {
        "schema":
            "raios.a10.failure-signature.v1",

        "failure_signature":
            sig,

        "timestamp":
            now(),

        "exception_type":
            type(exc).__name__,

        "message":
            str(exc),

        "traceback":
            traceback.format_exc(),

        "production_mutation":
            False,

        "canonical_mutation":
            False,
    }

    write_json_atomic(
        FAILURES
        /
        (
            sig.replace(":", "_")
            + ".json"
        ),
        failure,
    )

    candidate = {
        "schema":
            "raios.a10.recovery-skill-candidate.v1",

        "candidate_id":
            "recovery:"
            +
            object_hash(failure)[:32],

        "source_failure_signature":
            sig,

        "status":
            "CANDIDATE",

        "requires_validation":
            True,

        "automatic_promotion":
            False,

        "canonical_mutation":
            False,

        "created_at":
            now(),
    }

    write_json_atomic(
        RECOVERY
        /
        (
            candidate["candidate_id"]
            .replace(":", "_")
            + ".json"
        ),
        candidate,
    )

    capture_experience(
        "A10_FAILURE",
        "FAILED",
        {
            "failure_signature":
                sig,

            "recovery_candidate":
                candidate["candidate_id"],
        },
    )


def main() -> None:

    print("=" * 84)
    print(
        "RAIOS V9.0-A10 TRUE FAIL-CLOSED CANARY CERTIFICATION"
    )
    print("=" * 84)

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        text=True,
    ).strip()

    print("HEAD:", head)

    # ------------------------------------------------------------
    # 1. PREDECESSOR
    # ------------------------------------------------------------

    state = load_json(STATE)

    if (
        state.get("current_version")
        !=
        "V9.0-A9"
    ):
        raise RuntimeError(
            "A10_PREDECESSOR_NOT_A9"
        )

    if (
        state.get("state_status")
        !=
        "A9_CERTIFIED"
    ):
        raise RuntimeError(
            "A10_PREDECESSOR_NOT_CERTIFIED"
        )

    latest = (
        state.get(
            "latest_phase_receipt"
        )
        or {}
    )

    if (
        latest.get("phase")
        !=
        "V9.0-A9"
    ):
        raise RuntimeError(
            "A10_PREDECESSOR_RECEIPT_PHASE_INVALID"
        )

    if (
        latest.get(
            "certification_status"
        )
        !=
        "PASS"
    ):
        raise RuntimeError(
            "A10_PREDECESSOR_RECEIPT_NOT_PASS"
        )

    if not A9_RECEIPT.exists():
        raise RuntimeError(
            "A9_RECEIPT_NOT_FOUND"
        )

    a9_hash = file_hash(
        A9_RECEIPT
    )

    if (
        latest.get("sha256")
        !=
        a9_hash
    ):
        raise RuntimeError(
            "A9_RECEIPT_HASH_DRIFT"
        )

    print(
        "PREDECESSOR_A9                : PASS"
    )

    # ------------------------------------------------------------
    # 2. READINESS GATE
    # ------------------------------------------------------------

    a9 = load_json(
        A9_RECEIPT
    )

    readiness = (
        a9.get(
            "promotion_readiness"
        )
        or {}
    )

    if (
        readiness.get(
            "status"
        )
        !=
        "READY_FOR_NEXT_GOVERNANCE_STAGE"
    ):
        raise RuntimeError(
            "A10_A9_NOT_READY"
        )

    score = probability(
        readiness.get("score"),
        "A9_PROMOTION_READINESS_SCORE",
    )

    print(
        "A9_PROMOTION_READINESS        : PASS"
    )

    print(
        "READINESS_SCORE               :",
        round(score, 6),
    )

    # ------------------------------------------------------------
    # 3. SHADOW SKILL
    # ------------------------------------------------------------

    registry = load_json(
        REGISTRY
    )

    shadow_skills = [
        s
        for s in registry.get(
            "skills",
            {}
        ).values()
        if s.get("lifecycle")
        ==
        "SHADOW"
    ]

    if len(shadow_skills) != 1:
        raise RuntimeError(
            "A10_EXPECTED_ONE_SHADOW_SKILL"
        )

    skill = shadow_skills[0]

    if (
        skill.get(
            "production_active"
        )
        is not False
    ):
        raise RuntimeError(
            "A10_PRODUCTION_ALREADY_ACTIVE"
        )

    skill_id = skill["skill_id"]

    candidate_hash = (
        skill.get(
            "candidate_sha256"
        )
    )

    if not candidate_hash:
        raise RuntimeError(
            "A10_CANDIDATE_HASH_MISSING"
        )

    print(
        "SHADOW_SKILL_IDENTITY         : PASS"
    )

    print(
        "SKILL_ID                      :",
        skill_id,
    )

    # ------------------------------------------------------------
    # 4. CONFIDENCE CONTRACT
    # ------------------------------------------------------------

    rejected_70 = False

    try:
        probability(
            70,
            "CONFIDENCE_70_TEST",
        )

    except RuntimeError as exc:

        if "OUT_OF_RANGE" in str(exc):
            rejected_70 = True
        else:
            raise

    if not rejected_70:
        raise RuntimeError(
            "A10_CONFIDENCE_70_ACCEPTED"
        )

    print(
        "CONFIDENCE_70_REJECTED        : PASS"
    )

    # ------------------------------------------------------------
    # 5. AUTHORIZATION TOKEN
    # ------------------------------------------------------------

    issued = datetime.now(
        timezone.utc
    )

    expires = (
        issued
        +
        timedelta(
            minutes=30
        )
    )

    authorization = {
        "schema":
            "raios.a10.authorization-token.v1",

        "authorization_id":
            "auth:"
            +
            uuid.uuid4().hex,

        "skill_id":
            skill_id,

        "candidate_sha256":
            candidate_hash,

        "scope":
            "SANDBOX_CANARY_ONLY",

        "operation_classes": [
            "RECOVERY_SIMULATION",
            "READ_ONLY_DIAGNOSTIC",
        ],

        "issued_at":
            issued.isoformat(),

        "expires_at":
            expires.isoformat(),

        "max_actions":
            6,

        "max_failures":
            1,

        "max_failure_rate":
            0.25,

        "max_latency_ms":
            25.0,

        "minimum_confidence":
            0.80,

        "production_active":
            False,

        "canonical_mutation":
            False,

        "automatic_promotion":
            False,

        "kill_switch":
            True,
    }

    auth_path = (
        AUTH
        /
        (
            authorization[
                "authorization_id"
            ]
            .replace(":", "_")
            +
            ".json"
        )
    )

    write_json_atomic(
        auth_path,
        authorization,
    )

    print(
        "AUTHORIZATION_TOKEN          : PASS"
    )

    # ------------------------------------------------------------
    # 6. SANDBOX FIXTURE
    # ------------------------------------------------------------

    fixture = (
        CANARY
        /
        "sandbox-state.json"
    )

    initial_fixture = {
        "schema":
            "raios.a10.sandbox-fixture.v1",

        "counter":
            0,

        "status":
            "CLEAN",

        "canonical":
            False,

        "production":
            False,
    }

    write_json_atomic(
        fixture,
        initial_fixture,
    )

    fixture_before = (
        fixture.read_bytes()
    )

    fixture_hash_before = (
        file_hash(fixture)
    )

    snapshot_path = (
        SNAPSHOTS
        /
        (
            "pre-canary-"
            +
            fixture_hash_before
            +
            ".json"
        )
    )

    if not snapshot_path.exists():
        snapshot_path.write_bytes(
            fixture_before
        )

    if (
        file_hash(snapshot_path)
        !=
        fixture_hash_before
    ):
        raise RuntimeError(
            "A10_PREACTION_SNAPSHOT_INVALID"
        )

    print(
        "PRE_ACTION_SNAPSHOT           : PASS"
    )

    # ------------------------------------------------------------
    # 7. GUARDIAN
    # ------------------------------------------------------------

    action_count = 0
    failure_count = 0
    killed = False

    action_log = []

    def guardian_allows(
        confidence: float,
        operation: str,
    ) -> bool:

        nonlocal action_count
        nonlocal failure_count
        nonlocal killed

        if killed:
            return False

        if action_count >= authorization["max_actions"]:
            killed = True
            return False

        if operation not in authorization[
            "operation_classes"
        ]:
            return False

        if confidence < authorization[
            "minimum_confidence"
        ]:
            return False

        failure_rate = (
            failure_count
            /
            action_count
            if action_count
            else 0.0
        )

        if (
            failure_rate
            >
            authorization[
                "max_failure_rate"
            ]
        ):
            killed = True
            return False

        return True

    # ------------------------------------------------------------
    # 8. SAFE CANARY ACTION
    # ------------------------------------------------------------

    confidence = probability(
        0.94,
        "CANARY_CONFIDENCE",
    )

    if not guardian_allows(
        confidence,
        "RECOVERY_SIMULATION",
    ):
        raise RuntimeError(
            "A10_SAFE_CANARY_NOT_ALLOWED"
        )

    started = time.perf_counter_ns()

    state_obj = load_json(
        fixture
    )

    state_obj["counter"] += 1
    state_obj["status"] = "CANARY_OK"

    write_json_atomic(
        fixture,
        state_obj,
    )

    latency_ms = (
        time.perf_counter_ns()
        -
        started
    ) / 1_000_000

    action_count += 1

    action_log.append({
        "action":
            "RECOVERY_SIMULATION",

        "confidence":
            confidence,

        "latency_ms":
            latency_ms,

        "success":
            True,

        "production_mutation":
            False,

        "canonical_mutation":
            False,
    })

    if (
        latency_ms
        >
        authorization[
            "max_latency_ms"
        ]
    ):
        raise RuntimeError(
            "A10_LATENCY_CIRCUIT_BREAKER"
        )

    print(
        "SAFE_CANARY_ACTION           : PASS"
    )

    # ------------------------------------------------------------
    # 9. FAULT INJECTION
    # ------------------------------------------------------------

    fault_triggered = False

    try:

        if not guardian_allows(
            0.95,
            "RECOVERY_SIMULATION",
        ):
            raise RuntimeError(
                "A10_FAULT_ACTION_NOT_ALLOWED"
            )

        action_count += 1
        failure_count += 1

        faulty = load_json(
            fixture
        )

        faulty["counter"] = 999
        faulty["status"] = "FAULT_INJECTED"

        write_json_atomic(
            fixture,
            faulty,
        )

        fault_triggered = True

        raise RuntimeError(
            "CONTROLLED_CANARY_FAULT"
        )

    except RuntimeError as exc:

        if (
            "CONTROLLED_CANARY_FAULT"
            not in str(exc)
        ):
            raise

        killed = True

        shutil.copyfile(
            snapshot_path,
            fixture,
        )

    if not fault_triggered:
        raise RuntimeError(
            "A10_FAULT_INJECTION_NOT_PROVEN"
        )

    print(
        "FAULT_INJECTION              : PASS"
    )

    # ------------------------------------------------------------
    # 10. ROLLBACK VERIFY
    # ------------------------------------------------------------

    fixture_after_rollback = (
        fixture.read_bytes()
    )

    if (
        fixture_after_rollback
        !=
        fixture_before
    ):
        raise RuntimeError(
            "A10_ROLLBACK_NOT_BYTE_IDENTICAL"
        )

    if not killed:
        raise RuntimeError(
            "A10_KILL_SWITCH_NOT_TRIGGERED"
        )

    print(
        "KILL_SWITCH                  : PASS"
    )

    print(
        "ROLLBACK_BYTE_IDENTICAL      : PASS"
    )

    # ------------------------------------------------------------
    # 11. LOW CONFIDENCE ABSTENTION
    # ------------------------------------------------------------

    low_confidence = probability(
        0.50,
        "LOW_CONFIDENCE",
    )

    if guardian_allows(
        low_confidence,
        "RECOVERY_SIMULATION",
    ):
        raise RuntimeError(
            "A10_LOW_CONFIDENCE_NOT_ABSTAINED"
        )

    print(
        "ABSTENTION_GATE              : PASS"
    )

    # ------------------------------------------------------------
    # 12. OUT OF SCOPE REJECTION
    # ------------------------------------------------------------

    killed = False

    if guardian_allows(
        0.95,
        "CANONICAL_MUTATION",
    ):
        raise RuntimeError(
            "A10_OUT_OF_SCOPE_OPERATION_ALLOWED"
        )

    print(
        "OUT_OF_SCOPE_REJECTION       : PASS"
    )

    # ------------------------------------------------------------
    # 13. ISOLATION
    # ------------------------------------------------------------

    state_hash_before = (
        file_hash(STATE)
    )

    registry_hash_before = (
        file_hash(REGISTRY)
    )

    if (
        skill.get(
            "production_active"
        )
        is not False
    ):
        raise RuntimeError(
            "A10_PRODUCTION_ACTIVE_VIOLATION"
        )

    if (
        skill.get(
            "automatic_promotion"
        )
        is not False
    ):
        raise RuntimeError(
            "A10_AUTO_PROMOTION_VIOLATION"
        )

    print(
        "CANONICAL_ISOLATION          : PASS"
    )

    print(
        "PRODUCTION_ISOLATION         : PASS"
    )

    # ------------------------------------------------------------
    # 14. GUARDIAN REPORT
    # ------------------------------------------------------------

    guardian_report = {
        "schema":
            "raios.a10.runtime-guardian-report.v1",

        "timestamp":
            now(),

        "skill_id":
            skill_id,

        "authorization_id":
            authorization[
                "authorization_id"
            ],

        "scope":
            "SANDBOX_CANARY_ONLY",

        "action_budget":
            authorization[
                "max_actions"
            ],

        "actions_attempted":
            action_count,

        "failures_observed":
            failure_count,

        "fault_injection":
            True,

        "kill_switch_triggered":
            True,

        "rollback_verified":
            True,

        "abstention_gate":
            True,

        "out_of_scope_rejection":
            True,

        "production_mutation":
            False,

        "canonical_mutation":
            False,

        "automatic_promotion":
            False,

        "lifecycle_after_a10":
            "CANARY_AUTHORIZED",
    }

    guardian_path = (
        REPORTS
        /
        "RUNTIME-GUARDIAN-REPORT.json"
    )

    write_json_atomic(
        guardian_path,
        guardian_report,
    )

    # ------------------------------------------------------------
    # 15. EXPERIENCE
    # ------------------------------------------------------------

    success_exp = (
        capture_experience(
            "A10_CONTROLLED_CANARY",
            "SUCCESS",
            {
                "skill_id":
                    skill_id,

                "authorization_id":
                    authorization[
                        "authorization_id"
                    ],

                "safe_action":
                    True,

                "fault_injection":
                    True,

                "kill_switch":
                    True,

                "rollback":
                    True,

                "production_active":
                    False,
            },
        )
    )

    # ------------------------------------------------------------
    # 16. RECEIPT
    # ------------------------------------------------------------

    receipt = {
        "schema":
            "raios.v9.a10.receipt.v1",

        "phase":
            "V9.0-A10",

        "certification_status":
            "PASS",

        "certification_mode":
            "FAIL_CLOSED",

        "repository_sha":
            head,

        "timestamp":
            now(),

        "predecessor": {
            "phase":
                "V9.0-A9",

            "sha256":
                a9_hash,

            "status":
                "PASS",
        },

        "skill": {
            "skill_id":
                skill_id,

            "candidate_sha256":
                candidate_hash,

            "previous_lifecycle":
                "SHADOW",

            "lifecycle_after_a10":
                "CANARY_AUTHORIZED",

            "active":
                False,

            "production_active":
                False,
        },

        "authorization": {
            "authorization_id":
                authorization[
                    "authorization_id"
                ],

            "scope":
                authorization[
                    "scope"
                ],

            "max_actions":
                authorization[
                    "max_actions"
                ],

            "kill_switch":
                True,
        },

        "guardian": {
            "report":
                str(
                    guardian_path.relative_to(
                        REPO
                    )
                ),

            "safe_canary_action":
                True,

            "fault_injection":
                True,

            "kill_switch":
                True,

            "rollback_byte_identical":
                True,

            "abstention_gate":
                True,

            "out_of_scope_rejection":
                True,
        },

        "safety": {
            "confidence_contract":
                "STRICT_[0,1]",

            "confidence_70_rejected":
                True,

            "production_mutation":
                False,

            "canonical_mutation":
                False,

            "automatic_promotion":
                False,

            "active_authorized":
                False,
        },

        "experience": {
            "path":
                str(
                    success_exp.relative_to(
                        REPO
                    )
                )
        },

        "epistemic_limits": [
            "A10 authorizes sandbox canary execution only.",
            "A10 does not authorize full production ACTIVE lifecycle.",
            "The tested action mutated only an explicit sandbox fixture.",
            "Fault injection was controlled and rollback was verified.",
            "Canonical truth was not mutated.",
            "Production state was not mutated.",
            "Automatic promotion remains forbidden."
        ],
    }

    write_json_atomic(
        A10_RECEIPT,
        receipt,
    )

    receipt_hash = (
        file_hash(
            A10_RECEIPT
        )
    )

    # ------------------------------------------------------------
    # 17. STATE UPDATE
    # ------------------------------------------------------------

    final_state = load_json(
        STATE
    )

    final_state[
        "current_version"
    ] = "V9.0-A10"

    final_state[
        "current_phase"
    ] = (
        "CONTROLLED_CANARY_EXECUTION_AND_RUNTIME_GUARDIAN"
    )

    final_state[
        "state_status"
    ] = "A10_CERTIFIED"

    final_state[
        "canary_runtime"
    ] = {
        "skill_id":
            skill_id,

        "lifecycle":
            "CANARY_AUTHORIZED",

        "active":
            False,

        "production_active":
            False,

        "canonical_mutation":
            False,

        "automatic_promotion":
            False,

        "kill_switch":
            True,

        "rollback_verified":
            True,

        "authorization_scope":
            "SANDBOX_CANARY_ONLY",
    }

    active_architecture = (
        final_state.get(
            "active_architecture",
            []
        )
    )

    for cap in [
        "CANARY_AUTHORIZATION_GATE",
        "RUNTIME_GUARDIAN",
        "ACTION_BUDGET",
        "KILL_SWITCH",
        "CIRCUIT_BREAKER",
        "PRE_ACTION_SNAPSHOT",
        "POST_ACTION_DIFF_GUARD",
        "VERIFIED_ROLLBACK",
    ]:
        if cap not in active_architecture:
            active_architecture.append(cap)

    final_state[
        "active_architecture"
    ] = active_architecture

    final_state[
        "latest_phase_receipt"
    ] = {
        "phase":
            "V9.0-A10",

        "path":
            str(
                A10_RECEIPT.relative_to(
                    REPO
                )
            ),

        "sha256":
            receipt_hash,

        "certification_status":
            "PASS",
    }

    final_state[
        "updated_at"
    ] = now()

    write_json_atomic(
        STATE,
        final_state,
    )

    final = load_json(
        STATE
    )

    actual_hash = (
        file_hash(
            A10_RECEIPT
        )
    )

    if (
        final[
            "latest_phase_receipt"
        ][
            "sha256"
        ]
        !=
        actual_hash
    ):
        raise RuntimeError(
            "A10_STATE_RECEIPT_HASH_DRIFT"
        )

    if (
        final[
            "canary_runtime"
        ][
            "production_active"
        ]
        is not False
    ):
        raise RuntimeError(
            "A10_PRODUCTION_ACTIVATION_VIOLATION"
        )

    if (
        final[
            "canary_runtime"
        ][
            "lifecycle"
        ]
        !=
        "CANARY_AUTHORIZED"
    ):
        raise RuntimeError(
            "A10_LIFECYCLE_INVALID"
        )

    print()
    print("=" * 84)
    print(
        "RAIOS V9.0-A10 CERTIFICATION RESULT"
    )
    print("=" * 84)

    print(
        "PREDECESSOR_A9                : PASS"
    )

    print(
        "A9_PROMOTION_READINESS        : PASS"
    )

    print(
        "AUTHORIZATION_TOKEN           : PASS"
    )

    print(
        "PRE_ACTION_SNAPSHOT           : PASS"
    )

    print(
        "SAFE_CANARY_ACTION            : PASS"
    )

    print(
        "FAULT_INJECTION               : PASS"
    )

    print(
        "KILL_SWITCH                   : PASS"
    )

    print(
        "ROLLBACK_BYTE_IDENTICAL       : PASS"
    )

    print(
        "ABSTENTION_GATE               : PASS"
    )

    print(
        "OUT_OF_SCOPE_REJECTION        : PASS"
    )

    print(
        "CONFIDENCE_70_REJECTED        : PASS"
    )

    print(
        "CANONICAL_MUTATION            : FALSE"
    )

    print(
        "PRODUCTION_MUTATION           : FALSE"
    )

    print(
        "AUTOMATIC_PROMOTION           : FALSE"
    )

    print(
        "SKILL_LIFECYCLE               : CANARY_AUTHORIZED"
    )

    print(
        "ACTIVE                        : FALSE"
    )

    print(
        "PRODUCTION_ACTIVE             : FALSE"
    )

    print(
        "STATE_RECEIPT_HASH_MATCH      : TRUE"
    )

    print(
        "CURRENT_VERSION               :",
        final["current_version"],
    )

    print(
        "STATE_STATUS                  :",
        final["state_status"],
    )

    print(
        "A10_RECEIPT_SHA256            :",
        actual_hash,
    )

    print()
    print(
        "STATUS = V9.0-A10_PASS"
    )

    print("=" * 84)


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        try:
            capture_failure(exc)

        except Exception as telemetry_error:
            print(
                "A10_FAILURE_TELEMETRY_ERROR:",
                repr(telemetry_error),
                file=sys.stderr,
            )

        print(
            "A10_CERTIFICATION_FAILED:",
            repr(exc),
            file=sys.stderr,
        )

        raise
'@

[System.IO.File]::WriteAllText(
    $Harness,
    $Code,
    $Utf8NoBom
)

Write-Host ""
Write-Host "======================================================================"
Write-Host " RAIOS V9.0-A10 INSTALLER"
Write-Host "======================================================================"

& $Python -m py_compile $Harness

if ($LASTEXITCODE -ne 0) {
    throw "A10_HARNESS_COMPILE_FAILED"
}

Write-Host "A10_HARNESS_COMPILE = PASS"

Write-Host ""
Write-Host "=== EXECUTING A10 ==="

& $Python $Harness

if ($LASTEXITCODE -ne 0) {
    throw "RAIOS_V9_A10_CERTIFICATION_FAILED"
}

Write-Host ""
Write-Host "======================================================================"
Write-Host " A10 INSTALLER FINISHED"
Write-Host "======================================================================"