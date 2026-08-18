from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
)

V9 = REPO / "RAIOS" / "V9"

RUNTIME = V9 / "runtime"

import sys

sys.path.insert(
    0,
    str(RUNTIME),
)

from cognitive_event_bus import (
    WAL_FILE,
    load_jsonl,
)


EVOLUTION_ROOT = (
    V9 /
    "evolution" /
    "a5"
)

FAILURE_FAMILIES = (
    EVOLUTION_ROOT /
    "failure-families"
)

PATTERNS = (
    EVOLUTION_ROOT /
    "experience-patterns"
)

RECOVERY_MEMORY = (
    EVOLUTION_ROOT /
    "recovery-outcomes"
)

SKILL_CANDIDATES = (
    EVOLUTION_ROOT /
    "skill-candidates"
)

REPLAY_QUEUE = (
    EVOLUTION_ROOT /
    "replay-queue"
)

STATE_DIR = (
    EVOLUTION_ROOT /
    "state"
)

PROCESSED_LEDGER = (
    STATE_DIR /
    "processed-events.jsonl"
)

for directory in (
    FAILURE_FAMILIES,
    PATTERNS,
    RECOVERY_MEMORY,
    SKILL_CANDIDATES,
    REPLAY_QUEUE,
    STATE_DIR,
):
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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


def load_json(
    path: Path,
) -> dict[str, Any]:

    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def atomic_json_write(
    path: Path,
    obj: Any,
) -> None:

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
            default=str,
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
            "A5_ATOMIC_WRITE_READBACK_FAILED"
        )

    temp.replace(
        path
    )


