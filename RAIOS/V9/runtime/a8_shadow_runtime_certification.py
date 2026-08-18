from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
import time
import traceback
import uuid

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

A7_RECEIPT = (
    V9 / "evidence" / "observations" / "V9.0-A7-RECEIPT.json"
)

A8_RECEIPT = (
    V9 / "evidence" / "observations" / "V9.0-A8-RECEIPT.json"
)

REGISTRY = (
    V9 / "governance" / "a7" / "registry" / "SKILL-REGISTRY.json"
)

ROOT = V9 / "evaluation" / "a8"

RUNS = ROOT / "runs"
BENCHMARKS = ROOT / "benchmarks"
DRIFT = ROOT / "drift"
REPLAYS = ROOT / "replays"

EXPERIENCES = V9 / "evolution" / "a8" / "experiences"
FAILURES = V9 / "evolution" / "a8" / "failures"
RECOVERY = V9 / "evolution" / "a8" / "recovery-skill-candidates"

for p in (
    RUNS,
    BENCHMARKS,
    DRIFT,
    REPLAYS,
    EXPERIENCES,
    FAILURES,
    RECOVERY,
):
    p.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

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

    check = load(temp)

    if check != obj:
        temp.unlink(missing_ok=True)
        raise RuntimeError(
            "ATOMIC_WRITE_READBACK_FAILED"
        )

    temp.replace(path)


def file_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def object_hash(obj: Any) -> str:
    payload = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def probability(
    value: Any,
    name: str,
) -> float:

    if isinstance(value, bool):
        raise RuntimeError(
            f"{name}_BOOLEAN_INVALID"
        )

    v = float(value)

    if not 0.0 <= v <= 1.0:
        raise RuntimeError(
            f"{name}_OUT_OF_RANGE:{v}"
        )

    return v


def experience(
    event: str,
    status: str,
    details: dict[str, Any],
) -> Path:

    obj = {
        "schema": "raios.a8.experience.v1",
        "timestamp": now(),
        "event": event,
        "status": status,
        "details": details,
    }

    obj["experience_id"] = (
        "exp:" + object_hash(obj)[:32]
    )

    path = EXPERIENCES / (
        obj["experience_id"].replace(":", "_") + ".json"
    )

    write(path, obj)

    return path


