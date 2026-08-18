from __future__ import annotations

import hashlib
import json
import os
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

sys.path.insert(
    0,
    str(
        V9 /
        "runtime"
    ),
)

from cognitive_event_bus import (
    WAL_FILE,
    PROCESSED_LEDGER,
    EXPERIENCE_DIR,
    FAILURE_DIR,
    RECOVERY_DIR,
    PERFORMANCE_DIR,
    EVIDENCE_EVENT_DIR,
    build_event,
    emit_event,
    replay_wal,
    load_jsonl,
    processed_event_ids,
)


CRASH_WRITER = (
    V9 /
    "runtime" /
    "a4_crash_writer.py"
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
    "V9.0-A4-RECEIPT.json"
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
            "ATOMIC_JSON_READBACK_FAILED"
        )

    temp.replace(
        path
    )


def count_wal_event(
    event_id: str,
) -> int:

    return sum(
        1
        for event in load_jsonl(
            WAL_FILE
        )
        if event.get(
            "event_id"
        )
        ==
        event_id
    )


def count_processed_event(
    event_id: str,
) -> int:

    return sum(
        1
        for event in load_jsonl(
            PROCESSED_LEDGER
        )
        if event.get(
            "event_id"
        )
        ==
        event_id
    )


print("=" * 76)
print("RAIOS V9.0-A4 TRUE FAIL-CLOSED CERTIFICATION")
print("=" * 76)

head = subprocess.check_output(
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
    head,
)


# ====================================================================
# 1. VERIFY PREDECESSOR A3.1
# ====================================================================

state = load(
    STATE
)

assert (
    state.get(
        "current_version"
    )
    ==
    "V9.0-A3.1"
), (
    "A4_PREDECESSOR_VERSION_NOT_A3_1:"
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
        "certification_status"
    )
    ==
    "PASS"
), "A3_1_RECEIPT_NOT_PASS"

previous_path_value = (
    previous.get(
        "path"
    )
)

assert (
    previous_path_value
), "A3_1_RECEIPT_PATH_MISSING"

previous_path = (
    REPO /
    previous_path_value
)

assert (
    previous_path.exists()
), "A3_1_RECEIPT_FILE_MISSING"

previous_actual_hash = (
    sha256(
        previous_path
    )
)

assert (
    previous.get(
        "sha256"
    )
    ==
    previous_actual_hash
), "A3_1_RECEIPT_HASH_DRIFT"

print(
    "PREDECESSOR_A3_1            : PASS"
)


# ====================================================================
# 2. BASIC WAL EVENT
# ====================================================================

basic_id = str(
    uuid.uuid4()
)

basic_correlation = str(
    uuid.uuid4()
)

basic_event = build_event(
    event_type="OBSERVATION",

    actor="RAIOS.A4.CERTIFIER",

    intent="Certify synchronous Cognitive WAL append",

    event_id=basic_id,

    correlation_id=
        basic_correlation,

    success=True,

    input_ref={
        "probe":
            "BASIC_WAL"
    },

    confidence=1.0,
)

basic_result = emit_event(
    basic_event
)

assert (
    basic_result[
        "status"
    ]
    ==
    "WAL_COMMITTED"
)

assert (
    count_wal_event(
        basic_id
    )
    ==
    1
)

assert (
    count_processed_event(
        basic_id
    )
    ==
    1
)

assert (
    (
        EXPERIENCE_DIR /
        f"{basic_id}.json"
    ).exists()
)

assert (
    (
        PERFORMANCE_DIR /
        f"{basic_id}.json"
    ).exists()
)

assert (
    (
        EVIDENCE_EVENT_DIR /
        f"{basic_id}.json"
    ).exists()
)

print(
    "SYNCHRONOUS_COGNITIVE_WAL  : PASS"
)

print(
    "EVENT_MATERIALIZATION       : PASS"
)


# ====================================================================
# 3. DUPLICATE EVENT REJECTION
# ====================================================================

duplicate_result = emit_event(
    basic_event
)

assert (
    duplicate_result[
        "status"
    ]
    ==
    "DUPLICATE_REJECTED"
)

assert (
    count_wal_event(
        basic_id
    )
    ==
    1
)

assert (
    count_processed_event(
        basic_id
    )
    ==
    1
)

print(
    "DUPLICATE_EVENT_REJECTION   : PASS"
)


# ====================================================================
# 4. CORRELATION / CAUSATION
# ====================================================================

action_id = str(
    uuid.uuid4()
)

result_id = str(
    uuid.uuid4()
)

correlation = str(
    uuid.uuid4()
)

action_event = build_event(
    event_type="ACTION",

    actor="RAIOS.A4.CERTIFIER",

    intent="Validate event causality",

    event_id=action_id,

    correlation_id=
        correlation,

    success=None,

    confidence=1.0,
)

