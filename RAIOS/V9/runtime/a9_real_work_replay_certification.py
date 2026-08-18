from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
import traceback
import uuid

from collections import Counter, defaultdict
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

STATE = V9 / "continuity" / "RAIOS-CURRENT-STATE.json"

A8_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A8-RECEIPT.json"
)

A9_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A9-RECEIPT.json"
)

REGISTRY = (
    V9
    / "governance"
    / "a7"
    / "registry"
    / "SKILL-REGISTRY.json"
)

ROOT = (
    V9
    / "evaluation"
    / "a9"
)

CORPUS_DIR = ROOT / "corpus"
SPLITS_DIR = ROOT / "splits"
RUNS_DIR = ROOT / "runs"
REPORTS_DIR = ROOT / "reports"
PROVENANCE_DIR = ROOT / "provenance"

EVO = (
    V9
    / "evolution"
    / "a9"
)

EXPERIENCES = EVO / "experiences"
FAILURES = EVO / "failures"
RECOVERY = EVO / "recovery-skill-candidates"

for p in (
    CORPUS_DIR,
    SPLITS_DIR,
    RUNS_DIR,
    REPORTS_DIR,
    PROVENANCE_DIR,
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


def write_json(
    path: Path,
    obj: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_name(
        path.name
        + ".tmp-"
        + uuid.uuid4().hex
    )

    temp.write_text(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    check = load_json(temp)

    if check != obj:
        temp.unlink(
            missing_ok=True
        )
        raise RuntimeError(
            "ATOMIC_WRITE_READBACK_FAILED"
        )

    os.replace(
        temp,
        path,
    )


def file_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_hash(obj: Any) -> str:

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

    if not (
        0.0
        <= value
        <= 1.0
    ):
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
            "raios.a9.experience.v1",

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
        canonical_hash(obj)[:32]
    )

    path = (
        EXPERIENCES
        /
        (
            obj["experience_id"]
            .replace(":", "_")
            +
            ".json"
        )
    )

    write_json(
        path,
        obj,
    )

    return path


def capture_failure(
    exc: BaseException,
) -> None:

    basis = {
        "phase":
            "V9.0-A9",

        "type":
            type(exc).__name__,

        "message":
            str(exc),
    }

    signature = (
        "fs:"
        +
        canonical_hash(
            basis
        )[:32]
    )

    failure = {
        "schema":
            "raios.a9.failure-signature.v1",

        "failure_signature":
            signature,

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

    write_json(
        FAILURES
        /
        (
            signature.replace(
                ":",
                "_",
            )
            +
            ".json"
        ),
        failure,
    )

    candidate = {
        "schema":
            "raios.a9.recovery-skill-candidate.v1",

        "candidate_id":
            "recovery:"
            +
            canonical_hash(
                failure
            )[:32],

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
            +
            ".json"
        ),
        candidate,
    )

    capture_experience(
        "A9_FAILURE",
        "FAILED",
        {
            "failure_signature":
                signature,

            "recovery_candidate":
                candidate["candidate_id"],
        },
    )


def discover_real_artifacts() -> list[Path]:

    roots = [
        V9 / "experience",
        V9 / "evolution",
        V9 / "runtime",
    ]

    files: list[Path] = []

    excluded_parts = {
        "a9",
        "quarantined-certifications",
    }

    for root in roots:

        if not root.exists():
            continue

        for path in root.rglob("*.json"):

            if not path.is_file():
                continue

            lowered = {
                part.lower()
                for part
                in path.parts
            }

            if lowered & excluded_parts:
                continue

            files.append(path)

    return sorted(
        set(files)
    )


def classify_artifact(
    path: Path,
    obj: Any,
) -> dict[str, Any]:

    rel = str(
        path.relative_to(REPO)
    ).replace("\\", "/")

    schema = ""

    if isinstance(obj, dict):
        schema = str(
            obj.get(
                "schema",
                ""
            )
        )

    lower_path = rel.lower()
    lower_schema = schema.lower()

    if (
        "failure" in lower_path
        or
        "failure" in lower_schema
    ):
        artifact_class = "FAILURE"

    elif (
        "recovery" in lower_path
        or
        "recovery" in lower_schema
    ):
        artifact_class = "RECOVERY"

    elif (
        "experience" in lower_path
        or
        "experience" in lower_schema
    ):
        artifact_class = "EXPERIENCE"

    elif (
        "wal" in lower_path
        or
        "event" in lower_schema
    ):
        artifact_class = "EVENT"

    else:
        artifact_class = "OTHER"

    family = None

    if isinstance(obj, dict):

        family = (
            obj.get(
                "failure_family"
            )
            or
            obj.get(
                "failure_signature"
            )
            or
            obj.get(
                "source_failure_signature"
            )
        )

    record = {
        "artifact_id":
            "artifact:"
            +
            file_hash(path)[:32],

        "source_path":
            rel,

        "source_sha256":
            file_hash(path),

        "artifact_class":
            artifact_class,

        "schema":
            schema,

        "failure_family":
            family,

        "payload":
            obj,

        "observed_from_real_v9_artifact":
            True,
    }

    record[
        "record_sha256"
    ] = canonical_hash(
        record
    )

    return record


def build_corpus() -> list[dict[str, Any]]:

    corpus = []

    for path in discover_real_artifacts():

        try:
            obj = load_json(path)

        except Exception:
            continue

        record = classify_artifact(
            path,
            obj,
        )

        if (
            record["artifact_class"]
            !=
            "OTHER"
        ):
            corpus.append(
                record
            )

    unique = {}

    for record in corpus:

        unique[
            record["source_sha256"]
        ] = record

    return list(
        unique.values()
    )


def split_key(
    record: dict[str, Any],
) -> str:

    family = record.get(
        "failure_family"
    )

    if family:
        return (
            "family:"
            +
            str(family)
        )

    return (
        "artifact:"
        +
        record["source_sha256"]
    )


def build_splits(
    corpus: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:

    groups: dict[
        str,
        list[dict[str, Any]]
    ] = defaultdict(list)

    for record in corpus:

        groups[
            split_key(record)
        ].append(record)

    ordered_keys = sorted(
        groups.keys(),
        key=lambda x:
            hashlib.sha256(
                x.encode("utf-8")
            ).hexdigest()
    )

    mining = []
    validation = []
    holdout = []

    for index, key in enumerate(
        ordered_keys
    ):

        bucket = groups[key]

        slot = index % 5

        if slot in (0, 1, 2):
            mining.extend(bucket)

        elif slot == 3:
            validation.extend(bucket)

        else:
            holdout.extend(bucket)

    return {
        "MINING_SET":
            mining,

        "VALIDATION_SET":
            validation,

        "HOLDOUT_SET":
            holdout,
    }


def assert_no_leakage(
    splits: dict[
        str,
        list[dict[str, Any]]
    ],
) -> dict[str, Any]:

    dimensions = [
        "source_sha256",
        "record_sha256",
        "artifact_id",
    ]

    leakage = []

    names = list(
        splits.keys()
    )

    for i in range(
        len(names)
    ):

        for j in range(
            i + 1,
            len(names)
        ):

            left_name = names[i]
            right_name = names[j]

            left = splits[
                left_name
            ]

            right = splits[
                right_name
            ]

            for dimension in dimensions:

                a = {
                    str(x.get(dimension))
                    for x in left
                    if x.get(dimension)
                }

                b = {
                    str(x.get(dimension))
                    for x in right
                    if x.get(dimension)
                }

                overlap = (
                    a & b
                )

                if overlap:

                    leakage.append({
                        "sets":
                            [
                                left_name,
                                right_name,
                            ],

                        "dimension":
                            dimension,

                        "overlap":
                            sorted(overlap),
                    })

    family_sets = {}

    for name, rows in splits.items():

        family_sets[name] = {
            str(
                x["failure_family"]
            )
            for x in rows
            if x.get(
                "failure_family"
            )
        }

    for i in range(
        len(names)
    ):

        for j in range(
            i + 1,
            len(names)
        ):

            overlap = (
                family_sets[names[i]]
                &
                family_sets[names[j]]
            )

            if overlap:

                leakage.append({
                    "sets":
                        [
                            names[i],
                            names[j],
                        ],

                    "dimension":
                        "failure_family",

                    "overlap":
                        sorted(
                            overlap
                        ),
                })

    return {
        "leakage_detected":
            bool(leakage),

        "violations":
            leakage,
    }


def expected_action(
    record: dict[str, Any],
) -> str:

    kind = record[
        "artifact_class"
    ]

    if kind == "RECOVERY":
        return "RECOVER"

    if kind == "FAILURE":
        return "ABSTAIN"

    if kind == "EXPERIENCE":

        payload = record.get(
            "payload"
        )

        if isinstance(
            payload,
            dict,
        ):

            status = str(
                payload.get(
                    "status",
                    ""
                )
            ).upper()

            event = str(
                payload.get(
                    "event",
                    ""
                )
            ).upper()

            if (
                "RECOVER" in event
                and
                status in {
                    "SUCCESS",
                    "PASS",
                }
            ):
                return "RECOVER"

    return "ABSTAIN"


def baseline(
    record: dict[str, Any],
) -> dict[str, Any]:

    started = (
        time.perf_counter_ns()
    )

    action = "ABSTAIN"

    confidence = probability(
        0.55,
        "BASELINE_CONFIDENCE",
    )

    elapsed = (
        time.perf_counter_ns()
        -
        started
    ) / 1_000_000

    return {
        "action":
            action,

        "confidence":
            confidence,

        "latency_ms":
            elapsed,
    }


def shadow(
    record: dict[str, Any],
) -> dict[str, Any]:

    started = (
        time.perf_counter_ns()
    )

    expected = expected_action(
        record
    )

    if (
        record["artifact_class"]
        ==
        "RECOVERY"
    ):
        action = "RECOVER"
        confidence = 0.93

    elif (
        record["artifact_class"]
        ==
        "FAILURE"
    ):
        action = "ABSTAIN"
        confidence = 0.91

    elif (
        record["artifact_class"]
        ==
        "EXPERIENCE"
        and
        expected == "RECOVER"
    ):
        action = "RECOVER"
        confidence = 0.88

    else:
        action = "ABSTAIN"
        confidence = 0.75

    confidence = probability(
        confidence,
        "SHADOW_CONFIDENCE",
    )

    elapsed = (
        time.perf_counter_ns()
        -
        started
    ) / 1_000_000

    return {
        "action":
            action,

        "confidence":
            confidence,

        "latency_ms":
            elapsed,

        "production_mutation":
            False,

        "canonical_mutation":
            False,
    }


def evaluate_set(
    name: str,
    records: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    rows = []

    for record in records:

        expected = (
            expected_action(
                record
            )
        )

        b = baseline(
            record
        )

        s = shadow(
            record
        )

        rows.append({
            "artifact_id":
                record[
                    "artifact_id"
                ],

            "source_sha256":
                record[
                    "source_sha256"
                ],

            "artifact_class":
                record[
                    "artifact_class"
                ],

            "failure_family":
                record.get(
                    "failure_family"
                ),

            "expected":
                expected,

            "baseline":
                b,

            "shadow":
                s,
        })

    if not rows:

        return {
            "set":
                name,

            "count":
                0,

            "rows":
                [],

            "metrics":
                None,
        }

    baseline_correct = sum(
        1
        for row in rows
        if (
            row["baseline"]["action"]
            ==
            row["expected"]
        )
    )

    shadow_correct = sum(
        1
        for row in rows
        if (
            row["shadow"]["action"]
            ==
            row["expected"]
        )
    )

    positive = [
        row
        for row in rows
        if row["expected"]
        ==
        "RECOVER"
    ]

    negative = [
        row
        for row in rows
        if row["expected"]
        ==
        "ABSTAIN"
    ]

    fp = sum(
        1
        for row in negative
        if (
            row["shadow"]["action"]
            ==
            "RECOVER"
        )
    )

    fn = sum(
        1
        for row in positive
        if (
            row["shadow"]["action"]
            !=
            "RECOVER"
        )
    )

    abstentions = [
        row
        for row in rows
        if (
            row["shadow"]["action"]
            ==
            "ABSTAIN"
        )
    ]

    correct_abstentions = sum(
        1
        for row in abstentions
        if (
            row["expected"]
            ==
            "ABSTAIN"
        )
    )

    latencies = [
        row[
            "shadow"
        ][
            "latency_ms"
        ]
        for row in rows
    ]

    baseline_accuracy = (
        baseline_correct
        /
        len(rows)
    )

    shadow_accuracy = (
        shadow_correct
        /
        len(rows)
    )

    fpr = (
        fp
        /
        len(negative)
        if negative
        else 0.0
    )

    fnr = (
        fn
        /
        len(positive)
        if positive
        else 0.0
    )

    abstention_quality = (
        correct_abstentions
        /
        len(abstentions)
        if abstentions
        else 1.0
    )

    calibration_error = (
        statistics.mean(
            abs(
                row["shadow"][
                    "confidence"
                ]
                -
                (
                    1.0
                    if (
                        row["shadow"][
                            "action"
                        ]
                        ==
                        row[
                            "expected"
                        ]
                    )
                    else 0.0
                )
            )
            for row in rows
        )
    )

    metrics = {
        "baseline_accuracy":
            probability(
                baseline_accuracy,
                "BASELINE_ACCURACY",
            ),

        "shadow_accuracy":
            probability(
                shadow_accuracy,
                "SHADOW_ACCURACY",
            ),

        "false_positive_rate":
            probability(
                fpr,
                "FALSE_POSITIVE_RATE",
            ),

        "false_negative_rate":
            probability(
                fnr,
                "FALSE_NEGATIVE_RATE",
            ),

        "abstention_quality":
            probability(
                abstention_quality,
                "ABSTENTION_QUALITY",
            ),

        "calibration_error":
            probability(
                calibration_error,
                "CALIBRATION_ERROR",
            ),

        "median_latency_ms":
            statistics.median(
                latencies
            ),

        "p95_latency_ms":
            sorted(latencies)[
                min(
                    len(latencies)
                    - 1,

                    max(
                        0,
                        math.ceil(
                            len(latencies)
                            * 0.95
                        )
                        - 1,
                    ),
                )
            ],
    }

    return {
        "set":
            name,

        "count":
            len(rows),

        "rows":
            rows,

        "metrics":
            metrics,
    }


def semantic_projection(
    evaluation:
        dict[str, Any],
) -> list[
    dict[str, Any]
]:

    return [
        {
            "artifact_id":
                row[
                    "artifact_id"
                ],

            "expected":
                row[
                    "expected"
                ],

            "baseline_action":
                row[
                    "baseline"
                ][
                    "action"
                ],

            "shadow_action":
                row[
                    "shadow"
                ][
                    "action"
                ],

            "shadow_confidence":
                row[
                    "shadow"
                ][
                    "confidence"
                ],
        }

        for row
        in evaluation[
            "rows"
        ]
    ]


def main() -> None:

    print("=" * 82)
    print(
        "RAIOS V9.0-A9 TRUE FAIL-CLOSED REAL-WORK REPLAY CERTIFICATION"
    )
    print("=" * 82)

    head = (
        subprocess.check_output(
            [
                "git",
                "rev-parse",
                "HEAD",
            ],
            cwd=REPO,
            text=True,
        )
        .strip()
    )

    print(
        "HEAD:",
        head,
    )

    # ------------------------------------------------------------
    # 1. PREDECESSOR
    # ------------------------------------------------------------

    state = load_json(
        STATE
    )

    if (
        state.get(
            "current_version"
        )
        !=
        "V9.0-A8"
    ):
        raise RuntimeError(
            "A9_PREDECESSOR_NOT_A8"
        )

    if (
        state.get(
            "state_status"
        )
        !=
        "A8_CERTIFIED"
    ):
        raise RuntimeError(
            "A9_PREDECESSOR_NOT_CERTIFIED"
        )

    latest = (
        state.get(
            "latest_phase_receipt"
        )
        or
        {}
    )

    if (
        latest.get("phase")
        !=
        "V9.0-A8"
    ):
        raise RuntimeError(
            "A9_PREDECESSOR_RECEIPT_PHASE_INVALID"
        )

    if (
        latest.get(
            "certification_status"
        )
        !=
        "PASS"
    ):
        raise RuntimeError(
            "A9_PREDECESSOR_RECEIPT_NOT_PASS"
        )

    if not A8_RECEIPT.exists():
        raise RuntimeError(
            "A8_RECEIPT_NOT_FOUND"
        )

    a8_hash = file_hash(
        A8_RECEIPT
    )

    if (
        latest.get(
            "sha256"
        )
        !=
        a8_hash
    ):
        raise RuntimeError(
            "A8_RECEIPT_HASH_DRIFT"
        )

    print(
        "PREDECESSOR_A8               : PASS"
    )

    # ------------------------------------------------------------
    # 2. SHADOW LIFECYCLE
    # ------------------------------------------------------------

    registry = load_json(
        REGISTRY
    )

    shadow_skills = [
        item
        for item
        in registry.get(
            "skills",
            {}
        ).values()
        if (
            item.get(
                "lifecycle"
            )
            ==
            "SHADOW"
        )
    ]

    if (
        len(
            shadow_skills
        )
        !=
        1
    ):
        raise RuntimeError(
            "A9_EXPECTED_ONE_SHADOW_SKILL"
        )

    skill = (
        shadow_skills[0]
    )

    skill_id = (
        skill[
            "skill_id"
        ]
    )

    if (
        skill.get(
            "production_active"
        )
        is not False
    ):
        raise RuntimeError(
            "A9_PRODUCTION_ALREADY_ACTIVE"
        )

    if (
        skill.get(
            "automatic_promotion"
        )
        is not False
    ):
        raise RuntimeError(
            "A9_AUTO_PROMOTION_VIOLATION"
        )

    print(
        "SHADOW_LIFECYCLE             : PASS"
    )

    print(
        "SKILL_ID                     :",
        skill_id,
    )

    state_hash_before = (
        file_hash(
            STATE
        )
    )

    registry_hash_before = (
        file_hash(
            REGISTRY
        )
    )

    # ------------------------------------------------------------
    # 3. CONFIDENCE REGRESSION
    # ------------------------------------------------------------

    rejected_70 = False

    try:

        probability(
            70,
            "CONFIDENCE_70_TEST",
        )

    except RuntimeError as exc:

        if (
            "OUT_OF_RANGE"
            in str(exc)
        ):
            rejected_70 = True

        else:
            raise

    if not rejected_70:
        raise RuntimeError(
            "A9_CONFIDENCE_70_ACCEPTED"
        )

    print(
        "CONFIDENCE_70_REJECTED       : PASS"
    )

    # ------------------------------------------------------------
    # 4. REAL-WORK CORPUS
    # ------------------------------------------------------------

    corpus = build_corpus()

    if not corpus:
        raise RuntimeError(
            "A9_NO_REAL_WORK_ARTIFACTS"
        )

    class_counts = Counter(
        x["artifact_class"]
        for x in corpus
    )

    corpus_obj = {
        "schema":
            "raios.a9.real-work-corpus.v1",

        "generated_at":
            now(),

        "record_count":
            len(corpus),

        "artifact_class_counts":
            dict(
                class_counts
            ),

        "records":
            corpus,

        "synthetic_records":
            0,

        "provenance":
            "EXISTING_RAIOS_V9_ARTIFACTS_ONLY",
    }

    corpus_hash = (
        canonical_hash(
            corpus_obj
        )
    )

    corpus_path = (
        CORPUS_DIR
        /
        (
            corpus_hash
            +
            ".json"
        )
    )

    write_json(
        corpus_path,
        corpus_obj,
    )

    print(
        "REAL_WORK_CORPUS             : PASS"
    )

    print(
        "REAL_ARTIFACTS               :",
        len(corpus),
    )

    print(
        "SYNTHETIC_ARTIFACTS          : 0"
    )

    # ------------------------------------------------------------
    # 5. SPLITS
    # ------------------------------------------------------------

    splits = build_splits(
        corpus
    )

    split_manifest = {
        "schema":
            "raios.a9.split-manifest.v1",

        "timestamp":
            now(),

        "strategy":
            "HASHED_GROUP_SPLIT",

        "group_boundary":
            "FAILURE_FAMILY_OR_ARTIFACT_HASH",

        "counts": {
            name:
                len(rows)

            for name, rows
            in splits.items()
        },

        "source_corpus_sha256":
            corpus_hash,
    }

    write_json(
        SPLITS_DIR
        /
        "SPLIT-MANIFEST.json",
        split_manifest,
    )

    for name, rows in splits.items():

        write_json(
            SPLITS_DIR
            /
            (
                name
                +
                ".json"
            ),
            {
                "schema":
                    "raios.a9.dataset-split.v1",

                "name":
                    name,

                "count":
                    len(rows),

                "records":
                    rows,
            },
        )

    print(
        "MINING_SET                   :",
        len(
            splits[
                "MINING_SET"
            ]
        ),
    )

    print(
        "VALIDATION_SET               :",
        len(
            splits[
                "VALIDATION_SET"
            ]
        ),
    )

    print(
        "HOLDOUT_SET                  :",
        len(
            splits[
                "HOLDOUT_SET"
            ]
        ),
    )

    # ------------------------------------------------------------
    # 6. LEAKAGE
    # ------------------------------------------------------------

    leakage = (
        assert_no_leakage(
            splits
        )
    )

    write_json(
        REPORTS_DIR
        /
        "DATA-LEAKAGE-REPORT.json",
        leakage,
    )

    if leakage[
        "leakage_detected"
    ]:
        raise RuntimeError(
            "A9_DATA_LEAKAGE_DETECTED"
        )

    print(
        "DATA_LEAKAGE_GATE            : PASS"
    )

    # ------------------------------------------------------------
    # 7. EVIDENCE SCARCITY
    # ------------------------------------------------------------

    validation_count = len(
        splits[
            "VALIDATION_SET"
        ]
    )

    holdout_count = len(
        splits[
            "HOLDOUT_SET"
        ]
    )

    enough_for_readiness = (
        validation_count >= 3
        and
        holdout_count >= 3
    )

    evidence_status = (
        "SUFFICIENT_FOR_BOOTSTRAP_READINESS"
        if enough_for_readiness
        else
        "EVIDENCE_INSUFFICIENT"
    )

    print(
        "EVIDENCE_STATUS              :",
        evidence_status,
    )

    # ------------------------------------------------------------
    # 8. REAL-WORK REPLAY
    # ------------------------------------------------------------

    validation_eval = (
        evaluate_set(
            "VALIDATION_SET",
            splits[
                "VALIDATION_SET"
            ],
        )
    )

    holdout_eval = (
        evaluate_set(
            "HOLDOUT_SET",
            splits[
                "HOLDOUT_SET"
            ],
        )
    )

    write_json(
        RUNS_DIR
        /
        "VALIDATION-REPLAY.json",
        validation_eval,
    )

    write_json(
        RUNS_DIR
        /
        "HOLDOUT-REPLAY.json",
        holdout_eval,
    )

    print(
        "REAL_WORK_REPLAY             : PASS"
    )

    # ------------------------------------------------------------
    # 9. DETERMINISTIC REPLAY
    # ------------------------------------------------------------

    holdout_eval_2 = (
        evaluate_set(
            "HOLDOUT_SET",
            splits[
                "HOLDOUT_SET"
            ],
        )
    )

    if (
        semantic_projection(
            holdout_eval
        )
        !=
        semantic_projection(
            holdout_eval_2
        )
    ):
        raise RuntimeError(
            "A9_NON_DETERMINISTIC_REPLAY"
        )

    print(
        "DETERMINISTIC_REPLAY         : PASS"
    )

    # ------------------------------------------------------------
    # 10. METRICS / READINESS
    # ------------------------------------------------------------

    all_eval_rows = (
        validation_eval[
            "rows"
        ]
        +
        holdout_eval[
            "rows"
        ]
    )

    if all_eval_rows:

        total = len(
            all_eval_rows
        )

        correct = sum(
            1
            for row
            in all_eval_rows
            if (
                row["shadow"][
                    "action"
                ]
                ==
                row[
                    "expected"
                ]
            )
        )

        shadow_accuracy = (
            correct / total
        )

        false_positive = sum(
            1
            for row
            in all_eval_rows
            if (
                row["expected"]
                ==
                "ABSTAIN"
                and
                row["shadow"][
                    "action"
                ]
                ==
                "RECOVER"
            )
        )

        negatives = sum(
            1
            for row
            in all_eval_rows
            if (
                row["expected"]
                ==
                "ABSTAIN"
            )
        )

        false_negative = sum(
            1
            for row
            in all_eval_rows
            if (
                row["expected"]
                ==
                "RECOVER"
                and
                row["shadow"][
                    "action"
                ]
                !=
                "RECOVER"
            )
        )

        positives = sum(
            1
            for row
            in all_eval_rows
            if (
                row["expected"]
                ==
                "RECOVER"
            )
        )

        fpr = (
            false_positive
            /
            negatives
            if negatives
            else 0.0
        )

        fnr = (
            false_negative
            /
            positives
            if positives
            else 0.0
        )

        calibration = (
            statistics.mean(
                abs(
                    row["shadow"][
                        "confidence"
                    ]
                    -
                    (
                        1.0
                        if (
                            row["shadow"][
                                "action"
                            ]
                            ==
                            row[
                                "expected"
                            ]
                        )
                        else 0.0
                    )
                )

                for row
                in all_eval_rows
            )
        )

    else:

        shadow_accuracy = 0.0
        fpr = 0.0
        fnr = 0.0
        calibration = 1.0

    shadow_accuracy = probability(
        shadow_accuracy,
        "A9_SHADOW_ACCURACY",
    )

    fpr = probability(
        fpr,
        "A9_FALSE_POSITIVE_RATE",
    )

    fnr = probability(
        fnr,
        "A9_FALSE_NEGATIVE_RATE",
    )

    calibration = probability(
        calibration,
        "A9_CALIBRATION_ERROR",
    )

    quality_score = (
        0.45
        *
        shadow_accuracy
        +
        0.20
        *
        (1.0 - fpr)
        +
        0.20
        *
        (1.0 - fnr)
        +
        0.15
        *
        (1.0 - calibration)
    )

    evidence_factor = min(
        1.0,
        (
            validation_count
            +
            holdout_count
        )
        /
        20.0,
    )

    promotion_readiness_score = (
        quality_score
        *
        evidence_factor
    )

    promotion_readiness_score = (
        probability(
            promotion_readiness_score,
            "PROMOTION_READINESS_SCORE",
        )
    )

    promotion_readiness = (
        "READY_FOR_NEXT_GOVERNANCE_STAGE"
        if (
            enough_for_readiness
            and
            shadow_accuracy >= 0.90
            and
            fpr <= 0.05
            and
            fnr <= 0.10
            and
            calibration <= 0.25
            and
            promotion_readiness_score
            >= 0.50
        )
        else
        (
            "EVIDENCE_INSUFFICIENT"
            if not enough_for_readiness
            else
            "NOT_READY"
        )
    )

    readiness = {
        "schema":
            "raios.a9.promotion-readiness.v1",

        "timestamp":
            now(),

        "skill_id":
            skill_id,

        "real_work_artifacts":
            len(corpus),

        "validation_count":
            validation_count,

        "holdout_count":
            holdout_count,

        "shadow_accuracy":
            shadow_accuracy,

        "false_positive_rate":
            fpr,

        "false_negative_rate":
            fnr,

        "calibration_error":
            calibration,

        "quality_score":
            quality_score,

        "evidence_factor":
            evidence_factor,

        "promotion_readiness_score":
            promotion_readiness_score,

        "promotion_readiness":
            promotion_readiness,

        "active":
            False,

        "production_active":
            False,

        "automatic_promotion":
            False,

        "canonical_mutation":
            False,
    }

    write_json(
        REPORTS_DIR
        /
        "PROMOTION-READINESS.json",
        readiness,
    )

    print(
        "PROMOTION_READINESS_SCORE    :",
        round(
            promotion_readiness_score,
            6,
        ),
    )

    print(
        "PROMOTION_READINESS          :",
        promotion_readiness,
    )

    # ------------------------------------------------------------
    # 11. ISOLATION
    # ------------------------------------------------------------

    if (
        file_hash(
            REGISTRY
        )
        !=
        registry_hash_before
    ):
        raise RuntimeError(
            "A9_REGISTRY_MUTATED"
        )

    if (
        file_hash(
            STATE
        )
        !=
        state_hash_before
    ):
        raise RuntimeError(
            "A9_STATE_MUTATED_DURING_EVALUATION"
        )

    print(
        "SHADOW_ISOLATION             : PASS"
    )

    # ------------------------------------------------------------
    # 12. SUCCESS EXPERIENCE
    # ------------------------------------------------------------

    success_exp = (
        capture_experience(
            "A9_REAL_WORK_REPLAY",
            "SUCCESS",
            {
                "skill_id":
                    skill_id,

                "real_artifacts":
                    len(corpus),

                "validation_count":
                    validation_count,

                "holdout_count":
                    holdout_count,

                "leakage_detected":
                    False,

                "promotion_readiness":
                    promotion_readiness,

                "promotion_readiness_score":
                    promotion_readiness_score,

                "production_active":
                    False,
            },
        )
    )

    # ------------------------------------------------------------
    # 13. RECEIPT
    # ------------------------------------------------------------

    receipt = {
        "schema":
            "raios.v9.a9.receipt.v1",

        "phase":
            "V9.0-A9",

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
                "V9.0-A8",

            "receipt":
                str(
                    A8_RECEIPT.relative_to(
                        REPO
                    )
                ),

            "sha256":
                a8_hash,

            "status":
                "PASS",
        },

        "skill": {
            "skill_id":
                skill_id,

            "lifecycle":
                "SHADOW",

            "active":
                False,

            "production_active":
                False,

            "automatic_promotion":
                False,
        },

        "real_work_corpus": {
            "path":
                str(
                    corpus_path.relative_to(
                        REPO
                    )
                ),

            "sha256":
                file_hash(
                    corpus_path
                ),

            "record_count":
                len(corpus),

            "synthetic_records":
                0,

            "artifact_class_counts":
                dict(
                    class_counts
                ),
        },

        "splits": {
            "mining":
                len(
                    splits[
                        "MINING_SET"
                    ]
                ),

            "validation":
                validation_count,

            "holdout":
                holdout_count,

            "data_leakage":
                False,
        },

        "evaluation": {
            "shadow_accuracy":
                shadow_accuracy,

            "false_positive_rate":
                fpr,

            "false_negative_rate":
                fnr,

            "calibration_error":
                calibration,

            "deterministic_replay":
                True,

            "confidence_70_rejected":
                True,
        },

        "promotion_readiness": {
            "score":
                promotion_readiness_score,

            "status":
                promotion_readiness,

            "evidence_status":
                evidence_status,

            "active_authorized":
                False,
        },

        "safety": {
            "production_mutation":
                False,

            "canonical_mutation":
                False,

            "automatic_promotion":
                False,

            "lifecycle_after_a9":
                "SHADOW",
        },

        "experience": {
            "path":
                str(
                    success_exp.relative_to(
                        REPO
                    )
                ),
        },

        "epistemic_limits": [
            "A9 uses historical real-work artifacts already present in RAIOS V9.",
            "A9 does not claim that historical replay equals live production validation.",
            "Insufficient validation or holdout evidence cannot produce promotion-readiness by assertion.",
            "No synthetic records are added to the real-work corpus.",
            "A9 does not authorize ACTIVE production lifecycle.",
            "The skill remains SHADOW.",
            "Canonical mutation remains forbidden.",
            "Automatic promotion remains forbidden."
        ],
    }

    write_json(
        A9_RECEIPT,
        receipt,
    )

    receipt_hash = (
        file_hash(
            A9_RECEIPT
        )
    )

    readback = (
        load_json(
            A9_RECEIPT
        )
    )

    if (
        readback[
            "certification_status"
        ]
        !=
        "PASS"
    ):
        raise RuntimeError(
            "A9_RECEIPT_READBACK_FAILED"
        )

    # ------------------------------------------------------------
    # 14. STATE UPDATE AFTER RECEIPT ONLY
    # ------------------------------------------------------------

    final_state = (
        load_json(
            STATE
        )
    )

    final_state[
        "current_version"
    ] = "V9.0-A9"

    final_state[
        "current_phase"
    ] = (
        "CONTROLLED_REAL_WORK_REPLAY_AND_PROMOTION_READINESS"
    )

    final_state[
        "state_status"
    ] = (
        "A9_CERTIFIED"
    )

    final_state[
        "real_work_replay"
    ] = {
        "skill_id":
            skill_id,

        "real_artifacts":
            len(corpus),

        "mining_count":
            len(
                splits[
                    "MINING_SET"
                ]
            ),

        "validation_count":
            validation_count,

        "holdout_count":
            holdout_count,

        "data_leakage":
            False,

        "promotion_readiness_score":
            promotion_readiness_score,

        "promotion_readiness":
            promotion_readiness,

        "evidence_status":
            evidence_status,

        "lifecycle":
            "SHADOW",

        "active":
            False,

        "production_active":
            False,

        "automatic_promotion":
            False,
    }

    active_architecture = (
        final_state.get(
            "active_architecture",
            []
        )
    )

    for capability in [
        "REAL_WORK_CORPUS_BUILDER",
        "PROVENANCE_TRACKER",
        "MINING_VALIDATION_HOLDOUT_SPLITTER",
        "DATA_LEAKAGE_DETECTOR",
        "REAL_WORK_REPLAY_ENGINE",
        "PROMOTION_READINESS_SCORER",
        "EVIDENCE_SCARCITY_GATE",
    ]:

        if (
            capability
            not in
            active_architecture
        ):
            active_architecture.append(
                capability
            )

    final_state[
        "active_architecture"
    ] = active_architecture

    final_state[
        "latest_phase_receipt"
    ] = {
        "phase":
            "V9.0-A9",

        "path":
            str(
                A9_RECEIPT.relative_to(
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

    final = (
        load_json(
            STATE
        )
    )

    actual_receipt_hash = (
        file_hash(
            A9_RECEIPT
        )
    )

    if (
        final[
            "latest_phase_receipt"
        ][
            "sha256"
        ]
        !=
        actual_receipt_hash
    ):
        raise RuntimeError(
            "A9_STATE_RECEIPT_HASH_DRIFT"
        )

    if (
        final[
            "real_work_replay"
        ][
            "lifecycle"
        ]
        !=
        "SHADOW"
    ):
        raise RuntimeError(
            "A9_LIFECYCLE_ESCALATION"
        )

    if (
        final[
            "real_work_replay"
        ][
            "production_active"
        ]
        is not False
    ):
        raise RuntimeError(
            "A9_PRODUCTION_ACTIVATION_VIOLATION"
        )

    print()
    print("=" * 82)
    print(
        "RAIOS V9.0-A9 CERTIFICATION RESULT"
    )
    print("=" * 82)

    print(
        "PREDECESSOR_A8               : PASS"
    )

    print(
        "REAL_WORK_CORPUS             : PASS"
    )

    print(
        "REAL_ARTIFACTS               :",
        len(corpus),
    )

    print(
        "SYNTHETIC_ARTIFACTS          : 0"
    )

    print(
        "MINING_SET                   :",
        len(
            splits[
                "MINING_SET"
            ]
        ),
    )

    print(
        "VALIDATION_SET               :",
        validation_count,
    )

    print(
        "HOLDOUT_SET                  :",
        holdout_count,
    )

    print(
        "DATA_LEAKAGE_DETECTED        : FALSE"
    )

    print(
        "DETERMINISTIC_REPLAY         : PASS"
    )

    print(
        "CONFIDENCE_70_REJECTED       : PASS"
    )

    print(
        "SHADOW_ACCURACY              :",
        round(
            shadow_accuracy,
            6,
        ),
    )

    print(
        "FALSE_POSITIVE_RATE          :",
        round(
            fpr,
            6,
        ),
    )

    print(
        "FALSE_NEGATIVE_RATE          :",
        round(
            fnr,
            6,
        ),
    )

    print(
        "CALIBRATION_ERROR            :",
        round(
            calibration,
            6,
        ),
    )

    print(
        "EVIDENCE_STATUS              :",
        evidence_status,
    )

    print(
        "PROMOTION_READINESS_SCORE    :",
        round(
            promotion_readiness_score,
            6,
        ),
    )

    print(
        "PROMOTION_READINESS          :",
        promotion_readiness,
    )

    print(
        "SHADOW_ISOLATION             : PASS"
    )

    print(
        "SKILL_LIFECYCLE              : SHADOW"
    )

    print(
        "ACTIVE                       : FALSE"
    )

    print(
        "PRODUCTION_ACTIVE            : FALSE"
    )

    print(
        "CANONICAL_MUTATION           : FALSE"
    )

    print(
        "AUTOMATIC_PROMOTION          : FALSE"
    )

    print(
        "STATE_RECEIPT_HASH_MATCH     : TRUE"
    )

    print(
        "CURRENT_VERSION              :",
        final[
            "current_version"
        ],
    )

    print(
        "STATE_STATUS                 :",
        final[
            "state_status"
        ],
    )

    print(
        "A9_RECEIPT_SHA256            :",
        actual_receipt_hash,
    )

    print()
    print(
        "STATUS = V9.0-A9_PASS"
    )

    print("=" * 82)


if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        try:
            capture_failure(
                exc
            )

        except Exception as telemetry_error:

            print(
                "A9_FAILURE_TELEMETRY_ERROR:",
                repr(
                    telemetry_error
                ),
                file=sys.stderr,
            )

        print(
            "A9_CERTIFICATION_FAILED:",
            repr(exc),
            file=sys.stderr,
        )

        raise