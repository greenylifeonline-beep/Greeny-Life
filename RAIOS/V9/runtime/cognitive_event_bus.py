from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
)

V9 = REPO / "RAIOS" / "V9"

WAL_DIR = V9 / "wal"

WAL_FILE = (
    WAL_DIR /
    "cognitive-events.jsonl"
)

STATE_DIR = (
    V9 /
    "runtime" /
    "event-state"
)

PROCESSED_LEDGER = (
    STATE_DIR /
    "processed-events.jsonl"
)

EXPERIENCE_DIR = (
    V9 /
    "experience" /
    "automatic-a4"
)

FAILURE_DIR = (
    V9 /
    "failures" /
    "a4"
)

RECOVERY_DIR = (
    V9 /
    "skills" /
    "candidates-a4"
)

PERFORMANCE_DIR = (
    V9 /
    "performance" /
    "a4"
)

EVIDENCE_EVENT_DIR = (
    V9 /
    "evidence" /
    "events"
)

for directory in (
    WAL_DIR,
    STATE_DIR,
    EXPERIENCE_DIR,
    FAILURE_DIR,
    RECOVERY_DIR,
    PERFORMANCE_DIR,
    EVIDENCE_EVENT_DIR,
):
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


EVENT_TYPES = {
    "OBSERVATION",
    "ACTION",
    "RESULT",
    "FAILURE",
    "RECOVERY",
    "DECISION",
    "EVIDENCE",
    "CONTRADICTION",
    "MODEL_CALL",
    "TOOL_CALL",
    "SEARCH",
    "READ",
    "WRITE",
    "MUTATION",
    "BENCHMARK",
    "RESOURCE",
    "SECURITY",
    "GOVERNANCE",
    "LEARNING",
}


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def repo_sha() -> str:
    return subprocess.check_output(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        cwd=REPO,
        text=True,
    ).strip()


def canonical_bytes(
    obj: Any,
) -> bytes:

    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def digest(
    obj: Any,
) -> str:

    return hashlib.sha256(
        canonical_bytes(obj)
    ).hexdigest()


def validate_confidence(
    value: Any,
) -> float | None:

    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError(
            "BOOLEAN_IS_NOT_CONFIDENCE"
        )

    try:
        number = float(value)
    except Exception as exc:
        raise ValueError(
            "CONFIDENCE_NOT_NUMERIC"
        ) from exc

    if not 0.0 <= number <= 1.0:
        raise ValueError(
            f"CONFIDENCE_OUT_OF_RANGE:{number}"
        )

    return round(
        number,
        6,
    )


