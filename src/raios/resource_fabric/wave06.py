"""Wave-06 live-binding evidence. Not a second registry. No secrets in outputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .census import collect_world
from .factory import evaluate_workload, place, reservoir_view, resource_request
from .live import WAVE06_PACKAGE, apply_live_overlay, discover_auth
from .schema import UNOBSERVED
from .secrets import assert_no_secrets, mask_record

EVIDENCE_KEYS = (
    "PATH",
    "PRESENT",
    "HASH",
    "PROFILE_LABEL",
    "IDENTITY_PROOF",
    "AUTH_RESULT",
    "QUOTA_RESULT",
    "REDACTED",
)


def _row(account: dict[str, Any], path_rows: list[dict[str, Any]], labels: tuple[str, ...]) -> dict[str, Any]:
    match = next((p for p in path_rows if p.get("PROFILE_LABEL") in labels), {})
    quota = account.get("QUOTA_RESULT")
    if not isinstance(quota, dict):
        quota = {}
    out = {
        "PATH": account.get("PATH") or match.get("PATH"),
        "PRESENT": account.get("PRESENT") if "PRESENT" in account else match.get("PRESENT"),
        "HASH": account.get("HASH") if account.get("HASH") is not None else match.get("HASH"),
        "PROFILE_LABEL": account.get("PROFILE_LABEL") or match.get("PROFILE_LABEL") or account.get("account_id"),
        "IDENTITY_PROOF": account.get("IDENTITY_PROOF") or UNOBSERVED,
        "AUTH_RESULT": account.get("AUTH_RESULT") or account.get("status") or UNOBSERVED,
        "QUOTA_RESULT": quota,
        "REDACTED": True,
    }
    assert_no_secrets(out)
    extra = {k: out[k] for k in EVIDENCE_KEYS}
    return extra


def live_state_from_probe(probe: dict[str, Any]) -> dict[str, Any]:
    accounts = probe.get("accounts") or {}
    kag = accounts.get("KAGGLE_C1") or {}
    q = kag.get("QUOTA_RESULT") or {}
    lit = accounts.get("LIGHTNING_01") or {}
    lq = lit.get("QUOTA_RESULT") or {}
    modal = accounts.get("MODAL_01") or {}
    partner = accounts.get("KAGGLE_PARTNER") or {}
    oracle = accounts.get("ORACLE_01") or {}
    colab = accounts.get("COLAB_01") or {}
    probes = {
        "LOCAL_AG": {
            "account_id": "LOCAL_AG",
            "status": "REACHABLE",
            "ram_total_gb": 7.8,
            "ram_avail_gb": 0.4,
            "execution_blocked_by_memory": True,
            "c5": "SUCCESS",
        },
        "KAGGLE_C1": {
            "account_id": "KAGGLE_C1",
            "status": kag.get("AUTH_RESULT") or "AUTH_REQUIRED",
            "username_bound": kag.get("IDENTITY_PROOF"),
            "gpu_quota": q.get("gpu") or {},
            "tpu_quota": q.get("tpu") or {},
            "dataset_used_bytes": q.get("dataset_used_bytes"),
            "dataset_count": q.get("dataset_count"),
            "accelerator_types": q.get("accelerator_types") or [],
            "account_eligible_gpu": True,
            "active_session_gpu": bool(q.get("active_session_gpu")),
            "gpu_sku": UNOBSERVED,
            "gpu_vram": UNOBSERVED,
        },
        "MODAL_01": {
            "account_id": "MODAL_01",
            "status": modal.get("AUTH_RESULT") or "PARTIAL",
            "token_fields_present": True,
            "NO_RESOURCE_CREATED": True,
            "NO_GPU_STARTED": True,
            "gpu_entitlement": UNOBSERVED,
        },
        "KAGGLE_PARTNER": {
            "account_id": "KAGGLE_PARTNER",
            "status": partner.get("AUTH_RESULT") or "AUTH_REQUIRED",
            "live_auth_proven": bool(partner.get("live_auth_proven")),
            "distinct_from_c1": bool(partner.get("distinct_from_c1")),
            "copied_from_c1": bool(partner.get("copied_from_c1")),
            "isolated_from": "KAGGLE_C1",
        },
        "ORACLE_01": {"account_id": "ORACLE_01", "status": oracle.get("AUTH_RESULT") or "AUTH_REQUIRED"},
        "COLAB_01": {
            "account_id": "COLAB_01",
            "status": "AUTH_REQUIRED",
            "GOOGLE_AUTH": colab.get("GOOGLE_AUTH") or "ABSENT",
            "COLAB_ACCESS": colab.get("COLAB_ACCESS") or UNOBSERVED,
            "COLAB_GPU_ENTITLEMENT": UNOBSERVED,
        },
        "LIGHTNING_01": {
            "account_id": "LIGHTNING_01",
            "status": lit.get("AUTH_RESULT") or "PARTIAL",
            "credits_remaining": lq.get("credits_remaining"),
            "storage_used_bytes": lq.get("storage_used_bytes"),
            "free_storage_bytes": lq.get("free_storage_bytes"),
            "studio_count": lq.get("studio_count"),
            "account_eligible_gpu": False,
            "gpu_sku": UNOBSERVED,
            "gpu_vram": UNOBSERVED,
        },
        "NINEROUTER": {"provider_type": "MODEL_ROUTING_GATEWAY", "RESOURCE_AUTHORITY": False},
    }
    return {
        "auth": discover_auth(),
        "probes": probes,
        "observed_at": probe.get("observed_at"),
        "PAID_RESOURCE_CREATED": False,
        "GPU_SESSION_STARTED": False,
        "REDACTED": True,
    }


def world_from_probe(probe: dict[str, Any]) -> dict[str, Any]:
    world = collect_world()
    state = live_state_from_probe(probe)
    apply_live_overlay(world, state)
    world["live_state"] = state
    return world


def write_wave06_package(probe: dict[str, Any], dest: Path | None = None) -> dict[str, Any]:
    dest = dest or WAVE06_PACKAGE
    dest.mkdir(parents=True, exist_ok=True)
    world = world_from_probe(probe)
    accounts = probe.get("accounts") or {}
    paths = probe.get("paths") or []
    view = reservoir_view(world)
    gpu_burst = place(resource_request(workload_class="GPU_BURST", paid_allowed=False, request_id="W6-GPU"), world)
    batch = place(resource_request(workload_class="BATCH_CPU", request_id="W6-CPU"), world)
    store = place(resource_request(workload_class="MODEL_STORAGE", request_id="W6-STORE"), world)
    packed = evaluate_workload("DISCOVERY", world, request_id="W6-DISC")

    files: dict[str, Any] = {
        "KAGGLE-C1.json": _row(accounts.get("KAGGLE_C1") or {}, paths, ("KAGGLE_C1", "KAGGLE_C1_OAUTH", "KAGGLE_C1_JSON")),
        "KAGGLE-PARTNER.json": _row(accounts.get("KAGGLE_PARTNER") or {}, paths, ("KAGGLE_PARTNER", "KAGGLE_PARTNER_FILE", "KAGGLE_PARTNER_CANDIDATE_DIR")),
        "LIGHTNING.json": _row(accounts.get("LIGHTNING_01") or {}, paths, ("LIGHTNING_01",)),
        "MODAL.json": _row(accounts.get("MODAL_01") or {}, paths, ("MODAL_01",)),
        "ORACLE.json": _row(accounts.get("ORACLE_01") or {}, paths, ("ORACLE_01",)),
        "COLAB.json": _row(accounts.get("COLAB_01") or {}, paths, ("COLAB_01", "GOOGLE_ADC_ROAMING", "GOOGLE_ADC_CONFIG")),
        "ACCOUNT-BINDING-MATRIX.json": {
            "schema": "raios.wave06.account-binding-matrix.v1",
            "REDACTED": True,
            "RF_C5_12": "BLOCKED_BY_GOVERNED_CHANNEL",
            "RESOURCE_FACTORY_REUSED": True,
            "SECOND_RESOURCE_REGISTRY_CREATED": False,
            "PAID_RESOURCE_CREATED": False,
            "GPU_SESSION_STARTED": False,
            "KAGGLE_QUOTAS_MERGED": False,
            "accounts": {
                aid: {
                    "AUTH_RESULT": (accounts.get(aid) or {}).get("AUTH_RESULT"),
                    "IDENTITY_PROOF": (accounts.get(aid) or {}).get("IDENTITY_PROOF"),
                    "authenticated_for_dispatch": aid in (view.get("currently_schedulable") or []),
                    "REDACTED": True,
                }
                for aid in ("KAGGLE_C1", "KAGGLE_PARTNER", "LIGHTNING_01", "MODAL_01", "ORACLE_01", "COLAB_01", "LOCAL_AG")
            },
        },
        "FAILOVER-MATRIX.json": {
            "GPU_PRIMARY": (view.get("gpu_pool") or {}).get("current_primary"),
            "GPU_FAILOVER_1": (view.get("gpu_pool") or {}).get("failover"),
            "GPU_FAILOVER_2": "NONE_PROVEN",
            "REMOTE_CPU_PRIMARY": (view.get("cpu_pool") or {}).get("remote_primary"),
            "REMOTE_CPU_FAILOVER": (view.get("cpu_pool") or {}).get("failover"),
            "MODEL_STORAGE_PRIMARY": (view.get("storage_pool") or {}).get("primary_model_storage_candidate"),
            "MODEL_STORAGE_BACKUP": (view.get("storage_pool") or {}).get("backup_model_storage"),
            "PERSISTENT_CONTROL_PRIMARY": (view.get("persistent_control") or {}).get("primary"),
            "PERSISTENT_CONTROL_FAILOVER": (view.get("persistent_control") or {}).get("failover"),
            "gpu_failover_proven": bool((view.get("gpu_pool") or {}).get("failover_proven")),
            "UNPROVEN_NE_FAILOVER": True,
            "PAID_GPU_NE_UNPAID_FAILOVER": True,
            "REDACTED": True,
        },
        "COST-CREDIT-MATRIX.json": {
            "KAGGLE_C1_GPU_REMAINING_HOURS": ((accounts.get("KAGGLE_C1") or {}).get("QUOTA_RESULT") or {}).get("gpu", {}).get("remaining"),
            "LIGHTNING_CREDITS_REMAINING": ((accounts.get("LIGHTNING_01") or {}).get("QUOTA_RESULT") or {}).get("credits_remaining"),
            "MODAL_CREDITS": UNOBSERVED,
            "ORACLE_FREE_TIER": UNOBSERVED,
            "CREDIT_NE_CASH": True,
            "CATALOG_NE_ENTITLEMENT": True,
            "PAID_RESOURCE_CREATED": False,
            "REDACTED": True,
        },
        "USER-ACTION-QUEUE.json": probe.get("USER_ACTION_QUEUE") or [],
        "PLACEMENT-PROOFS.json": {
            "GPU_BURST": {
                "selected": gpu_burst.get("selected_resource"),
                "result_class": gpu_burst.get("result_class"),
                "gpu_failover": gpu_burst.get("gpu_failover"),
                "dispatch_allowed": gpu_burst.get("dispatch_allowed"),
            },
            "BATCH_CPU": {
                "selected": batch.get("selected_resource"),
                "result_class": batch.get("result_class"),
                "eligible": batch.get("eligible_resources"),
            },
            "MODEL_STORAGE": {"selected": store.get("selected_resource"), "result_class": store.get("result_class")},
            "DISCOVERY": {
                "GPU_SESSION_STARTED": packed["decision"]["GPU_SESSION_STARTED"],
                "gpu_required": packed["request"]["gpu_required"],
            },
            "currently_schedulable": view.get("currently_schedulable"),
            "kaggle_partner_dispatch_allowed": view.get("kaggle_partner_dispatch_allowed"),
            "RF_C5_12": "BLOCKED_BY_GOVERNED_CHANNEL",
            "REDACTED": True,
        },
    }
    files["ACCOUNT-BINDING-MATRIX.json"]["LOCAL_AG"] = {"AUTH_RESULT": "REACHABLE", "REDACTED": True}
    written = []
    for name, payload in files.items():
        payload = mask_record(payload)
        assert_no_secrets(payload)
        (dest / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(name)
    return {"PACKAGE": str(dest), "FILES": written, "view": view}
