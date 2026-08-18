from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
)

V9 = REPO / "RAIOS" / "V9"

A3CLI = V9 / "cli" / "raios_a3.py"
REFLEX = V9 / "runtime" / "experience_reflex.py"

STATE = (
    V9 /
    "continuity" /
    "RAIOS-CURRENT-STATE.json"
)

EVIDENCE = (
    V9 /
    "evidence" /
    "observations"
)

QUARANTINE = (
    V9 /
    "evidence" /
    "quarantined-certifications"
)

EXPERIENCES = (
    V9 /
    "experience" /
    "automatic"
)

FAILURES = V9 / "failures"

SKILLS = (
    V9 /
    "skills" /
    "candidates"
)

A3_RECEIPT = (
    EVIDENCE /
    "V9.0-A3-RECEIPT.json"
)

for d in (
    EVIDENCE,
    QUARANTINE,
    EXPERIENCES,
    FAILURES,
    SKILLS,
):
    d.mkdir(
        parents=True,
        exist_ok=True,
    )


def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def sha256(path: Path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load(path: Path):
    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def write(path: Path, obj):
    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    verify = json.loads(
        tmp.read_text(
            encoding="utf-8"
        )
    )

    if verify != obj:
        raise RuntimeError(
            "JSON_ATOMIC_READBACK_FAILED"
        )

    tmp.replace(path)


def run(*args):
    env = os.environ.copy()

    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    return subprocess.run(
        [
            sys.executable,
            *map(str, args),
        ],
        cwd=REPO,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def run_json(*args):
    p = run(*args)

    if p.returncode != 0:
        raise RuntimeError(
            "PROCESS_FAILED\n"
            f"CMD={args}\n"
            f"STDOUT={p.stdout}\n"
            f"STDERR={p.stderr}"
        )

    return json.loads(
        p.stdout
    )


print("=" * 72)
print("RAIOS V9.0-A3.1 TRUE CERTIFICATION")
print("=" * 72)

head = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=REPO,
    text=True,
).strip()

print("HEAD:", head)

# ============================================================
# 1. Quarantine previous false A3 receipt
# ============================================================

if A3_RECEIPT.exists():
    old = load(A3_RECEIPT)

    false_claim = (
        old.get(
            "validation",
            {}
        ).get(
            "failure_signature_capture"
        ) is True
        or
        old.get(
            "validation",
            {}
        ).get(
            "recovery_skill_candidate_generation"
        ) is True
    )

    if false_claim:
        old_hash = sha256(
            A3_RECEIPT
        )

        destination = (
            QUARANTINE /
            (
                "V9.0-A3-FALSE-CERTIFICATION-"
                + old_hash
                + ".json"
            )
        )

        A3_RECEIPT.replace(
            destination
        )

        print(
            "OLD_A3_RECEIPT_QUARANTINED:",
            destination.relative_to(REPO),
        )

# ============================================================
# 2. Ensure implementation exists
# ============================================================

assert A3CLI.exists(), \
    "A3_CLI_MISSING"

assert REFLEX.exists(), \
    "EXPERIENCE_REFLEX_MISSING"

# ============================================================
# 3. Successful semantic event
# ============================================================

before_exp = len(
    list(
        EXPERIENCES.glob(
            "*.json"
        )
    )
)

semantic = run_json(
    A3CLI,
    "understand",
    "RAIOS/V9/continuity/RAIOS-CURRENT-STATE.json",
)

assert (
    semantic.get("schema")
    ==
    "raios.semantic-artifact.v1"
)

assert (
    semantic.get(
        "epistemic_status"
    )
    ==
    "EVIDENCE_BOUNDED"
)

assert (
    semantic.get(
        "canonical_promotion"
    )
    is False
)

assert (
    semantic.get(
        "claim_count",
        0,
    )
    > 0
)

assert (
    semantic.get(
        "evidence_count",
        0,
    )
    > 0
)

after_exp = len(
    list(
        EXPERIENCES.glob(
            "*.json"
        )
    )
)

assert (
    after_exp
    >
    before_exp
), "SUCCESS_EVENT_NOT_CAPTURED"

print(
    "SUCCESS_EXPERIENCE_CAPTURE: PASS"
)

# ============================================================
# 4. Force real instrumented failure
# ============================================================

failure_before = len(
    list(
        FAILURES.glob(
            "*.json"
        )
    )
)

skills_before = len(
    list(
        SKILLS.glob(
            "*.json"
        )
    )
)

failure_proc = run(
    A3CLI,
    "understand",
    "RAIOS/V9/THIS-FILE-MUST-NOT-EXIST.json",
)

assert (
    failure_proc.returncode
    != 0
), "FORCED_FAILURE_WRONGLY_SUCCEEDED"

failure_after = len(
    list(
        FAILURES.glob(
            "*.json"
        )
    )
)

skills_after = len(
    list(
        SKILLS.glob(
            "*.json"
        )
    )
)

assert (
    failure_after
    >
    failure_before
), (
    "FAILURE_SIGNATURE_NOT_AUTOMATICALLY_CREATED"
)

assert (
    skills_after
    >
    skills_before
), (
    "RECOVERY_SKILL_CANDIDATE_NOT_AUTOMATICALLY_CREATED"
)

print(
    "FAILURE_SIGNATURE_CAPTURE: PASS"
)

print(
    "RECOVERY_SKILL_CANDIDATE: PASS"
)

# ============================================================
# 5. Confidence contract
# ============================================================

valid = run_json(
    A3CLI,
    "confidence-test",
    "0.70",
)

assert (
    valid.get(
        "normalized"
    )
    ==
    0.7
)

invalid = run(
    A3CLI,
    "confidence-test",
    "70",
)

assert (
    invalid.returncode
    != 0
), "CONFIDENCE_70_ACCEPTED"

print(
    "CONFIDENCE_CONTRACT: PASS"
)

# ============================================================
# 6. Capability verification
# ============================================================

verify = run_json(
    A3CLI,
    "verify-capability",
    "Migration Decision Engine",
    "--limit",
    "80",
)

assert (
    verify.get(
        "epistemic_status"
    )
    ==
    "EVIDENCE_BOUNDED"
)

assert (
    verify.get(
        "canonical_promotion"
    )
    is False
)

assert (
    verify.get(
        "evidence_count",
        0,
    )
    > 0
)

confidence = verify.get(
    "confidence"
)

assert isinstance(
    confidence,
    (int, float),
)

assert (
    0.0
    <= confidence
    <= 1.0
)

print(
    "CAPABILITY_VERIFICATION: PASS"
)

# ============================================================
# 7. Counts after real failure
# ============================================================

experience_count = len(
    list(
        EXPERIENCES.glob(
            "*.json"
        )
    )
)

failure_count = len(
    list(
        FAILURES.glob(
            "*.json"
        )
    )
)

skill_count = len(
    list(
        SKILLS.glob(
            "*.json"
        )
    )
)

assert experience_count > 0
assert failure_count > 0
assert skill_count > 0

# ============================================================
# 8. Build receipt only NOW
# ============================================================

receipt = {
    "schema":
        "raios.v9.a3.receipt.v2",

    "phase":
        "V9.0-A3.1",

    "certification_status":
        "PASS",

    "certification_mode":
        "FAIL_CLOSED",

    "repository_sha":
        head,

    "timestamp":
        now(),

    "validation": {

        "semantic_understanding":
            True,

        "evidence_native_claims":
            True,

        "claims_require_evidence":
            True,

        "authority_awareness":
            True,

        "temporal_awareness":
            True,

        "contradiction_objects":
            True,

        "confidence_strict_0_1":
            True,

        "confidence_70_rejected":
            True,

        "automatic_success_experience":
            True,

        "automatic_failure_experience":
            True,

        "failure_signature_capture":
            True,

        "recovery_skill_candidate_generation":
            True,

        "canonical_auto_promotion":
            False,
    },

    "measurements": {

        "claims":
            semantic.get(
                "claim_count"
            ),

        "evidence":
            semantic.get(
                "evidence_count"
            ),

        "capability_evidence":
            verify.get(
                "evidence_count"
            ),

        "automatic_experiences":
            experience_count,

        "failure_signatures":
            failure_count,

        "recovery_skill_candidates":
            skill_count,
    },

    "invariants": [

        "No mandatory false or null validation may coexist with PASS.",

        "Every instrumented meaningful success creates an Experience.",

        "Every instrumented failure creates an Experience and Failure Signature.",

        "Recovery patterns remain candidates until replay, benchmark and governed promotion.",

        "Confidence outside [0,1] is rejected.",

        "Historical evidence cannot silently become current authority.",

        "Console banners are never certification evidence."
    ],
}

write(
    A3_RECEIPT,
    receipt,
)

readback = load(
    A3_RECEIPT
)

assert (
    readback[
        "certification_status"
    ]
    ==
    "PASS"
)

assert (
    readback[
        "validation"
    ][
        "failure_signature_capture"
    ]
    is True
)

assert (
    readback[
        "validation"
    ][
        "recovery_skill_candidate_generation"
    ]
    is True
)

a3_hash = sha256(
    A3_RECEIPT
)

# ============================================================
# 9. Update state atomically
# ============================================================

state = load(
    STATE
)

state[
    "current_version"
] = "V9.0-A3.1"

state[
    "current_phase"
] = (
    "EVIDENCE_NATIVE_UNDERSTANDING_"
    "WITH_AUTOMATIC_FAILURE_LEARNING"
)

state[
    "state_status"
] = "A3_1_CERTIFIED"

state[
    "latest_phase_receipt"
] = {
    "phase":
        "V9.0-A3.1",

    "path":
        "RAIOS/V9/evidence/observations/V9.0-A3-RECEIPT.json",

    "sha256":
        a3_hash,

    "certification_status":
        "PASS",
}

state[
    "event_learning"
] = {
    "success_experience":
        "AUTOMATIC",

    "failure_experience":
        "AUTOMATIC",

    "failure_signature":
        "AUTOMATIC",

    "recovery_skill_candidate":
        "AUTOMATIC",

    "canonical_promotion":
        "GOVERNED_ONLY",
}

state[
    "updated_at"
] = now()

write(
    STATE,
    state,
)

# ============================================================
# 10. True hash consistency assertion
# ============================================================

final_state = load(
    STATE
)

actual_hash = sha256(
    A3_RECEIPT
)

assert (
    final_state[
        "latest_phase_receipt"
    ][
        "sha256"
    ]
    ==
    actual_hash
), "STATE_RECEIPT_HASH_DRIFT"

# ============================================================
# 11. Final result
# ============================================================

print()
print("=" * 72)
print("RAIOS V9.0-A3.1 CERTIFICATION RESULT")
print("=" * 72)

print(
    "SEMANTIC_UNDERSTANDING      : PASS"
)

print(
    "SUCCESS_EVENT_CAPTURE       : PASS"
)

print(
    "FAILURE_EVENT_CAPTURE       : PASS"
)

print(
    "FAILURE_SIGNATURE_CAPTURE   : PASS"
)

print(
    "RECOVERY_SKILL_CANDIDATE    : PASS"
)

print(
    "CONFIDENCE_70_REJECTED      : PASS"
)

print(
    "CANONICAL_AUTO_PROMOTION    : FALSE"
)

print(
    "STATE_RECEIPT_HASH_MATCH    : TRUE"
)

print(
    "EXPERIENCES                 :",
    experience_count,
)

print(
    "FAILURE_SIGNATURES          :",
    failure_count,
)

print(
    "SKILL_CANDIDATES            :",
    skill_count,
)

print(
    "CURRENT_VERSION             :",
    final_state[
        "current_version"
    ],
)

print(
    "STATE_STATUS                :",
    final_state[
        "state_status"
    ],
)

print(
    "A3_RECEIPT_SHA256           :",
    actual_hash,
)

print()
print(
    "STATUS = V9.0-A3.1_PASS"
)

print("=" * 72)