def atomic_json_write(
    path: Path,
    obj: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_suffix(
        path.suffix + ".tmp"
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

    reread = json.loads(
        tmp.read_text(
            encoding="utf-8"
        )
    )

    if reread != obj:
        raise RuntimeError(
            "ATOMIC_WRITE_READBACK_MISMATCH"
        )

    tmp.replace(path)


def append_jsonl_sync(
    path: Path,
    obj: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    line = (
        json.dumps(
            obj,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        +
        "\n"
    )

    with path.open(
        "a",
        encoding="utf-8",
        newline="\n",
    ) as handle:

        handle.write(line)

        handle.flush()

        os.fsync(
            handle.fileno()
        )


def load_jsonl(
    path: Path,
) -> list[dict[str, Any]]:

    if not path.exists():
        return []

    records = []

    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as handle:

        for number, raw in enumerate(
            handle,
            start=1,
        ):

            raw = raw.strip()

            if not raw:
                continue

            try:
                records.append(
                    json.loads(raw)
                )

            except Exception as exc:
                raise RuntimeError(
                    f"CORRUPT_JSONL:{path}:{number}"
                ) from exc

    return records


def wal_event_ids() -> set[str]:

    return {
        record["event_id"]
        for record in load_jsonl(
            WAL_FILE
        )
        if record.get(
            "event_id"
        )
    }


def processed_event_ids() -> set[str]:

    return {
        record["event_id"]
        for record in load_jsonl(
            PROCESSED_LEDGER
        )
        if record.get(
            "event_id"
        )
    }


def build_event(
    *,
    event_type: str,
    actor: str,
    intent: str,
    success: bool | None = None,
    tool: str | None = None,
    model: str | None = None,
    input_ref: Any = None,
    output_ref: Any = None,
    evidence_refs: list[str] | None = None,
    pre_state: Any = None,
    post_state: Any = None,
    latency_ms: float | None = None,
    resource_usage: Any = None,
    confidence: float | None = None,
    unresolved_flags: list[str] | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    event_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:

    event_type = str(
        event_type
    ).upper()

    if event_type not in EVENT_TYPES:
        raise ValueError(
            f"UNKNOWN_EVENT_TYPE:{event_type}"
        )

    normalized_confidence = (
        validate_confidence(
            confidence
        )
    )

    correlation_id = (
        correlation_id
        or
        str(uuid.uuid4())
    )

    event_id = (
        event_id
        or
        str(uuid.uuid4())
    )

    event = {
        "schema":
            "raios.cognitive-event.v1",

        "event_id":
            event_id,

        "event_type":
            event_type,

        "timestamp":
            now(),

        "correlation_id":
            correlation_id,

        "causation_id":
            causation_id,

        "actor":
            actor,

        "tool":
            tool,

        "model":
            model,

        "intent":
            intent,

        "input_ref":
            input_ref,

        "output_ref":
            output_ref,

        "evidence_refs":
            evidence_refs or [],

        "pre_state":
            pre_state,

        "post_state":
            post_state,

        "success":
            success,

        "latency_ms":
            latency_ms,

        "resource_usage":
            resource_usage,

        "confidence":
            normalized_confidence,

        "unresolved_flags":
            unresolved_flags or [],

        "repository_sha":
            repo_sha(),

        "metadata":
            metadata or {},
    }

    event["event_hash"] = digest(
        event
    )

    return event


def validate_event(
    event: dict[str, Any],
) -> None:

    required = (
        "schema",
        "event_id",
        "event_type",
        "timestamp",
        "correlation_id",
        "actor",
        "intent",
        "event_hash",
    )

    for key in required:
        if not event.get(
            key
        ):
            raise ValueError(
                f"EVENT_REQUIRED_FIELD_MISSING:{key}"
            )

    if (
        event["schema"]
        !=
        "raios.cognitive-event.v1"
    ):
        raise ValueError(
            "EVENT_SCHEMA_INVALID"
        )

    if (
        event["event_type"]
        not in EVENT_TYPES
    ):
        raise ValueError(
            "EVENT_TYPE_INVALID"
        )

    validate_confidence(
        event.get(
            "confidence"
        )
    )

    supplied_hash = event[
        "event_hash"
    ]

    without_hash = dict(
        event
    )

    without_hash.pop(
        "event_hash",
        None,
    )

    calculated = digest(
        without_hash
    )

    if supplied_hash != calculated:
        raise ValueError(
            "EVENT_HASH_INVALID"
        )


def event_exists_in_wal(
    event_id: str,
) -> bool:

    return (
        event_id
        in
        wal_event_ids()
    )


def append_to_wal(
    event: dict[str, Any],
) -> dict[str, Any]:

    validate_event(
        event
    )

    if event_exists_in_wal(
        event["event_id"]
    ):
        return {
            "status":
                "DUPLICATE_REJECTED",

            "event_id":
                event["event_id"],

            "wal_appended":
                False,
        }

    append_jsonl_sync(
        WAL_FILE,
        event,
    )

    return {
        "status":
            "WAL_COMMITTED",

        "event_id":
            event["event_id"],

        "wal_appended":
            True,
    }


def experience_from_event(
    event: dict[str, Any],
) -> dict[str, Any]:

    return {
        "schema":
            "raios.experience.v3",

        "experience_id":
            f"exp:{event['event_id']}",

        "source_event_id":
            event["event_id"],

        "event_type":
            event["event_type"],

        "correlation_id":
            event["correlation_id"],

        "causation_id":
            event.get(
                "causation_id"
            ),

        "actor":
            event["actor"],

        "intent":
            event["intent"],

        "tool":
            event.get(
                "tool"
            ),

        "model":
            event.get(
                "model"
            ),

        "input_ref":
            event.get(
                "input_ref"
            ),

        "output_ref":
            event.get(
                "output_ref"
            ),

        "success":
            event.get(
                "success"
            ),

        "evidence_refs":
            event.get(
                "evidence_refs",
                [],
            ),

        "pre_state":
            event.get(
                "pre_state"
            ),

        "post_state":
            event.get(
                "post_state"
            ),

        "latency_ms":
            event.get(
                "latency_ms"
            ),

        "resource_usage":
            event.get(
                "resource_usage"
            ),

        "confidence":
            event.get(
                "confidence"
            ),

        "unresolved_flags":
            event.get(
                "unresolved_flags",
                [],
            ),

        "repository_sha":
            event.get(
                "repository_sha"
            ),

        "captured_at":
            now(),
    }


def failure_from_event(
    event: dict[str, Any],
) -> dict[str, Any]:

    signature_payload = {
        "event_type":
            event["event_type"],

        "tool":
            event.get(
                "tool"
            ),

        "intent":
            event["intent"],

        "output_ref":
            event.get(
                "output_ref"
            ),

        "unresolved_flags":
            event.get(
                "unresolved_flags",
                [],
            ),
    }

    signature = (
        "failure:"
        +
        digest(
            signature_payload
        )
    )

    return {
        "schema":
            "raios.failure-signature.v2",

        "failure_id":
            f"failure:{event['event_id']}",

        "source_event_id":
            event["event_id"],

        "signature":
            signature,

        "intent":
            event["intent"],

        "tool":
            event.get(
                "tool"
            ),

        "evidence_refs":
            event.get(
                "evidence_refs",
                [],
            ),

        "unresolved_flags":
            event.get(
                "unresolved_flags",
                [],
            ),

        "status":
            "ACTIVE",

        "created_at":
            now(),
    }


def recovery_candidate_from_failure(
    event: dict[str, Any],
    failure: dict[str, Any],
) -> dict[str, Any]:

    return {
        "schema":
            "raios.recovery-skill-candidate.v2",

        "candidate_id":
            f"recovery:{event['event_id']}",

        "source_event_id":
            event["event_id"],

        "failure_signature":
            failure["signature"],

        "status":
            "REVIEW_REQUIRED",

        "canonical_promotion":
            False,

        "promotion_requirements": [
            "replay",
            "benchmark",
            "verification",
            "governed_promotion",
        ],

        "candidate_behavior": {
            "detect_failure_signature":
                True,

            "preserve_evidence":
                True,

            "generate_recovery_plan":
                True,

            "validate_recovery":
                True,

            "rollback_on_regression":
                True,
        },

        "created_at":
            now(),
    }


def performance_from_event(
    event: dict[str, Any],
) -> dict[str, Any]:

    return {
        "schema":
            "raios.performance-observation.v1",

        "performance_id":
            f"perf:{event['event_id']}",

        "source_event_id":
            event["event_id"],

        "event_type":
            event["event_type"],

        "tool":
            event.get(
                "tool"
            ),

        "model":
            event.get(
                "model"
            ),

        "success":
            event.get(
                "success"
            ),

        "latency_ms":
            event.get(
                "latency_ms"
            ),

        "resource_usage":
            event.get(
                "resource_usage"
            ),

        "observed_at":
            now(),
    }


def materialize_event(
    event: dict[str, Any],
) -> dict[str, Any]:

    validate_event(
        event
    )

    event_id = event[
        "event_id"
    ]

    if (
        event_id
        in
        processed_event_ids()
    ):
        return {
            "status":
                "ALREADY_MATERIALIZED",

            "event_id":
                event_id,
        }

    experience = experience_from_event(
        event
    )

    atomic_json_write(
        EXPERIENCE_DIR /
        f"{event_id}.json",
        experience,
    )

    atomic_json_write(
        EVIDENCE_EVENT_DIR /
        f"{event_id}.json",
        event,
    )

    performance = performance_from_event(
        event
    )

    atomic_json_write(
        PERFORMANCE_DIR /
        f"{event_id}.json",
        performance,
    )

    failure_written = False
    recovery_written = False

    is_failure = (
        event["event_type"]
        ==
        "FAILURE"
        or
        event.get(
            "success"
        )
        is False
    )

    if is_failure:
        failure = failure_from_event(
            event
        )

        atomic_json_write(
            FAILURE_DIR /
            f"{event_id}.json",
            failure,
        )

        failure_written = True

        candidate = (
            recovery_candidate_from_failure(
                event,
                failure,
            )
        )

        atomic_json_write(
            RECOVERY_DIR /
            f"{event_id}.json",
            candidate,
        )

        recovery_written = True

    append_jsonl_sync(
        PROCESSED_LEDGER,
        {
            "event_id":
                event_id,

            "event_hash":
                event[
                    "event_hash"
                ],

            "materialized_at":
                now(),
        },
    )

    return {
        "status":
            "MATERIALIZED",

        "event_id":
            event_id,

        "experience":
            True,

        "failure":
            failure_written,

        "recovery_candidate":
            recovery_written,

        "performance":
            True,

        "evidence":
            True,
    }


def emit_event(
    event: dict[str, Any],
    *,
    materialize: bool = True,
) -> dict[str, Any]:

    wal_result = append_to_wal(
        event
    )

    if (
        wal_result["status"]
        ==
        "DUPLICATE_REJECTED"
    ):
        return {
            **wal_result,
            "materialized":
                False,
        }

    materialized = None

    if materialize:
        materialized = (
            materialize_event(
                event
            )
        )

    return {
        **wal_result,

        "materialized":
            materialized,
    }


def emit(
    *,
    event_type: str,
    actor: str,
    intent: str,
    materialize: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:

    event = build_event(
        event_type=event_type,
        actor=actor,
        intent=intent,
        **kwargs,
    )

    result = emit_event(
        event,
        materialize=materialize,
    )

    return {
        "event":
            event,

        "result":
            result,
    }


def replay_wal() -> dict[str, Any]:

    events = load_jsonl(
        WAL_FILE
    )

    before = processed_event_ids()

    processed_now = 0
    already_processed = 0

    seen = set()

    for event in events:
        event_id = event.get(
            "event_id"
        )

        if not event_id:
            raise RuntimeError(
                "WAL_EVENT_ID_MISSING"
            )

        if event_id in seen:
            continue

        seen.add(
            event_id
        )

        if event_id in before:
            already_processed += 1
            continue

        result = materialize_event(
            event
        )

        if (
            result["status"]
            ==
            "MATERIALIZED"
        ):
            processed_now += 1

    return {
        "schema":
            "raios.wal-replay.v1",

        "wal_events":
            len(events),

        "unique_events":
            len(seen),

        "processed_now":
            processed_now,

        "already_processed":
            already_processed,

        "processed_total":
            len(
                processed_event_ids()
            ),
    }


def instrumented_call(
    *,
    actor: str,
    intent: str,
    tool: str,
    fn: Callable[[], Any],
    input_ref: Any = None,
    evidence_refs: list[str] | None = None,
    confidence: float | None = None,
    resource_usage: Any = None,
) -> Any:

    correlation_id = str(
        uuid.uuid4()
    )

    action = build_event(
        event_type="ACTION",
        actor=actor,
        intent=intent,
        tool=tool,
        input_ref=input_ref,
        evidence_refs=evidence_refs or [],
        correlation_id=correlation_id,
        confidence=confidence,
    )

    emit_event(
        action
    )

    started = time.perf_counter()

    try:
        result = fn()

        latency_ms = round(
            (
                time.perf_counter()
                -
                started
            )
            *
            1000,
            3,
        )

        result_event = build_event(
            event_type="RESULT",
            actor=actor,
            intent=intent,
            tool=tool,
            input_ref=input_ref,
            output_ref=result,
            evidence_refs=evidence_refs or [],
            correlation_id=correlation_id,
            causation_id=action[
                "event_id"
            ],
            success=True,
            latency_ms=latency_ms,
            resource_usage=resource_usage,
            confidence=confidence,
        )

        emit_event(
            result_event
        )

        return result

    except BaseException as exc:

        latency_ms = round(
            (
                time.perf_counter()
                -
                started
            )
            *
            1000,
            3,
        )

        failure_event = build_event(
            event_type="FAILURE",
            actor=actor,
            intent=intent,
            tool=tool,
            input_ref=input_ref,
            output_ref={
                "exception_type":
                    type(exc).__name__,

                "message":
                    str(exc),
            },
            evidence_refs=evidence_refs or [],
            correlation_id=correlation_id,
            causation_id=action[
                "event_id"
            ],
            success=False,
            latency_ms=latency_ms,
            resource_usage=resource_usage,
            confidence=confidence,
            unresolved_flags=[
                "EXECUTION_FAILED"
            ],
        )

        emit_event(
            failure_event
        )

        raise