def append_jsonl(
    path: Path,
    obj: Any,
) -> None:

    line = (
        json.dumps(
            obj,
            separators=(",", ":"),
            ensure_ascii=False,
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

        handle.write(
            line
        )

        handle.flush()


def processed_ids() -> set[str]:

    if not PROCESSED_LEDGER.exists():
        return set()

    return {
        item["event_id"]
        for item in load_jsonl(
            PROCESSED_LEDGER
        )
        if item.get(
            "event_id"
        )
    }


def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    text = str(
        value
    ).lower()

    text = text.replace(
        "\\",
        "/"
    )

    text = re.sub(
        r"[0-9a-f]{32,64}",
        "<hash>",
        text,
    )

    text = re.sub(
        r"\b\d+\b",
        "<n>",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def failure_geometry(
    event: dict[str, Any],
) -> dict[str, Any]:

    output = event.get(
        "output_ref"
    )

    if not isinstance(
        output,
        dict,
    ):
        output = {
            "message":
                output
        }

    return {
        "event_type":
            "FAILURE",

        "tool":
            normalize_text(
                event.get(
                    "tool"
                )
            ),

        "exception_type":
            normalize_text(
                output.get(
                    "exception_type"
                )
            ),

        "message":
            normalize_text(
                output.get(
                    "message"
                )
            ),

        "unresolved_flags":
            sorted(
                normalize_text(
                    item
                )
                for item
                in event.get(
                    "unresolved_flags",
                    [],
                )
            ),
    }


def failure_family_id(
    event: dict[str, Any],
) -> str:

    return (
        "ff:"
        +
        digest(
            failure_geometry(
                event
            )
        )[:32]
    )


def failure_family_path(
    family_id: str,
) -> Path:

    safe = family_id.replace(
        ":",
        "_"
    )

    return (
        FAILURE_FAMILIES /
        f"{safe}.json"
    )


def pattern_id(
    event: dict[str, Any],
) -> str:

    payload = {
        "event_type":
            event.get(
                "event_type"
            ),

        "intent":
            normalize_text(
                event.get(
                    "intent"
                )
            ),

        "tool":
            normalize_text(
                event.get(
                    "tool"
                )
            ),

        "success":
            event.get(
                "success"
            ),
    }

    return (
        "pattern:"
        +
        digest(
            payload
        )[:32]
    )


def update_pattern(
    event: dict[str, Any],
) -> None:

    pid = pattern_id(
        event
    )

    safe = pid.replace(
        ":",
        "_"
    )

    path = (
        PATTERNS /
        f"{safe}.json"
    )

    if path.exists():
        pattern = load_json(
            path
        )
    else:
        pattern = {
            "schema":
                "raios.experience-pattern.v1",

            "pattern_id":
                pid,

            "event_type":
                event.get(
                    "event_type"
                ),

            "normalized_intent":
                normalize_text(
                    event.get(
                        "intent"
                    )
                ),

            "tool":
                normalize_text(
                    event.get(
                        "tool"
                    )
                ),

            "success":
                event.get(
                    "success"
                ),

            "occurrence_count":
                0,

            "source_event_ids":
                [],

            "first_seen":
                event.get(
                    "timestamp"
                )
                or
                now(),

            "last_seen":
                event.get(
                    "timestamp"
                )
                or
                now(),

            "status":
                "OBSERVED",
        }

    event_id = event[
        "event_id"
    ]

    if (
        event_id
        not in
        pattern[
            "source_event_ids"
        ]
    ):
        pattern[
            "source_event_ids"
        ].append(
            event_id
        )

        pattern[
            "occurrence_count"
        ] += 1

    pattern[
        "last_seen"
    ] = (
        event.get(
            "timestamp"
        )
        or
        now()
    )

    if (
        pattern[
            "occurrence_count"
        ]
        >=
        2
    ):
        pattern[
            "status"
        ] = "REPEATED"

    atomic_json_write(
        path,
        pattern,
    )


def update_failure_family(
    event: dict[str, Any],
) -> str:

    fid = failure_family_id(
        event
    )

    path = failure_family_path(
        fid
    )

    geometry = failure_geometry(
        event
    )

    if path.exists():
        family = load_json(
            path
        )
    else:
        family = {
            "schema":
                "raios.failure-family.v1",

            "family_id":
                fid,

            "geometry":
                geometry,

            "occurrence_count":
                0,

            "successful_recoveries":
                0,

            "failed_recoveries":
                0,

            "source_event_ids":
                [],

            "tools":
                [],

            "repository_shas":
                [],

            "first_seen":
                event.get(
                    "timestamp"
                )
                or
                now(),

            "last_seen":
                event.get(
                    "timestamp"
                )
                or
                now(),

            "status":
                "ACTIVE",
        }

    event_id = event[
        "event_id"
    ]

    if (
        event_id
        not in
        family[
            "source_event_ids"
        ]
    ):
        family[
            "source_event_ids"
        ].append(
            event_id
        )

        family[
            "occurrence_count"
        ] += 1

    tool = event.get(
        "tool"
    )

    if (
        tool
        and
        tool
        not in
        family[
            "tools"
        ]
    ):
        family[
            "tools"
        ].append(
            tool
        )

    sha = event.get(
        "repository_sha"
    )

    if (
        sha
        and
        sha
        not in
        family[
            "repository_shas"
        ]
    ):
        family[
            "repository_shas"
        ].append(
            sha
        )

    family[
        "last_seen"
    ] = (
        event.get(
            "timestamp"
        )
        or
        now()
    )

    atomic_json_write(
        path,
        family,
    )

    return fid


def record_recovery(
    event: dict[str, Any],
) -> None:

    metadata = (
        event.get(
            "metadata"
        )
        or
        {}
    )

    family_id = metadata.get(
        "failure_family_id"
    )

    if not family_id:
        return

    family_path = failure_family_path(
        family_id
    )

    if not family_path.exists():
        return

    outcome_id = (
        "recovery:"
        +
        event[
            "event_id"
        ]
    )

    safe = outcome_id.replace(
        ":",
        "_"
    )

    outcome_path = (
        RECOVERY_MEMORY /
        f"{safe}.json"
    )

    success = bool(
        metadata.get(
            "recovery_success"
        )
    )

    if outcome_path.exists():
        return

    outcome = {
        "schema":
            "raios.recovery-outcome.v1",

        "outcome_id":
            outcome_id,

        "source_event_id":
            event[
                "event_id"
            ],

        "failure_family_id":
            family_id,

        "success":
            success,

        "recovery_method":
            metadata.get(
                "recovery_method"
            ),

        "evidence_refs":
            event.get(
                "evidence_refs",
                [],
            ),

        "observed_at":
            event.get(
                "timestamp"
            )
            or
            now(),
    }

    atomic_json_write(
        outcome_path,
        outcome,
    )

    family = load_json(
        family_path
    )

    if success:
        family[
            "successful_recoveries"
        ] += 1
    else:
        family[
            "failed_recoveries"
        ] += 1

    atomic_json_write(
        family_path,
        family,
    )


def candidate_score(
    family: dict[str, Any],
) -> float:

    occurrences = int(
        family.get(
            "occurrence_count",
            0,
        )
    )

    success = int(
        family.get(
            "successful_recoveries",
            0,
        )
    )

    failed = int(
        family.get(
            "failed_recoveries",
            0,
        )
    )

    frequency_component = (
        min(
            occurrences / 3.0,
            1.0,
        )
        *
        0.40
    )

    recovery_component = (
        min(
            success / 2.0,
            1.0,
        )
        *
        0.40
    )

    total_recovery = (
        success
        +
        failed
    )

    if total_recovery == 0:
        reliability_component = 0.0
    else:
        reliability_component = (
            success /
            total_recovery
        ) * 0.20

    score = (
        frequency_component
        +
        recovery_component
        +
        reliability_component
    )

    return round(
        min(
            max(
                score,
                0.0,
            ),
            1.0,
        ),
        6,
    )


def mine_skill_candidates() -> int:

    created_or_updated = 0

    for family_path in sorted(
        FAILURE_FAMILIES.glob(
            "*.json"
        )
    ):

        family = load_json(
            family_path
        )

        occurrences = int(
            family.get(
                "occurrence_count",
                0,
            )
        )

        successful = int(
            family.get(
                "successful_recoveries",
                0,
            )
        )

        if occurrences < 2:
            continue

        if successful < 1:
            continue

        score = candidate_score(
            family
        )

        if score < 0.60:
            continue

        family_id = family[
            "family_id"
        ]

        candidate_id = (
            "skill:"
            +
            family_id
        )

        safe = candidate_id.replace(
            ":",
            "_"
        )

        candidate_path = (
            SKILL_CANDIDATES /
            f"{safe}.json"
        )

        candidate = {
            "schema":
                "raios.skill-candidate.v2",

            "candidate_id":
                candidate_id,

            "source_failure_family":
                family_id,

            "candidate_type":
                "RECOVERY_SKILL",

            "status":
                "REVIEW_REQUIRED",

            "canonical_promotion":
                False,

            "evidence_score":
                score,

            "occurrence_count":
                occurrences,

            "successful_recoveries":
                successful,

            "failed_recoveries":
                int(
                    family.get(
                        "failed_recoveries",
                        0,
                    )
                ),

            "evidence_refs":
                list(
                    family.get(
                        "source_event_ids",
                        [],
                    )
                ),

            "promotion_path": [
                "CANDIDATE",
                "REPLAY",
                "BENCHMARK",
                "VERIFICATION",
                "GOVERNED_PROMOTION",
            ],

            "updated_at":
                now(),
        }

        atomic_json_write(
            candidate_path,
            candidate,
        )

        replay_id = (
            "replay:"
            +
            candidate_id
        )

        replay_safe = replay_id.replace(
            ":",
            "_"
        )

        replay_path = (
            REPLAY_QUEUE /
            f"{replay_safe}.json"
        )

        if not replay_path.exists():

            replay = {
                "schema":
                    "raios.replay-job.v1",

                "replay_id":
                    replay_id,

                "candidate_id":
                    candidate_id,

                "failure_family_id":
                    family_id,

                "status":
                    "QUEUED",

                "canonical_mutation":
                    False,

                "created_at":
                    now(),
            }

            atomic_json_write(
                replay_path,
                replay,
            )

        created_or_updated += 1

    return created_or_updated


def process_event(
    event: dict[str, Any],
) -> dict[str, Any]:

    event_id = event.get(
        "event_id"
    )

    if not event_id:
        raise RuntimeError(
            "A5_EVENT_ID_MISSING"
        )

    if (
        event_id
        in
        processed_ids()
    ):
        return {
            "event_id":
                event_id,

            "status":
                "ALREADY_PROCESSED",
        }

    update_pattern(
        event
    )

    family_id = None

    event_type = event.get(
        "event_type"
    )

    if (
        event_type
        ==
        "FAILURE"
        or
        event.get(
            "success"
        )
        is False
    ):
        family_id = (
            update_failure_family(
                event
            )
        )

    if (
        event_type
        ==
        "RECOVERY"
    ):
        record_recovery(
            event
        )

    append_jsonl(
        PROCESSED_LEDGER,
        {
            "event_id":
                event_id,

            "processed_at":
                now(),

            "event_type":
                event_type,

            "failure_family_id":
                family_id,
        },
    )

    return {
        "event_id":
            event_id,

        "status":
            "PROCESSED",

        "failure_family_id":
            family_id,
    }


def process_all() -> dict[str, Any]:

    events = load_jsonl(
        WAL_FILE
    )

    already = processed_ids()

    processed_now = 0
    skipped = 0

    for event in events:

        event_id = event.get(
            "event_id"
        )

        if event_id in already:
            skipped += 1
            continue

        result = process_event(
            event
        )

        if (
            result.get(
                "status"
            )
            ==
            "PROCESSED"
        ):
            processed_now += 1

            already.add(
                event_id
            )

    candidates_touched = (
        mine_skill_candidates()
    )

    return {
        "schema":
            "raios.evolution-consumer-pass.v1",

        "timestamp":
            now(),

        "wal_events":
            len(
                events
            ),

        "processed_now":
            processed_now,

        "skipped_existing":
            skipped,

        "processed_total":
            len(
                processed_ids()
            ),

        "failure_families":
            len(
                list(
                    FAILURE_FAMILIES.glob(
                        "*.json"
                    )
                )
            ),

        "experience_patterns":
            len(
                list(
                    PATTERNS.glob(
                        "*.json"
                    )
                )
            ),

        "recovery_outcomes":
            len(
                list(
                    RECOVERY_MEMORY.glob(
                        "*.json"
                    )
                )
            ),

        "skill_candidates":
            len(
                list(
                    SKILL_CANDIDATES.glob(
                        "*.json"
                    )
                )
            ),

        "replay_jobs":
            len(
                list(
                    REPLAY_QUEUE.glob(
                        "*.json"
                    )
                )
            ),

        "candidate_updates":
            candidates_touched,

        "canonical_mutation":
            False,
    }


def status() -> dict[str, Any]:

    families = [
        load_json(
            path
        )
        for path
        in sorted(
            FAILURE_FAMILIES.glob(
                "*.json"
            )
        )
    ]

    candidates = [
        load_json(
            path
        )
        for path
        in sorted(
            SKILL_CANDIDATES.glob(
                "*.json"
            )
        )
    ]

    return {
        "schema":
            "raios.evolution-brain-status.v1",

        "failure_family_count":
            len(
                families
            ),

        "families":
            families,

        "skill_candidate_count":
            len(
                candidates
            ),

        "candidates":
            candidates,

        "replay_queue_count":
            len(
                list(
                    REPLAY_QUEUE.glob(
                        "*.json"
                    )
                )
            ),

        "canonical_auto_promotion":
            False,
    }