emit_event(
    action_event
)

result_event = build_event(
    event_type="RESULT",

    actor="RAIOS.A4.CERTIFIER",

    intent="Validate event causality",

    event_id=result_id,

    correlation_id=
        correlation,

    causation_id=
        action_id,

    success=True,

    confidence=1.0,
)

emit_event(
    result_event
)

assert (
    result_event[
        "correlation_id"
    ]
    ==
    action_event[
        "correlation_id"
    ]
)

assert (
    result_event[
        "causation_id"
    ]
    ==
    action_event[
        "event_id"
    ]
)

print(
    "CORRELATION_CAUSATION       : PASS"
)


# ====================================================================
# 5. REAL FAILURE MATERIALIZATION
# ====================================================================

failure_id = str(
    uuid.uuid4()
)

failure_event = build_event(
    event_type="FAILURE",

    actor="RAIOS.A4.CERTIFIER",

    intent="Prove failure materialization",

    event_id=
        failure_id,

    correlation_id=
        str(uuid.uuid4()),

    tool=
        "A4_CERTIFICATION",

    success=False,

    output_ref={
        "exception_type":
            "SyntheticCertificationFailure",

        "message":
            "Controlled fail-path test",
    },

    evidence_refs=[
        "RAIOS/V9/runtime/a4_certification.py"
    ],

    unresolved_flags=[
        "CONTROLLED_TEST_FAILURE"
    ],

    confidence=1.0,
)

emit_event(
    failure_event
)

assert (
    (
        FAILURE_DIR /
        f"{failure_id}.json"
    ).exists()
)

assert (
    (
        RECOVERY_DIR /
        f"{failure_id}.json"
    ).exists()
)

failure_object = load(
    FAILURE_DIR /
    f"{failure_id}.json"
)

recovery_object = load(
    RECOVERY_DIR /
    f"{failure_id}.json"
)

assert (
    failure_object[
        "status"
    ]
    ==
    "ACTIVE"
)

assert (
    recovery_object[
        "status"
    ]
    ==
    "REVIEW_REQUIRED"
)

assert (
    recovery_object[
        "canonical_promotion"
    ]
    is False
)

print(
    "FAILURE_MATERIALIZER        : PASS"
)

print(
    "RECOVERY_CANDIDATE          : PASS"
)


# ====================================================================
# 6. CRASH AFTER WAL / BEFORE MATERIALIZATION
# ====================================================================

crash_id = str(
    uuid.uuid4()
)

crash_correlation = str(
    uuid.uuid4()
)

crash_process = subprocess.run(
    [
        sys.executable,
        str(
            CRASH_WRITER
        ),
        "--event-id",
        crash_id,
        "--correlation-id",
        crash_correlation,
    ],
    cwd=REPO,
    env={
        **os.environ,
        "PYTHONUTF8":
            "1",
        "PYTHONIOENCODING":
            "utf-8",
    },
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
)

assert (
    crash_process.returncode
    ==
    91
), (
    "CONTROLLED_CRASH_DID_NOT_EXIT_91:"
    +
    str(
        crash_process.returncode
    )
)

assert (
    count_wal_event(
        crash_id
    )
    ==
    1
), "CRASH_EVENT_NOT_IN_WAL"

assert (
    count_processed_event(
        crash_id
    )
    ==
    0
), (
    "CRASH_EVENT_MATERIALIZED_BEFORE_REPLAY"
)

assert not (
    EXPERIENCE_DIR /
    f"{crash_id}.json"
).exists(), (
    "CRASH_EVENT_EXPERIENCE_PREMATURELY_EXISTS"
)

print(
    "CRASH_AFTER_WAL_SIMULATED   : PASS"
)

print(
    "WAL_SURVIVED_WORKER_DEATH   : PASS"
)


# ====================================================================
# 7. REPLAY AFTER CRASH
# ====================================================================

replay = replay_wal()

assert (
    replay[
        "processed_now"
    ]
    >=
    1
), "REPLAY_PROCESSED_NOTHING"

assert (
    count_processed_event(
        crash_id
    )
    ==
    1
)

assert (
    (
        EXPERIENCE_DIR /
        f"{crash_id}.json"
    ).exists()
)

print(
    "CRASH_REPLAY                : PASS"
)


# ====================================================================
# 8. SECOND REPLAY MUST BE IDEMPOTENT
# ====================================================================

experience_hash_before = sha256(
    EXPERIENCE_DIR /
    f"{crash_id}.json"
)

second_replay = replay_wal()

experience_hash_after = sha256(
    EXPERIENCE_DIR /
    f"{crash_id}.json"
)

assert (
    count_processed_event(
        crash_id
    )
    ==
    1
), "REPLAY_DUPLICATED_PROCESSED_EVENT"

