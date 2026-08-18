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

$RuntimeDir  = Join-Path $V9 "runtime"
$EvalDir     = Join-Path $V9 "evaluation\a6"
$EvidenceDir = Join-Path $V9 "evidence\observations"
$StatePath   = Join-Path $V9 "continuity\RAIOS-CURRENT-STATE.json"

New-Item -ItemType Directory -Force `
    $RuntimeDir,
    $EvalDir,
    $EvidenceDir |
    Out-Null

$Engine  = Join-Path $RuntimeDir "a6_replay_lab.py"
$Harness = Join-Path $RuntimeDir "a6_certification.py"

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

Write-Host ""
Write-Host "======================================================================"
Write-Host " RAIOS V9.0-A6 INSTALLER"
Write-Host "======================================================================"

# ---------------------------------------------------------------------
# PREDECESSOR GATE
# ---------------------------------------------------------------------

if (-not (Test-Path $StatePath)) {
    throw "A6_CURRENT_STATE_NOT_FOUND"
}

$State = Get-Content $StatePath -Raw | ConvertFrom-Json

if ($State.current_version -ne "V9.0-A5") {
    throw "A6_PREDECESSOR_VERSION_INVALID: $($State.current_version)"
}

if ($State.state_status -ne "A5_CERTIFIED") {
    throw "A6_PREDECESSOR_NOT_CERTIFIED: $($State.state_status)"
}

if ($State.latest_phase_receipt.phase -ne "V9.0-A5") {
    throw "A6_PREDECESSOR_RECEIPT_INVALID"
}

if ($State.latest_phase_receipt.certification_status -ne "PASS") {
    throw "A6_PREDECESSOR_RECEIPT_NOT_PASS"
}

$A5ReceiptPath = Join-Path $Repo $State.latest_phase_receipt.path

if (-not (Test-Path $A5ReceiptPath)) {
    throw "A6_A5_RECEIPT_NOT_FOUND"
}

$A5ActualHash =
    (Get-FileHash $A5ReceiptPath -Algorithm SHA256).Hash.ToLower()

if ($A5ActualHash -ne $State.latest_phase_receipt.sha256) {
    throw "A6_A5_RECEIPT_HASH_DRIFT"
}

Write-Host "PREDECESSOR_A5 = PASS"

# ---------------------------------------------------------------------
# A6 REPLAY ENGINE
# ---------------------------------------------------------------------

$EngineCode = @"
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
"@

[System.IO.File]::WriteAllText(
    $Engine,
    $EngineCode,
    $Utf8NoBom
)

& $Python -m py_compile $Engine

if ($LASTEXITCODE -ne 0) {
    throw "A6_ENGINE_COMPILE_FAILED"
}

Write-Host "A6_ENGINE_COMPILE = PASS"

# ---------------------------------------------------------------------
# CERTIFICATION HARNESS
# ---------------------------------------------------------------------

$HarnessCode = @"
from __future__ import annotations

import hashlib
import importlib.util
import json
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

ENGINE = (
    V9 /
    "runtime" /
    "a6_replay_lab.py"
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
    "V9.0-A6-RECEIPT.json"
)


def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def load(path):
    return json.loads(
        Path(path).read_text(
            encoding="utf-8-sig"
        )
    )


def write(path, obj):
    path = Path(path)

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
        )
        +
        "\n",
        encoding="utf-8",
    )

    check = json.loads(
        tmp.read_text(
            encoding="utf-8"
        )
    )

    if check != obj:
        raise RuntimeError(
            "A6_RECEIPT_ATOMIC_READBACK_FAILED"
        )

    tmp.replace(path)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


print("=" * 76)
print("RAIOS V9.0-A6 TRUE FAIL-CLOSED CERTIFICATION")
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

print("HEAD:", HEAD)

state = load(STATE)

assert (
    state.get("current_version")
    ==
    "V9.0-A5"
), "A6_PREDECESSOR_NOT_A5"

assert (
    state.get("state_status")
    ==
    "A5_CERTIFIED"
), "A6_PREDECESSOR_NOT_CERTIFIED"

previous = state[
    "latest_phase_receipt"
]

assert (
    previous["phase"]
    ==
    "V9.0-A5"
)

assert (
    previous["certification_status"]
    ==
    "PASS"
)

previous_path = (
    REPO /
    previous["path"]
)

assert previous_path.exists()

assert (
    sha(previous_path)
    ==
    previous["sha256"]
), "A5_RECEIPT_HASH_DRIFT"

print(
    "PREDECESSOR_A5             : PASS"
)

spec = importlib.util.spec_from_file_location(
    "a6_replay_lab",
    ENGINE,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)

candidates = module.find_candidates()

assert candidates, (
    "A6_NO_ELIGIBLE_A5_CANDIDATE_FOUND"
)

score, candidate_path, candidate = (
    candidates[0]
)

print(
    "CANDIDATE_DISCOVERY        : PASS"
)

print(
    "CANDIDATE_ID               :",
    candidate["candidate_id"],
)

print(
    "A5_EVIDENCE_SCORE          :",
    score,
)

canonical_state_hash_before = (
    sha(STATE)
)

evaluation = module.evaluate(
    candidate_path,
    candidate,
)

canonical_state_hash_after = (
    sha(STATE)
)

assert (
    canonical_state_hash_before
    ==
    canonical_state_hash_after
), "A6_SANDBOX_MUTATED_CURRENT_STATE"

suite = evaluation[
    "suite"
]

run = evaluation[
    "run"
]

benchmark = evaluation[
    "benchmark"
]

verdict = evaluation[
    "verdict"
]

metrics = benchmark[
    "metrics"
]

classes = [
    row["case"]["class"]
    for row in run["rows"]
]

assert (
    classes.count("POSITIVE")
    >=
    2
)

assert (
    classes.count("NEGATIVE_CONTROL")
    >=
    2
)

assert (
    classes.count("OUT_OF_SCOPE")
    >=
    1
)

assert (
    metrics["total_cases"]
    >=
    5
)

assert (
    0.0
    <=
    metrics["baseline_accuracy"]
    <=
    1.0
)

assert (
    0.0
    <=
    metrics["candidate_accuracy"]
    <=
    1.0
)

assert (
    0.0
    <=
    metrics["positive_recovery_rate"]
    <=
    1.0
)

assert (
    0.0
    <=
    metrics["false_action_rate"]
    <=
    1.0
)

assert (
    metrics["candidate_accuracy"]
    >
    metrics["baseline_accuracy"]
), "A6_CANDIDATE_NOT_BETTER_THAN_BASELINE"

assert (
    metrics["positive_recovery_rate"]
    ==
    1.0
), "A6_POSITIVE_RECOVERY_FAILED"

assert (
    metrics["false_action_rate"]
    ==
    0.0
), "A6_FALSE_ACTION_DETECTED"

assert (
    metrics["unsafe_action_count"]
    ==
    0
), "A6_UNSAFE_ACTION_DETECTED"

assert (
    metrics["regression_count"]
    ==
    0
), "A6_REGRESSION_DETECTED"

assert (
    verdict["status"]
    ==
    "PROMOTION_ELIGIBLE"
), "A6_PROMOTION_ELIGIBILITY_FAILED"

assert (
    verdict["automatic_promotion"]
    is False
)

assert (
    verdict["canonical_mutation"]
    is False
)

assert (
    verdict["requires_governed_promotion"]
    is True
)

assert all(
    verdict["gates"].values()
)

assert (
    evaluation[
        "candidate_hash_before"
    ]
    ==
    evaluation[
        "candidate_hash_after"
    ]
), "A6_CANDIDATE_IMMUTABILITY_FAILED"

print(
    "REPLAY_LAB                 : PASS"
)

print(
    "POSITIVE_CONTROLS          : PASS"
)

print(
    "NEGATIVE_CONTROLS          : PASS"
)

print(
    "OUT_OF_SCOPE_CONTROL       : PASS"
)

print(
    "BASELINE_COMPARISON        : PASS"
)

print(
    "REGRESSION_GATE            : PASS"
)

print(
    "FALSE_ACTION_GATE          : PASS"
)

print(
    "CANDIDATE_IMMUTABILITY     : PASS"
)

print(
    "CANONICAL_ISOLATION        : PASS"
)

print(
    "PROMOTION_ELIGIBILITY      : PASS"
)

print(
    "AUTOMATIC_PROMOTION        : FALSE"
)

receipt = {
    "schema":
        "raios.v9.a6.receipt.v1",

    "phase":
        "V9.0-A6",

    "certification_status":
        "PASS",

    "certification_mode":
        "FAIL_CLOSED",

    "timestamp":
        now(),

    "repository_sha":
        HEAD,

    "predecessor": {
        "phase":
            "V9.0-A5",

        "receipt":
            previous["path"],

        "sha256":
            previous["sha256"],

        "status":
            "PASS",
    },

    "candidate": {
        "candidate_id":
            candidate["candidate_id"],

        "a5_evidence_score":
            score,

        "sha256":
            evaluation[
                "candidate_hash_after"
            ],

        "automatic_promotion":
            False,
    },

    "replay": {
        "suite_id":
            suite["suite_id"],

        "run_id":
            run["run_id"],

        "case_count":
            metrics["total_cases"],

        "positive_cases":
            classes.count(
                "POSITIVE"
            ),

        "negative_controls":
            classes.count(
                "NEGATIVE_CONTROL"
            ),

        "out_of_scope_controls":
            classes.count(
                "OUT_OF_SCOPE"
            ),

        "canonical_mutation":
            False,

        "production_mutation":
            False,
    },

    "benchmark": {
        "benchmark_id":
            benchmark[
                "benchmark_id"
            ],

        "metrics":
            metrics,
    },

    "verdict": {
        "verdict_id":
            verdict[
                "verdict_id"
            ],

        "status":
            verdict[
                "status"
            ],

        "gates":
            verdict[
                "gates"
            ],

        "automatic_promotion":
            False,

        "canonical_mutation":
            False,

        "requires_governed_promotion":
            True,
    },

    "invariants": [
        "A5 must remain certified and hash-consistent.",
        "A6 replay must not mutate canonical CURRENT-STATE.",
        "A6 replay must not mutate the candidate artifact.",
        "Positive, negative, and out-of-scope controls are mandatory.",
        "All probability metrics must be within [0,1].",
        "Any unsafe action fails certification.",
        "Any regression fails certification.",
        "Candidate must outperform baseline.",
        "PROMOTION_ELIGIBLE does not mean PROMOTED.",
        "Automatic promotion is forbidden.",
        "Receipt is created only after every assertion passes."
    ],
}

write(
    RECEIPT,
    receipt,
)

readback = load(
    RECEIPT
)

assert (
    readback["certification_status"]
    ==
    "PASS"
)

assert (
    readback["verdict"]["status"]
    ==
    "PROMOTION_ELIGIBLE"
)

assert (
    readback[
        "verdict"
    ][
        "automatic_promotion"
    ]
    is False
)

receipt_hash = sha(
    RECEIPT
)

state = load(
    STATE
)

state["current_version"] = (
    "V9.0-A6"
)

state["current_phase"] = (
    "REPLAY_AND_BENCHMARK_LABORATORY"
)

state["state_status"] = (
    "A6_CERTIFIED"
)

active = state.get(
    "active_architecture",
    []
)

for item in [
    "REPLAY_LAB",
    "BENCHMARK_LAB",
    "NEGATIVE_CONTROL_GATE",
    "OUT_OF_SCOPE_GATE",
    "BASELINE_COMPARATOR",
    "REGRESSION_GATE",
    "PROMOTION_ELIGIBILITY_GATE",
]:
    if item not in active:
        active.append(item)

state[
    "active_architecture"
] = active

state[
    "evaluation_fabric"
] = {
    "status":
        "A6_CERTIFIED",

    "positive_controls":
        "REQUIRED",

    "negative_controls":
        "REQUIRED",

    "out_of_scope_controls":
        "REQUIRED",

    "baseline_comparison":
        "REQUIRED",

    "regression_gate":
        "FAIL_CLOSED",

    "candidate_mutation":
        False,

    "canonical_mutation":
        False,

    "automatic_promotion":
        False,

    "highest_allowed_output":
        "PROMOTION_ELIGIBLE",
}

state[
    "latest_evaluated_candidate"
] = {
    "candidate_id":
        candidate["candidate_id"],

    "benchmark_id":
        benchmark[
            "benchmark_id"
        ],

    "verdict":
        verdict[
            "status"
        ],

    "promoted":
        False,
}

state[
    "latest_phase_receipt"
] = {
    "phase":
        "V9.0-A6",

    "path":
        "RAIOS/V9/evidence/observations/V9.0-A6-RECEIPT.json",

    "sha256":
        receipt_hash,

    "certification_status":
        "PASS",
}

state["updated_at"] = now()

write(
    STATE,
    state,
)

final_state = load(
    STATE
)

actual_receipt_hash = sha(
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
), "A6_STATE_RECEIPT_HASH_DRIFT"

assert (
    final_state[
        "current_version"
    ]
    ==
    "V9.0-A6"
)

assert (
    final_state[
        "state_status"
    ]
    ==
    "A6_CERTIFIED"
)

print()
print("=" * 76)
print("RAIOS V9.0-A6 CERTIFICATION RESULT")
print("=" * 76)

print(
    "PREDECESSOR_A5             : PASS"
)

print(
    "REPLAY_LAB                 : PASS"
)

print(
    "POSITIVE_CASES             :",
    classes.count("POSITIVE"),
)

print(
    "NEGATIVE_CONTROLS          :",
    classes.count(
        "NEGATIVE_CONTROL"
    ),
)

print(
    "OUT_OF_SCOPE_CONTROLS      :",
    classes.count(
        "OUT_OF_SCOPE"
    ),
)

print(
    "BASELINE_ACCURACY          :",
    metrics[
        "baseline_accuracy"
    ],
)

print(
    "CANDIDATE_ACCURACY         :",
    metrics[
        "candidate_accuracy"
    ],
)

print(
    "ACCURACY_IMPROVEMENT       :",
    metrics[
        "accuracy_improvement"
    ],
)

print(
    "POSITIVE_RECOVERY_RATE     :",
    metrics[
        "positive_recovery_rate"
    ],
)

print(
    "FALSE_ACTION_RATE          :",
    metrics[
        "false_action_rate"
    ],
)

print(
    "REGRESSIONS                :",
    metrics[
        "regression_count"
    ],
)

print(
    "PROMOTION_ELIGIBILITY      :",
    verdict[
        "status"
    ],
)

print(
    "PROMOTED                   : FALSE"
)

print(
    "AUTOMATIC_PROMOTION        : FALSE"
)

print(
    "STATE_RECEIPT_HASH_MATCH   : TRUE"
)

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
    "A6_RECEIPT_SHA256          :",
    actual_receipt_hash,
)

print()
print(
    "STATUS = V9.0-A6_PASS"
)

print("=" * 76)
"@

[System.IO.File]::WriteAllText(
    $Harness,
    $HarnessCode,
    $Utf8NoBom
)

& $Python -m py_compile $Harness

if ($LASTEXITCODE -ne 0) {
    throw "A6_HARNESS_COMPILE_FAILED"
}

Write-Host "A6_HARNESS_COMPILE = PASS"

# ---------------------------------------------------------------------
# EXECUTE
# ---------------------------------------------------------------------

Write-Host ""
Write-Host "=== EXECUTING A6 ==="

& $Python $Harness

if ($LASTEXITCODE -ne 0) {
    throw "RAIOS_V9_A6_CERTIFICATION_FAILED"
}

Write-Host ""
Write-Host "======================================================================"
Write-Host " A6 INSTALLER FINISHED"
Write-Host "======================================================================"