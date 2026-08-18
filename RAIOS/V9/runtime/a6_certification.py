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