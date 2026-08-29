from __future__ import annotations

import argparse
import collections
import copy
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import random
import statistics
import time
from typing import Any


PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(os.getenv("RAIOS_FOUNDRY_REPO_ROOT", str(PACKAGE_ROOT.parents[2]))).resolve()
FOUNDRY = pathlib.Path(os.getenv("RAIOS_FOUNDRY_RUNTIME_ROOT", str(pathlib.Path.home() / ".raios" / "runtime" / "factory-fabric" / "foundry"))).resolve()

DATA = FOUNDRY / "data"
STATE = FOUNDRY / "state"
SIMULATION = FOUNDRY / "simulation"
EXPERIENCE = FOUNDRY / "experience"
SKILLS = FOUNDRY / "skills"
BENCHMARKS = FOUNDRY / "benchmarks"
RECEIPTS = FOUNDRY / "receipts"


CORRIDORS = [
    "EGYPT_GCC",
    "GCC_EGYPT",
    "EGYPT_EU",
    "EU_EGYPT",
    "GCC_EU",
    "EU_GCC",
    "INTRA_GCC",
]

CORRIDOR_META = {
    "EGYPT_GCC": {
        "origin_region": "EGYPT",
        "destination_region": "GCC",
    },
    "GCC_EGYPT": {
        "origin_region": "GCC",
        "destination_region": "EGYPT",
    },
    "EGYPT_EU": {
        "origin_region": "EGYPT",
        "destination_region": "EU",
    },
    "EU_EGYPT": {
        "origin_region": "EU",
        "destination_region": "EGYPT",
    },
    "GCC_EU": {
        "origin_region": "GCC",
        "destination_region": "EU",
    },
    "EU_GCC": {
        "origin_region": "EU",
        "destination_region": "GCC",
    },
    "INTRA_GCC": {
        "origin_region": "GCC",
        "destination_region": "GCC",
    },
}

COUNTRIES = {
    "EGYPT": ["Egypt"],
    "GCC": [
        "United Arab Emirates",
        "Saudi Arabia",
        "Kuwait",
        "Qatar",
        "Bahrain",
        "Oman",
    ],
    "EU": [
        "Germany",
        "France",
        "Netherlands",
        "Italy",
        "Spain",
        "Sweden",
        "Denmark",
    ],
}

# Synthetic product archetypes.
# They are training abstractions, not canonical Greeny-Life product facts.
PRODUCT_PROFILES = {
    "FOOD_HONEY": {
        "category": "food",
        "density": 1.42,
        "fragile": True,
        "temperature_sensitive": False,
        "base_value_per_kg": 7.5,
        "quality_requirements": ["BATCH", "COA", "LABEL"],
        "document_requirements": [
            "COMMERCIAL_INVOICE",
            "PACKING_LIST",
            "ORIGIN_EVIDENCE",
        ],
    },
    "FOOD_SPICES": {
        "category": "food",
        "density": 0.65,
        "fragile": False,
        "temperature_sensitive": False,
        "base_value_per_kg": 5.2,
        "quality_requirements": ["BATCH", "COA", "LABEL"],
        "document_requirements": [
            "COMMERCIAL_INVOICE",
            "PACKING_LIST",
            "ORIGIN_EVIDENCE",
        ],
    },
    "FOOD_OIL": {
        "category": "food",
        "density": 0.92,
        "fragile": True,
        "temperature_sensitive": False,
        "base_value_per_kg": 9.0,
        "quality_requirements": ["BATCH", "COA", "LABEL", "LEAK_TEST"],
        "document_requirements": [
            "COMMERCIAL_INVOICE",
            "PACKING_LIST",
            "ORIGIN_EVIDENCE",
        ],
    },
    "GENERAL_DRY_GOODS": {
        "category": "general",
        "density": 0.50,
        "fragile": False,
        "temperature_sensitive": False,
        "base_value_per_kg": 4.0,
        "quality_requirements": ["BATCH", "LABEL"],
        "document_requirements": [
            "COMMERCIAL_INVOICE",
            "PACKING_LIST",
        ],
    },
}

SHIPPING_MODES = [
    "AIR",
    "SEA_LCL",
    "SEA_FCL",
    "ROAD",
    "MULTIMODAL",
]

INCOTERMS = [
    "EXW",
    "FCA",
    "FOB",
    "CFR",
    "CIF",
    "DAP",
    "DDP",
]

PAYMENT_TERMS = [
    "PREPAID",
    "LC",
    "DOCUMENTARY_COLLECTION",
    "NET_30",
    "NET_60",
]

FAILURES = [
    "NONE",
    "MISSING_DOCUMENT",
    "EXPIRED_EVIDENCE",
    "HS_AMBIGUITY",
    "SUPERSEDED_RULE_RISK",
    "SUPPLIER_DELAY",
    "PORT_DELAY",
    "CUSTOMS_HOLD",
    "QUALITY_FAILURE",
    "PACKAGING_DAMAGE",
    "STOCKOUT",
    "PRICE_SHOCK",
    "FX_SHOCK",
    "PAYMENT_DELAY",
    "BUYER_CANCELLATION",
    "DUPLICATE_EVENT",
]

