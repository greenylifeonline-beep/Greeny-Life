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
    / "RESOURCE-PROJECTION.json"
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


    # A receipt proves material execution evidence, not semantic success.
    # Success/failure may be promoted only by explicit external verification.
    outcome_verified = bool(
        verification
        and verification.get("verified") is True
    )

    if outcome_verified:
        success = bool(
            receipt.get("output_hash")
            or receipt.get("receipt_hash")
            or receipt.get("sha256")
        )

        row["task_success_rate"] = (
            1.0 if success else 0.0
        )

        row["failure_rate"] = (
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

    if (
        outcome_verified
        and row.get("confidence") == UNKNOWN
    ):
        row["confidence"] = 1.0


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


# ============================================================
# UNIVERSAL_PROVIDER_EVIDENCE_INGESTION_V1
# ============================================================

def ingest_provider_evidence(
    provider: str, evidence: dict[str, Any], *, path: Path | None = None,
) -> dict[str, Any]:
    from ...cloud.nomadic.provider_contract import NOT_PROVEN, normalize_capacity_bounds
    if not provider:
        raise ValueError("PROVIDER_REQUIRED")
    if not isinstance(evidence, dict):
        raise TypeError("PROVIDER_EVIDENCE_MUST_BE_MAPPING")
    target = path or PROJECTION
    current = load_projection(target)
    records = list(current.get("records", []))
    incoming_account = evidence.get("account", UNKNOWN)
    incoming_workspace = evidence.get("workspace", UNKNOWN)
    def known(v): return v not in {None, "", UNKNOWN}
    def same_identity(row):
        if str(row.get("provider")) != str(provider): return False
        for key, incoming in (("account", incoming_account), ("workspace", incoming_workspace)):
            existing = row.get(key, UNKNOWN)
            if known(incoming) and known(existing) and str(incoming) != str(existing): return False
        return True
    found = next((i for i,r in enumerate(records) if same_identity(r)), None)
    if found is None:
        row = normalize_resource_record({"provider": provider})
        records.append(row); found=len(records)-1
    row=dict(records[found])
    def stamp(v):
        if not isinstance(v,str): return None
        try:
            d=datetime.fromisoformat(v.replace("Z","+00:00"))
            return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
        except ValueError: return None
    old_t=stamp(row.get("last_probe")); new_t=stamp(evidence.get("last_probe"))
    if old_t is not None and new_t is not None and new_t < old_t:
        return current
    incoming_capacity = None
    if "capacity_bounds" in evidence:
        incoming_capacity=normalize_capacity_bounds(evidence["capacity_bounds"])
        old_capacity=row.get("capacity_bounds")
        if old_capacity and incoming_capacity != old_capacity and str(row.get("freshness")).upper()=="FRESH":
            row["evidence_conflict"]="QUARANTINED_CONTRADICTION"
            row["conflicting_evidence_hash"]=_evidence_hash({"provider":provider,"capacity_bounds":incoming_capacity,"last_probe":evidence.get("last_probe")})
            incoming_capacity=None
    for key in ("account","workspace","auth_state","control_plane_state","availability","data_locality","model_availability","model_cache","task_classes","observed_latency","last_probe","confidence","freshness"):
        if key in evidence: row[key]=evidence[key]
    for key in ("free_credit","paid_credit","credit_expiry","estimated_burn_rate","projected_runway","price_cpu_second","price_gpu_second","price_storage_gb","egress_cost","currency"):
        if key in evidence: row[key]=evidence[key]
    if incoming_capacity is not None: row["capacity_bounds"]=incoming_capacity
    row["evidence_source"]=str(evidence.get("evidence_source","UNSPECIFIED_PROVIDER_EVIDENCE"))
    if "freshness" not in evidence: row["freshness"]="FRESH"
    if "confidence" not in evidence: row["confidence"]=NOT_PROVEN
    row["last_probe"]=evidence.get("last_probe",utc())
    row["evidence_hash"]=_evidence_hash(row)
    records[found]=row
    return write_projection(records,path=target)


# ============================================================
# PHASE4B1_VALIDATED_PROVIDER_OBSERVATION_V1
# ============================================================

PROVIDER_OBSERVATION_STALE_SECONDS = {
    "local": 30,
    "colab": 60,
    "lightning": 180,
    "modal": 180,
    "oracle": 300,
    "kaggle": 300,
    "huggingface": 300,
}

INVALID_OBSERVATION = "UNKNOWN_INVALID_OBSERVATION"
INCOMPLETE_EVIDENCE = "UNKNOWN_INCOMPLETE_EVIDENCE"
STALE_OBSERVATION = "UNKNOWN_STALE_EVIDENCE"


def _observation_numeric(value):
    """
    Numeric evidence only.

    bool is rejected even though bool subclasses int in Python.
    NaN / Infinity / negative values are rejected.
    """
    import math

    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    value = float(value)

    if not math.isfinite(value):
        return None

    if value < 0:
        return None

    return value


def _nested_get(payload, path):
    current = payload

    for key in path.split("."):
        if not isinstance(current, dict):
            return None

        if key not in current:
            return None

        current = current[key]

    return current


def _observation_age_seconds(observed_at, now=None):
    """
    Return evidence age in seconds.

    Invalid timestamp => None => fail closed.
    """
    from datetime import datetime, timezone

    if not isinstance(observed_at, str) or not observed_at.strip():
        return None

    try:
        observed = datetime.fromisoformat(
            observed_at.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)

    if now is None:
        current = datetime.now(timezone.utc)

    elif isinstance(now, str):
        try:
            current = datetime.fromisoformat(
                now.replace("Z", "+00:00")
            )
        except ValueError:
            return None

        if current.tzinfo is None:
            current = current.replace(
                tzinfo=timezone.utc
            )

    else:
        current = now

    return max(
        0.0,
        (current - observed).total_seconds(),
    )


def provider_freshness_limit(provider):
    """
    Policy default, not provider truth.
    Unknown provider fails closed to the conservative minimum.
    """
    key = str(provider).lower()

    return PROVIDER_OBSERVATION_STALE_SECONDS.get(
        key,
        30,
    )


def _validate_oracle_observation(raw):
    """
    OCI resource availability proves QUOTA AVAILABILITY ONLY.
    It does not prove free entitlement or physical host capacity.
    """
    data = raw.get("data")

    if not isinstance(data, dict):
        return False, INCOMPLETE_EVIDENCE, {}

    available = data.get(
        "fractional-availability",
        data.get("fractional_availability",
            data.get("available")
        ),
    )

    used = data.get(
        "fractional-usage",
        data.get("fractional_usage",
            data.get("used")
        ),
    )

    available_n = _observation_numeric(available)
    used_n = _observation_numeric(used)

    if available_n is None or used_n is None:
        return False, INVALID_OBSERVATION, {}

    dimension = raw.get(
        "capacity_dimension"
    )

    unit = raw.get("unit")

    if not isinstance(dimension, str) or not dimension:
        return False, INCOMPLETE_EVIDENCE, {}

    if not isinstance(unit, str) or not unit:
        return False, INCOMPLETE_EVIDENCE, {}

    evidence = {
        "auth_state":
            raw.get("auth_state", "PROVEN"),

        "control_plane_state":
            raw.get(
                "control_plane_state",
                "REACHABLE",
            ),

        "freshness":
            "FRESH",

        "confidence":
            raw.get("confidence", 1.0),

        "capacity_bounds": {
            dimension: {
                "unit":
                    unit,

                "quota_available":
                    available_n,

                # Never infer these from service limits.
                "free_entitlement":
                    raw.get(
                        "free_entitlement",
                        "UNKNOWN",
                    ),

                "policy_budget":
                    raw.get(
                        "policy_budget",
                        "UNKNOWN",
                    ),
            }
        },

        "evidence_source":
            raw.get(
                "evidence_source",
                "OCI_RESOURCE_AVAILABILITY",
            ),

        "last_probe":
            raw.get("observed_at"),
    }

    return True, "VALIDATED", evidence


def _validate_local_observation(raw):
    """
    Local raw totals are observations, not automatically schedulable.
    """
    required = (
        "host_identity",
        "cpu_total",
        "memory_total",
        "memory_available",
        "storage_total",
        "storage_available",
    )

    for key in required:
        if key not in raw:
            return False, INCOMPLETE_EVIDENCE, {}

    cpu_total = _observation_numeric(
        raw.get("cpu_total")
    )

    memory_total = _observation_numeric(
        raw.get("memory_total")
    )

    memory_available = _observation_numeric(
        raw.get("memory_available")
    )

    storage_total = _observation_numeric(
        raw.get("storage_total")
    )

    storage_available = _observation_numeric(
        raw.get("storage_available")
    )

    if None in (
        cpu_total,
        memory_total,
        memory_available,
        storage_total,
        storage_available,
    ):
        return False, INVALID_OBSERVATION, {}

    if memory_available > memory_total:
        return False, INVALID_OBSERVATION, {}

    if storage_available > storage_total:
        return False, INVALID_OBSERVATION, {}

    evidence = {
        "account":
            str(raw["host_identity"]),

        "auth_state":
            "NOT_APPLICABLE_LOCAL_TRUST_DOMAIN",

        "control_plane_state":
            "REACHABLE",

        "freshness":
            "FRESH",

        "confidence":
            raw.get("confidence", 1.0),

        "capacity_bounds": {
            "cpu_count": {
                "unit":
                    "CPU",

                "quota_available":
                    cpu_total,

                "free_entitlement":
                    cpu_total,

                "policy_budget":
                    raw.get(
                        "policy_budget_cpu",
                        "UNKNOWN",
                    ),
            },

            "ram_gb": {
                "unit":
                    "GB",

                "quota_available":
                    memory_available,

                "free_entitlement":
                    memory_available,

                "policy_budget":
                    raw.get(
                        "policy_budget_ram_gb",
                        "UNKNOWN",
                    ),
            },

            "storage_gb": {
                "unit":
                    "GB",

                "quota_available":
                    storage_available,

                "free_entitlement":
                    storage_available,

                "policy_budget":
                    raw.get(
                        "policy_budget_storage_gb",
                        "UNKNOWN",
                    ),
            },
        },

        "evidence_source":
            raw.get(
                "evidence_source",
                "LOCAL_OS_INTROSPECTION",
            ),

        "last_probe":
            raw.get("observed_at"),
    }

    return True, "VALIDATED", evidence


def validate_provider_observation(
    provider,
    raw,
    *,
    now=None,
):
    """
    Validate raw provider evidence BEFORE canonical ingestion.

    Exit code zero is never sufficient.

    Returns a machine-readable validation receipt.
    """
    if not isinstance(raw, dict):
        return {
            "provider":
                str(provider),

            "valid":
                False,

            "status":
                INVALID_OBSERVATION,

            "reason":
                "RAW_OBSERVATION_NOT_MAPPING",

            "evidence":
                None,
        }

    # Explicit probe failure always fails closed.
    exit_code = raw.get("exit_code")

    if exit_code is not None and exit_code != 0:
        return {
            "provider":
                str(provider),

            "valid":
                False,

            "status":
                INVALID_OBSERVATION,

            "reason":
                "PROBE_EXIT_NONZERO",

            "evidence":
                None,
        }

    # Exit 0 without semantic payload proves nothing.
    if (
        exit_code == 0
        and len(raw.keys()) <= 2
    ):
        return {
            "provider":
                str(provider),

            "valid":
                False,

            "status":
                INCOMPLETE_EVIDENCE,

            "reason":
                "EXIT_ZERO_WITHOUT_SEMANTIC_EVIDENCE",

            "evidence":
                None,
        }

    observed_at = raw.get("observed_at")

    age = _observation_age_seconds(
        observed_at,
        now=now,
    )

    if age is None:
        return {
            "provider":
                str(provider),

            "valid":
                False,

            "status":
                INCOMPLETE_EVIDENCE,

            "reason":
                "OBSERVATION_TIMESTAMP_MISSING_OR_INVALID",

            "evidence":
                None,
        }

    freshness_limit = provider_freshness_limit(
        provider
    )

    if age > freshness_limit:
        return {
            "provider":
                str(provider),

            "valid":
                False,

            "status":
                STALE_OBSERVATION,

            "reason":
                "EVIDENCE_TOO_OLD",

            "age_seconds":
                age,

            "stale_after_seconds":
                freshness_limit,

            "evidence":
                None,
        }

    key = str(provider).lower()

    if key == "oracle":
        ok, status, evidence = (
            _validate_oracle_observation(raw)
        )

    elif key == "local":
        ok, status, evidence = (
            _validate_local_observation(raw)
        )

    else:
        # Phase 4B.1 deliberately fails closed for providers
        # whose semantic adapters are not yet bound.
        return {
            "provider":
                str(provider),

            "valid":
                False,

            "status":
                INCOMPLETE_EVIDENCE,

            "reason":
                "PROVIDER_SEMANTIC_ADAPTER_NOT_BOUND",

            "evidence":
                None,
        }

    return {
        "provider":
            str(provider),

        "valid":
            bool(ok),

        "status":
            status,

        "reason":
            (
                "SEMANTIC_SUCCESS"
                if ok
                else status
            ),

        "age_seconds":
            age,

        "stale_after_seconds":
            freshness_limit,

        "evidence":
            evidence if ok else None,
    }


def ingest_validated_provider_observation(
    provider,
    raw,
    *,
    path=None,
    now=None,
):
    """
    Canonical boundary:

    RAW
      -> VALIDATE
      -> INGEST

    Invalid/stale observations never mutate projection.
    """
    result = validate_provider_observation(
        provider,
        raw,
        now=now,
    )

    if not result.get("valid"):
        return {
            "ingested":
                False,

            "projection_mutated":
                False,

            "validation":
                result,
        }

    projection = ingest_provider_evidence(
        provider,
        result["evidence"],
        path=path,
    )

    return {
        "ingested":
            True,

        "projection_mutated":
            True,

        "validation":
            result,

        "projection":
            projection,
    }
