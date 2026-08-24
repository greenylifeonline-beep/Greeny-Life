from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .engine import cloud_capacity_census as run
from ...cloud.nomadic.provider_contract import (
    UNKNOWN,
    normalize_resource_record,
)


ROOT = Path(__file__).resolve().parents[4]

PROJECTION = (
    ROOT
    / ".ai-os"
    / "learning"
    / "FREE-RESOURCES.json"
)

SCHEMA = "raios.resource-projection.v1"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def projection_path() -> Path:
    return PROJECTION


def _evidence_hash(row: dict[str, Any]) -> str:
    material = {
        key: value
        for key, value in row.items()
        if key != "evidence_hash"
    }

    raw = json.dumps(
        material,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _normalize_with_hash(
    record: dict[str, Any],
) -> dict[str, Any]:

    row = normalize_resource_record(record)

    if row.get("evidence_hash") in {
        None,
        "",
        UNKNOWN,
    }:
        row["evidence_hash"] = _evidence_hash(row)

    return row


def initial_proven_records() -> list[dict[str, Any]]:
    """
    Bootstrap only facts already proven outside this module.

    UNKNOWN means no validated account/runtime evidence.
    UNKNOWN must never be rewritten as zero or False.
    """

    return [

        # ----------------------------------------------------
        # LOCAL / OWNER CONTROL PLANE
        # ----------------------------------------------------
        {
            "provider": "founder-laptop",
            "account": UNKNOWN,
            "workspace": "Greeny-Life-Repair",

            "auth_state": "LOCAL",
            "control_plane_state": "REACHABLE",

            # Local ownership/reachability is not proof that
            # this machine is eligible for a requested task.
            "availability": UNKNOWN,

            "evidence_source":
                "OWNER_LOCAL_CONTROL_PLANE",

            "confidence": UNKNOWN,
            "freshness": UNKNOWN,
        },

        # ----------------------------------------------------
        # ORACLE
        # ----------------------------------------------------
        {
            "provider": "oracle-primary",
            "account": UNKNOWN,
            "workspace": "eu-stockholm-1",

            "auth_state": "PROVEN",
            "control_plane_state": "REACHABLE",

            # OCI CLI + tenancy + region are proven.
            # Actual free/available execution capacity is not
            # yet proven by the unresolved availability probes.
            "availability": UNKNOWN,

            "cpu_available": UNKNOWN,
            "ram_available": UNKNOWN,

            "persistent_storage": UNKNOWN,
            "ephemeral_storage": UNKNOWN,

            "free_credit": UNKNOWN,
            "paid_credit": UNKNOWN,

            "evidence_source":
                "OCI_CLOUD_SHELL_AUTH_AND_REGION_PROVEN;"
                "LIVE_CAPACITY_NOT_YET_PROVEN",

            "confidence": UNKNOWN,
            "freshness": UNKNOWN,
        },

        # ----------------------------------------------------
        # LIGHTNING
        # ----------------------------------------------------
        {
            "provider": "lightning",
            "account": "greenylifeonline-org",
            "workspace": "default-project",

            "auth_state": "PROVEN",
            "control_plane_state": "REACHABLE",

            # Studios observed sleeping does not prove current
            # GPU readiness.
            "availability": UNKNOWN,

            # 30.00 total organization credits was observed,
            # but that is deliberately NOT encoded as current
            # free balance.
            "free_credit": UNKNOWN,
            "paid_credit": UNKNOWN,

            "evidence_source":
                "LIGHTNING_AUTH_PROVEN;"
                "TOTAL_ORG_CREDITS_OBSERVED_30.00;"
                "CURRENT_BALANCE_NOT_PROVEN;"
                "STUDIO_COUNT_OBSERVED_2_SLEEPING",

            "confidence": UNKNOWN,
            "freshness": UNKNOWN,
        },

        # ----------------------------------------------------
        # MODAL
        # ----------------------------------------------------
        {
            "provider": "modal",
            "account": UNKNOWN,
            "workspace": "greenylife-online",

            "auth_state": "PROVEN",
            "control_plane_state": "REACHABLE",

            # running_apps=0 does not mean available capacity=0.
            "availability": UNKNOWN,

            "free_credit": UNKNOWN,
            "paid_credit": UNKNOWN,

            "evidence_source":
                "MODAL_AUTH_CONTROL_PLANE_PROVEN;"
                "RUNNING_APPS_OBSERVED_0;"
                "ACCOUNT_CAPACITY_NOT_PROVEN",

            "confidence": UNKNOWN,
            "freshness": UNKNOWN,
        },

        # ----------------------------------------------------
        # KAGGLE
        # ----------------------------------------------------
        {
            "provider": "kaggle-a",
            "account": "greenylife",
            "workspace": UNKNOWN,

            "auth_state": "PROVEN",
            "control_plane_state": "REACHABLE",

            # Authentication + datasets list does not prove a
            # currently allocated GPU worker.
            "availability": UNKNOWN,

            "gpu_type": UNKNOWN,
            "gpu_count": UNKNOWN,
            "gpu_vram": UNKNOWN,

            "persistent_storage": UNKNOWN,
            "ephemeral_storage": UNKNOWN,

            "model_availability": UNKNOWN,

            "evidence_source":
                "KAGGLE_DATASETS_LIST_AUTHENTICATED;"
                "OWNED_MODELS_OBSERVED_0;"
                "SESSION_GPU_NOT_PROVEN",

            "confidence": UNKNOWN,
            "freshness": UNKNOWN,
        },

        # ----------------------------------------------------
        # COLAB
        # ----------------------------------------------------
        {
            "provider": "colab",
            "account": UNKNOWN,
            "workspace": UNKNOWN,

            # Project binding/install evidence is not enough
            # to claim authenticated active compute.
            "auth_state": UNKNOWN,
            "control_plane_state": "BOUND_NOT_PROVEN_READY",
            "availability": UNKNOWN,

            "gpu_type": UNKNOWN,
            "gpu_count": UNKNOWN,

            "evidence_source":
                "PROJECT_BIND_REPORTED;"
                "LIVE_SESSION_NOT_PROVEN",

            "confidence": UNKNOWN,
            "freshness": UNKNOWN,
        },

        # ----------------------------------------------------
        # HUGGING FACE
        # ----------------------------------------------------
        {
            "provider": "huggingface",
            "account": "greenylifeonline",
            "workspace": UNKNOWN,

            "auth_state": "PROVEN",
            "control_plane_state": "REACHABLE",

            # Login is proven. Storage plan/quota and compute
            # availability are deliberately not inferred.
            "availability": UNKNOWN,

            "persistent_storage": UNKNOWN,
            "free_credit": UNKNOWN,
            "paid_credit": UNKNOWN,

            "model_availability": UNKNOWN,

            "evidence_source":
                "HF_AUTH_WHOAMI_PROVEN;"
                "HF_ACCOUNT_STORAGE_QUOTA_NOT_PROVEN;"
                "HF_COMPUTE_CAPACITY_NOT_PROVEN",

            "confidence": UNKNOWN,
            "freshness": UNKNOWN,
        },
    ]


def write_projection(
    records: list[dict[str, Any]],
    *,
    path: Path | None = None,
) -> dict[str, Any]:

    target = path or PROJECTION

    normalized = [
        _normalize_with_hash(row)
        for row in records
    ]

    matrix = {
        "providers": {
            row["provider"]: {
                "auth_state":
                    row.get("auth_state", UNKNOWN),

                "control_plane_state":
                    row.get(
                        "control_plane_state",
                        UNKNOWN,
                    ),

                "availability":
                    row.get(
                        "availability",
                        UNKNOWN,
                    ),
            }
            for row in normalized
        }
    }

    census = run(matrix)

    payload = {
        "schema": SCHEMA,

        "generated_at": utc(),

        "authority":
            "provider_contract+worker_contract",

        "projection_is_source_of_truth": False,

        "record_count": len(normalized),

        "records": normalized,

        "census": census,

        "laws": [
            "UNKNOWN_NE_ZERO",
            "NOT_PROVEN_NE_FALSE",
            "SERVICE_LIMIT_NE_FREE_ENTITLEMENT",
            "CONNECTED_NE_READY_FOR_EXECUTION",
            "MODEL_INSTALLED_NE_MODEL_LOADED",
            "CREDIT_ENTITLEMENT_NE_CURRENT_BALANCE",
            "STALE_EVIDENCE_MUST_NOT_ROUTE",
            "UI_MUST_NOT_BE_SOURCE_OF_TRUTH",
            "SCHEDULER_MUST_NOT_PROBE_PROVIDERS",
        ],
    }

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = target.with_suffix(
        target.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    tmp.replace(target)

    return payload


def bootstrap_projection(
    *,
    path: Path | None = None,
) -> dict[str, Any]:

    return write_projection(
        initial_proven_records(),
        path=path,
    )


def load_projection(
    path: Path | None = None,
) -> dict[str, Any]:

    target = path or PROJECTION

    if not target.exists():
        return {
            "schema": SCHEMA,
            "record_count": 0,
            "records": [],
            "state": "NOT_PROVEN",
        }

    data = json.loads(
        target.read_text(
            encoding="utf-8",
        )
    )

    if data.get("schema") != SCHEMA:
        raise ValueError(
            "RESOURCE_PROJECTION_SCHEMA_MISMATCH"
        )

    return data


def manager_projection(
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Read-only Command Deck projection.
    UI is never the authority.
    """

    payload = load_projection(path)

    keys = (
        "provider",
        "account",
        "workspace",
        "auth_state",
        "control_plane_state",
        "availability",
        "cpu_type",
        "cpu_available",
        "ram_available",
        "gpu_type",
        "gpu_count",
        "gpu_vram",
        "persistent_storage",
        "ephemeral_storage",
        "free_credit",
        "paid_credit",
        "estimated_burn_rate",
        "projected_runway",
        "model_availability",
        "observed_latency",
        "task_success_rate",
        "verified_accuracy",
        "failure_rate",
        "last_probe",
        "freshness",
        "confidence",
        "evidence_source",
    )

    return [
        {
            key: row.get(key, UNKNOWN)
            for key in keys
        }
        for row in payload.get(
            "records",
            [],
        )
    ]



# RESOURCE_RECEIPT_FEEDBACK_V1

def apply_receipt_feedback(
    worker_id: str,
    receipt: dict[str, Any],
    *,
    path: Path | None = None,
    observed_latency: Any = UNKNOWN,
    observed_cost: Any = UNKNOWN,
    verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Update empirical resource evidence.

    verified_accuracy may only come from an explicit
    external verification result.
    """

    target=path or PROJECTION

    payload=load_projection(
        target
    )

    records=list(
        payload.get(
            "records",
            []
        )
    )

    index=None

    for i,row in enumerate(records):

        if (
            row.get("worker_id")
            == worker_id
        ):
            index=i
            break


    if index is None:
        raise KeyError(
            "RESOURCE_WORKER_NOT_FOUND::"
            +worker_id
        )


    row=dict(records[index])


    # Existing ReceiptWriter produces material output
    # evidence only after execution completes.
    success=bool(
        receipt.get("output_hash")
        or receipt.get("receipt_hash")
        or receipt.get("sha256")
    )


    row["task_success_rate"]=(
        1.0 if success else 0.0
    )

    row["failure_rate"]=(
        0.0 if success else 1.0
    )


    if observed_latency != UNKNOWN:

        row["observed_latency"]=(
            observed_latency
        )

    elif (
        receipt.get("latency_ms")
        is not None
    ):

        row["observed_latency"]=(
            receipt["latency_ms"]
        )


    # Observed cost is evidence.
    # Published price is not observed job cost.
    if observed_cost != UNKNOWN:

        row[
            "observed_cost"
        ]=observed_cost


    # NEVER accept model self-confidence as accuracy.
    if (
        verification
        and verification.get(
            "verified"
        ) is True
        and isinstance(
            verification.get(
                "accuracy"
            ),
            (int,float),
        )
        and not isinstance(
            verification.get(
                "accuracy"
            ),
            bool,
        )
    ):

        row["verified_accuracy"]=float(
            verification["accuracy"]
        )


    row["last_probe"]=utc()

    row["freshness"]="FRESH"

    if row.get("confidence") == UNKNOWN:
        row["confidence"]=1.0


    row["evidence_source"]=(
        str(
            row.get(
                "evidence_source",
                ""
            )
        )
        +"|EXISTING_EXECUTION_RECEIPT"
    ).strip("|")


    row["evidence_hash"]=_evidence_hash(
        row
    )


    records[index]=row


    return write_projection(
        records,
        path=target,
    )
