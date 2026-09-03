from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
import uuid

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
REPO = Path(
    os.getenv("RAIOS_CANONICAL_REPO", str(Path(__file__).resolve().parents[3]))
).expanduser().resolve()
_REPO_SHA_CACHE: dict[str, Any] = {"value": None, "checked_at": 0.0}
_REPO_SHA_LOCK = threading.Lock()

V9 = REPO / "RAIOS" / "V9"

COGNITIVE_STORE_ROOT = Path(
    os.getenv("RAIOS_COGNITIVE_STORE_ROOT", str(V9))
).expanduser().resolve()

WAL_DIR = COGNITIVE_STORE_ROOT / "wal"

WAL_FILE = (
    WAL_DIR /
    "cognitive-events.jsonl"
)

STATE_DIR = (
    COGNITIVE_STORE_ROOT /
    "runtime" /
    "event-state"
)

PROCESSED_LEDGER = (
    STATE_DIR /
    "processed-events.jsonl"
)

EXPERIENCE_DIR = (
    COGNITIVE_STORE_ROOT /
    "experience" /
    "automatic-a4"
)

FAILURE_DIR = (
    COGNITIVE_STORE_ROOT /
    "failures" /
    "a4"
)

RECOVERY_DIR = (
    COGNITIVE_STORE_ROOT /
    "skills" /
    "candidates-a4"
)

PERFORMANCE_DIR = (
    COGNITIVE_STORE_ROOT /
    "performance" /
    "a4"
)

EVIDENCE_EVENT_DIR = (
    COGNITIVE_STORE_ROOT /
    "evidence" /
    "events"
)

JSONL_RECOVERY_DIR = (
    COGNITIVE_STORE_ROOT /
    "recovery" /
    "jsonl"
)

