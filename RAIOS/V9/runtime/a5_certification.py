from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import uuid

from datetime import datetime, timezone
from pathlib import Path


REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
)

V9 = REPO / "RAIOS" / "V9"

RUNTIME = V9 / "runtime"

sys.path.insert(
    0,
    str(RUNTIME),
)

from cognitive_event_bus import (
    build_event,
    emit_event,
)

from evolution_brain import (
    FAILURE_FAMILIES,
    PATTERNS,
    RECOVERY_MEMORY,
    SKILL_CANDIDATES,
    REPLAY_QUEUE,
    PROCESSED_LEDGER,
    failure_family_id,
    load_json,
    process_all,
    status,
)


STATE = (
    V9 /
    "continuity" /
    "RAIOS-CURRENT-STATE.json"
)

RECEIPT = (
    V9 /
    "evidence" /
    "observations" /
    "V9.0-A5-RECEIPT.json"
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

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    temp.write_text(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    readback = json.loads(
        temp.read_text(
            encoding="utf-8"
        )
    )

    if readback != obj:
        raise RuntimeError(
            "A5_ATOMIC_READBACK_FAILED"
        )

    temp.replace(
        path
    )


print("=" * 76)
print("RAIOS V9.0-A5 TRUE FAIL-CLOSED CERTIFICATION")
print("=" * 76)

HEAD = subprocess.check_output(
    [
        "git",
        "rev-parse",
        "HEAD",
    ],
    cwd=REPO,
    text=True,
).strip()

print(
    "HEAD:",
    HEAD,
)

# ====================================================================
# 1. CERTIFY PREDECESSOR A4
# ====================================================================

state = load(
    STATE
)

assert (
    state.get(
        "current_version"
    )
    ==
    "V9.0-A4"
), (
    "A5_PREDECESSOR_NOT_A4:"
    +
    str(
        state.get(
            "current_version"
        )
    )
)

previous = (
    state.get(
        "latest_phase_receipt"
    )
    or
    {}
)

assert (
    previous.get(
        "phase"
    )
    ==
    "V9.0-A4"
)

assert (
    previous.get(
        "certification_status"
    )
    ==
    "PASS"
)

previous_path = (
    REPO /
    previous[
        "path"
    ]
)

assert (
    previous_path.exists()
)

previous_actual_hash = (
    sha256(
        previous_path
    )
)

assert (
    previous_actual_hash
    ==
    previous.get(
        "sha256"
    )
), "A4_RECEIPT_HASH_DRIFT"

print(
    "PREDECESSOR_A4             : PASS"
)

# ====================================================================
# 2. BASELINE EVOLUTION CONSUMPTION
# ====================================================================

baseline = process_all()

assert (
    baseline.get(
        "canonical_mutation"
    )
    is False
)

print(
    "BASELINE_CONSUMER          : PASS"
)

# ====================================================================
# 3. CREATE TWO SAME-ROOT FAILURES
# ====================================================================

correlation_1 = str(
    uuid.uuid4()
)

failure_1 = build_event(
    event_type="FAILURE",

    actor="RAIOS.A5.CERTIFIER",

    intent="Read required architecture artifact",

    tool="RAIOS.FILE.READER",

    correlation_id=
        correlation_1,

    success=False,

    output_ref={
        "exception_type":
            "FileNotFoundError",

        "message":
            "Required architecture file 101 was not found",
    },

    unresolved_flags=[
        "SOURCE_MISSING"
    ],

    evidence_refs=[
        "RAIOS/V9/runtime/a5_certification.py"
    ],

    confidence=1.0,
)

emit_event(
    failure_1
)

failure_2 = build_event(
    event_type="FAILURE",

    actor="RAIOS.A5.CERTIFIER",

    intent="Read required architecture artifact",

    tool="RAIOS.FILE.READER",

    correlation_id=
        str(
            uuid.uuid4()
        ),

    success=False,

    output_ref={
        "exception_type":
            "FileNotFoundError",

        "message":
            "Required architecture file 202 was not found",
    },

    unresolved_flags=[
        "SOURCE_MISSING"
    ],

    evidence_refs=[
        "RAIOS/V9/runtime/a5_certification.py"
    ],

    confidence=1.0,
)

emit_event(
    failure_2
)

expected_family_1 = (
    failure_family_id(
        failure_1
    )
)

expected_family_2 = (
    failure_family_id(
        failure_2
    )
)

assert (
    expected_family_1
    ==
    expected_family_2
), (
    "NORMALIZATION_FAILED_TO_COLLAPSE_SAME_ROOT"
)

pass_after_same = process_all()

same_family_path = (
    FAILURE_FAMILIES /
    (
        expected_family_1.replace(
            ":",
            "_"
        )
        +
        ".json"
    )
)

assert (
    same_family_path.exists()
)

same_family = load(
    same_family_path
)

assert (
    same_family[
        "occurrence_count"
    ]
    ==
    2
), (
    "SAME_ROOT_FAILURES_NOT_CLUSTERED"
)

assert (
    len(
        same_family[
            "source_event_ids"
        ]
    )
    ==
    2
)

print(
    "SAME_ROOT_CLUSTERING       : PASS"
)

# ====================================================================
# 4. CREATE DISTINCT FAILURE
# ====================================================================

failure_3 = build_event(
    event_type="FAILURE",

    actor="RAIOS.A5.CERTIFIER",

    intent="Parse architecture contract",

    tool="RAIOS.JSON.PARSER",

    correlation_id=
        str(
            uuid.uuid4()
        ),

    success=False,

    output_ref={
        "exception_type":
            "JSONDecodeError",

        "message":
            "Malformed JSON at line 77",
    },

    unresolved_flags=[
        "PARSE_FAILED"
    ],

    evidence_refs=[
        "RAIOS/V9/runtime/a5_certification.py"
    ],

    confidence=1.0,
)

emit_event(
    failure_3
)

distinct_family = (
    failure_family_id(
        failure_3
    )
)

assert (
    distinct_family
    !=
    expected_family_1
), (
    "DISTINCT_FAILURE_COLLAPSED_INCORRECTLY"
)

process_all()

distinct_path = (
    FAILURE_FAMILIES /
    (
        distinct_family.replace(
            ":",
            "_"
        )
        +
        ".json"
    )
)

assert (
    distinct_path.exists()
)

assert (
    len(
        [
            path
            for path
            in FAILURE_FAMILIES.glob(
                "*.json"
            )
            if load(
                path
            ).get(
                "family_id"
            )
            in {
                expected_family_1,
                distinct_family,
            }
        ]
    )
    ==
    2
)

print(
    "DISTINCT_FAILURE_ISOLATION : PASS"
)

# ====================================================================
# 5. VERIFY REPEATED EXPERIENCE PATTERN
# ====================================================================

repeated_patterns = []

for path in PATTERNS.glob(
    "*.json"
):
    pattern = load(
        path
    )

    if (
        pattern.get(
            "occurrence_count",
            0,
        )
        >=
        2
    ):
        repeated_patterns.append(
            pattern
        )

assert (
    repeated_patterns
), "NO_REPEATED_EXPERIENCE_PATTERN_FOUND"

print(
    "EXPERIENCE_PATTERN_MINING  : PASS"
)

# ====================================================================
# 6. BEFORE RECOVERY THERE MUST BE NO CANDIDATE FOR FAMILY
# ====================================================================

target_candidate_id = (
    "skill:"
    +
    expected_family_1
)

target_candidate_path = (
    SKILL_CANDIDATES /
    (
        target_candidate_id.replace(
            ":",
            "_"
        )
        +
        ".json"
    )
)

assert not (
    target_candidate_path.exists()
), (
    "SKILL_CANDIDATE_CREATED_WITHOUT_RECOVERY_EVIDENCE"
)

print(
    "CANDIDATE_EVIDENCE_GATE    : PASS"
)

# ====================================================================
# 7. SUCCESSFUL RECOVERY EVENT
# ====================================================================

recovery = build_event(
    event_type="RECOVERY",

    actor="RAIOS.A5.CERTIFIER",

    intent="Recover missing architecture artifact",

    tool="RAIOS.RECOVERY.TEST",

    correlation_id=
        correlation_1,

    causation_id=
        failure_1[
            "event_id"
        ],

    success=True,

    output_ref={
        "result":
            "RECOVERED"
    },

    evidence_refs=[
        "RAIOS/V9/runtime/a5_certification.py"
    ],

    confidence=1.0,

    metadata={
        "failure_family_id":
            expected_family_1,

        "recovery_success":
            True,

        "recovery_method":
            "RESTORE_VERIFIED_ARTIFACT",
    },
)

emit_event(
    recovery
)

recovery_pass = process_all()

same_family_after = load(
    same_family_path
)

assert (
    same_family_after[
        "successful_recoveries"
    ]
    ==
    1
), (
    "RECOVERY_OUTCOME_NOT_CONNECTED_TO_FAILURE_FAMILY"
)

assert (
    same_family_after[
        "failed_recoveries"
    ]
    ==
    0
)

assert (
    len(
        list(
            RECOVERY_MEMORY.glob(
                "*.json"
            )
        )
    )
    >=
    1
)

print(
    "RECOVERY_OUTCOME_MEMORY    : PASS"
)

# ====================================================================
# 8. SKILL CANDIDATE MUST NOW EXIST
# ====================================================================

assert (
    target_candidate_path.exists()
), (
    "QUALIFIED_SKILL_CANDIDATE_NOT_CREATED"
)

candidate = load(
    target_candidate_path
)

assert (
    candidate[
        "candidate_id"
    ]
    ==
    target_candidate_id
)

assert (
    candidate[
        "status"
    ]
    ==
    "REVIEW_REQUIRED"
)

assert (
    candidate[
        "canonical_promotion"
    ]
    is False
)

assert (
    0.0
    <=
    float(
        candidate[
            "evidence_score"
        ]
    )
    <=
    1.0
)

assert (
    float(
        candidate[
            "evidence_score"
        ]
    )
    >=
    0.60
)

assert (
    candidate[
        "occurrence_count"
    ]
    ==
    2
)

assert (
    candidate[
        "successful_recoveries"
    ]
    ==
    1
)

print(
    "SKILL_CANDIDATE_MINING     : PASS"
)

print(
    "EVIDENCE_SCORE_BOUNDARY    : PASS"
)

print(
    "AUTO_PROMOTION             : FALSE"
)

# ====================================================================
# 9. REPLAY QUEUE
# ====================================================================

target_replay_id = (
    "replay:"
    +
    target_candidate_id
)

target_replay_path = (
    REPLAY_QUEUE /
    (
        target_replay_id.replace(
            ":",
            "_"
        )
        +
        ".json"
    )
)

assert (
    target_replay_path.exists()
), (
    "REPLAY_JOB_NOT_CREATED"
)

replay_job = load(
    target_replay_path
)

assert (
    replay_job[
        "status"
    ]
    ==
    "QUEUED"
)

assert (
    replay_job[
        "canonical_mutation"
    ]
    is False
)

print(
    "REPLAY_QUEUE               : PASS"
)

# ====================================================================
# 10. IDEMPOTENCY TEST
# ====================================================================

family_hash_before = sha256(
    same_family_path
)

candidate_hash_before = sha256(
    target_candidate_path
)

replay_hash_before = sha256(
    target_replay_path
)

recovery_count_before = len(
    list(
        RECOVERY_MEMORY.glob(
            "*.json"
        )
    )
)

processed_lines_before = (
    len(
        PROCESSED_LEDGER.read_text(
            encoding="utf-8-sig"
        ).splitlines()
    )
)

second_pass = process_all()

family_hash_after = sha256(
    same_family_path
)

candidate_hash_after = sha256(
    target_candidate_path
)

replay_hash_after = sha256(
    target_replay_path
)

recovery_count_after = len(
    list(
        RECOVERY_MEMORY.glob(
            "*.json"
        )
    )
)

processed_lines_after = (
    len(
        PROCESSED_LEDGER.read_text(
            encoding="utf-8-sig"
        ).splitlines()
    )
)

assert (
    family_hash_before
    ==
    family_hash_after
), "A5_IDEMPOTENCY_FAMILY_DRIFT"

assert (
    replay_hash_before
    ==
    replay_hash_after
), "A5_IDEMPOTENCY_REPLAY_DRIFT"

assert (
    recovery_count_before
    ==
    recovery_count_after
), "A5_DUPLICATE_RECOVERY_OUTCOME"

assert (
    processed_lines_before
    ==
    processed_lines_after
), "A5_DUPLICATE_PROCESSED_LEDGER_ENTRY"

# Candidate updated_at may legitimately refresh during candidate mining.
# Therefore identity/count are tested rather than requiring byte hash equality.

candidate_after = load(
    target_candidate_path
)

assert (
    candidate_after[
        "candidate_id"
    ]
    ==
    candidate[
        "candidate_id"
    ]
)

assert (
    candidate_after[
        "occurrence_count"
    ]
    ==
    candidate[
        "occurrence_count"
    ]
)

assert (
    candidate_after[
        "successful_recoveries"
    ]
    ==
    candidate[
        "successful_recoveries"
    ]
)

assert (
    len(
        [
            p
            for p
            in SKILL_CANDIDATES.glob(
                "*.json"
            )
            if load(
                p
            ).get(
                "candidate_id"
            )
            ==
            target_candidate_id
        ]
    )
    ==
    1
), (
    "DUPLICATE_SKILL_CANDIDATE"
)

print(
    "EVOLUTION_IDEMPOTENCY      : PASS"
)

print(
    "CANDIDATE_DEDUPLICATION    : PASS"
)

# ====================================================================
# 11. FINAL STATUS / SAFETY
# ====================================================================

final_status = status()

assert (
    final_status[
        "canonical_auto_promotion"
    ]
    is False
)

assert (
    final_status[
        "failure_family_count"
    ]
    >=
    2
)

assert (
    final_status[
        "skill_candidate_count"
    ]
    >=
    1
)

assert (
    final_status[
        "replay_queue_count"
    ]
    >=
    1
)

# No candidate may be promoted automatically.

for item in final_status[
    "candidates"
]:
    assert (
        item.get(
            "canonical_promotion"
        )
        is False
    )

    assert (
        item.get(
            "status"
        )
        ==
        "REVIEW_REQUIRED"
    )

print(
    "PROMOTION_GOVERNANCE       : PASS"
)

# ====================================================================
# 12. BUILD RECEIPT
# ====================================================================

family_count = len(
    list(
        FAILURE_FAMILIES.glob(
            "*.json"
        )
    )
)

pattern_count = len(
    list(
        PATTERNS.glob(
            "*.json"
        )
    )
)

recovery_count = len(
    list(
        RECOVERY_MEMORY.glob(
            "*.json"
        )
    )
)

candidate_count = len(
    list(
        SKILL_CANDIDATES.glob(
            "*.json"
        )
    )
)

replay_count = len(
    list(
        REPLAY_QUEUE.glob(
            "*.json"
        )
    )
)

receipt = {
    "schema":
        "raios.v9.a5.receipt.v1",

    "phase":
        "V9.0-A5",

    "certification_status":
        "PASS",

    "certification_mode":
        "FAIL_CLOSED",

    "repository_sha":
        HEAD,

    "timestamp":
        now(),

    "predecessor": {
        "phase":
            "V9.0-A4",

        "path":
            previous[
                "path"
            ],

        "sha256":
            previous_actual_hash,

        "status":
            "PASS",
    },

    "architecture": {
        "evolution_brain_consumers":
            "ACTIVE_BOOTSTRAP_CERTIFIED",

        "failure_clustering":
            "ACTIVE",

        "experience_pattern_mining":
            "ACTIVE",

        "recovery_outcome_memory":
            "ACTIVE",

        "skill_candidate_mining":
            "ACTIVE",

        "replay_queue":
            "ACTIVE",

        "candidate_deduplication":
            "ACTIVE",

        "canonical_auto_promotion":
            False,
    },

    "validation": {
        "a4_predecessor_verified":
            True,

        "same_root_failure_clustering":
            True,

        "distinct_failure_isolation":
            True,

        "experience_pattern_mining":
            True,

        "recovery_outcome_memory":
            True,

        "candidate_evidence_threshold":
            True,

        "skill_candidate_generation":
            True,

        "evidence_score_strict_0_1":
            True,

        "replay_queue_generation":
            True,

        "consumer_idempotency":
            True,

        "candidate_deduplication":
            True,

        "canonical_auto_promotion":
            False,
    },

    "tested_family": {
        "family_id":
            expected_family_1,

        "occurrences":
            same_family_after[
                "occurrence_count"
            ],

        "successful_recoveries":
            same_family_after[
                "successful_recoveries"
            ],

        "failed_recoveries":
            same_family_after[
                "failed_recoveries"
            ],

        "candidate_id":
            target_candidate_id,

        "candidate_score":
            candidate_after[
                "evidence_score"
            ],
    },

    "measurements": {
        "failure_families":
            family_count,

        "experience_patterns":
            pattern_count,

        "recovery_outcomes":
            recovery_count,

        "skill_candidates":
            candidate_count,

        "replay_jobs":
            replay_count,
    },

    "invariants": [
        "Raw events do not become skills directly.",

        "EVENT -> EXPERIENCE -> PATTERN -> CANDIDATE -> VERIFIED SKILL is the required maturation path.",

        "Repeated failures are clustered by normalized failure geometry, not event identity.",

        "Distinct failure geometry must not be collapsed merely because failures are temporally adjacent.",

        "A recovery skill candidate requires repeated failure evidence and successful recovery evidence.",

        "Candidate confidence/evidence scores remain bounded to [0,1].",

        "Evolution consumption is idempotent by source event_id.",

        "A candidate maps deterministically to one failure family.",

        "Replay is mandatory before verification or promotion.",

        "Skill candidates cannot promote themselves.",

        "Canonical state mutation remains governed.",

        "No PASS receipt is written before every mandatory assertion succeeds."
    ],

    "known_limits": [
        "A5 failure clustering currently uses deterministic normalized failure geometry.",

        "Embedding-based or learned clustering is intentionally deferred until evidence justifies it.",

        "Replay execution is queued but the replay executor is not yet certified.",

        "Benchmark execution is not yet part of A5.",

        "Cross-environment family generalization requires future Environment Memory integration.",

        "Recovery causality is explicit for certified events but broad automatic root-cause inference is not yet implemented."
    ],
}

write(
    RECEIPT,
    receipt,
)

receipt_readback = load(
    RECEIPT
)

assert (
    receipt_readback[
        "certification_status"
    ]
    ==
    "PASS"
)

assert (
    receipt_readback[
        "validation"
    ][
        "canonical_auto_promotion"
    ]
    is False
)

assert (
    receipt_readback[
        "validation"
    ][
        "same_root_failure_clustering"
    ]
    is True
)

assert (
    receipt_readback[
        "validation"
    ][
        "consumer_idempotency"
    ]
    is True
)

receipt_hash = sha256(
    RECEIPT
)

# ====================================================================
# 13. UPDATE CURRENT STATE
# ====================================================================

state = load(
    STATE
)

state[
    "current_version"
] = "V9.0-A5"

state[
    "current_phase"
] = "EVOLUTION_BRAIN_PATTERN_AND_SKILL_MINING"

state[
    "state_status"
] = "A5_CERTIFIED"

active = state.get(
    "active_architecture",
    [],
)

for capability in (
    "EVOLUTION_BRAIN_CONSUMERS",
    "FAILURE_FAMILY_CLUSTERING",
    "EXPERIENCE_PATTERN_MINING",
    "RECOVERY_OUTCOME_MEMORY",
    "SKILL_CANDIDATE_MINER",
    "REPLAY_QUEUE",
):

    if capability not in active:
        active.append(
            capability
        )

state[
    "active_architecture"
] = active

state[
    "evolution_brain"
] = {
    "consumer_status":
        "ACTIVE_BOOTSTRAP_CERTIFIED",

    "source":
        "COGNITIVE_WAL",

    "failure_clustering":
        "DETERMINISTIC_NORMALIZED_GEOMETRY",

    "pattern_mining":
        "ACTIVE",

    "recovery_memory":
        "ACTIVE",

    "skill_candidate_mining":
        "ACTIVE",

    "replay_queue":
        "ACTIVE",

    "canonical_auto_promotion":
        False,

    "maturation_path": [
        "EVENT",
        "EXPERIENCE",
        "PATTERN",
        "CANDIDATE",
        "REPLAY",
        "BENCHMARK",
        "VERIFICATION",
        "GOVERNED_PROMOTION",
    ],
}

state[
    "latest_phase_receipt"
] = {
    "phase":
        "V9.0-A5",

    "path":
        "RAIOS/V9/evidence/observations/V9.0-A5-RECEIPT.json",

    "sha256":
        receipt_hash,

    "certification_status":
        "PASS",
}

state[
    "updated_at"
] = now()

write(
    STATE,
    state,
)

# ====================================================================
# 14. TRUE STATE HASH CONSISTENCY
# ====================================================================

final_state = load(
    STATE
)

actual_receipt_hash = sha256(
    RECEIPT
)

assert (
    final_state[
        "latest_phase_receipt"
    ][
        "sha256"
    ]
    ==
    actual_receipt_hash
), "A5_STATE_RECEIPT_HASH_DRIFT"

assert (
    final_state[
        "current_version"
    ]
    ==
    "V9.0-A5"
)

assert (
    final_state[
        "state_status"
    ]
    ==
    "A5_CERTIFIED"
)

# ====================================================================
# 15. FINAL RESULT
# ====================================================================

print()
print("=" * 76)
print("RAIOS V9.0-A5 CERTIFICATION RESULT")
print("=" * 76)

print(
    "PREDECESSOR_A4             : PASS"
)

print(
    "EVOLUTION_CONSUMER         : PASS"
)

print(
    "SAME_ROOT_CLUSTERING       : PASS"
)

print(
    "DISTINCT_FAILURE_ISOLATION : PASS"
)

print(
    "EXPERIENCE_PATTERN_MINING  : PASS"
)

print(
    "RECOVERY_OUTCOME_MEMORY    : PASS"
)

print(
    "SKILL_CANDIDATE_MINING     : PASS"
)

print(
    "EVIDENCE_SCORE_BOUNDARY    : PASS"
)

print(
    "REPLAY_QUEUE               : PASS"
)

print(
    "EVOLUTION_IDEMPOTENCY      : PASS"
)

print(
    "CANDIDATE_DEDUPLICATION    : PASS"
)

print(
    "CANONICAL_AUTO_PROMOTION   : FALSE"
)

print(
    "STATE_RECEIPT_HASH_MATCH   : TRUE"
)

print()

print(
    "FAILURE_FAMILIES           :",
    family_count,
)

print(
    "EXPERIENCE_PATTERNS        :",
    pattern_count,
)

print(
    "RECOVERY_OUTCOMES          :",
    recovery_count,
)

print(
    "SKILL_CANDIDATES           :",
    candidate_count,
)

print(
    "REPLAY_JOBS                :",
    replay_count,
)

print()

print(
    "TESTED_FAMILY              :",
    expected_family_1,
)

print(
    "TESTED_OCCURRENCES         :",
    same_family_after[
        "occurrence_count"
    ],
)

print(
    "SUCCESSFUL_RECOVERIES      :",
    same_family_after[
        "successful_recoveries"
    ],
)

print(
    "CANDIDATE_SCORE            :",
    candidate_after[
        "evidence_score"
    ],
)

print()

print(
    "CURRENT_VERSION            :",
    final_state[
        "current_version"
    ],
)

print(
    "STATE_STATUS               :",
    final_state[
        "state_status"
    ],
)

print(
    "A5_RECEIPT_SHA256          :",
    actual_receipt_hash,
)

print()

print(
    "STATUS = V9.0-A5_PASS"
)

print("=" * 76)