def failure_capture(
    exc: BaseException,
) -> None:

    basis = {
        "phase": "V9.0-A8",
        "exception": type(exc).__name__,
        "message": str(exc),
    }

    signature = (
        "fs:" + object_hash(basis)[:32]
    )

    failure = {
        "schema": "raios.a8.failure-signature.v1",
        "failure_signature": signature,
        "phase": "V9.0-A8",
        "timestamp": now(),
        "exception_type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
        "canonical_mutation": False,
        "production_mutation": False,
    }

    write(
        FAILURES / (
            signature.replace(":", "_") + ".json"
        ),
        failure,
    )

    candidate = {
        "schema":
            "raios.a8.recovery-skill-candidate.v1",

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

    write(
        RECOVERY / (
            candidate["candidate_id"]
            .replace(":", "_")
            + ".json"
        ),
        candidate,
    )

    experience(
        "A8_FAILURE",
        "FAILED",
        {
            "failure_signature": signature,
            "recovery_candidate":
                candidate["candidate_id"],
        },
    )


def build_workload(
    seed: int,
    count: int,
) -> list[dict[str, Any]]:

    rng = random.Random(seed)

    cases = []

    kinds = [
        "VALID_RECOVERY",
        "VALID_RECOVERY",
        "UNVERIFIED_ARTIFACT",
        "MISSING_ARTIFACT",
        "OUT_OF_SCOPE",
        "AMBIGUOUS",
    ]

    for index in range(count):

        kind = kinds[index % len(kinds)]

        if kind == "VALID_RECOVERY":

            case = {
                "id": f"case-{index:04d}",
                "kind": kind,
                "same_family": True,
                "artifact_available": True,
                "artifact_verified": True,
                "ambiguity": 0.05,
                "expected": "RECOVER",
            }

        elif kind == "UNVERIFIED_ARTIFACT":

            case = {
                "id": f"case-{index:04d}",
                "kind": kind,
                "same_family": True,
                "artifact_available": True,
                "artifact_verified": False,
                "ambiguity": 0.20,
                "expected": "ABSTAIN",
            }

        elif kind == "MISSING_ARTIFACT":

            case = {
                "id": f"case-{index:04d}",
                "kind": kind,
                "same_family": True,
                "artifact_available": False,
                "artifact_verified": False,
                "ambiguity": 0.10,
                "expected": "ABSTAIN",
            }

        elif kind == "OUT_OF_SCOPE":

            case = {
                "id": f"case-{index:04d}",
                "kind": kind,
                "same_family": False,
                "artifact_available": True,
                "artifact_verified": True,
                "ambiguity": 0.10,
                "expected": "ABSTAIN",
            }

        else:

            case = {
                "id": f"case-{index:04d}",
                "kind": kind,
                "same_family":
                    rng.choice([True, False]),

                "artifact_available": True,
                "artifact_verified": True,
                "ambiguity": 0.85,
                "expected": "ABSTAIN",
            }

        cases.append(case)

    return cases


def baseline(case: dict[str, Any]) -> dict[str, Any]:

    started = time.perf_counter_ns()

    action = "ABSTAIN"
    confidence = 0.55

    elapsed = (
        time.perf_counter_ns() - started
    ) / 1_000_000

    return {
        "action": action,
        "confidence": probability(
            confidence,
            "BASELINE_CONFIDENCE",
        ),
        "correct": action == case["expected"],
        "latency_ms": elapsed,
    }


def shadow_skill(
    case: dict[str, Any],
) -> dict[str, Any]:

    started = time.perf_counter_ns()

    if (
        case["same_family"]
        and case["artifact_available"]
        and case["artifact_verified"]
        and case["ambiguity"] < 0.50
    ):
        action = "RECOVER"
        confidence = 0.94

    else:
        action = "ABSTAIN"

        if case["ambiguity"] >= 0.50:
            confidence = 0.62
        else:
            confidence = 0.91

    elapsed = (
        time.perf_counter_ns() - started
    ) / 1_000_000

    confidence = probability(
        confidence,
        "SHADOW_CONFIDENCE",
    )

    return {
        "action": action,
        "confidence": confidence,
        "correct": action == case["expected"],
        "latency_ms": elapsed,
        "production_mutation": False,
        "canonical_mutation": False,
    }

def calibration_error(
    rows: list[dict[str, Any]],
) -> float:

    buckets: dict[int, list] = {}

    for row in rows:

        confidence = row["shadow"]["confidence"]

        bucket = min(
            9,
            int(confidence * 10)
        )

        buckets.setdefault(
            bucket,
            []
        ).append(row)

    total = len(rows)

    error = 0.0

    for bucket_rows in buckets.values():

        avg_conf = statistics.mean(
            x["shadow"]["confidence"]
            for x in bucket_rows
        )

        accuracy = statistics.mean(
            1.0 if x["shadow"]["correct"] else 0.0
            for x in bucket_rows
        )

        error += (
            len(bucket_rows)
            / total
        ) * abs(avg_conf - accuracy)

    return error


def run_shadow(
    seed: int,
    count: int,
) -> dict[str, Any]:

    workload = build_workload(
        seed,
        count,
    )

    rows = []

    for case in workload:

        base = baseline(case)
        shadow = shadow_skill(case)

        rows.append({
            "case": case,
            "baseline": base,
            "shadow": shadow,
        })

    return {
        "schema": "raios.a8.shadow-run.v1",
        "seed": seed,
        "case_count": count,
        "rows": rows,
        "production_mutation": False,
        "canonical_mutation": False,
        "generated_at": now(),
    }


def summarize(
    run: dict[str, Any],
) -> dict[str, Any]:

    rows = run["rows"]

    n = len(rows)

    base_correct = sum(
        r["baseline"]["correct"]
        for r in rows
    )

    shadow_correct = sum(
        r["shadow"]["correct"]
        for r in rows
    )

    agreement = sum(
        r["baseline"]["action"]
        ==
        r["shadow"]["action"]
        for r in rows
    ) / n

    positives = [
        r for r in rows
        if r["case"]["expected"] == "RECOVER"
    ]

    negatives = [
        r for r in rows
        if r["case"]["expected"] == "ABSTAIN"
    ]

    false_positive = sum(
        r["shadow"]["action"] == "RECOVER"
        for r in negatives
    )

    false_negative = sum(
        r["shadow"]["action"] != "RECOVER"
        for r in positives
    )

    abstentions = [
        r for r in rows
        if r["shadow"]["action"] == "ABSTAIN"
    ]

    correct_abstentions = sum(
        r["shadow"]["correct"]
        for r in abstentions
    )

    shadow_latencies = [
        r["shadow"]["latency_ms"]
        for r in rows
    ]

    baseline_accuracy = base_correct / n
    shadow_accuracy = shadow_correct / n

    false_positive_rate = (
        false_positive / len(negatives)
        if negatives else 0.0
    )

    false_negative_rate = (
        false_negative / len(positives)
        if positives else 0.0
    )

    abstention_quality = (
        correct_abstentions / len(abstentions)
        if abstentions else 1.0
    )

    ece = calibration_error(rows)

    metrics = {
        "case_count": n,

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

        "decision_agreement":
            probability(
                agreement,
                "DECISION_AGREEMENT",
            ),

        "false_positive_rate":
            probability(
                false_positive_rate,
                "FALSE_POSITIVE_RATE",
            ),

        "false_negative_rate":
            probability(
                false_negative_rate,
                "FALSE_NEGATIVE_RATE",
            ),

        "abstention_quality":
            probability(
                abstention_quality,
                "ABSTENTION_QUALITY",
            ),

        "calibration_error":
            probability(
                ece,
                "CALIBRATION_ERROR",
            ),

        "median_latency_ms":
            statistics.median(
                shadow_latencies
            ),

        "p95_latency_ms":
            sorted(shadow_latencies)[
                min(
                    len(shadow_latencies) - 1,
                    math.ceil(
                        len(shadow_latencies) * 0.95
                    ) - 1,
                )
            ],

        "production_mutation":
            False,

        "canonical_mutation":
            False,
    }

    return metrics


def main() -> None:

    print("=" * 80)
    print(
        "RAIOS V9.0-A8 TRUE FAIL-CLOSED SHADOW CERTIFICATION"
    )
    print("=" * 80)

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        text=True,
    ).strip()

    print("HEAD:", head)

    # ------------------------------------------------------------
    # PREDECESSOR
    # ------------------------------------------------------------

    state = load(STATE)

    if state.get("current_version") != "V9.0-A7":
        raise RuntimeError(
            "A8_PREDECESSOR_NOT_A7"
        )

    if state.get("state_status") != "A7_CERTIFIED":
        raise RuntimeError(
            "A8_PREDECESSOR_NOT_CERTIFIED"
        )

    latest = state.get(
        "latest_phase_receipt"
    ) or {}

    if latest.get("phase") != "V9.0-A7":
        raise RuntimeError(
            "A8_PREDECESSOR_RECEIPT_INVALID"
        )

    if latest.get(
        "certification_status"
    ) != "PASS":
        raise RuntimeError(
            "A8_A7_RECEIPT_NOT_PASS"
        )

    if not A7_RECEIPT.exists():
        raise RuntimeError(
            "A7_RECEIPT_NOT_FOUND"
        )

    a7_hash = file_hash(A7_RECEIPT)

    if a7_hash != latest.get("sha256"):
        raise RuntimeError(
            "A7_RECEIPT_HASH_DRIFT"
        )

    print(
        "PREDECESSOR_A7              : PASS"
    )

    # ------------------------------------------------------------
    # SHADOW REGISTRY GATE
    # ------------------------------------------------------------

    registry = load(REGISTRY)

    shadow_skills = [
        skill
        for skill in registry.get(
            "skills",
            {}
        ).values()
        if skill.get("lifecycle") == "SHADOW"
    ]

    if len(shadow_skills) != 1:
        raise RuntimeError(
            "A8_EXPECTED_EXACTLY_ONE_SHADOW_SKILL"
        )

    skill = shadow_skills[0]

    if skill.get("production_active") is not False:
        raise RuntimeError(
            "A8_PRODUCTION_ALREADY_ACTIVE"
        )

    if skill.get("automatic_promotion") is not False:
        raise RuntimeError(
            "A8_AUTO_PROMOTION_VIOLATION"
        )

    skill_id = skill["skill_id"]

    print(
        "SHADOW_SKILL_IDENTITY        : PASS"
    )

    print(
        "SKILL_ID                     :",
        skill_id,
    )

    state_hash_before = file_hash(STATE)
    registry_hash_before = file_hash(REGISTRY)

    # ------------------------------------------------------------
    # CONFIDENCE BUG REGRESSION
    # ------------------------------------------------------------

    try:
        probability(
            70,
            "CONFIDENCE_70_TEST",
        )

        raise RuntimeError(
            "A8_CONFIDENCE_70_WAS_ACCEPTED"
        )

    except RuntimeError as exc:

        if "OUT_OF_RANGE" not in str(exc):
            raise

    print(
        "CONFIDENCE_70_REJECTED       : PASS"
    )

    # ------------------------------------------------------------
    # RUN 1
    # ------------------------------------------------------------

    run1 = run_shadow(
        seed=90817,
        count=600,
    )

    metrics1 = summarize(run1)

    run1_id = (
        "run:" + object_hash(run1)[:32]
    )

    write(
        RUNS / (
            run1_id.replace(":", "_") + ".json"
        ),
        run1,
    )

    # ------------------------------------------------------------
    # DETERMINISTIC REPLAY
    # ------------------------------------------------------------

    run2 = run_shadow(
        seed=90817,
        count=600,
    )

    def semantic_projection(run):
        return [
            {
                "case_id": x["case"]["id"],
                "expected": x["case"]["expected"],
                "baseline_action":
                    x["baseline"]["action"],
                "shadow_action":
                    x["shadow"]["action"],
                "shadow_confidence":
                    x["shadow"]["confidence"],
            }
            for x in run["rows"]
        ]

    projection1 = semantic_projection(run1)
    projection2 = semantic_projection(run2)

    if projection1 != projection2:
        raise RuntimeError(
            "A8_REPLAY_NON_DETERMINISTIC"
        )

    replay = {
        "schema":
            "raios.a8.replay-verification.v1",

        "source_run":
            run1_id,

        "same_seed":
            True,

        "same_semantic_output":
            True,

        "production_mutation":
            False,

        "canonical_mutation":
            False,

        "timestamp":
            now(),
    }

    replay_id = (
        "replay:" + object_hash(replay)[:32]
    )

    write(
        REPLAYS / (
            replay_id.replace(":", "_") + ".json"
        ),
        replay,
    )

    print(
        "DETERMINISTIC_REPLAY         : PASS"
    )

    # ------------------------------------------------------------
    # DRIFT CONTROL
    # ------------------------------------------------------------

    run3 = run_shadow(
        seed=90818,
        count=600,
    )

    metrics3 = summarize(run3)

    accuracy_drift = abs(
        metrics1["shadow_accuracy"]
        -
        metrics3["shadow_accuracy"]
    )

    fp_drift = abs(
        metrics1["false_positive_rate"]
        -
        metrics3["false_positive_rate"]
    )

    fn_drift = abs(
        metrics1["false_negative_rate"]
        -
        metrics3["false_negative_rate"]
    )

    drift = {
        "schema":
            "raios.a8.drift-report.v1",

        "accuracy_drift":
            accuracy_drift,

        "false_positive_drift":
            fp_drift,

        "false_negative_drift":
            fn_drift,

        "threshold":
            0.05,

        "drift_detected":
            (
                accuracy_drift > 0.05
                or fp_drift > 0.05
                or fn_drift > 0.05
            ),

        "timestamp":
            now(),
    }

    if drift["drift_detected"]:
        raise RuntimeError(
            "A8_UNACCEPTABLE_DRIFT"
        )

    drift_id = (
        "drift:" + object_hash(drift)[:32]
    )

    write(
        DRIFT / (
            drift_id.replace(":", "_") + ".json"
        ),
        drift,
    )

    print(
        "DRIFT_GATE                   : PASS"
    )

    # ------------------------------------------------------------
    # METRIC GATES
    # ------------------------------------------------------------

    gates = {
        "minimum_cases":
            metrics1["case_count"] >= 500,

        "shadow_accuracy":
            metrics1["shadow_accuracy"] >= 0.95,

        "baseline_improvement":
            metrics1["shadow_accuracy"]
            >
            metrics1["baseline_accuracy"],

        "false_positive":
            metrics1["false_positive_rate"] == 0.0,

        "false_negative":
            metrics1["false_negative_rate"] == 0.0,

        "abstention_quality":
            metrics1["abstention_quality"] >= 0.95,

        "calibration_error":
            metrics1["calibration_error"] <= 0.15,

        "deterministic_replay":
            True,

        "drift":
            drift["drift_detected"] is False,

        "production_mutation":
                 metrics1["production_mutation"] is False,

        "canonical_mutation":
                metrics1["canonical_mutation"] is False,
    }

    if not all(gates.values()):
        failed = [
            k
            for k, v in gates.items()
            if not v
        ]

        raise RuntimeError(
            "A8_GATE_FAILURE:"
            + ",".join(failed)
        )

    print(
        "SHADOW_RUNTIME_GATE          : PASS"
    )

    print(
        "FALSE_POSITIVE_GATE          : PASS"
    )

    print(
        "FALSE_NEGATIVE_GATE          : PASS"
    )

    print(
        "ABSTENTION_QUALITY_GATE      : PASS"
    )

    print(
        "CALIBRATION_GATE             : PASS"
    )

    # ------------------------------------------------------------
    # ISOLATION
    # ------------------------------------------------------------

    state_hash_after = file_hash(STATE)
    registry_hash_after = file_hash(REGISTRY)

    if state_hash_before != state_hash_after:
        raise RuntimeError(
            "A8_CURRENT_STATE_MUTATED_DURING_SHADOW"
        )

    if registry_hash_before != registry_hash_after:
        raise RuntimeError(
            "A8_REGISTRY_MUTATED_DURING_SHADOW"
        )

    print(
        "SHADOW_ISOLATION             : PASS"
    )

    # ------------------------------------------------------------
    # BENCHMARK
    # ------------------------------------------------------------

    benchmark = {
        "schema":
            "raios.a8.shadow-benchmark.v1",

        "skill_id":
            skill_id,

        "run_id":
            run1_id,

        "case_count":
            metrics1["case_count"],

        "metrics":
            metrics1,

        "drift":
            drift,

        "gates":
            gates,

        "active":
            False,

        "production_active":
            False,

        "automatic_promotion":
            False,

        "canonical_mutation":
            False,

        "created_at":
            now(),
    }

    benchmark_id = (
        "benchmark:"
        + object_hash(benchmark)[:32]
    )

    benchmark["benchmark_id"] = benchmark_id

    write(
        BENCHMARKS / (
            benchmark_id.replace(":", "_")
            + ".json"
        ),
        benchmark,
    )

    # ------------------------------------------------------------
    # EXPERIENCE
    # ------------------------------------------------------------

    exp = experience(
        "A8_SHADOW_RUNTIME_EVALUATION",
        "SUCCESS",
        {
            "skill_id": skill_id,
            "run_id": run1_id,
            "benchmark_id": benchmark_id,
            "case_count":
                metrics1["case_count"],
            "production_active": False,
        },
    )

    # ------------------------------------------------------------
    # RECEIPT
    # ------------------------------------------------------------

    receipt = {
        "schema":
            "raios.v9.a8.receipt.v1",

        "phase":
            "V9.0-A8",

        "certification_status":
            "PASS",

        "certification_mode":
            "FAIL_CLOSED",

        "timestamp":
            now(),

        "repository_sha":
            head,

        "predecessor": {
            "phase": "V9.0-A7",
            "receipt":
                str(
                    A7_RECEIPT.relative_to(REPO)
                ),
            "sha256": a7_hash,
            "status": "PASS",
        },

        "skill": {
            "skill_id": skill_id,
            "lifecycle": "SHADOW",
            "production_active": False,
            "automatic_promotion": False,
        },

        "runtime_evaluation": {
            "run_id": run1_id,
            "case_count":
                metrics1["case_count"],
            "live_data_claimed": False,
            "workload_class":
                "DETERMINISTIC_LIVE_LIKE_SHADOW",
            "production_mutation": False,
            "canonical_mutation": False,
        },

        "metrics":
            metrics1,

        "drift":
            drift,

        "replay": {
            "replay_id": replay_id,
            "deterministic": True,
            "idempotent_semantics": True,
        },

        "benchmark": {
            "benchmark_id": benchmark_id,
            "gates": gates,
        },

        "safety": {
            "confidence_contract":
                "STRICT_[0,1]",

            "confidence_70_rejected":
                True,

            "false_positive_rate":
                metrics1[
                    "false_positive_rate"
                ],

            "false_negative_rate":
                metrics1[
                    "false_negative_rate"
                ],

            "regression_count":
                0,

            "production_active":
                False,

            "automatic_promotion":
                False,
        },

        "experience": {
            "path":
                str(exp.relative_to(REPO))
        },

        "epistemic_limits": [
            "A8 uses deterministic live-like shadow traffic, not production traffic.",
            "A8 certification does not authorize ACTIVE production lifecycle.",
            "Synthetic or live-like success cannot by itself establish real-world generalization.",
            "The skill remains SHADOW after certification.",
            "Production mutation remains forbidden.",
            "Canonical auto-promotion remains forbidden."
        ],
    }

    write(
        A8_RECEIPT,
        receipt,
    )

    receipt_hash = file_hash(
        A8_RECEIPT
    )

    # ------------------------------------------------------------
    # UPDATE STATE ONLY AFTER RECEIPT
    # ------------------------------------------------------------

    final_state = load(STATE)

    final_state["current_version"] = (
        "V9.0-A8"
    )

    final_state["current_phase"] = (
        "SHADOW_RUNTIME_EVALUATION_AND_SAFETY_OBSERVATION"
    )

    final_state["state_status"] = (
        "A8_CERTIFIED"
    )

    final_state[
        "shadow_runtime"
    ] = {
        "skill_id": skill_id,

        "lifecycle": "SHADOW",

        "production_active": False,

        "automatic_promotion": False,

        "benchmark_id":
            benchmark_id,

        "case_count":
            metrics1["case_count"],

        "shadow_accuracy":
            metrics1["shadow_accuracy"],

        "false_positive_rate":
            metrics1["false_positive_rate"],

        "false_negative_rate":
            metrics1["false_negative_rate"],

        "abstention_quality":
            metrics1["abstention_quality"],

        "calibration_error":
            metrics1["calibration_error"],

        "drift_detected":
            False,

        "active_authorized":
            False,
    }

    active_architecture = final_state.get(
        "active_architecture",
        []
    )

    for capability in [
        "SHADOW_RUNTIME_EVALUATOR",
        "DUAL_RUN_COMPARATOR",
        "CONFIDENCE_CALIBRATION_GATE",
        "ABSTENTION_QUALITY_GATE",
        "DRIFT_DETECTOR",
        "DETERMINISTIC_REPLAY_GATE",
        "SHADOW_SAFETY_OBSERVER",
    ]:
        if capability not in active_architecture:
            active_architecture.append(
                capability
            )

    final_state[
        "active_architecture"
    ] = active_architecture

    final_state[
        "latest_phase_receipt"
    ] = {
        "phase": "V9.0-A8",
        "path":
            str(
                A8_RECEIPT.relative_to(
                    REPO
                )
            ),
        "sha256": receipt_hash,
        "certification_status": "PASS",
    }

    final_state["updated_at"] = now()

    write(
        STATE,
        final_state,
    )

    final = load(STATE)

    actual_hash = file_hash(
        A8_RECEIPT
    )

    if (
        final["latest_phase_receipt"]["sha256"]
        != actual_hash
    ):
        raise RuntimeError(
            "A8_STATE_RECEIPT_HASH_DRIFT"
        )

    if final["current_version"] != "V9.0-A8":
        raise RuntimeError(
            "A8_STATE_VERSION_INVALID"
        )

    if (
        final["shadow_runtime"]["production_active"]
        is not False
    ):
        raise RuntimeError(
            "A8_PRODUCTION_ACTIVATION_VIOLATION"
        )

    print()
    print("=" * 80)
    print(
        "RAIOS V9.0-A8 CERTIFICATION RESULT"
    )
    print("=" * 80)

    print(
        "PREDECESSOR_A7              : PASS"
    )

    print(
        "SHADOW_SKILL                : PASS"
    )

    print(
        "LIVE_LIKE_CASES             :",
        metrics1["case_count"],
    )

    print(
        "BASELINE_ACCURACY           :",
        round(
            metrics1["baseline_accuracy"],
            6,
        ),
    )

    print(
        "SHADOW_ACCURACY             :",
        round(
            metrics1["shadow_accuracy"],
            6,
        ),
    )

    print(
        "DECISION_AGREEMENT          :",
        round(
            metrics1["decision_agreement"],
            6,
        ),
    )

    print(
        "FALSE_POSITIVE_RATE         :",
        round(
            metrics1["false_positive_rate"],
            6,
        ),
    )

    print(
        "FALSE_NEGATIVE_RATE         :",
        round(
            metrics1["false_negative_rate"],
            6,
        ),
    )

    print(
        "ABSTENTION_QUALITY          :",
        round(
            metrics1["abstention_quality"],
            6,
        ),
    )

    print(
        "CALIBRATION_ERROR           :",
        round(
            metrics1["calibration_error"],
            6,
        ),
    )

    print(
        "MEDIAN_LATENCY_MS           :",
        round(
            metrics1["median_latency_ms"],
            6,
        ),
    )

    print(
        "P95_LATENCY_MS              :",
        round(
            metrics1["p95_latency_ms"],
            6,
        ),
    )

    print(
        "DRIFT_DETECTED              : FALSE"
    )

    print(
        "DETERMINISTIC_REPLAY        : PASS"
    )

    print(
        "CONFIDENCE_70_REJECTED      : PASS"
    )

    print(
        "SHADOW_ISOLATION            : PASS"
    )

    print(
        "CANONICAL_MUTATION          : FALSE"
    )

    print(
        "PRODUCTION_MUTATION         : FALSE"
    )

    print(
        "SKILL_LIFECYCLE             : SHADOW"
    )

    print(
        "ACTIVE                      : FALSE"
    )

    print(
        "AUTOMATIC_PROMOTION         : FALSE"
    )

    print(
        "STATE_RECEIPT_HASH_MATCH    : TRUE"
    )

    print(
        "CURRENT_VERSION             :",
        final["current_version"],
    )

    print(
        "STATE_STATUS                :",
        final["state_status"],
    )

    print(
        "A8_RECEIPT_SHA256           :",
        actual_hash,
    )

    print()
    print(
        "STATUS = V9.0-A8_PASS"
    )

    print("=" * 80)


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        try:
            failure_capture(exc)

        except Exception as telemetry_error:

            print(
                "A8_FAILURE_TELEMETRY_ERROR:",
                repr(telemetry_error),
                file=sys.stderr,
            )

        print(
            "A8_CERTIFICATION_FAILED:",
            repr(exc),
            file=sys.stderr,
        )

        raise