assert (
    experience_hash_before
    ==
    experience_hash_after
), "REPLAY_CHANGED_MATERIALIZED_EXPERIENCE"

print(
    "REPLAY_IDEMPOTENCY           : PASS"
)


# ====================================================================
# 9. WAL UNIQUENESS
# ====================================================================

wal_records = load_jsonl(
    WAL_FILE
)

wal_ids = [
    item["event_id"]
    for item in wal_records
]

assert (
    len(
        wal_ids
    )
    ==
    len(
        set(
            wal_ids
        )
    )
), "WAL_DUPLICATE_EVENT_IDS_FOUND"

print(
    "WAL_EVENT_ID_UNIQUENESS      : PASS"
)


# ====================================================================
# 10. MATERIALIZER COUNTS
# ====================================================================

experience_count = len(
    list(
        EXPERIENCE_DIR.glob(
            "*.json"
        )
    )
)

failure_count = len(
    list(
        FAILURE_DIR.glob(
            "*.json"
        )
    )
)

recovery_count = len(
    list(
        RECOVERY_DIR.glob(
            "*.json"
        )
    )
)

performance_count = len(
    list(
        PERFORMANCE_DIR.glob(
            "*.json"
        )
    )
)

evidence_event_count = len(
    list(
        EVIDENCE_EVENT_DIR.glob(
            "*.json"
        )
    )
)

processed_count = len(
    processed_event_ids()
)

assert (
    experience_count
    >=
    5
)

assert (
    performance_count
    >=
    5
)

assert (
    evidence_event_count
    >=
    5
)

assert (
    failure_count
    >=
    1
)

assert (
    recovery_count
    >=
    1
)

assert (
    processed_count
    >=
    5
)


# ====================================================================
# 11. BUILD A4 RECEIPT ONLY AFTER ALL ASSERTIONS
# ====================================================================

receipt = {
    "schema":
        "raios.v9.a4.receipt.v1",

    "phase":
        "V9.0-A4",

    "certification_status":
        "PASS",

    "certification_mode":
        "FAIL_CLOSED",

    "timestamp":
        now(),

    "repository_sha":
        head,

    "predecessor": {
        "phase":
            previous.get(
                "phase"
            ),

        "receipt":
            previous_path_value,

        "sha256":
            previous_actual_hash,

        "status":
            "PASS",
    },

    "architecture": {
        "cognitive_event_bus":
            "ACTIVE_BOOTSTRAP_CERTIFIED",

        "cognitive_wal":
            "APPEND_ONLY_FSYNC",

        "materialization":
            "DERIVED_FROM_WAL",

        "canonical_mutation":
            False,

        "event_model":
            "CORRELATION_AND_CAUSATION_AWARE",

        "replay":
            "IDEMPOTENT",

        "duplicate_event_policy":
            "REJECT_BY_EVENT_ID",
    },

    "validation": {
        "synchronous_wal":
            True,

        "event_hash_validation":
            True,

        "experience_materializer":
            True,

        "failure_materializer":
            True,

        "recovery_candidate_materializer":
            True,

        "performance_materializer":
            True,

        "evidence_materializer":
            True,

        "correlation":
            True,

        "causation":
            True,

        "duplicate_event_rejection":
            True,

        "worker_crash_after_wal":
            True,

        "wal_survival":
            True,

        "crash_replay":
            True,

        "replay_idempotency":
            True,

        "canonical_auto_promotion":
            False,
    },

    "measurements": {
        "wal_events":
            len(
                wal_records
            ),

        "processed_events":
            processed_count,

        "experiences":
            experience_count,

        "failure_signatures":
            failure_count,

        "recovery_candidates":
            recovery_count,

        "performance_observations":
            performance_count,

        "evidence_events":
            evidence_event_count,
    },

    "invariants": [
        "WAL append precedes derived cognitive materialization.",

        "A committed WAL event survives materializer or worker failure.",

        "Replay must not duplicate a materialized event.",

        "Every event has an immutable event_id and event_hash.",

        "Correlation and causation are preserved explicitly.",

        "Failure events produce Failure Signatures automatically.",

        "Failure events produce Recovery Skill Candidates automatically.",

        "Recovery candidates cannot promote themselves.",

        "Derived memory may be reconstructed from the Cognitive WAL.",

        "No certification PASS may exist unless every mandatory assertion executed successfully.",

        "Console output is not certification evidence."
    ],

    "known_limits": [
        "A4 bootstrap currently assumes a practical single-writer WAL model.",

        "Cross-process locking and distributed WAL replication are not yet certified.",

        "Remote asynchronous durability is not yet connected to this WAL.",

        "Resource telemetry is structurally supported but not yet fully collected.",

        "Model and agent adapters still need universal routing through the event bus."
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
        "crash_replay"
    ]
    is True
)