for directory in (
    WAL_DIR,
    STATE_DIR,
    EXPERIENCE_DIR,
    FAILURE_DIR,
    RECOVERY_DIR,
    PERFORMANCE_DIR,
    EVIDENCE_EVENT_DIR,
    JSONL_RECOVERY_DIR,
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
    current = time.monotonic()
    cached = _REPO_SHA_CACHE.get("value")
    if cached and current - float(_REPO_SHA_CACHE["checked_at"]) < 60.0:
        return str(cached)
    with _REPO_SHA_LOCK:
        cached = _REPO_SHA_CACHE.get("value")
        current = time.monotonic()
        if cached and current - float(_REPO_SHA_CACHE["checked_at"]) < 60.0:
            return str(cached)
        try:
            value = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=REPO,
                text=True,
                creationflags=CREATE_NO_WINDOW,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            value = str(cached or "UNKNOWN")
        _REPO_SHA_CACHE.update(value=value, checked_at=current)
        return value


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


_ATOMIC_WRITE_LOCK = threading.RLock()


def atomic_json_write(
    path: Path,
    obj: Any,
) -> None:
    """Validated Windows-resilient JSON write with a unique temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        obj,
        indent=2,
        ensure_ascii=False,
        default=str,
    ) + "\n"
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    expected = json.loads(payload)

    with _ATOMIC_WRITE_LOCK:
        try:
            tmp.write_text(payload, encoding="utf-8")
            if json.loads(tmp.read_text(encoding="utf-8")) != expected:
                raise RuntimeError("ATOMIC_WRITE_READBACK_MISMATCH")

            last_error: PermissionError | None = None
            for attempt in range(8):
                try:
                    os.replace(tmp, path)
                    last_error = None
                    break
                except PermissionError as exc:
                    last_error = exc
                    time.sleep(0.02 * (attempt + 1))

            if last_error is not None:
                with path.open("w", encoding="utf-8", newline="\n") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                if json.loads(path.read_text(encoding="utf-8")) != expected:
                    raise RuntimeError("STABLE_WRITE_READBACK_MISMATCH")
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass


_JSONL_THREAD_LOCK = threading.RLock()


@contextmanager
def _jsonl_process_lock(path: Path):
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    acquired = False
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            for attempt in range(100):
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                    break
                except OSError:
                    time.sleep(0.01 * min(attempt + 1, 10))
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            acquired = True
        if not acquired:
            raise TimeoutError(f"JSONL_LOCK_TIMEOUT:{path}")
        yield
    finally:
        if acquired:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _repair_terminal_jsonl_unlocked(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "MISSING", "repaired": False}
    blob = path.read_bytes()
    segments = blob.splitlines(keepends=True)
    invalid: list[int] = []
    nonblank: list[int] = []
    for index, segment in enumerate(segments):
        stripped = segment.strip()
        if not stripped:
            continue
        nonblank.append(index)
        try:
            json.loads(stripped.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid.append(index)
    if not invalid:
        return {"status": "VALID", "repaired": False}
    if len(invalid) != 1 or not nonblank or invalid[0] != nonblank[-1]:
        line = invalid[0] + 1
        raise RuntimeError(f"CORRUPT_JSONL_INTERIOR:{path}:{line}")

    index = invalid[0]
    fragment = segments[index]
    evidence = {
        "schema": "raios.jsonl-tail-recovery.v1",
        "recovered_at": now(),
        "source": str(path),
        "line": index + 1,
        "fragment_sha256": hashlib.sha256(fragment).hexdigest(),
        "fragment_bytes": len(fragment),
        "fragment_preview": fragment.decode("utf-8", errors="replace")[:2000],
    }
    evidence_path = JSONL_RECOVERY_DIR / (
        f"{path.name}-{time.time_ns()}-{uuid.uuid4().hex[:8]}.json"
    )
    atomic_json_write(evidence_path, evidence)

    retained = b"".join(
        segment for position, segment in enumerate(segments) if position != index
    )
    tmp = path.with_name(path.name + ".repair-" + uuid.uuid4().hex)
    try:
        with tmp.open("wb") as handle:
            handle.write(retained)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(8):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 7:
                    with path.open("wb") as handle:
                        handle.write(retained)
                        handle.flush()
                        os.fsync(handle.fileno())
                else:
                    time.sleep(0.02 * (attempt + 1))
    finally:
        tmp.unlink(missing_ok=True)
    return {
        "status": "REPAIRED_TERMINAL_FRAGMENT",
        "repaired": True,
        "line": index + 1,
        "evidence": str(evidence_path),
    }


def repair_terminal_jsonl(path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _JSONL_THREAD_LOCK, _jsonl_process_lock(path):
        return _repair_terminal_jsonl_unlocked(path)


JSONL_TAIL_SCAN_BYTES = 1024 * 1024


def _jsonl_tail_state_unlocked(path: Path) -> dict[str, Any]:
    """Validate only the terminal JSONL record before an append.

    Normal appends stay O(last-record). A missing separator, an invalid terminal
    record, or an unusually large terminal record is escalated to the existing
    full repair path while the same process lock remains held.
    """
    if not path.exists():
        return {"status": "MISSING", "needs_separator": False}
    size = path.stat().st_size
    if size == 0:
        return {"status": "EMPTY", "needs_separator": False}

    read_size = min(size, JSONL_TAIL_SCAN_BYTES)
    with path.open("rb") as handle:
        handle.seek(size - read_size)
        tail = handle.read(read_size)

    if not tail:
        return {"status": "EMPTY", "needs_separator": False}

    needs_separator = not tail.endswith((b"\n", b"\r"))
    candidate_blob = tail.rstrip(b"\r\n \t")
    if not candidate_blob:
        return {"status": "WHITESPACE", "needs_separator": needs_separator}

    separator = candidate_blob.rfind(b"\n")
    candidate = candidate_blob[separator + 1 :].strip()
    candidate_starts_in_tail = separator >= 0 or read_size == size
    if not candidate_starts_in_tail:
        return {
            "status": "FULL_VALIDATION_REQUIRED",
            "needs_separator": needs_separator,
        }

    try:
        json.loads(candidate.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "INVALID_TERMINAL", "needs_separator": needs_separator}
    return {"status": "VALID", "needs_separator": needs_separator}


def append_jsonl_sync(path: Path, obj: Any) -> tuple[int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
        + "\n"
    ).encode("utf-8")
    with _JSONL_THREAD_LOCK, _jsonl_process_lock(path):
        tail_state = _jsonl_tail_state_unlocked(path)
        if tail_state["status"] in {
            "FULL_VALIDATION_REQUIRED",
            "INVALID_TERMINAL",
        }:
            _repair_terminal_jsonl_unlocked(path)
            tail_state = _jsonl_tail_state_unlocked(path)
            if tail_state["status"] not in {
                "MISSING",
                "EMPTY",
                "WHITESPACE",
                "VALID",
            }:
                raise RuntimeError(
                    f"JSONL_TERMINAL_UNRECOVERABLE:{path}:{tail_state['status']}"
                )

        prefix = b"\n" if tail_state.get("needs_separator") else b""
        with path.open("ab", buffering=0) as handle:
            view = memoryview(prefix + payload)
            while view:
                written = handle.write(view)
                if not written:
                    raise OSError(f"JSONL_APPEND_ZERO_WRITE:{path}")
                view = view[written:]
            os.fsync(handle.fileno())
        stat = path.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
    return signature


def _load_jsonl_unlocked(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for number, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except Exception as exc:
                raise RuntimeError(f"CORRUPT_JSONL:{path}:{number}") from exc
    return records


def _load_jsonl_snapshot(
    path: Path,
) -> tuple[list[dict[str, Any]], tuple[int, int]]:
    if not path.exists():
        return [], (0, 0)
    with _JSONL_THREAD_LOCK, _jsonl_process_lock(path):
        _repair_terminal_jsonl_unlocked(path)
        records = _load_jsonl_unlocked(path)
        stat = path.stat()
        return records, (stat.st_size, stat.st_mtime_ns)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records, _signature = _load_jsonl_snapshot(path)
    return records


_WAL_ID_CACHE_LOCK = threading.RLock()
_WAL_ID_CACHE_SIGNATURE: tuple[int, int] | None = None
_WAL_ID_CACHE: set[str] = set()


def _wal_signature() -> tuple[int, int]:
    try:
        stat = WAL_FILE.stat()
        return stat.st_size, stat.st_mtime_ns
    except FileNotFoundError:
        return 0, 0


def wal_event_ids() -> set[str]:
    global _WAL_ID_CACHE_SIGNATURE, _WAL_ID_CACHE
    signature = _wal_signature()
    with _WAL_ID_CACHE_LOCK:
        if signature == _WAL_ID_CACHE_SIGNATURE:
            return set(_WAL_ID_CACHE)
        records, observed_signature = _load_jsonl_snapshot(WAL_FILE)
        _WAL_ID_CACHE = {
            str(record["event_id"])
            for record in records
            if record.get("event_id")
        }
        _WAL_ID_CACHE_SIGNATURE = observed_signature
        return set(_WAL_ID_CACHE)


def _remember_wal_event(event_id: str, signature: tuple[int, int]) -> None:
    global _WAL_ID_CACHE_SIGNATURE
    with _WAL_ID_CACHE_LOCK:
        _WAL_ID_CACHE.add(event_id)
        _WAL_ID_CACHE_SIGNATURE = signature


_PROCESSED_ID_CACHE_LOCK = threading.RLock()
_PROCESSED_ID_CACHE_SIGNATURE: tuple[int, int] | None = None
_PROCESSED_ID_CACHE: set[str] = set()


def _processed_signature() -> tuple[int, int]:
    try:
        stat = PROCESSED_LEDGER.stat()
        return stat.st_size, stat.st_mtime_ns
    except FileNotFoundError:
        return 0, 0


def processed_event_ids() -> set[str]:
    global _PROCESSED_ID_CACHE_SIGNATURE, _PROCESSED_ID_CACHE
    signature = _processed_signature()
    with _PROCESSED_ID_CACHE_LOCK:
        if signature == _PROCESSED_ID_CACHE_SIGNATURE:
            return set(_PROCESSED_ID_CACHE)
        records, observed_signature = _load_jsonl_snapshot(PROCESSED_LEDGER)
        _PROCESSED_ID_CACHE = {
            str(record["event_id"])
            for record in records
            if record.get("event_id")
        }
        _PROCESSED_ID_CACHE_SIGNATURE = observed_signature
        return set(_PROCESSED_ID_CACHE)


def _remember_processed_event(
    event_id: str,
    signature: tuple[int, int],
) -> None:
    global _PROCESSED_ID_CACHE_SIGNATURE
    with _PROCESSED_ID_CACHE_LOCK:
        _PROCESSED_ID_CACHE.add(event_id)
        _PROCESSED_ID_CACHE_SIGNATURE = signature


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

    wal_signature = append_jsonl_sync(
        WAL_FILE,
        event,
    )
    _remember_wal_event(str(event["event_id"]), wal_signature)

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

    processed_signature = append_jsonl_sync(
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
    _remember_processed_event(str(event_id), processed_signature)

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