from __future__ import annotations

import tempfile
from pathlib import Path

from RAIOS.V9.cloud.nomadic.provider_contract import (
    UNKNOWN,
    normalize_resource_record,
)

from RAIOS.V9.cloud.nomadic.receipt_writer import (
    ReceiptWriter,
)

from RAIOS.V9.cloud.nomadic.work_stealing_scheduler import (
    WorkStealingScheduler,
)

from RAIOS.V9.autonomic.self_inspection.cloud_capacity_census import (
    apply_receipt_feedback,
    write_projection,
)


def worker(
    worker_id,
    provider,
    *,
    capability="code",
    freshness="FRESH",
    availability="READY",
    accuracy=0.95,
    confidence=0.90,
    success=0.90,
    failure=0.10,
    cost=0.10,
    latency=100,
):

    return normalize_resource_record({
        "provider":provider,
        "worker_id":worker_id,

        "auth_state":"PROVEN",
        "control_plane_state":"REACHABLE",
        "availability":availability,

        "task_classes":[capability],

        "verified_accuracy":accuracy,
        "confidence":confidence,

        "task_success_rate":success,
        "failure_rate":failure,

        "price_cpu_second":cost,
        "observed_latency":latency,

        "max_concurrency":2,
        "projected_runway":100,

        "freshness":freshness,
        "evidence_source":
            "SYNTHETIC_CONTROLLED_PHASE3",
    })


scheduler=WorkStealingScheduler()


# ============================================================
# 1 — REAL LIVE BOOTSTRAP PROJECTION MUST NOT ROUTE
# ============================================================

live=scheduler.load_resource_projection()

live_result=scheduler.route_resource_task(
    {
        "capability":"code",
        "min_verified_accuracy":0.90,
    },
    projection=live,
)

assert live_result["ok"] is False

print(
    "LIVE_UNPROVEN_RESOURCE_REJECTION_TEST=true"
)


# ============================================================
# 2 — STALE REJECTION
# ============================================================

r=scheduler.route_resource_task(
    {
        "capability":"code",
        "min_verified_accuracy":0.90,
    },
    projection={
        "records":[
            worker(
                "STALE",
                "provider-a",
                freshness="STALE",
                accuracy=1.0,
            ),
            worker(
                "FRESH",
                "provider-b",
                accuracy=0.92,
            ),
        ]
    },
)

assert r["ok"] is True
assert r["worker_id"]=="FRESH"

assert any(
    x["worker_id"]=="STALE"
    and x["reason"]
        =="STALE_OR_UNPROVEN_EVIDENCE"
    for x in r["rejected"]
)

print(
    "STALE_EVIDENCE_REJECTION_TEST=true"
)


# ============================================================
# 3 — CAPABILITY FILTER
# ============================================================

r=scheduler.route_resource_task(
    {
        "capability":"code",
        "min_verified_accuracy":0.90,
    },
    projection={
        "records":[
            worker(
                "WRONG",
                "provider-a",
                capability="embedding",
            )
        ]
    },
)

assert r["ok"] is False

assert any(
    x["reason"]
    =="CAPABILITY_MISMATCH"
    for x in r["rejected"]
)

print(
    "CAPABILITY_FILTER_TEST=true"
)


# ============================================================
# 4 — ACCURACY BEFORE COST
# ============================================================

r=scheduler.route_resource_task(
    {
        "capability":"code",
        "risk_class":"HIGH",
        "min_verified_accuracy":0.90,
    },
    projection={
        "records":[

            worker(
                "CHEAP_BAD",
                "cheap-provider",
                accuracy=0.50,
                cost=0.0001,
            ),

            worker(
                "GOOD",
                "quality-provider",
                accuracy=0.97,
                cost=1.0,
            ),
        ]
    },
)

assert r["ok"] is True
assert r["worker_id"]=="GOOD"

print(
    "ACCURACY_GATE_TEST=true"
)


# ============================================================
# 5 — COST ONLY AFTER EQUAL ELIGIBILITY
# ============================================================

r=scheduler.route_resource_task(
    {
        "capability":"code",
        "min_verified_accuracy":0.90,
    },
    projection={
        "records":[

            worker(
                "EXPENSIVE",
                "p1",
                accuracy=0.95,
                confidence=0.90,
                success=0.90,
                failure=0.10,
                cost=0.50,
                latency=100,
            ),

            worker(
                "CHEAP",
                "p2",
                accuracy=0.95,
                confidence=0.90,
                success=0.90,
                failure=0.10,
                cost=0.05,
                latency=100,
            ),
        ]
    },
)

assert r["worker_id"]=="CHEAP"

print(
    "COST_ROUTING_TEST=true"
)


# ============================================================
# 6 — FRESH EVIDENCE BEATS STALE CONTRADICTION
# ============================================================

r=scheduler.route_resource_task(
    {
        "capability":"code",
        "min_verified_accuracy":0.90,
    },
    projection={
        "records":[

            worker(
                "OLD",
                "p1",
                freshness="STALE",
                accuracy=1.0,
                confidence=1.0,
            ),

            worker(
                "NEW",
                "p2",
                freshness="FRESH",
                accuracy=0.92,
                confidence=0.80,
            ),
        ]
    },
)

assert r["worker_id"]=="NEW"

print(
    "EVIDENCE_FRESHNESS_TEST=true"
)


