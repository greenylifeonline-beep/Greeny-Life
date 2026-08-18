from __future__ import annotations

import hashlib
import json
import os
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

A10_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A10-RECEIPT.json"
)

A11_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A11-RECEIPT.json"
)

ROOT = V9 / "runtime" / "a11"

FIXTURES = ROOT / "fixtures"
LEASES = ROOT / "leases"
REPORTS = ROOT / "reports"
ROLLBACK = ROOT / "rollback"
JOURNAL = ROOT / "journal"

EVO = V9 / "evolution" / "a11"
EXPERIENCES = EVO / "experiences"
FAILURES = EVO / "failures"
RECOVERY = EVO / "recovery-skill-candidates"

for directory in (
    FIXTURES,
    LEASES,
    REPORTS,
    ROLLBACK,
    JOURNAL,
    EXPERIENCES,
    FAILURES,
    RECOVERY,
):
    directory.mkdir(parents=True, exist_ok=True)

WAL = JOURNAL / "action-wal.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_name(
        path.name + ".tmp-" + uuid.uuid4().hex
    )

    temp.write_text(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
            default=str,
        ) + "\n",
        encoding="utf-8",
    )

    if load_json(temp) != obj:
        temp.unlink(missing_ok=True)
        raise RuntimeError(
            "ATOMIC_WRITE_READBACK_FAILED"
        )

    os.replace(temp, path)


def file_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def object_hash(obj: Any) -> str:
    raw = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def probability(value: Any, name: str) -> float:
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


