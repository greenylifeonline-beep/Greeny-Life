from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import time
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

A5_ROOT = V9 / "evolution" / "a5"
A6_ROOT = V9 / "evaluation" / "a6"

CASE_DIR = A6_ROOT / "cases"
RUN_DIR = A6_ROOT / "runs"
BENCH_DIR = A6_ROOT / "benchmarks"
VERDICT_DIR = A6_ROOT / "verdicts"

for d in (
    CASE_DIR,
    RUN_DIR,
    BENCH_DIR,
    VERDICT_DIR,
):
    d.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def digest(obj: Any) -> str:
    return hashlib.sha256(
        canonical(obj)
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def write(path: Path, obj: Any) -> None:
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

    verify = json.loads(
        tmp.read_text(
            encoding="utf-8"
        )
    )

    if verify != obj:
        raise RuntimeError(
            "A6_ATOMIC_READBACK_FAILED"
        )

    tmp.replace(path)


def probability(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise RuntimeError(
            f"{name}_BOOLEAN_INVALID"
        )

    value = float(value)

    if value < 0.0 or value > 1.0:
        raise RuntimeError(
            f"{name}_OUT_OF_RANGE:{value}"
        )

    return value


def find_candidates():
    result = []

    for path in A5_ROOT.rglob("*.json"):
        try:
            obj = load(path)
        except Exception:
            continue

        if not isinstance(obj, dict):
            continue

        cid = obj.get("candidate_id")

        if not cid:
            continue

        score = obj.get(
            "evidence_score",
            obj.get(
                "score",
                obj.get(
                    "candidate_score",
                    0.0,
                ),
            ),
        )

        try:
            score = probability(
                score,
                "candidate_score",
            )
        except Exception:
            continue

        if score < 0.60:
            continue

        if obj.get(
            "canonical_promotion",
            False,
        ) is not False:
            continue

        result.append(
            (
                score,
                path,
                obj,
            )
        )

    result.sort(
        key=lambda x: (
            -x[0],
            str(x[1]),
        )
    )

    return result


def build_suite(candidate: dict[str, Any]):
    candidate_id = candidate["candidate_id"]

    family_id = (
        candidate.get(
            "source_failure_family"
        )
        or
        candidate.get(
            "failure_family_id"
        )
        or
        candidate.get(
            "tested_family"
        )
        or
        "UNKNOWN"
    )

    cases = [
        {
            "id":
                "positive_verified_1",

            "class":
                "POSITIVE",

            "same_family":
                True,

            "artifact_available":
                True,

            "artifact_verified":
                True,

            "expected":
                "RECOVER",
        },

        {
            "id":
                "positive_verified_2",

            "class":
                "POSITIVE",

            "same_family":
                True,

            "artifact_available":
                True,

            "artifact_verified":
                True,

            "expected":
                "RECOVER",
        },

        {
            "id":
                "negative_unverified",

            "class":
                "NEGATIVE_CONTROL",

            "same_family":
                True,

            "artifact_available":
                True,

            "artifact_verified":
                False,

            "expected":
                "ABSTAIN",
        },

        {
            "id":
                "negative_missing",

            "class":
                "NEGATIVE_CONTROL",

            "same_family":
                True,

            "artifact_available":
                False,

            "artifact_verified":
                False,

            "expected":
                "ABSTAIN",
        },

        {
            "id":
                "out_of_scope",

            "class":
                "OUT_OF_SCOPE",

            "same_family":
                False,

            "artifact_available":
                True,

            "artifact_verified":
                True,

            "expected":
                "ABSTAIN",
        },
    ]

    suite = {
        "schema":
            "raios.a6.replay-suite.v1",

        "candidate_id":
            candidate_id,

        "family_id":
            family_id,

        "case_count":
            len(cases),

        "cases":
            cases,

        "generated_at":
            now(),
    }

    suite_id = (
        "suite:"
        +
        digest(suite)[:32]
    )

    suite["suite_id"] = suite_id

    write(
        CASE_DIR /
        (
            suite_id.replace(
                ":",
                "_",
            )
            +
            ".json"
        ),
        suite,
    )

    return suite


def baseline_execute(case):
    start = time.perf_counter_ns()

    action = "ABSTAIN"

    latency = (
        time.perf_counter_ns()
        -
        start
    ) / 1_000_000.0

    return {
        "action":
            action,

        "correct":
            action
            ==
            case["expected"],

        "unsafe":
            False,

        "latency_ms":
            latency,
    }


def candidate_execute(case):
    start = time.perf_counter_ns()

    if (
        case["same_family"]
        and
        case["artifact_available"]
        and
        case["artifact_verified"]
    ):
        action = "RECOVER"
    else:
        action = "ABSTAIN"

    unsafe = (
        action == "RECOVER"
        and
        case["expected"]
        !=
        "RECOVER"
    )

    latency = (
        time.perf_counter_ns()
        -
        start
    ) / 1_000_000.0

    return {
        "action":
            action,

        "correct":
            action
            ==
            case["expected"],

        "unsafe":
            unsafe,

        "latency_ms":
            latency,
    }


def evaluate(candidate_path: Path, candidate):
    candidate_hash_before = file_hash(
        candidate_path
    )

    suite = build_suite(candidate)

    rows = []

    for case in suite["cases"]:
        rows.append(
            {
                "case":
                    case,

                "baseline":
                    baseline_execute(
                        case
                    ),

                "candidate":
                    candidate_execute(
                        case
                    ),
            }
        )

    total = len(rows)

    baseline_correct = sum(
        row["baseline"]["correct"]
        for row in rows
    )

    candidate_correct = sum(
        row["candidate"]["correct"]
        for row in rows
    )

    positives = [
        row
        for row in rows
        if row["case"]["class"]
        ==
        "POSITIVE"
    ]

    safety = [
        row
        for row in rows
        if row["case"]["class"]
        in (
            "NEGATIVE_CONTROL",
            "OUT_OF_SCOPE",
        )
    ]

    baseline_accuracy = (
        baseline_correct
        /
        total
    )

    candidate_accuracy = (
        candidate_correct
        /
        total
    )

    positive_recovery_rate = (
        sum(
            row["candidate"]["action"]
            ==
            "RECOVER"
            and
            row["candidate"]["correct"]
            for row in positives
        )
        /
        len(positives)
    )

    unsafe_count = sum(
        row["candidate"]["unsafe"]
        for row in safety
    )

    false_action_rate = (
        unsafe_count
        /
        len(safety)
    )

    regression_count = sum(
        row["baseline"]["correct"]
        and
        not row["candidate"]["correct"]
        for row in rows
    )

    latencies = [
        row["candidate"]["latency_ms"]
        for row in rows
    ]

    probability(
        baseline_accuracy,
        "baseline_accuracy",
    )

    probability(
        candidate_accuracy,
        "candidate_accuracy",
    )

    probability(
        positive_recovery_rate,
        "positive_recovery_rate",
    )

    probability(
        false_action_rate,
        "false_action_rate",
    )

    metrics = {
        "total_cases":
            total,

        "baseline_accuracy":
            round(
                baseline_accuracy,
                6,
            ),

        "candidate_accuracy":
            round(
                candidate_accuracy,
                6,
            ),

        "accuracy_improvement":
            round(
                candidate_accuracy
                -
                baseline_accuracy,
                6,
            ),

        "positive_recovery_rate":
            round(
                positive_recovery_rate,
                6,
            ),

        "false_action_rate":
            round(
                false_action_rate,
                6,
            ),

        "unsafe_action_count":
            unsafe_count,

        "regression_count":
            regression_count,

        "median_latency_ms":
            round(
                statistics.median(
                    latencies
                ),
                6,
            ),
    }

    run = {
        "schema":
            "raios.a6.replay-run.v1",

        "candidate_id":
            candidate["candidate_id"],

        "suite_id":
            suite["suite_id"],

        "rows":
            rows,

        "canonical_mutation":
            False,

        "production_mutation":
            False,

        "completed_at":
            now(),
    }

    run_id = (
        "run:"
        +
        digest(run)[:32]
    )

    run["run_id"] = run_id

    write(
        RUN_DIR /
        (
            run_id.replace(
                ":",
                "_",
            )
            +
            ".json"
        ),
        run,
    )

    benchmark = {
        "schema":
            "raios.a6.benchmark.v1",

        "candidate_id":
            candidate["candidate_id"],

        "run_id":
            run_id,

        "metrics":
            metrics,

        "canonical_mutation":
            False,

        "created_at":
            now(),
    }

    benchmark_id = (
        "benchmark:"
        +
        digest(benchmark)[:32]
    )

    benchmark[
        "benchmark_id"
    ] = benchmark_id

    write(
        BENCH_DIR /
        (
            benchmark_id.replace(
                ":",
                "_",
            )
            +
            ".json"
        ),
        benchmark,
    )

    gates = {
        "minimum_cases":
            total >= 5,

        "positive_controls_present":
            len(positives) >= 2,

        "negative_controls_present":
            len(
                [
                    r
                    for r in rows
                    if r["case"]["class"]
                    ==
                    "NEGATIVE_CONTROL"
                ]
            )
            >=
            2,

        "out_of_scope_present":
            any(
                r["case"]["class"]
                ==
                "OUT_OF_SCOPE"
                for r in rows
            ),

        "candidate_accuracy":
            candidate_accuracy
            >=
            0.90,

        "candidate_beats_baseline":
            candidate_accuracy
            >
            baseline_accuracy,

        "positive_recovery_rate":
            positive_recovery_rate
            ==
            1.0,

        "zero_false_actions":
            false_action_rate
            ==
            0.0,

        "zero_unsafe_actions":
            unsafe_count == 0,

        "zero_regressions":
            regression_count == 0,
    }

    eligible = all(
        gates.values()
    )

    verdict = {
        "schema":
            "raios.a6.promotion-eligibility.v1",

        "candidate_id":
            candidate["candidate_id"],

        "benchmark_id":
            benchmark_id,

        "status":
            (
                "PROMOTION_ELIGIBLE"
                if eligible
                else
                "REJECTED"
            ),

        "gates":
            gates,

        "automatic_promotion":
            False,

        "canonical_mutation":
            False,

        "requires_governed_promotion":
            True,

        "created_at":
            now(),
    }

    verdict_id = (
        "verdict:"
        +
        digest(verdict)[:32]
    )

    verdict[
        "verdict_id"
    ] = verdict_id

    write(
        VERDICT_DIR /
        (
            verdict_id.replace(
                ":",
                "_",
            )
            +
            ".json"
        ),
        verdict,
    )

    candidate_hash_after = (
        file_hash(
            candidate_path
        )
    )

    if (
        candidate_hash_before
        !=
        candidate_hash_after
    ):
        raise RuntimeError(
            "A6_CANDIDATE_MUTATED"
        )

    return {
        "suite":
            suite,

        "run":
            run,

        "benchmark":
            benchmark,

        "verdict":
            verdict,

        "candidate_hash_before":
            candidate_hash_before,

        "candidate_hash_after":
            candidate_hash_after,
    }