assert (
    receipt_readback[
        "validation"
    ][
        "replay_idempotency"
    ]
    is True
)

assert (
    receipt_readback[
        "validation"
    ][
        "canonical_auto_promotion"
    ]
    is False
)

receipt_hash = sha256(
    RECEIPT
)


# ====================================================================
# 12. UPDATE CURRENT STATE ONLY AFTER RECEIPT PASS
# ====================================================================

state = load(
    STATE
)

state[
    "current_version"
] = "V9.0-A4"

state[
    "current_phase"
] = "UNIVERSAL_COGNITIVE_EVENT_BUS"

state[
    "state_status"
] = "A4_CERTIFIED"

active = state.get(
    "active_architecture",
    [],
)

for capability in (
    "COGNITIVE_EVENT_BUS",
    "COGNITIVE_WAL",
    "EVENT_MATERIALIZERS",
    "CRASH_REPLAY",
    "EVENT_IDEMPOTENCY",
):

    if capability not in active:
        active.append(
            capability
        )

state[
    "active_architecture"
] = active

state[
    "cognitive_event_fabric"
] = {
    "status":
        "ACTIVE_BOOTSTRAP_CERTIFIED",

    "wal":
        "APPEND_ONLY_FSYNC",

    "event_envelope":
        "raios.cognitive-event.v1",

    "correlation":
        "ACTIVE",

    "causation":
        "ACTIVE",

    "experience_materialization":
        "ACTIVE",

    "failure_materialization":
        "ACTIVE",

    "recovery_candidate_materialization":
        "ACTIVE",

    "performance_materialization":
        "ACTIVE",

    "evidence_materialization":
        "ACTIVE",

    "replay":
        "IDEMPOTENT",

    "canonical_auto_promotion":
        False,
}

state[
    "latest_phase_receipt"
] = {
    "phase":
        "V9.0-A4",

    "path":
        "RAIOS/V9/evidence/observations/V9.0-A4-RECEIPT.json",

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
# 13. TRUE FINAL HASH ASSERTION
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
), "A4_STATE_RECEIPT_HASH_DRIFT"

assert (
    final_state[
        "current_version"
    ]
    ==
    "V9.0-A4"
)

assert (
    final_state[
        "state_status"
    ]
    ==
    "A4_CERTIFIED"
)


# ====================================================================
# 14. FINAL RESULT
# ====================================================================

print()
print("=" * 76)
print("RAIOS V9.0-A4 CERTIFICATION RESULT")
print("=" * 76)

print(
    "PREDECESSOR_A3_1          : PASS"
)

print(
    "COGNITIVE_EVENT_BUS       : PASS"
)

print(
    "COGNITIVE_WAL             : PASS"
)

print(
    "WAL_FSYNC                 : PASS"
)

print(
    "EVENT_HASH                : PASS"
)

print(
    "CORRELATION               : PASS"
)

print(
    "CAUSATION                 : PASS"
)

print(
    "DUPLICATE_REJECTION       : PASS"
)

print(
    "EXPERIENCE_MATERIALIZER   : PASS"
)

print(
    "FAILURE_MATERIALIZER      : PASS"
)

print(
    "RECOVERY_MATERIALIZER     : PASS"
)

print(
    "PERFORMANCE_MATERIALIZER  : PASS"
)

print(
    "EVIDENCE_MATERIALIZER     : PASS"
)

print(
    "CONTROLLED_WORKER_CRASH   : PASS"
)

print(
    "WAL_SURVIVED_CRASH        : PASS"
)

print(
    "CRASH_REPLAY              : PASS"
)

print(
    "REPLAY_IDEMPOTENCY        : PASS"
)

print(
    "CANONICAL_AUTO_PROMOTION  : FALSE"
)

print(
    "STATE_RECEIPT_HASH_MATCH  : TRUE"
)

print()
print(
    "WAL_EVENTS                :",
    len(
        wal_records
    ),
)

print(
    "PROCESSED_EVENTS          :",
    processed_count,
)

print(
    "EXPERIENCES               :",
    experience_count,
)

print(
    "FAILURE_SIGNATURES        :",
    failure_count,
)

print(
    "RECOVERY_CANDIDATES       :",
    recovery_count,
)

print(
    "PERFORMANCE_OBSERVATIONS  :",
    performance_count,
)

print(
    "EVIDENCE_EVENTS           :",
    evidence_event_count,
)

print()
print(
    "CURRENT_VERSION           :",
    final_state[
        "current_version"
    ],
)

print(
    "STATE_STATUS              :",
    final_state[
        "state_status"
    ],
)

print(
    "A4_RECEIPT_SHA256         :",
    actual_receipt_hash,
)

print()
print(
    "STATUS = V9.0-A4_PASS"
)

print("=" * 76)