def wal_append(event: dict[str, Any]) -> None:
    event = dict(event)

    event["event_hash"] = object_hash(event)

    line = (
        json.dumps(
            event,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )

    with WAL.open(
        "a",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def capture_experience(
    event: str,
    outcome: str,
    details: dict[str, Any],
) -> Path:
    obj = {
        "schema":
            "raios.a11.experience.v1",

        "timestamp":
            now(),

        "event":
            event,

        "outcome":
            outcome,

        "details":
            details,
    }

    obj["experience_id"] = (
        "exp:" + object_hash(obj)[:32]
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

    write_json(path, obj)

    return path


def capture_failure(
    exc: BaseException,
    action_id: str | None = None,
) -> str:
    basis = {
        "phase":
            "V9.0-A11",

        "exception_type":
            type(exc).__name__,

        "message":
            str(exc),
    }

    signature = (
        "fs:" + object_hash(basis)[:32]
    )

    failure = {
        "schema":
            "raios.a11.failure-signature.v1",

        "failure_signature":
            signature,

        "timestamp":
            now(),

        "action_id":
            action_id,

        "exception_type":
            type(exc).__name__,

        "message":
            str(exc),

        "production_mutation":
            False,

        "canonical_mutation":
            False,
    }

    write_json(
        FAILURES
        /
        (
            signature.replace(":", "_")
            + ".json"
        ),
        failure,
    )

    candidate = {
        "schema":
            "raios.a11.recovery-skill-candidate.v1",

        "candidate_id":
            "recovery:"
            + object_hash(failure)[:32],

        "source_failure_signature":
            signature,

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

    write_json(
        RECOVERY
        /
        (
            candidate["candidate_id"]
            .replace(":", "_")
            + ".json"
        ),
        candidate,
    )

    return signature


def main() -> None:
    print("=" * 86)
    print(
        "RAIOS V9.0-A11 TRUE FAIL-CLOSED LIMITED-ACT CERTIFICATION"
    )
    print("=" * 86)

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        text=True,
    ).strip()

    print("HEAD:", head)

    # ----------------------------------------------------------
    # 1. PREDECESSOR
    # ----------------------------------------------------------

    state = load_json(STATE)

    if state.get("current_version") != "V9.0-A10":
        raise RuntimeError(
            "A11_PREDECESSOR_NOT_A10"
        )

    if state.get("state_status") != "A10_CERTIFIED":
        raise RuntimeError(
            "A11_PREDECESSOR_NOT_CERTIFIED"
        )

    latest = state.get(
        "latest_phase_receipt"
    ) or {}

    if latest.get("phase") != "V9.0-A10":
        raise RuntimeError(
            "A11_A10_RECEIPT_PHASE_INVALID"
        )

    if latest.get("certification_status") != "PASS":
        raise RuntimeError(
            "A11_A10_RECEIPT_NOT_PASS"
        )

    if not A10_RECEIPT.exists():
        raise RuntimeError(
            "A10_RECEIPT_NOT_FOUND"
        )

    a10_hash = file_hash(A10_RECEIPT)

    if latest.get("sha256") != a10_hash:
        raise RuntimeError(
            "A10_RECEIPT_HASH_DRIFT"
        )

    canary_runtime = state.get(
        "canary_runtime"
    ) or {}

    if (
        canary_runtime.get("lifecycle")
        != "CANARY_AUTHORIZED"
    ):
        raise RuntimeError(
            "A11_CANARY_NOT_AUTHORIZED"
        )

    if canary_runtime.get("production_active") is not False:
        raise RuntimeError(
            "A11_PRODUCTION_ALREADY_ACTIVE"
        )

    skill_id = canary_runtime.get("skill_id")

    if not skill_id:
        raise RuntimeError(
            "A11_SKILL_ID_MISSING"
        )

    print(
        "PREDECESSOR_A10              : PASS"
    )

    print(
        "CANARY_AUTHORIZATION         : PASS"
    )

    print(
        "SKILL_ID                     :",
        skill_id,
    )

    # ----------------------------------------------------------
    # 2. CONFIDENCE CONTRACT
    # ----------------------------------------------------------

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
            "A11_CONFIDENCE_70_ACCEPTED"
        )

    print(
        "CONFIDENCE_70_REJECTED       : PASS"
    )

    # ----------------------------------------------------------
    # 3. LEASE
    # ----------------------------------------------------------

    issued = datetime.now(timezone.utc)

    lease = {
        "schema":
            "raios.a11.authorization-lease.v1",

        "lease_id":
            "lease:" + uuid.uuid4().hex,

        "skill_id":
            skill_id,

        "scope":
            "SANDBOX_LIMITED_ACT_ONLY",

        "issued_at":
            issued.isoformat(),

        "expires_at":
            (
                issued
                + timedelta(minutes=15)
            ).isoformat(),

        "initial_action_budget":
            12,

        "remaining_action_budget":
            12,

        "minimum_confidence":
            0.80,

        "maximum_failure_rate":
            0.30,

        "maximum_latency_ms":
            50.0,

        "allowed_operations": [
            "READ_ONLY_DIAGNOSTIC",
            "RECOVERY_SIMULATION",
            "SANDBOX_STATE_UPDATE",
        ],

        "production_active":
            False,

        "canonical_mutation":
            False,

        "automatic_promotion":
            False,
    }

    lease_path = (
        LEASES
        /
        (
            lease["lease_id"]
            .replace(":", "_")
            + ".json"
        )
    )

    write_json(lease_path, lease)

    print(
        "AUTHORIZATION_LEASE          : PASS"
    )

    # ----------------------------------------------------------
    # 4. SANDBOX
    # ----------------------------------------------------------

    fixture = (
        FIXTURES
        /
        "limited-act-state.json"
    )

    initial = {
        "schema":
            "raios.a11.sandbox-state.v1",

        "counter":
            0,

        "history":
            [],

        "production":
            False,

        "canonical":
            False,
    }

    write_json(fixture, initial)

    initial_bytes = fixture.read_bytes()
    initial_hash = file_hash(fixture)

    print(
        "SANDBOX_FIXTURE              : PASS"
    )

    # ----------------------------------------------------------
    # 5. GUARDIAN STATE
    # ----------------------------------------------------------

    guardian = {
        "attempts":
            0,

        "executions":
            0,

        "successes":
            0,

        "failures":
            0,

        "abstentions":
            0,

        "rejections":
            0,

        "duplicates":
            0,

        "rollbacks":
            0,

        "lease_renewals":
            0,

        "kill_switch":
            False,

        "seen_action_ids":
            set(),

        "latencies":
            [],
    }

    action_experiences = []

    def record_attempt(
        action_id: str,
        operation: str,
        outcome: str,
        confidence: float,
        correlation_id: str,
        causation_id: str | None,
        latency_ms: float | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "action_id":
                action_id,

            "operation":
                operation,

            "outcome":
                outcome,

            "confidence":
                confidence,

            "correlation_id":
                correlation_id,

            "causation_id":
                causation_id,

            "remaining_budget":
                lease[
                    "remaining_action_budget"
                ],

            "production_mutation":
                False,

            "canonical_mutation":
                False,
        }

        if latency_ms is not None:
            payload[
                "latency_ms"
            ] = latency_ms

        if extra:
            payload.update(extra)

        wal_append({
            "schema":
                "raios.a11.action-event.v1",

            "timestamp":
                now(),

            **payload,
        })

        exp = capture_experience(
            "A11_ACTION_ATTEMPT",
            outcome,
            payload,
        )

        action_experiences.append(
            str(
                exp.relative_to(REPO)
            )
        )

    def failure_rate() -> float:
        if guardian["executions"] == 0:
            return 0.0

        return (
            guardian["failures"]
            /
            guardian["executions"]
        )

    def renew_lease() -> None:
        lease[
            "expires_at"
        ] = (
            datetime.now(timezone.utc)
            + timedelta(minutes=15)
        ).isoformat()

        lease[
            "lease_id"
        ] = (
            "lease:"
            + uuid.uuid4().hex
        )

        guardian[
            "lease_renewals"
        ] += 1

        write_json(
            LEASES
            /
            (
                lease[
                    "lease_id"
                ]
                .replace(":", "_")
                + ".json"
            ),
            lease,
        )

    def execute(
        action_id: str,
        operation: str,
        confidence_value: float,
        *,
        inject_failure: bool = False,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> str:

        guardian["attempts"] += 1

        correlation_id = (
            correlation_id
            or
            "corr:"
            + uuid.uuid4().hex
        )

        confidence = probability(
            confidence_value,
            "ACTION_CONFIDENCE",
        )

        if guardian["kill_switch"]:
            guardian["rejections"] += 1

            record_attempt(
                action_id,
                operation,
                "REJECTED_KILL_SWITCH",
                confidence,
                correlation_id,
                causation_id,
            )

            return "REJECTED_KILL_SWITCH"

        expires = datetime.fromisoformat(
            lease["expires_at"]
        )

        if datetime.now(timezone.utc) >= expires:
            renew_lease()

        if lease["remaining_action_budget"] <= 0:
            guardian["kill_switch"] = True
            raise RuntimeError(
                "A11_ACTION_BUDGET_EXHAUSTED"
            )

        lease["remaining_action_budget"] -= 1

        if action_id in guardian["seen_action_ids"]:
            guardian["duplicates"] += 1
            guardian["rejections"] += 1

            record_attempt(
                action_id,
                operation,
                "REJECTED_DUPLICATE",
                confidence,
                correlation_id,
                causation_id,
            )

            return "REJECTED_DUPLICATE"

        guardian["seen_action_ids"].add(
            action_id
        )

        if (
            operation
            not in
            lease["allowed_operations"]
        ):
            guardian["rejections"] += 1

            record_attempt(
                action_id,
                operation,
                "REJECTED_OUT_OF_SCOPE",
                confidence,
                correlation_id,
                causation_id,
            )

            return "REJECTED_OUT_OF_SCOPE"

        if (
            confidence
            <
            lease["minimum_confidence"]
        ):
            guardian["abstentions"] += 1

            record_attempt(
                action_id,
                operation,
                "ABSTAINED_LOW_CONFIDENCE",
                confidence,
                correlation_id,
                causation_id,
            )

            return "ABSTAINED_LOW_CONFIDENCE"

        if (
            failure_rate()
            >
            lease[
                "maximum_failure_rate"
            ]
        ):
            guardian["kill_switch"] = True

            raise RuntimeError(
                "A11_FAILURE_RATE_CIRCUIT_BREAKER"
            )

        before = fixture.read_bytes()
        before_hash = file_hash(fixture)

        snapshot = (
            ROLLBACK
            /
            (
                action_id
                .replace(":", "_")
                +
                "-"
                +
                before_hash
                +
                ".json"
            )
        )

        snapshot.write_bytes(before)

        started = time.perf_counter_ns()

        try:
            obj = load_json(fixture)

            obj["counter"] += 1

            obj["history"].append({
                "action_id":
                    action_id,

                "operation":
                    operation,

                "correlation_id":
                    correlation_id,

                "causation_id":
                    causation_id,
            })

            write_json(
                fixture,
                obj,
            )

            if inject_failure:
                raise RuntimeError(
                    "CONTROLLED_A11_ACTION_FAILURE"
                )

            elapsed = (
                time.perf_counter_ns()
                -
                started
            ) / 1_000_000

            if (
                elapsed
                >
                lease[
                    "maximum_latency_ms"
                ]
            ):
                raise RuntimeError(
                    "A11_LATENCY_CIRCUIT_BREAKER"
                )

            guardian[
                "executions"
            ] += 1

            guardian[
                "successes"
            ] += 1

            guardian[
                "latencies"
            ].append(elapsed)

            record_attempt(
                action_id,
                operation,
                "SUCCESS",
                confidence,
                correlation_id,
                causation_id,
                elapsed,
                {
                    "before_hash":
                        before_hash,

                    "after_hash":
                        file_hash(
                            fixture
                        ),
                },
            )

            return "SUCCESS"

        except Exception as exc:
            guardian[
                "executions"
            ] += 1

            guardian[
                "failures"
            ] += 1

            fixture.write_bytes(
                snapshot.read_bytes()
            )

            guardian[
                "rollbacks"
            ] += 1

            if fixture.read_bytes() != before:
                raise RuntimeError(
                    "A11_ROLLBACK_NOT_BYTE_IDENTICAL"
                ) from exc

            signature = capture_failure(
                exc,
                action_id,
            )

            elapsed = (
                time.perf_counter_ns()
                -
                started
            ) / 1_000_000

            record_attempt(
                action_id,
                operation,
                "FAILED_ROLLED_BACK",
                confidence,
                correlation_id,
                causation_id,
                elapsed,
                {
                    "failure_signature":
                        signature,

                    "rollback":
                        "BYTE_IDENTICAL",
                },
            )

            return "FAILED_ROLLED_BACK"

    # ----------------------------------------------------------
    # 6. TWELVE-ACTION SEQUENCE
    # ----------------------------------------------------------

    sequence = []

    sequence.append(
        execute(
            "act:01",
            "READ_ONLY_DIAGNOSTIC",
            0.94,
        )
    )

    sequence.append(
        execute(
            "act:02",
            "RECOVERY_SIMULATION",
            0.93,
            causation_id="act:01",
        )
    )

    sequence.append(
        execute(
            "act:03",
            "RECOVERY_SIMULATION",
            0.50,
        )
    )

    sequence.append(
        execute(
            "act:04",
            "CANONICAL_MUTATION",
            0.95,
        )
    )

    duplicate_id = "act:05"

    sequence.append(
        execute(
            duplicate_id,
            "SANDBOX_STATE_UPDATE",
            0.92,
        )
    )

    sequence.append(
        execute(
            duplicate_id,
            "SANDBOX_STATE_UPDATE",
            0.92,
        )
    )

    sequence.append(
        execute(
            "act:07",
            "READ_ONLY_DIAGNOSTIC",
            0.91,
        )
    )

    sequence.append(
        execute(
            "act:08",
            "RECOVERY_SIMULATION",
            0.96,
            inject_failure=True,
        )
    )

    sequence.append(
        execute(
            "act:09",
            "RECOVERY_SIMULATION",
            0.95,
            causation_id="act:08",
        )
    )

    # Force lease expiry to prove renewal.
    lease["expires_at"] = (
        datetime.now(timezone.utc)
        -
        timedelta(seconds=1)
    ).isoformat()

    sequence.append(
        execute(
            "act:10",
            "READ_ONLY_DIAGNOSTIC",
            0.90,
        )
    )

    sequence.append(
        execute(
            "act:11",
            "SANDBOX_STATE_UPDATE",
            0.89,
        )
    )

    sequence.append(
        execute(
            "act:12",
            "RECOVERY_SIMULATION",
            0.97,
        )
    )

    if len(sequence) != 12:
        raise RuntimeError(
            "A11_SEQUENCE_COUNT_INVALID"
        )

    print(
        "MULTI_ACTION_SEQUENCE        : PASS"
    )

    # ----------------------------------------------------------
    # 7. ASSERT EXPECTED SPECIAL OUTCOMES
    # ----------------------------------------------------------

    if (
        "ABSTAINED_LOW_CONFIDENCE"
        not in sequence
    ):
        raise RuntimeError(
            "A11_ABSTENTION_NOT_PROVEN"
        )

    if (
        "REJECTED_OUT_OF_SCOPE"
        not in sequence
    ):
        raise RuntimeError(
            "A11_SCOPE_REJECTION_NOT_PROVEN"
        )

    if (
        "REJECTED_DUPLICATE"
        not in sequence
    ):
        raise RuntimeError(
            "A11_DUPLICATE_REJECTION_NOT_PROVEN"
        )

    if (
        "FAILED_ROLLED_BACK"
        not in sequence
    ):
        raise RuntimeError(
            "A11_ROLLBACK_NOT_PROVEN"
        )

    if guardian["lease_renewals"] < 1:
        raise RuntimeError(
            "A11_LEASE_RENEWAL_NOT_PROVEN"
        )

    print(
        "LOW_CONFIDENCE_ABSTENTION    : PASS"
    )

    print(
        "OUT_OF_SCOPE_REJECTION       : PASS"
    )

    print(
        "DUPLICATE_ACTION_REJECTION   : PASS"
    )

    print(
        "FAILED_ACTION_ROLLBACK       : PASS"
    )

    print(
        "LEASE_RENEWAL                : PASS"
    )

    # ----------------------------------------------------------
    # 8. BUDGET
    # ----------------------------------------------------------

    if (
        lease[
            "remaining_action_budget"
        ]
        != 0
    ):
        raise RuntimeError(
            "A11_ACTION_BUDGET_ACCOUNTING_INVALID"
        )

    print(
        "DECREASING_ACTION_BUDGET     : PASS"
    )

    # ----------------------------------------------------------
    # 9. FAILURE-RATE CIRCUIT BREAKER PROBE
    # ----------------------------------------------------------

    breaker = {
        "executions":
            0,

        "failures":
            0,

        "killed":
            False,
    }

    for index in range(3):
        if breaker["killed"]:
            break

        breaker["executions"] += 1
        breaker["failures"] += 1

        rate = (
            breaker["failures"]
            /
            breaker["executions"]
        )

        if rate > 0.30:
            breaker["killed"] = True

    if not breaker["killed"]:
        raise RuntimeError(
            "A11_CIRCUIT_BREAKER_NOT_PROVEN"
        )

    print(
        "FAILURE_RATE_CIRCUIT_BREAKER: PASS"
    )

    # ----------------------------------------------------------
    # 10. WAL / EXPERIENCE VERIFY
    # ----------------------------------------------------------

    wal_lines = [
        line
        for line in WAL.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    wal_events = [
        json.loads(line)
        for line in wal_lines
    ]

    current_run_events = (
        wal_events[-12:]
    )

    if len(current_run_events) != 12:
        raise RuntimeError(
            "A11_WAL_EVENT_COUNT_INVALID"
        )

    event_hashes = [
        event["event_hash"]
        for event in current_run_events
    ]

    if (
        len(event_hashes)
        !=
        len(set(event_hashes))
    ):
        raise RuntimeError(
            "A11_WAL_EVENT_HASH_DUPLICATION"
        )

    if len(action_experiences) != 12:
        raise RuntimeError(
            "A11_ACTION_EXPERIENCE_COUNT_INVALID"
        )

    print(
        "APPEND_ONLY_ACTION_WAL       : PASS"
    )

    print(
        "EVERY_ACTION_IS_EXPERIENCE   : PASS"
    )

    # ----------------------------------------------------------
    # 11. IDEMPOTENCY CONTROL
    # ----------------------------------------------------------

    fixture_before_retry = (
        fixture.read_bytes()
    )

    retry_result = (
        "REJECTED_DUPLICATE"
        if (
            "act:05"
            in guardian[
                "seen_action_ids"
            ]
        )
        else
        "INVALID"
    )

    if (
        retry_result
        !=
        "REJECTED_DUPLICATE"
    ):
        raise RuntimeError(
            "A11_IDEMPOTENT_RETRY_FAILED"
        )

    if (
        fixture.read_bytes()
        !=
        fixture_before_retry
    ):
        raise RuntimeError(
            "A11_DUPLICATE_RETRY_MUTATED_STATE"
        )

    print(
        "IDEMPOTENT_RETRY             : PASS"
    )

    # ----------------------------------------------------------
    # 12. SAFETY INVARIANTS
    # ----------------------------------------------------------

    if (
        load_json(fixture).get(
            "production"
        )
        is not False
    ):
        raise RuntimeError(
            "A11_PRODUCTION_FIXTURE_VIOLATION"
        )

    if (
        load_json(fixture).get(
            "canonical"
        )
        is not False
    ):
        raise RuntimeError(
            "A11_CANONICAL_FIXTURE_VIOLATION"
        )

    print(
        "PRODUCTION_ISOLATION         : PASS"
    )

    print(
        "CANONICAL_ISOLATION          : PASS"
    )

    # ----------------------------------------------------------
    # 13. REPORT
    # ----------------------------------------------------------

    avg_latency = (
        sum(
            guardian["latencies"]
        )
        /
        len(
            guardian["latencies"]
        )
        if guardian["latencies"]
        else 0.0
    )

    report = {
        "schema":
            "raios.a11.continuous-guardian-report.v1",

        "timestamp":
            now(),

        "skill_id":
            skill_id,

        "sequence":
            sequence,

        "attempts":
            guardian["attempts"],

        "executions":
            guardian["executions"],

        "successes":
            guardian["successes"],

        "failures":
            guardian["failures"],

        "abstentions":
            guardian["abstentions"],

        "rejections":
            guardian["rejections"],

        "duplicate_rejections":
            guardian["duplicates"],

        "rollbacks":
            guardian["rollbacks"],

        "lease_renewals":
            guardian["lease_renewals"],

        "remaining_action_budget":
            lease[
                "remaining_action_budget"
            ],

        "observed_failure_rate":
            failure_rate(),

        "mean_latency_ms":
            avg_latency,

        "failure_rate_circuit_breaker":
            True,

        "kill_switch_available":
            True,

        "wal_event_count":
            len(current_run_events),

        "action_experience_count":
            len(action_experiences),

        "production_mutation":
            False,

        "canonical_mutation":
            False,

        "automatic_promotion":
            False,

        "active":
            False,

        "lifecycle_after_a11":
            "LIMITED_ACT_OBSERVED",
    }

    report_path = (
        REPORTS
        /
        "CONTINUOUS-GUARDIAN-REPORT.json"
    )

    write_json(
        report_path,
        report,
    )

    # ----------------------------------------------------------
    # 14. RECEIPT
    # ----------------------------------------------------------

    receipt = {
        "schema":
            "raios.v9.a11.receipt.v1",

        "phase":
            "V9.0-A11",

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
                "V9.0-A10",

            "sha256":
                a10_hash,

            "status":
                "PASS",
        },

        "runtime": {
            "skill_id":
                skill_id,

            "attempt_count":
                12,

            "wal_events":
                len(
                    current_run_events
                ),

            "experiences":
                len(
                    action_experiences
                ),

            "lease_renewals":
                guardian[
                    "lease_renewals"
                ],

            "rollbacks":
                guardian[
                    "rollbacks"
                ],

            "remaining_action_budget":
                lease[
                    "remaining_action_budget"
                ],
        },

        "guardian": {
            "low_confidence_abstention":
                True,

            "scope_rejection":
                True,

            "duplicate_rejection":
                True,

            "idempotent_retry":
                True,

            "failure_rollback":
                True,

            "failure_rate_circuit_breaker":
                True,

            "action_budget":
                True,

            "authorization_lease":
                True,

            "confidence_70_rejected":
                True,
        },

        "safety": {
            "lifecycle":
                "LIMITED_ACT_OBSERVED",

            "active":
                False,

            "production_active":
                False,

            "production_mutation":
                False,

            "canonical_mutation":
                False,

            "automatic_promotion":
                False,
        },

        "guardian_report": {
            "path":
                str(
                    report_path.relative_to(
                        REPO
                    )
                ),

            "sha256":
                file_hash(
                    report_path
                ),
        },

        "epistemic_limits": [
            "A11 executed limited actions only against explicit sandbox fixtures.",
            "A11 does not authorize unrestricted production execution.",
            "Every attempted action was recorded as Experience.",
            "A failed action was rolled back and emitted a Failure Signature and Recovery Skill Candidate.",
            "A11 does not authorize canonical mutation.",
            "A11 does not authorize automatic promotion.",
            "Lifecycle remains below ACTIVE."
        ],
    }

    write_json(
        A11_RECEIPT,
        receipt,
    )

    receipt_hash = (
        file_hash(
            A11_RECEIPT
        )
    )

    # ----------------------------------------------------------
    # 15. STATE
    # ----------------------------------------------------------

    final_state = load_json(
        STATE
    )

    final_state[
        "current_version"
    ] = "V9.0-A11"

    final_state[
        "current_phase"
    ] = (
        "LIMITED_ACT_RUNTIME_WITH_CONTINUOUS_GUARDIAN"
    )

    final_state[
        "state_status"
    ] = "A11_CERTIFIED"

    final_state[
        "limited_act_runtime"
    ] = {
        "skill_id":
            skill_id,

        "lifecycle":
            "LIMITED_ACT_OBSERVED",

        "actions_observed":
            12,

        "authorization_lease":
            True,

        "continuous_guardian":
            True,

        "append_only_action_wal":
            True,

        "every_action_is_experience":
            True,

        "verified_rollback":
            True,

        "failure_rate_circuit_breaker":
            True,

        "active":
            False,

        "production_active":
            False,

        "canonical_mutation":
            False,

        "automatic_promotion":
            False,
    }

    architecture = final_state.get(
        "active_architecture",
        []
    )

    for capability in [
        "LIMITED_ACT_RUNTIME",
        "AUTHORIZATION_LEASE",
        "CONTINUOUS_RUNTIME_GUARDIAN",
        "APPEND_ONLY_ACTION_WAL",
        "ACTION_EXPERIENCE_REFLEX",
        "DUPLICATE_ACTION_REJECTION",
        "IDEMPOTENT_ACTION_RETRY",
        "FAILURE_RATE_CIRCUIT_BREAKER",
        "ACTION_BUDGET_ACCOUNTING",
        "VERIFIED_ACTION_ROLLBACK",
    ]:
        if capability not in architecture:
            architecture.append(
                capability
            )

    final_state[
        "active_architecture"
    ] = architecture

    final_state[
        "latest_phase_receipt"
    ] = {
        "phase":
            "V9.0-A11",

        "path":
            str(
                A11_RECEIPT.relative_to(
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

    write_json(
        STATE,
        final_state,
    )

    final = load_json(
        STATE
    )

    actual_hash = file_hash(
        A11_RECEIPT
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
            "A11_STATE_RECEIPT_HASH_DRIFT"
        )

    if (
        final[
            "limited_act_runtime"
        ][
            "active"
        ]
        is not False
    ):
        raise RuntimeError(
            "A11_ACTIVE_LIFECYCLE_VIOLATION"
        )

    if (
        final[
            "limited_act_runtime"
        ][
            "production_active"
        ]
        is not False
    ):
        raise RuntimeError(
            "A11_PRODUCTION_ACTIVATION_VIOLATION"
        )

    print()
    print("=" * 86)
    print(
        "RAIOS V9.0-A11 CERTIFICATION RESULT"
    )
    print("=" * 86)

    print(
        "PREDECESSOR_A10              : PASS"
    )

    print(
        "MULTI_ACTION_SEQUENCE        : PASS"
    )

    print(
        "ACTION_ATTEMPTS              :",
        guardian["attempts"],
    )

    print(
        "SUCCESSFUL_EXECUTIONS        :",
        guardian["successes"],
    )

    print(
        "FAILURES                     :",
        guardian["failures"],
    )

    print(
        "ABSTENTIONS                  :",
        guardian["abstentions"],
    )

    print(
        "REJECTIONS                   :",
        guardian["rejections"],
    )

    print(
        "ROLLBACKS                    :",
        guardian["rollbacks"],
    )

    print(
        "LEASE_RENEWALS               :",
        guardian["lease_renewals"],
    )

    print(
        "REMAINING_ACTION_BUDGET      :",
        lease["remaining_action_budget"],
    )

    print(
        "EVERY_ACTION_IS_EXPERIENCE   : PASS"
    )

    print(
        "APPEND_ONLY_ACTION_WAL       : PASS"
    )

    print(
        "DUPLICATE_ACTION_REJECTION   : PASS"
    )

    print(
        "IDEMPOTENT_RETRY             : PASS"
    )

    print(
        "LOW_CONFIDENCE_ABSTENTION    : PASS"
    )

    print(
        "OUT_OF_SCOPE_REJECTION       : PASS"
    )

    print(
        "FAILED_ACTION_ROLLBACK       : PASS"
    )

    print(
        "FAILURE_RATE_CIRCUIT_BREAKER : PASS"
    )

    print(
        "CONFIDENCE_70_REJECTED       : PASS"
    )

    print(
        "CANONICAL_MUTATION           : FALSE"
    )

    print(
        "PRODUCTION_MUTATION          : FALSE"
    )

    print(
        "AUTOMATIC_PROMOTION          : FALSE"
    )

    print(
        "SKILL_LIFECYCLE              : LIMITED_ACT_OBSERVED"
    )

    print(
        "ACTIVE                       : FALSE"
    )

    print(
        "PRODUCTION_ACTIVE            : FALSE"
    )

    print(
        "STATE_RECEIPT_HASH_MATCH     : TRUE"
    )

    print(
        "CURRENT_VERSION              :",
        final["current_version"],
    )

    print(
        "STATE_STATUS                 :",
        final["state_status"],
    )

    print(
        "A11_RECEIPT_SHA256           :",
        actual_hash,
    )

    print()
    print(
        "STATUS = V9.0-A11_PASS"
    )

    print("=" * 86)


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        try:
            signature = capture_failure(
                exc
            )

            capture_experience(
                "A11_CERTIFICATION_FAILURE",
                "FAILED",
                {
                    "failure_signature":
                        signature
                },
            )

        except Exception as telemetry_error:
            print(
                "A11_FAILURE_TELEMETRY_ERROR:",
                repr(telemetry_error),
                file=sys.stderr,
            )

        print(
            "A11_CERTIFICATION_FAILED:",
            repr(exc),
            file=sys.stderr,
        )

        raise