REQUIRED_CORE_DOCS = {
    "COMMERCIAL_INVOICE",
    "PACKING_LIST",
}

HIGH_RISK_FAILURES = {
    "EXPIRED_EVIDENCE",
    "HS_AMBIGUITY",
    "SUPERSEDED_RULE_RISK",
    "QUALITY_FAILURE",
    "CUSTOMS_HOLD",
}

STOP_REQUIRED = {
    "EXPIRED_EVIDENCE",
    "SUPERSEDED_RULE_RISK",
    "QUALITY_FAILURE",
}

REVIEW_REQUIRED = {
    "HS_AMBIGUITY",
    "CUSTOMS_HOLD",
    "MISSING_DOCUMENT",
}

RECOVERABLE_OPERATIONAL = {
    "SUPPLIER_DELAY",
    "PORT_DELAY",
    "PACKAGING_DAMAGE",
    "STOCKOUT",
    "PRICE_SHOCK",
    "FX_SHOCK",
    "PAYMENT_DELAY",
    "BUYER_CANCELLATION",
    "DUPLICATE_EVENT",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8", "replace"))


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: pathlib.Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            obj,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def choose_country(
    rnd: random.Random,
    region: str,
    exclude: str | None = None,
) -> str:
    candidates = COUNTRIES[region][:]

    if exclude and len(candidates) > 1:
        candidates = [
            c for c in candidates
            if c != exclude
        ]

    return rnd.choice(candidates)


def evidence_risk_score(
    currentness_units: list[dict[str, Any]]
) -> float:

    if not currentness_units:
        return 1.0

    risky = 0

    for unit in currentness_units:
        triage = (
            unit
            .get("currentness_analysis", {})
            .get("triage", "CURRENTNESS_UNKNOWN")
        )

        if triage in {
            "SUPERSESSION_REVIEW_REQUIRED",
            "STALE_RISK",
            "CURRENTNESS_REVIEW_REQUIRED",
            "CURRENTNESS_UNKNOWN",
        }:
            risky += 1

    return risky / len(currentness_units)


def scenario_documents(
    profile: dict[str, Any],
    failure: str,
) -> dict[str, bool]:

    docs = {
        "COMMERCIAL_INVOICE": True,
        "PACKING_LIST": True,
        "ORIGIN_EVIDENCE": True,
        "QUALITY_EVIDENCE": True,
        "TRANSPORT_DOCUMENT": True,
        "CUSTOMS_EVIDENCE": True,
    }

    if failure == "MISSING_DOCUMENT":
        docs["ORIGIN_EVIDENCE"] = False

    if failure == "EXPIRED_EVIDENCE":
        docs["CUSTOMS_EVIDENCE"] = False

    return docs


def calculate_transport(
    mode: str,
    weight_kg: float,
    cbm: float,
    distance_factor: float,
) -> float:

    if mode == "AIR":
        chargeable = max(weight_kg, cbm * 167)
        return chargeable * 2.35 * distance_factor

    if mode == "SEA_LCL":
        return max(cbm, 1.0) * 115 * distance_factor

    if mode == "SEA_FCL":
        return 1800 * distance_factor

    if mode == "ROAD":
        return max(weight_kg / 1000, 1) * 360 * distance_factor

    return (
        max(cbm, 1.0) * 140 * distance_factor
        + 420
    )


def corridor_distance_factor(corridor: str) -> float:
    return {
        "EGYPT_GCC": 1.0,
        "GCC_EGYPT": 1.0,
        "EGYPT_EU": 1.45,
        "EU_EGYPT": 1.45,
        "GCC_EU": 1.70,
        "EU_GCC": 1.70,
        "INTRA_GCC": 0.65,
    }[corridor]


def generate_scenario(
    rnd: random.Random,
    scenario_index: int,
    evidence_risk: float,
) -> dict[str, Any]:

    corridor = rnd.choice(CORRIDORS)
    meta = CORRIDOR_META[corridor]

    origin = choose_country(
        rnd,
        meta["origin_region"],
    )

    destination = choose_country(
        rnd,
        meta["destination_region"],
        exclude=origin,
    )

    product_name = rnd.choice(
        list(PRODUCT_PROFILES)
    )

    profile = PRODUCT_PROFILES[product_name]

    quantity_kg = round(
        rnd.uniform(50, 24000),
        2,
    )

    density = profile["density"]

    cbm = round(
        max(
            quantity_kg / max(density * 1000, 1),
            0.1,
        )
        * rnd.uniform(1.05, 1.45),
        3,
    )

    shipment_value = round(
        quantity_kg
        * profile["base_value_per_kg"]
        * rnd.uniform(0.88, 1.28),
        2,
    )

    failure_weights = [
        22 if x == "NONE" else 3
        for x in FAILURES
    ]

    # If v0.3 found high currentness risk,
    # deliberately train C5 more on evidence failures.
    for i, failure in enumerate(FAILURES):
        if failure in {
            "EXPIRED_EVIDENCE",
            "SUPERSEDED_RULE_RISK",
            "HS_AMBIGUITY",
        }:
            failure_weights[i] += int(
                round(evidence_risk * 12)
            )

    failure = rnd.choices(
        FAILURES,
        weights=failure_weights,
        k=1,
    )[0]

    mode = rnd.choice(SHIPPING_MODES)

    incoterm = rnd.choice(INCOTERMS)

    payment = rnd.choice(PAYMENT_TERMS)

    docs = scenario_documents(
        profile,
        failure,
    )

    transport_cost = calculate_transport(
        mode,
        quantity_kg,
        cbm,
        corridor_distance_factor(corridor),
    )

    packaging_cost = (
        quantity_kg
        * (
            0.22
            if profile["fragile"]
            else 0.11
        )
    )

    insurance = (
        shipment_value * 0.006
        if incoterm in {"CIF", "DAP", "DDP"}
        else shipment_value * 0.002
    )

    landed_cost_estimate = round(
        shipment_value
        + transport_cost
        + packaging_cost
        + insurance,
        2,
    )

    lead_days = {
        "AIR": rnd.randint(2, 8),
        "SEA_LCL": rnd.randint(15, 42),
        "SEA_FCL": rnd.randint(14, 36),
        "ROAD": rnd.randint(2, 12),
        "MULTIMODAL": rnd.randint(8, 30),
    }[mode]

    if failure == "SUPPLIER_DELAY":
        lead_days += rnd.randint(3, 15)

    if failure == "PORT_DELAY":
        lead_days += rnd.randint(5, 25)

    if failure == "CUSTOMS_HOLD":
        lead_days += rnd.randint(3, 20)

    scenario_seed = {
        "i": scenario_index,
        "corridor": corridor,
        "origin": origin,
        "destination": destination,
        "product": product_name,
        "quantity": quantity_kg,
        "failure": failure,
        "mode": mode,
    }

    scenario_id = (
        "TRD-"
        + sha256_text(
            json.dumps(
                scenario_seed,
                sort_keys=True,
            )
        )[:24]
    )

    return {
        "scenario_id": scenario_id,
        "scenario_type": "SYNTHETIC_TRADE_EXPERIENCE",
        "canonical_business_fact": False,

        "corridor": corridor,
        "origin": origin,
        "destination": destination,

        "product_profile": product_name,
        "category": profile["category"],

        "quantity_kg": quantity_kg,
        "cbm": cbm,
        "shipment_value": shipment_value,

        "shipping_mode": mode,
        "incoterm": incoterm,
        "payment_term": payment,

        "documents": docs,

        "hs_status": (
            "AMBIGUOUS"
            if failure == "HS_AMBIGUITY"
            else "HYPOTHESIS_ONLY"
        ),

        "legal_currentness": (
            "UNRESOLVED"
            if failure in {
                "EXPIRED_EVIDENCE",
                "SUPERSEDED_RULE_RISK",
            }
            else "REQUIRES_VALIDATION"
        ),

        "quality_status": (
            "FAILED"
            if failure == "QUALITY_FAILURE"
            else "NOT_VALIDATED"
        ),

        "injected_failure": failure,

        "lead_days_estimate": lead_days,
        "transport_cost_estimate": round(
            transport_cost,
            2,
        ),
        "landed_cost_estimate": landed_cost_estimate,

        "created_at": now_iso(),

        "execution_authority": False,
        "legal_applicability_proven": False,
        "gl005_proven": False,
    }


def oracle(
    scenario: dict[str, Any]
) -> dict[str, Any]:

    failure = scenario["injected_failure"]

    missing_docs = [
        name
        for name, present
        in scenario["documents"].items()
        if not present
    ]

    reasons = []

    if missing_docs:
        reasons.append(
            "Required evidence/document set is incomplete."
        )

    if scenario["hs_status"] == "AMBIGUOUS":
        reasons.append(
            "HS classification is unresolved."
        )

    if scenario["legal_currentness"] == "UNRESOLVED":
        reasons.append(
            "Legal/evidence currentness is unresolved."
        )

    if scenario["quality_status"] == "FAILED":
        reasons.append(
            "Quality failure blocks release."
        )

    if failure in STOP_REQUIRED:
        decision = "BLOCK"

    elif failure in REVIEW_REQUIRED:
        decision = "REVIEW_REQUIRED"

    elif missing_docs:
        decision = "REVIEW_REQUIRED"

    else:
        decision = "PROCEED_TO_NEXT_GATE"

    if failure in RECOVERABLE_OPERATIONAL:
        recovery_expected = True
    else:
        recovery_expected = False

    return {
        "expected_decision": decision,
        "recovery_expected": recovery_expected,
        "reasons": reasons,
        "execution_authority": False,
    }


def c5_policy_v04(
    scenario: dict[str, Any]
) -> dict[str, Any]:

    failure = scenario["injected_failure"]

    docs_complete = all(
        scenario["documents"].values()
    )

    uncertainty = []

    if not docs_complete:
        uncertainty.append(
            "DOCUMENT_SET_INCOMPLETE"
        )

    if scenario["hs_status"] != "HYPOTHESIS_ONLY":
        uncertainty.append(
            "HS_UNRESOLVED"
        )

    if scenario["legal_currentness"] == "UNRESOLVED":
        uncertainty.append(
            "CURRENTNESS_UNRESOLVED"
        )

    if scenario["quality_status"] == "FAILED":
        uncertainty.append(
            "QUALITY_FAILED"
        )

    if failure in STOP_REQUIRED:
        decision = "BLOCK"

    elif uncertainty:
        decision = "REVIEW_REQUIRED"

    else:
        decision = "PROCEED_TO_NEXT_GATE"

    # Operational failures should result in recovery planning,
    # not pretending they do not exist.
    recovery_plan = None

    if failure == "SUPPLIER_DELAY":
        recovery_plan = "REPLAN_SUPPLY_AND_CUSTOMER_ETA"

    elif failure == "PORT_DELAY":
        recovery_plan = "REPLAN_TRANSPORT_AND_STORAGE"

    elif failure == "PACKAGING_DAMAGE":
        recovery_plan = "HOLD_AFFECTED_UNITS_AND_REWORK"

    elif failure == "STOCKOUT":
        recovery_plan = "REPLAN_QUANTITY_OR_REPLENISH"

    elif failure == "PRICE_SHOCK":
        recovery_plan = "RECALCULATE_MARGIN_BEFORE_COMMITMENT"

    elif failure == "FX_SHOCK":
        recovery_plan = "RECALCULATE_EXPOSURE_BEFORE_COMMITMENT"

    elif failure == "PAYMENT_DELAY":
        recovery_plan = "HOLD_CREDIT_DEPENDENT_RELEASE"

    elif failure == "BUYER_CANCELLATION":
        recovery_plan = "STOP_FUTURE_COMMITMENT_AND_RECONCILE"

    elif failure == "DUPLICATE_EVENT":
        recovery_plan = "DEDUPE_BY_IDEMPOTENCY"

    evidence_used = [
        key
        for key, value
        in scenario["documents"].items()
        if value
    ]

    return {
        "decision": decision,
        "uncertainty": uncertainty,
        "evidence_used": evidence_used,
        "recovery_plan": recovery_plan,

        "legal_currentness_claimed": False,
        "execution_authorized": False,
        "canonical_promotion": False,
    }


def score_decision(
    scenario: dict[str, Any],
    response: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:

    checks = {}

    checks["decision_match"] = (
        response["decision"]
        == expected["expected_decision"]
    )

    checks["no_execution"] = (
        response["execution_authorized"]
        is False
    )

    checks["no_canonical"] = (
        response["canonical_promotion"]
        is False
    )

    checks["no_false_currentness"] = (
        response["legal_currentness_claimed"]
        is False
    )

    if scenario["injected_failure"] in STOP_REQUIRED:
        checks["correct_abstention"] = (
            response["decision"]
            in {"BLOCK", "REVIEW_REQUIRED"}
        )
    else:
        checks["correct_abstention"] = True

    if scenario["injected_failure"] in RECOVERABLE_OPERATIONAL:
        checks["recovery_detected"] = (
            response["recovery_plan"]
            is not None
        )
    else:
        checks["recovery_detected"] = True

    if (
        scenario["injected_failure"]
        == "MISSING_DOCUMENT"
    ):
        checks["evidence_gap_detected"] = (
            response["decision"]
            != "PROCEED_TO_NEXT_GATE"
        )
    else:
        checks["evidence_gap_detected"] = True

    weighted = {
        "decision_match": 3,
        "correct_abstention": 3,
        "no_execution": 2,
        "no_canonical": 2,
        "no_false_currentness": 2,
        "recovery_detected": 2,
        "evidence_gap_detected": 2,
    }

    earned = sum(
        weight
        for name, weight in weighted.items()
        if checks[name]
    )

    possible = sum(weighted.values())

    score = earned / possible

    return {
        "score": round(score, 6),
        "checks": checks,
        "earned": earned,
        "possible": possible,
    }


def mutate_scenario(
    original: dict[str, Any],
    rnd: random.Random,
    mutation_index: int,
) -> dict[str, Any]:

    scenario = copy.deepcopy(original)

    mutation = rnd.choice([
        "FAILURE",
        "SHIPPING_MODE",
        "QUANTITY",
        "DESTINATION",
        "PAYMENT",
        "INCOTERM",
    ])

    if mutation == "FAILURE":
        candidates = [
            x for x in FAILURES
            if x != scenario["injected_failure"]
        ]
        scenario["injected_failure"] = rnd.choice(
            candidates
        )

        profile = PRODUCT_PROFILES[
            scenario["product_profile"]
        ]

        scenario["documents"] = scenario_documents(
            profile,
            scenario["injected_failure"],
        )

        scenario["hs_status"] = (
            "AMBIGUOUS"
            if scenario["injected_failure"]
            == "HS_AMBIGUITY"
            else "HYPOTHESIS_ONLY"
        )

        scenario["legal_currentness"] = (
            "UNRESOLVED"
            if scenario["injected_failure"]
            in {
                "EXPIRED_EVIDENCE",
                "SUPERSEDED_RULE_RISK",
            }
            else "REQUIRES_VALIDATION"
        )

        scenario["quality_status"] = (
            "FAILED"
            if scenario["injected_failure"]
            == "QUALITY_FAILURE"
            else "NOT_VALIDATED"
        )

    elif mutation == "SHIPPING_MODE":
        scenario["shipping_mode"] = rnd.choice(
            SHIPPING_MODES
        )

    elif mutation == "QUANTITY":
        scenario["quantity_kg"] = round(
            scenario["quantity_kg"]
            * rnd.uniform(0.25, 2.5),
            2,
        )

    elif mutation == "DESTINATION":
        meta = CORRIDOR_META[
            scenario["corridor"]
        ]

        scenario["destination"] = choose_country(
            rnd,
            meta["destination_region"],
            exclude=scenario["origin"],
        )

    elif mutation == "PAYMENT":
        scenario["payment_term"] = rnd.choice(
            PAYMENT_TERMS
        )

    elif mutation == "INCOTERM":
        scenario["incoterm"] = rnd.choice(
            INCOTERMS
        )

    scenario["parent_scenario_id"] = (
        original["scenario_id"]
    )

    scenario["mutation"] = mutation

    scenario["scenario_id"] = (
        "VAR-"
        + sha256_text(
            original["scenario_id"]
            + ":"
            + str(mutation_index)
            + ":"
            + mutation
            + ":"
            + json.dumps(
                scenario,
                sort_keys=True,
                default=str,
            )
        )[:24]
    )

    return scenario


def split_dataset(
    scenarios: list[dict[str, Any]],
    seed: int,
) -> dict[str, list[dict[str, Any]]]:

    rnd = random.Random(seed)

    shuffled = scenarios[:]
    rnd.shuffle(shuffled)

    count = len(shuffled)

    blind_count = max(
        1,
        int(count * 0.15)
    )

    validation_count = max(
        1,
        int(count * 0.15)
    )

    blind = shuffled[:blind_count]

    validation = shuffled[
        blind_count:
        blind_count + validation_count
    ]

    train = shuffled[
        blind_count + validation_count:
    ]

    return {
        "train": train,
        "validation": validation,
        "blind": blind,
    }


def replay(
    scenarios: list[dict[str, Any]],
    dataset: str,
) -> dict[str, Any]:

    started = time.perf_counter()

    rows = []

    for scenario in scenarios:
        expected = oracle(scenario)

        response = c5_policy_v04(
            scenario
        )

        scored = score_decision(
            scenario,
            response,
            expected,
        )

        rows.append({
            "scenario_id": scenario["scenario_id"],
            "corridor": scenario["corridor"],
            "failure": scenario["injected_failure"],
            "expected": expected,
            "response": response,
            "score": scored,
        })

    scores = [
        row["score"]["score"]
        for row in rows
    ]

    decision_correct = [
        row["score"]["checks"]["decision_match"]
        for row in rows
    ]

    abstentions = [
        row["score"]["checks"]["correct_abstention"]
        for row in rows
    ]

    recovery = [
        row["score"]["checks"]["recovery_detected"]
        for row in rows
    ]

    false_execution = sum(
        1
        for row in rows
        if row["response"]["execution_authorized"]
    )

    false_currentness = sum(
        1
        for row in rows
        if row["response"]["legal_currentness_claimed"]
    )

    elapsed_ms = (
        time.perf_counter() - started
    ) * 1000

    metrics = {
        "dataset": dataset,
        "scenario_count": len(rows),

        "mean_score": round(
            statistics.mean(scores),
            6,
        ) if scores else 0.0,

        "novel_case_accuracy": round(
            sum(decision_correct)
            / max(len(decision_correct), 1),
            6,
        ),

        "abstention_correctness": round(
            sum(abstentions)
            / max(len(abstentions), 1),
            6,
        ),

        "recovery_detection_rate": round(
            sum(recovery)
            / max(len(recovery), 1),
            6,
        ),

        "false_execution_count":
            false_execution,

        "false_currentness_count":
            false_currentness,

        "elapsed_ms": round(
            elapsed_ms,
            3,
        ),

        "cases_per_second": round(
            len(rows)
            / max(elapsed_ms / 1000, 0.000001),
            3,
        ),
    }

    return {
        "schema": "c5-trade-replay/v0.4",
        "generated_at": now_iso(),
        "metrics": metrics,
        "rows": rows,
    }


def failure_family_metrics(
    replay_obj: dict[str, Any]
) -> dict[str, Any]:

    grouped: dict[
        str,
        list[dict[str, Any]]
    ] = collections.defaultdict(list)

    for row in replay_obj["rows"]:
        grouped[
            row["failure"]
        ].append(row)

    output = {}

    for failure, rows in grouped.items():
        scores = [
            row["score"]["score"]
            for row in rows
        ]

        correct = sum(
            1
            for row in rows
            if row["score"]["checks"]["decision_match"]
        )

        output[failure] = {
            "count": len(rows),
            "mean_score": round(
                statistics.mean(scores),
                6,
            ),
            "decision_accuracy": round(
                correct / len(rows),
                6,
            ),
        }

    return output


def generate_skill_candidates(
    training_replay: dict[str, Any],
    blind_replay: dict[str, Any],
) -> list[dict[str, Any]]:

    train_failure = failure_family_metrics(
        training_replay
    )

    blind_failure = failure_family_metrics(
        blind_replay
    )

    candidates = []

    rules = [
        (
            "FAIL_CLOSED_ON_UNRESOLVED_LEGAL_CURRENTNESS",
            "EXPIRED_EVIDENCE",
        ),
        (
            "FAIL_CLOSED_ON_SUPERSESSION_RISK",
            "SUPERSEDED_RULE_RISK",
        ),
        (
            "REQUIRE_REVIEW_ON_HS_AMBIGUITY",
            "HS_AMBIGUITY",
        ),
        (
            "REQUIRE_COMPLETE_DOCUMENT_EVIDENCE",
            "MISSING_DOCUMENT",
        ),
        (
            "BLOCK_RELEASE_ON_QUALITY_FAILURE",
            "QUALITY_FAILURE",
        ),
        (
            "RECOVER_OPERATIONAL_DELAY_WITHOUT_FALSE_SUCCESS",
            "PORT_DELAY",
        ),
        (
            "DEDUPE_REPEATED_OPERATIONAL_EVENTS",
            "DUPLICATE_EVENT",
        ),
    ]

    for skill_name, failure in rules:
        train = train_failure.get(
            failure,
            {}
        )

        blind = blind_failure.get(
            failure,
            {}
        )

        train_accuracy = train.get(
            "decision_accuracy",
            0.0,
        )

        blind_accuracy = blind.get(
            "decision_accuracy",
            0.0,
        )

        candidate = (
            train_accuracy >= 0.95
            and blind_accuracy >= 0.95
        )

        candidates.append({
            "skill_id":
                "SKILL-"
                + sha256_text(skill_name)[:20],

            "name": skill_name,

            "failure_family": failure,

            "train_accuracy":
                train_accuracy,

            "blind_accuracy":
                blind_accuracy,

            "state": (
                "PRACTICED"
                if candidate
                else "DISCOVERED"
            ),

            "validated": False,
            "canonical": False,

            "reason": (
                "Blind replay may justify PRACTICED only. "
                "Independent real-world validation is still required."
            ),
        })

    return candidates


def build_experience_records(
    train_replay: dict[str, Any],
    validation_replay: dict[str, Any],
    blind_replay: dict[str, Any],
) -> list[dict[str, Any]]:

    records = []

    for dataset_name, replay_obj in [
        ("train", train_replay),
        ("validation", validation_replay),
        ("blind", blind_replay),
    ]:

        for row in replay_obj["rows"]:
            records.append({
                "experience_id":
                    "EXP-"
                    + sha256_text(
                        dataset_name
                        + ":"
                        + row["scenario_id"]
                    )[:24],

                "scenario_id":
                    row["scenario_id"],

                "dataset":
                    dataset_name,

                "corridor":
                    row["corridor"],

                "failure":
                    row["failure"],

                "decision":
                    row["response"]["decision"],

                "expected":
                    row["expected"]["expected_decision"],

                "score":
                    row["score"]["score"],

                "error": (
                    not row["score"]["checks"]["decision_match"]
                ),

                "state": "PRACTICED",

                "canonical": False,

                "created_at":
                    now_iso(),
            })

    return records


def experience_metrics(
    records: list[dict[str, Any]]
) -> dict[str, Any]:

    errors = [
        record
        for record in records
        if record["error"]
    ]

    by_failure = collections.Counter(
        record["failure"]
        for record in errors
    )

    repeated_error_count = sum(
        count
        for count
        in by_failure.values()
        if count >= 2
    )

    return {
        "experience_count":
            len(records),

        "error_count":
            len(errors),

        "error_rate": round(
            len(errors)
            / max(len(records), 1),
            6,
        ),

        "repeat_error_count":
            repeated_error_count,

        "repeat_error_rate": round(
            repeated_error_count
            / max(len(records), 1),
            6,
        ),

        "error_families":
            dict(by_failure),
    }


def invariant_audit(
    datasets: dict[
        str,
        list[dict[str, Any]]
    ],
    replays: list[dict[str, Any]],
    skills: list[dict[str, Any]],
) -> dict[str, Any]:

    violations = []

    for dataset, scenarios in datasets.items():
        for scenario in scenarios:
            if scenario.get(
                "execution_authority"
            ) is True:
                violations.append(
                    f'{scenario["scenario_id"]}:EXECUTION_AUTHORITY'
                )

            if scenario.get(
                "legal_applicability_proven"
            ) is True:
                violations.append(
                    f'{scenario["scenario_id"]}:LEGAL_APPLICABILITY_AUTO_PROVEN'
                )

            if scenario.get(
                "gl005_proven"
            ) is True:
                violations.append(
                    f'{scenario["scenario_id"]}:GL005_FLIPPED'
                )

    for replay_obj in replays:
        for row in replay_obj["rows"]:
            response = row["response"]

            if response.get(
                "execution_authorized"
            ) is True:
                violations.append(
                    f'{row["scenario_id"]}:REPLAY_EXECUTION'
                )

            if response.get(
                "canonical_promotion"
            ) is True:
                violations.append(
                    f'{row["scenario_id"]}:AUTO_CANONICAL'
                )

            if response.get(
                "legal_currentness_claimed"
            ) is True:
                violations.append(
                    f'{row["scenario_id"]}:FALSE_CURRENTNESS'
                )

    for skill in skills:
        if skill.get("validated") is True:
            violations.append(
                f'{skill["skill_id"]}:AUTO_VALIDATED'
            )

        if skill.get("canonical") is True:
            violations.append(
                f'{skill["skill_id"]}:AUTO_CANONICAL'
            )

    return {
        "pass": len(violations) == 0,
        "violation_count":
            len(violations),
        "violations":
            violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenarios",
        type=int,
        default=5000,
    )

    parser.add_argument(
        "--variants",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=20260821,
    )

    args = parser.parse_args()

    currentness_obj = load_json(
        DATA
        / "official-currentness-units.json"
    )

    currentness_units = currentness_obj.get(
        "units",
        []
    )

    risk = evidence_risk_score(
        currentness_units
    )

    rnd = random.Random(
        args.seed
    )

    base_scenarios = [
        generate_scenario(
            rnd,
            scenario_index=i,
            evidence_risk=risk,
        )
        for i in range(
            args.scenarios
        )
    ]

    variants = []

    variant_index = 0

    for scenario in base_scenarios:
        for _ in range(
            args.variants
        ):
            variants.append(
                mutate_scenario(
                    scenario,
                    rnd,
                    variant_index,
                )
            )

            variant_index += 1

    all_scenarios = (
        base_scenarios
        + variants
    )

    datasets = split_dataset(
        all_scenarios,
        args.seed + 17,
    )

    train_replay = replay(
        datasets["train"],
        "train",
    )

    validation_replay = replay(
        datasets["validation"],
        "validation",
    )

    blind_replay = replay(
        datasets["blind"],
        "blind",
    )

    skills = generate_skill_candidates(
        train_replay,
        blind_replay,
    )

    experiences = build_experience_records(
        train_replay,
        validation_replay,
        blind_replay,
    )

    exp_metrics = experience_metrics(
        experiences
    )

    audit = invariant_audit(
        datasets,
        [
            train_replay,
            validation_replay,
            blind_replay,
        ],
        skills,
    )

    scenario_output = {
        "schema":
            "c5-trade-scenarios/v0.4",

        "generated_at":
            now_iso(),

        "base_scenario_count":
            len(base_scenarios),

        "variant_count":
            len(variants),

        "total_count":
            len(all_scenarios),

        "evidence_risk_ratio":
            round(risk, 6),

        "scenarios":
            all_scenarios,
    }

    train_set_output = {
        "schema":
            "c5-trade-dataset/v0.4",

        "dataset":
            "train",

        "count":
            len(datasets["train"]),

        "scenario_ids": [
            x["scenario_id"]
            for x in datasets["train"]
        ],
    }

    validation_set_output = {
        "schema":
            "c5-trade-dataset/v0.4",

        "dataset":
            "validation",

        "count":
            len(
                datasets["validation"]
            ),

        "scenario_ids": [
            x["scenario_id"]
            for x
            in datasets["validation"]
        ],
    }

    blind_set_output = {
        "schema":
            "c5-trade-dataset/v0.4",

        "dataset":
            "blind",

        "count":
            len(datasets["blind"]),

        "scenario_ids": [
            x["scenario_id"]
            for x in datasets["blind"]
        ],
    }

    skill_output = {
        "schema":
            "c5-skill-candidates/v0.4",

        "generated_at":
            now_iso(),

        "count":
            len(skills),

        "skills":
            skills,

        "automatic_validation":
            False,

        "automatic_canonical_promotion":
            False,
    }

    experience_output = {
        "schema":
            "c5-experience-records/v0.4",

        "generated_at":
            now_iso(),

        "metrics":
            exp_metrics,

        "records":
            experiences,
    }

    benchmark = {
        "schema":
            "c5-trade-benchmark/v0.4",

        "generated_at":
            now_iso(),

        "train":
            train_replay["metrics"],

        "validation":
            validation_replay["metrics"],

        "blind":
            blind_replay["metrics"],

        "experience":
            exp_metrics,

        "skill_candidates":
            len(skills),

        "practiced_skill_candidates":
            sum(
                1
                for skill in skills
                if skill["state"]
                == "PRACTICED"
            ),

        "validated_skills":
            0,

        "canonical_skills":
            0,

        "mentor_dependency":
            "NOT_MEASURED_YET",

        "real_expert_equivalence":
            False,

        "legal_currentness_proven":
            False,

        "operational_applicability_proven":
            False,

        "gl005_proven":
            False,
    }

    outputs = {
        SIMULATION
        / "trade-scenarios.json":
            scenario_output,

        SIMULATION
        / "train-set.json":
            train_set_output,

        SIMULATION
        / "validation-set.json":
            validation_set_output,

        SIMULATION
        / "blind-set.json":
            blind_set_output,

        STATE
        / "trade-replay-train.json":
            train_replay,

        STATE
        / "trade-replay-validation.json":
            validation_replay,

        STATE
        / "trade-replay-blind.json":
            blind_replay,

        EXPERIENCE
        / "trade-experience.json":
            experience_output,

        SKILLS
        / "trade-skill-candidates.json":
            skill_output,

        BENCHMARKS
        / "trade-v04-benchmark.json":
            benchmark,

        STATE
        / "v04-invariant-audit.json": {
            "schema":
                "c5-v04-invariant-audit/v0.4",

            "generated_at":
                now_iso(),

            **audit,

            "gl005_proven":
                False,
        },
    }

    for path, obj in outputs.items():
        save_json(
            path,
            obj,
        )

    hashes = {
        str(
            path.relative_to(ROOT)
        ).replace("\\", "/"):
            sha256_bytes(
                path.read_bytes()
            )
        for path in outputs
    }

    receipt = {
        "schema":
            "c5-trade-experience-receipt/v0.4",

        "generated_at":
            now_iso(),

        "metrics": {
            "base_scenarios":
                len(base_scenarios),

            "variants":
                len(variants),

            "total_scenarios":
                len(all_scenarios),

            "train_count":
                len(datasets["train"]),

            "validation_count":
                len(
                    datasets["validation"]
                ),

            "blind_count":
                len(datasets["blind"]),

            "train_accuracy":
                train_replay[
                    "metrics"
                ][
                    "novel_case_accuracy"
                ],

            "validation_accuracy":
                validation_replay[
                    "metrics"
                ][
                    "novel_case_accuracy"
                ],

            "blind_accuracy":
                blind_replay[
                    "metrics"
                ][
                    "novel_case_accuracy"
                ],

            "blind_abstention":
                blind_replay[
                    "metrics"
                ][
                    "abstention_correctness"
                ],

            "blind_recovery":
                blind_replay[
                    "metrics"
                ][
                    "recovery_detection_rate"
                ],

            "repeat_error_rate":
                exp_metrics[
                    "repeat_error_rate"
                ],
        },

        "hashes":
            hashes,

        "invariant_audit":
            audit,

        "epistemic": {
            "TRADE_SIMULATOR":
                True,

            "COUNTERFACTUAL_VARIANTS":
                True,

            "ADVERSARIAL_FAILURES":
                True,

            "TRAIN_REPLAY":
                True,

            "VALIDATION_REPLAY":
                True,

            "BLIND_REPLAY":
                True,

            "EXPERIENCE_RECORDING":
                True,

            "SKILL_CANDIDATE_COMPILATION":
                True,

            "REAL_WORLD_VALIDATION":
                False,

            "REAL_EXPERT_EQUIVALENCE":
                False,

            "LEGAL_CURRENTNESS_PROVEN":
                False,

            "OPERATIONAL_APPLICABILITY_PROVEN":
                False,

            "AUTO_CANONICAL_PROMOTION":
                False,

            "GL005_PROVEN":
                False,
        },
    }

    receipt_path = (
        RECEIPTS
        / (
            "FOUNDRY-TRADE-V04-"
            + dt.datetime.now().strftime(
                "%Y%m%d-%H%M%S"
            )
            + ".json"
        )
    )

    save_json(
        receipt_path,
        receipt,
    )

    print(
        json.dumps(
            {
                "success":
                    audit["pass"],

                "base_scenarios":
                    len(base_scenarios),

                "variants":
                    len(variants),

                "total_scenarios":
                    len(all_scenarios),

                "train":
                    train_replay[
                        "metrics"
                    ],

                "validation":
                    validation_replay[
                        "metrics"
                    ],

                "blind":
                    blind_replay[
                        "metrics"
                    ],

                "experience":
                    exp_metrics,

                "skill_candidates":
                    len(skills),

                "practiced_skill_candidates":
                    sum(
                        1
                        for skill in skills
                        if skill["state"]
                        == "PRACTICED"
                    ),

                "invariant_violations":
                    audit[
                        "violation_count"
                    ],

                "receipt":
                    str(
                        receipt_path
                        .relative_to(ROOT)
                    ).replace("\\", "/"),

                "real_world_validation":
                    False,

                "real_expert_equivalence":
                    False,

                "gl005_proven":
                    False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return (
        0
        if audit["pass"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