# ============================================================
# 7 — PROVIDER NAME DOES NOT DETERMINE ROUTE
# ============================================================

task={
    "capability":"code",
    "min_verified_accuracy":0.90,
}

a=worker(
    "WORKER_A",
    "provider-alpha",
    cost=0.50,
)

b=worker(
    "WORKER_B",
    "provider-beta",
    cost=0.05,
)

r1=scheduler.route_resource_task(
    task,
    projection={
        "records":[a,b]
    },
)

a2=dict(a)
a2["provider"]="totally-renamed-one"

b2=dict(b)
b2["provider"]="totally-renamed-two"

r2=scheduler.route_resource_task(
    task,
    projection={
        "records":[a2,b2]
    },
)

assert r1["worker_id"]=="WORKER_B"
assert r2["worker_id"]=="WORKER_B"

print(
    "PROVIDER_INDEPENDENCE_TEST=true"
)


# ============================================================
# 8 — SAME TASK MIGRATES PROVIDER
# ============================================================

first=scheduler.route_resource_task(
    task,
    projection={
        "records":[
            worker(
                "A",
                "provider-one",
                cost=0.01,
            ),
            worker(
                "B",
                "provider-two",
                cost=0.10,
            ),
        ]
    },
)

second=scheduler.route_resource_task(
    task,
    projection={
        "records":[
            worker(
                "A",
                "provider-one",
                cost=0.01,
                freshness="STALE",
            ),
            worker(
                "B",
                "provider-two",
                cost=0.10,
            ),
        ]
    },
)

assert first["worker_id"]=="A"
assert second["worker_id"]=="B"

assert (
    first["task_fingerprint"]
    ==second["task_fingerprint"]
)

print(
    "PROVIDER_MIGRATION_TEST=true"
)


# ============================================================
# 9 — A14 SELECTION SEMANTICS ARE REUSED
# ============================================================

factors=(
    scheduler.resource_selection_factors()
)

for required in (
    "capability_fit",
    "verified_availability",
    "historical_success",
    "failure_rate",
    "latency",
    "cost_observation",
):

    assert required in factors


for extension in (
    "verified_accuracy",
    "freshness",
    "resource_scarcity",
    "credit_runway",
    "risk_budget",
    "data_locality",
):

    assert extension in factors


print(
    "A14_SELECTION_SEMANTICS_REUSED_TEST=true"
)


# ============================================================
# 10 — CONTROLLED E2E
#      NO CLOUD WORKLOAD
# ============================================================

with tempfile.TemporaryDirectory() as td:

    td=Path(td)

    projection_path=(
        td/"FREE-RESOURCES.json"
    )

    receipt_path=(
        td/"receipts.jsonl"
    )

    synthetic_worker=worker(
        "SYNTH_EXECUTOR",
        "synthetic-provider",
        capability="code",
        accuracy=0.95,
        confidence=0.95,
        cost=0.02,
        latency=50,
    )

    projection=write_projection(
        [synthetic_worker],
        path=projection_path,
    )


    decision=(
        scheduler.route_resource_task(
            {
                "capability":"code",
                "risk_class":"HIGH",
                "min_verified_accuracy":0.90,
            },
            projection=projection,
        )
    )

    assert decision["ok"] is True

    assert (
        decision["worker_id"]
        =="SYNTH_EXECUTOR"
    )


    # Synthetic result only.
    output={
        "status":"OK",
        "result":
            "RESOURCE_PHASE3_SYNTHETIC",
    }


    writer=ReceiptWriter(
        path=receipt_path
    )

    receipt=writer.write(
        job_id="RESOURCE-PHASE3-E2E",
        worker_id="SYNTH_EXECUTOR",
        input_hash="SYNTHETIC_INPUT_HASH",
        output=output,
        steps=[
            "RESOURCE_PROJECTION",
            "TASK_FINGERPRINT",
            "CAPABILITY_FILTER",
            "RISK_ACCURACY_GATE",
            "SCHEDULER_DECISION",
            "SYNTHETIC_EXECUTION",
            "VERIFICATION",
        ],
        resumed=False,
    )


    assert receipt_path.exists()

    assert isinstance(
        receipt,
        dict,
    )


    updated=apply_receipt_feedback(
        "SYNTH_EXECUTOR",
        receipt,
        path=projection_path,
        observed_latency=25,
        observed_cost=0.0,
        verification={
            "verified":True,
            "accuracy":0.98,
        },
    )


    row=updated["records"][0]


    assert (
        row["task_success_rate"]
        ==1.0
    )

    assert (
        row["failure_rate"]
        ==0.0
    )

    assert (
        row["observed_latency"]
        ==25
    )

    assert (
        row["verified_accuracy"]
        ==0.98
    )

    assert (
        row["freshness"]
        =="FRESH"
    )


print(
    "RECEIPT_FEEDBACK_TEST=true"
)

print(
    "CONTROLLED_E2E_PROVEN=true"
)

print(
    "CLOUD_WORKLOAD_EXECUTED=false"
)

print(
    "GPU_CREDIT_BURN=false"
)

print(
    "NEW_SCHEDULER_CREATED=false"
)

print(
    "NEW_PROVIDER_FRAMEWORK_CREATED=false"
)

print(
    "NEW_BUS_CREATED=false"
)
