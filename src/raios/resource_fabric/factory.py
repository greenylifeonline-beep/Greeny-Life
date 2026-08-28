"""Executable Resource Factory: placement + dry-run dispatch.

Composes existing census/live/placement/cost plus V9 job ledger, command-fabric
leases, TASKS.json, and receipts. Not a second scheduler, registry, or lease store.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .placement import MODEL_WEIGHTS_LOCAL, decide, placement_request
from .schema import (
    EXISTING_JOB_LEDGER,
    EXISTING_LEASE_SYSTEM,
    EXISTING_NOMADIC_CONTRACT,
    EXISTING_RECEIPT_ROOT,
    EXISTING_TASK_REGISTRY,
    UNKNOWN,
    UNOBSERVED,
    is_unknown,
    numeric_or_unknown,
    resource_lease,
)

SCHEMA = "raios.resource-factory.v1"
POLICY_VERSION = "wave06-closure.v1"
EXISTING_SCHEDULER = "RAIOS/V9/cloud/nomadic/work_stealing_scheduler.py"
EXISTING_LEASE_ADAPTER = "src/raios/command_fabric/lease.py"
EXISTING_RECEIPT_MODULE = "src/raios/c1c5/receipts.py"

WORKLOAD_CLASSES = (
    "CONTROL",
    "DISCOVERY",
    "TEST_LIGHT",
    "BATCH_CPU",
    "GPU_BURST",
    "MODEL_STORAGE",
    "MODEL_FACTORY",
    "LONG_RUNNING_SERVICE",
)

AUTH_DISPATCH_OK = frozenset({"REACHABLE", "REACHABLE_CREDENTIAL_PRESENT"})
LOCAL_AUTH_OK = frozenset({"REACHABLE", "REACHABLE_CREDENTIAL_PRESENT", "DECLARED", "PARTIAL"})
CATALOG_GPU_CLASSES = frozenset({"CATALOG_GPU", None, ""})

PLACEMENT_ENGINE = "raios.resource_fabric.placement.decide"
PROVIDER_REGISTRY = "raios.resource_fabric.adapters.ADAPTERS"

DEFAULT_POLICY: dict[str, Any] = {
    "schema": "raios.resource-placement-policy.v1",
    "version": POLICY_VERSION,
    "decision_order": [
        "AUTHORITY",
        "SAFETY",
        "RESOURCE_FIT",
        "FREE_QUOTA",
        "WARM_ASSET_AFFINITY",
        "LATENCY",
        "FAILOVER",
        "PAID_COST",
    ],
    "hard_rules": [
        "DO_NOT_SCHEDULE_ON_UNAUTHENTICATED_ACCOUNT",
        "DO_NOT_ASSUME_UNOBSERVED_CAPACITY",
        "DO_NOT_START_GPU_FOR_DISCOVERY",
        "DO_NOT_USE_PAID_GPU_WITHOUT_C1_AUTHORIZATION",
        "DO_NOT_STORE_MODEL_WEIGHTS_ON_LOCAL_AG",
        "DO_NOT_LOAD_HEAVY_MODELS_ON_LOCAL_AG_UNDER_CURRENT_RAM",
        "DO_NOT_MERGE_KAGGLE_C1_AND_PARTNER_QUOTAS",
        "DO_NOT_TREAT_AT_LEAST_ONCE_AS_EXACTLY_ONCE",
        "UNOBSERVED_CAPACITY_NE_ABSENT_CAPACITY",
        "CATALOG_CAPABILITY_NE_OWNED_ENTITLEMENT",
    ],
    "local_ag": {"max_class": "LIGHTWEIGHT", "heavy_inference": "DENY", "reason": "RAM_PRESSURE"},
    "gpu": {"current_primary": "KAGGLE_C1", "failover": "NONE_PROVEN", "source": "PROVEN_CAPACITY"},
    "remote_cpu": {"primary": "MODAL_01", "secondary": "KAGGLE_C1", "tertiary": "LIGHTNING_01", "source": "PROVEN_CAPACITY"},
    "model_storage": {"primary_candidate": "KAGGLE_C1", "backup": "UNPROVEN", "source": "PROVEN_CAPACITY"},
    "persistent_control": {"primary": "LOCAL_AG", "failover": "LIGHTNING_01", "source": "PROVEN_CAPACITY"},
    "paid_policy": {"default": "DENY", "override_authority": "C1"},
    "workload_classes": {
        "CONTROL": {"gpu": False, "preferred": ["LOCAL_AG"], "latency": "LOW"},
        "DISCOVERY": {"gpu": False, "preferred": ["LOCAL_AG", "MODAL_01"], "must_not_start_gpu": True},
        "TEST_LIGHT": {"gpu": False, "preferred": ["LOCAL_AG", "MODAL_01"]},
        "BATCH_CPU": {"gpu": False, "preferred": ["MODAL_01", "KAGGLE_C1"]},
        "GPU_BURST": {"gpu": True, "preferred": ["KAGGLE_C1"]},
        "MODEL_STORAGE": {
            "gpu": False,
            "preferred": ["KAGGLE_C1"],
            "prohibited": ["LOCAL_AG"],
            "persistence": True,
        },
        "MODEL_FACTORY": {"gpu": True, "preferred": ["KAGGLE_C1"], "failover": "NONE_PROVEN"},
        "LONG_RUNNING_SERVICE": {"gpu": False, "preferred": ["LOCAL_AG"], "persistence": True},
    },
    "warm_asset_affinity": {
        "KAGGLE_C1": ["MODEL_STORAGE", "MODEL_FACTORY", "GPU_BURST"],
        "MODAL_01": ["REMOTE_CPU", "SHORT_SERVERLESS_JOB", "BATCH_CPU", "TEST_LIGHT", "DISCOVERY"],
        "LIGHTNING_01": ["BATCH_CPU", "LONG_RUNNING_SERVICE"],
        "LOCAL_AG": ["CONTROL", "ROUTING", "STATE", "POLICY", "LONG_RUNNING_SERVICE", "DISCOVERY", "TEST_LIGHT"],
    },
    "failover": {
        "CONTROL": ["LOCAL_AG", "LIGHTNING_01"],
        "GPU": ["KAGGLE_C1"],
        "REMOTE_CPU": ["MODAL_01", "KAGGLE_C1", "LIGHTNING_01"],
        "PERSISTENT_STORAGE": ["KAGGLE_C1"],
        "PERSISTENT_CONTROL": ["LOCAL_AG", "LIGHTNING_01"],
    },
    "kaggle_quota_isolation": {"KAGGLE_C1": "KAGGLE_C1", "KAGGLE_PARTNER": "KAGGLE_PARTNER"},
}

PAID_GPU_ACCOUNTS = frozenset({"MODAL_01", "ORACLE_01", "LIGHTNING_01"})
BLOCKED_C1_ACCOUNTS = frozenset({"KAGGLE_PARTNER", "ORACLE_01", "COLAB_01"})
C1_ACTION_QUEUE: tuple[dict[str, Any], ...] = (
    {
        "id": "UA-KAGGLE-PARTNER-CLI-TOKEN",
        "account_id": "KAGGLE_PARTNER",
        "classification": "BLOCKED_C1_ACTION",
        "action": "Export a distinct Kaggle API token for the partner account into an isolated directory that is not %USERPROFILE%\\.kaggle. Do not copy C1 credentials. Then set KAGGLE_CONFIG_DIR_B to that directory.",
        "authority": "C1",
        "do_not_repeat_probe": True,
    },
    {
        "id": "UA-ORACLE-OCI-SETUP",
        "account_id": "ORACLE_01",
        "classification": "BLOCKED_C1_ACTION",
        "action": "If an Oracle Cloud account already exists, run official `oci setup config` locally. Do not create a VM, volume, bucket, database, GPU, or other paid cloud resource.",
        "authority": "C1",
        "do_not_repeat_probe": True,
    },
    {
        "id": "UA-COLAB-BROWSER-GPU-MENU",
        "account_id": "COLAB_01",
        "classification": "BLOCKED_C1_ACTION",
        "action": "In the intended Google account, open https://colab.research.google.com , create no runtime, and confirm whether a GPU runtime class is listed. Do not start GPU. Do not create a Google Cloud project or billing account.",
        "authority": "C1",
        "do_not_repeat_probe": True,
    },
)
CLOUD_ACCOUNTS = (
    "LOCAL_AG",
    "KAGGLE_C1",
    "KAGGLE_PARTNER",
    "MODAL_01",
    "LIGHTNING_01",
    "ORACLE_01",
    "COLAB_01",
)


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _digest(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


def _accounts(world: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {a["account_id"]: a for a in world.get("accounts") or [] if a.get("account_id")}


def _probes(world: dict[str, Any]) -> dict[str, dict[str, Any]]:
    live = world.get("live_state") or {}
    probes = live.get("probes") if isinstance(live, dict) else {}
    return probes if isinstance(probes, dict) else {}


def _account_row(world: dict[str, Any], account_id: str) -> dict[str, Any]:
    return _accounts(world).get(account_id) or {}


def resource_request(**kw: Any) -> dict[str, Any]:
    """Canonical ResourceRequest. Extra fields overlay Wave-01 placement_request."""
    workload = str(kw.get("workload_class") or kw.get("task_type") or "CONTROL").upper()
    if workload not in WORKLOAD_CLASSES:
        workload = "CONTROL"
    class_pol = DEFAULT_POLICY["workload_classes"][workload]
    gpu_required = bool(kw["gpu_required"]) if "gpu_required" in kw else bool(class_pol.get("gpu"))
    preferred = list(kw.get("preferred_resources") or class_pol.get("preferred") or [])
    prohibited = list(kw.get("prohibited_resources") or class_pol.get("prohibited") or [])
    persistence = bool(kw["persistence_required"]) if "persistence_required" in kw else bool(class_pol.get("persistence"))
    paid_allowed = bool(kw.get("paid_allowed", False))
    request_id = str(kw.get("request_id") or "")
    body = {
        "schema": SCHEMA,
        "kind": "ResourceRequest",
        "request_id": request_id,
        "workload_class": workload,
        "task_type": str(kw.get("task_type") or workload),
        "cpu_requirement": kw.get("cpu_requirement", UNKNOWN),
        "ram_requirement_gb": kw.get("ram_requirement_gb", kw.get("min_ram_gb", UNKNOWN)),
        "gpu_required": gpu_required,
        "gpu_vram_min_gb": kw.get("gpu_vram_min_gb", kw.get("min_gpu_vram_gb", UNKNOWN)),
        "persistence_required": persistence,
        "storage_required_gb": kw.get("storage_required_gb", UNKNOWN),
        "expected_duration": kw.get("expected_duration", UNKNOWN),
        "latency_class": kw.get("latency_class", class_pol.get("latency", UNKNOWN)),
        "cost_policy": kw.get("cost_policy", "FREE_DEFAULT"),
        "paid_allowed": paid_allowed,
        "preferred_resources": preferred,
        "prohibited_resources": prohibited,
        "warm_assets": list(kw.get("warm_assets") or []),
        "data_locality": kw.get("data_locality", UNKNOWN),
        "model_id": kw.get("model_id", UNKNOWN),
        "risk_class": kw.get("risk_class", UNKNOWN),
        "authority_context": kw.get("authority_context", UNKNOWN),
        "heavy_inference": bool(kw.get("heavy_inference", False)),
        "local_model_storage_prohibited": True,
        "MODEL_WEIGHTS_LOCAL": MODEL_WEIGHTS_LOCAL,
    }
    fit = placement_request(
        requires_gpu=gpu_required,
        min_gpu_vram_gb=body["gpu_vram_min_gb"],
        min_ram_gb=body["ram_requirement_gb"],
        storage_required_gb=body["storage_required_gb"],
        persistent_output=persistence,
        preferred_capabilities=list(kw.get("preferred_capabilities") or []),
    )
    body["placement_fit"] = fit
    if not body["request_id"]:
        body["request_id"] = "RR-" + _digest({k: body[k] for k in body if k != "request_id"})[:16]
    return body


def _c1_paid_override(req: dict[str, Any]) -> bool:
    auth = str(req.get("authority_context") or "").upper()
    return bool(req.get("paid_allowed")) and auth == "C1"


def _needs_c1_for_paid(req: dict[str, Any]) -> bool:
    return bool(req.get("paid_allowed")) and str(req.get("authority_context") or "").upper() != "C1"


def _is_catalog_gpu(gpu: dict[str, Any]) -> bool:
    kind = gpu.get("observation_kind")
    gclass = gpu.get("gpu_class")
    if kind == "LIVE":
        return False
    if gclass in {"ACCOUNT_ELIGIBLE_GPU", "ACTIVE_SESSION_GPU", "CURRENT_ALLOCATABLE_GPU"}:
        return False
    return kind == "CATALOG" or gclass in CATALOG_GPU_CLASSES or kind is None


def _live_gpus(world: dict[str, Any], account_id: str) -> list[dict[str, Any]]:
    return [
        g
        for g in world.get("accelerators") or []
        if g.get("account_id") == account_id and not _is_catalog_gpu(g)
    ]


def _catalog_gpus(world: dict[str, Any], account_id: str) -> list[dict[str, Any]]:
    return [
        g
        for g in world.get("accelerators") or []
        if g.get("account_id") == account_id and _is_catalog_gpu(g)
    ]


def _live_vram(world: dict[str, Any], account_id: str) -> Any:
    observed: list[float] = []
    for gpu in _live_gpus(world, account_id):
        n = numeric_or_unknown(gpu.get("gpu_vram_gb"))
        if n is not UNKNOWN:
            observed.append(float(n))
    if observed:
        return max(observed)
    return UNOBSERVED


def _live_sku(world: dict[str, Any], account_id: str) -> Any:
    for gpu in _live_gpus(world, account_id):
        model = gpu.get("gpu_model")
        if model not in (None, "", UNKNOWN, UNOBSERVED):
            return model
    return UNOBSERVED


def _gpu_eligible(world: dict[str, Any], account_id: str) -> bool:
    probes = _probes(world)
    rec = probes.get(account_id) or {}
    if rec.get("account_eligible_gpu") is True:
        return True
    for gpu in _live_gpus(world, account_id):
        if gpu.get("available") is True:
            return True
        if gpu.get("gpu_class") == "ACCOUNT_ELIGIBLE_GPU":
            return True
    return False


def _local_ram(world: dict[str, Any]) -> tuple[Any, Any]:
    probes = _probes(world)
    loc = probes.get("LOCAL_AG") or {}
    total = numeric_or_unknown(loc.get("ram_total_gb"))
    avail = numeric_or_unknown(loc.get("ram_avail_gb"))
    if total is UNKNOWN or avail is UNKNOWN:
        for cmp in world.get("compute") or []:
            if cmp.get("account_id") != "LOCAL_AG":
                continue
            if total is UNKNOWN:
                total = numeric_or_unknown(cmp.get("ram_gb"))
            if avail is UNKNOWN:
                avail = numeric_or_unknown(cmp.get("ram_avail_gb"))
    return total, avail


def _partner_dispatch_ok(world: dict[str, Any]) -> bool:
    rec = _probes(world).get("KAGGLE_PARTNER") or {}
    acc = _account_row(world, "KAGGLE_PARTNER")
    proven = bool(acc.get("live_auth_proven") or rec.get("live_auth_proven"))
    distinct = bool(acc.get("distinct_from_c1") or rec.get("distinct_from_c1"))
    copied = bool(acc.get("copied_from_c1") or rec.get("copied_from_c1"))
    return proven and distinct and not copied


def _auth_state(world: dict[str, Any], account_id: str) -> str:
    acc = _account_row(world, account_id)
    status = str(acc.get("status") or UNKNOWN)
    probes = _probes(world)
    rec = probes.get(account_id) or {}
    if rec.get("status") in {
        "REACHABLE",
        "REACHABLE_CREDENTIAL_PRESENT",
        "AUTH_REQUIRED",
        "PARTIAL",
        "SEPARATE_PROFILE_CANDIDATE_PRESENT",
        "NOT_DISTINCT_FROM_C1",
        "BLOCKED_C1_ACTION",
    }:
        status = str(rec.get("status") or status)
    if account_id == "KAGGLE_PARTNER" and _partner_dispatch_ok(world) and status in AUTH_DISPATCH_OK:
        return status
    if account_id in BLOCKED_C1_ACCOUNTS:
        return "BLOCKED_C1_ACTION"
    if account_id == "LIGHTNING_01" and status not in AUTH_DISPATCH_OK:
        return "CURRENT_LIVE_AUTH_NOT_REPROVEN"
    return status


def _authenticated(world: dict[str, Any], account_id: str) -> bool:
    state = _auth_state(world, account_id)
    rec = _probes(world).get(account_id) or {}
    acc = _account_row(world, account_id)
    if account_id == "LOCAL_AG":
        return state in LOCAL_AUTH_OK or state == "REACHABLE"
    if account_id == "KAGGLE_PARTNER":
        if not _partner_dispatch_ok(world):
            return False
        return state in AUTH_DISPATCH_OK
    if account_id in BLOCKED_C1_ACCOUNTS:
        return False
    return state in AUTH_DISPATCH_OK


def _is_paid_gpu_account(account_id: str) -> bool:
    return account_id in PAID_GPU_ACCOUNTS


def _quota_account(account_id: str) -> str:
    return DEFAULT_POLICY["kaggle_quota_isolation"].get(account_id, account_id)


def _warm_bonus(account_id: str, workload: str) -> int:
    tags = DEFAULT_POLICY["warm_asset_affinity"].get(account_id) or []
    return 0 if workload in tags else 1


def _fit_world(world: dict[str, Any]) -> dict[str, Any]:
    """Catalog GPU VRAM is not live capacity; strip it before reuse of decide()."""
    gpus = []
    for gpu in world.get("accelerators") or []:
        row = dict(gpu)
        if _is_catalog_gpu(row):
            row["gpu_vram_gb"] = UNKNOWN
            row["CATALOG_NE_LIVE"] = True
        gpus.append(row)
    out = dict(world)
    out["accelerators"] = gpus
    return out


def _storage_ok(world: dict[str, Any], account_id: str, req: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    need = numeric_or_unknown(req.get("storage_required_gb"))
    stores = [s for s in world.get("storage") or [] if s.get("account_id") == account_id]
    if req.get("workload_class") == "MODEL_STORAGE" or req.get("model_id") not in (None, "", UNKNOWN):
        if account_id == "LOCAL_AG":
            return False, ["LOCAL_MODEL_STORAGE_PROHIBITED"]
        suitable = [s for s in stores if s.get("model_weights_suitable") or s.get("type") == "dataset_storage"]
        if not suitable and req.get("workload_class") == "MODEL_STORAGE":
            reasons.append("NO_MODEL_STORAGE")
            return False, reasons
    if need is not UNKNOWN:
        free_known = False
        for st in stores:
            free = numeric_or_unknown(st.get("capacity_free_gb"))
            if free is UNKNOWN:
                continue
            free_known = True
            if float(free) >= float(need):
                return True, []
        if not free_known:
            return True, ["STORAGE_CAPACITY_UNOBSERVED"]
        return False, ["STORAGE_SHORT"]
    return True, reasons


def evaluate_account(req: dict[str, Any], world: dict[str, Any], account_id: str) -> dict[str, Any]:
    reasons: list[str] = []
    conditional: list[str] = []
    auth = _auth_state(world, account_id)
    authenticated = _authenticated(world, account_id)
    paid_gpu = _is_paid_gpu_account(account_id) and bool(req.get("gpu_required"))
    c1_ok = _c1_paid_override(req)
    live_vram = _live_vram(world, account_id)
    live_sku = _live_sku(world, account_id)
    gpu_elig = _gpu_eligible(world, account_id)
    quota_account = _quota_account(account_id)

    if account_id in req.get("prohibited_resources") or []:
        reasons.append("PROHIBITED_BY_REQUEST")
    if not authenticated:
        reasons.append("UNAUTHENTICATED_RESOURCE")
        if auth == "BLOCKED_C1_ACTION":
            reasons.append("BLOCKED_C1_ACTION")
        elif auth == "GOOGLE_AUTH_SETUP_REQUIRED":
            reasons.append("GOOGLE_AUTH_SETUP_REQUIRED")
        elif auth == "LIVE_AUTH_UNPROVEN":
            reasons.append("KAGGLE_PARTNER_LIVE_AUTH_UNPROVEN")
        elif auth in {"AUTH_REQUIRED", "CURRENT_LIVE_AUTH_NOT_REPROVEN", "NOT_DISTINCT_FROM_C1"}:
            reasons.append(auth)
        if account_id == "COLAB_01":
            reasons.append("GOOGLE_AUTH_SETUP_REQUIRED")
    if req.get("workload_class") == "DISCOVERY" and req.get("gpu_required"):
        reasons.append("DISCOVERY_MUST_NOT_START_GPU")
    if account_id == "LOCAL_AG":
        if req.get("workload_class") == "MODEL_STORAGE" or (
            req.get("model_id") not in (None, "", UNKNOWN) and req.get("workload_class") in {"MODEL_STORAGE", "MODEL_FACTORY"}
        ):
            reasons.append("LOCAL_MODEL_STORAGE_PROHIBITED")
        heavy = bool(req.get("heavy_inference")) or req.get("workload_class") in {"GPU_BURST", "MODEL_FACTORY"}
        if heavy:
            reasons.append("LOCAL_AG_HEAVY_INFERENCE_DENIED")
            reasons.append("RAM_PRESSURE")
        total, avail = _local_ram(world)
        need = numeric_or_unknown(req.get("ram_requirement_gb"))
        if need is not UNKNOWN and avail is not UNKNOWN and float(avail) < float(need):
            reasons.append("LOCAL_RAM_SHORT")
        if avail is not UNKNOWN and float(avail) < 1.0 and req.get("workload_class") not in {"CONTROL", "DISCOVERY", "TEST_LIGHT", "LONG_RUNNING_SERVICE"}:
            if req.get("workload_class") in {"BATCH_CPU"}:
                reasons.append("LOCAL_RAM_PRESSURE_BATCH")
    store_ok, store_reasons = _storage_ok(world, account_id, req)
    reasons.extend(store_reasons)
    if req.get("gpu_required"):
        if account_id == "LOCAL_AG":
            reasons.append("LOCAL_AG_NO_GPU")
        elif paid_gpu and not c1_ok:
            reasons.append("PAID_GPU_DENIED")
            if _needs_c1_for_paid(req):
                reasons.append("C1_AUTH_REQUIRED")
            else:
                reasons.append("PAID_DEFAULT_DENY")
        elif not gpu_elig and not _catalog_gpus(world, account_id):
            reasons.append("NO_GPU_RESOURCE")
        elif not gpu_elig and _catalog_gpus(world, account_id):
            reasons.append("CATALOG_CAPABILITY_NE_ENTITLEMENT")
            conditional.append("CATALOG_ONLY")
        need_vram = numeric_or_unknown(req.get("gpu_vram_min_gb"))
        if need_vram is not UNKNOWN:
            if live_vram in (UNKNOWN, UNOBSERVED) or is_unknown(live_vram):
                conditional.append("VRAM_UNOBSERVED")
                conditional.append("CAPACITY_PROBE_REQUIRED")
            elif float(live_vram) < float(need_vram):
                reasons.append("VRAM_SHORT")
        elif gpu_elig and (live_vram in (UNKNOWN, UNOBSERVED) or is_unknown(live_vram)):
            conditional.append("LIVE_VRAM_UNOBSERVED")
        if live_sku in (UNKNOWN, UNOBSERVED) or is_unknown(live_sku):
            conditional.append("LIVE_SKU_UNOBSERVED")
    if paid_gpu and not req.get("gpu_required") and not c1_ok:
        pass
    hard = [r for r in reasons if r]
    eligible = not hard
    dispatch_allowed = eligible and authenticated and "CAPACITY_PROBE_REQUIRED" not in conditional
    if req.get("gpu_required") and "CAPACITY_PROBE_REQUIRED" in conditional:
        dispatch_allowed = False
        eligible = False
    cost_class = "UNPAID_OR_QUOTA"
    if paid_gpu:
        cost_class = "PAID_CATALOG" if not c1_ok else "PAID_C1_OVERRIDE"
    elif account_id == "MODAL_01":
        cost_class = "SERVERLESS_UNACTIVATED"
    elif account_id == "LOCAL_AG":
        cost_class = "LOCAL_SUNK"
    cap_conf = "UNOBSERVED"
    if req.get("gpu_required"):
        if live_vram not in (UNKNOWN, UNOBSERVED) and not is_unknown(live_vram):
            cap_conf = "LIVE"
        elif gpu_elig:
            cap_conf = "ELIGIBLE_VRAM_UNOBSERVED"
        else:
            cap_conf = "CATALOG_OR_ABSENT"
    elif account_id == "LOCAL_AG":
        _t, avail = _local_ram(world)
        cap_conf = "LIVE" if avail not in (UNKNOWN, UNOBSERVED) and not is_unknown(avail) else "UNOBSERVED"
    return {
        "account_id": account_id,
        "auth_state": auth,
        "authenticated": authenticated,
        "eligible": eligible and authenticated and "CAPACITY_PROBE_REQUIRED" not in conditional,
        "conditional": bool(conditional) and authenticated and not hard,
        "rejected": bool(hard) or not authenticated,
        "dispatch_allowed": bool(dispatch_allowed and authenticated and not hard),
        "reasons": sorted(set(hard)),
        "conditional_reasons": sorted(set(conditional)),
        "cost_class": cost_class,
        "capacity_confidence": cap_conf,
        "live_gpu_sku": live_sku,
        "live_gpu_vram": live_vram if live_vram not in (UNKNOWN,) else UNOBSERVED,
        "gpu_eligibility_proven": gpu_elig,
        "quota_account": quota_account,
        "KAGGLE_QUOTA_ISOLATED_FROM_C1": account_id == "KAGGLE_PARTNER",
        "warm_asset_affinity": [t for t in (DEFAULT_POLICY["warm_asset_affinity"].get(account_id) or []) if t == req.get("workload_class") or True][
            :3
        ],
        "warm_match": req.get("workload_class") in (DEFAULT_POLICY["warm_asset_affinity"].get(account_id) or []),
        "NINEROUTER_IS_RESOURCE_AUTHORITY": False,
        "CATALOG_NE_ENTITLEMENT": True,
        "UNOBSERVED_NE_ABSENT": True,
        "KAGGLE_C1_QUOTA_NE_PARTNER": quota_account == account_id,
    }


def _rank(rows: list[dict[str, Any]], req: dict[str, Any]) -> list[dict[str, Any]]:
    preferred = list(req.get("preferred_resources") or [])

    def key(row: dict[str, Any]) -> tuple:
        aid = row["account_id"]
        try:
            pref = preferred.index(aid)
        except ValueError:
            pref = 100
        selectable = 0 if (row.get("eligible") or row.get("conditional")) else 1
        rejected = 0 if not row.get("rejected") else 1
        dispatch = 0 if row.get("dispatch_allowed") else 1
        warm = 0 if row.get("warm_match") else 1
        cond = 0 if row.get("eligible") else 1
        return (rejected, selectable, dispatch, pref, warm, cond, aid)

    return sorted(rows, key=key)


def _failover_order(req: dict[str, Any]) -> list[str]:
    wl = req.get("workload_class")
    if wl in {"GPU_BURST", "MODEL_FACTORY"}:
        chain = list(DEFAULT_POLICY["failover"]["GPU"])
        return chain
    if wl == "MODEL_STORAGE":
        return list(DEFAULT_POLICY["failover"]["PERSISTENT_STORAGE"])
    if wl in {"BATCH_CPU", "DISCOVERY", "TEST_LIGHT"}:
        return list(DEFAULT_POLICY["failover"]["REMOTE_CPU"])
    return list(DEFAULT_POLICY["failover"]["CONTROL"])


def _result_class(
    *,
    selected: dict[str, Any] | None,
    ranked: list[dict[str, Any]],
    req: dict[str, Any],
) -> str:
    if _needs_c1_for_paid(req) and req.get("gpu_required") and not any(r.get("dispatch_allowed") for r in ranked):
        if any("C1_AUTH_REQUIRED" in (r.get("reasons") or []) or "PAID_GPU_DENIED" in (r.get("reasons") or []) for r in ranked):
            return "C1_AUTH_REQUIRED"
    if selected and selected.get("conditional") and "CAPACITY_PROBE_REQUIRED" in (selected.get("conditional_reasons") or []):
        return "CAPACITY_PROBE_REQUIRED"
    if any("CAPACITY_PROBE_REQUIRED" in (r.get("conditional_reasons") or []) for r in ranked) and not any(
        r.get("dispatch_allowed") for r in ranked
    ):
        return "CAPACITY_PROBE_REQUIRED"
    if selected and selected.get("dispatch_allowed"):
        return "PLACED"
    if selected and selected.get("conditional"):
        return "CONDITIONAL"
    if _needs_c1_for_paid(req) and not any(r.get("dispatch_allowed") for r in ranked):
        return "C1_AUTH_REQUIRED"
    return "NO_ELIGIBLE_RESOURCE"


def place(req: dict[str, Any], world: dict[str, Any], *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or DEFAULT_POLICY
    if req.get("kind") != "ResourceRequest":
        req = resource_request(**req)
    fit_world = _fit_world(world)
    fit_decision = decide(req.get("placement_fit") or placement_request(), fit_world)
    rows = [evaluate_account(req, world, aid) for aid in CLOUD_ACCOUNTS if aid in _accounts(world) or aid == "LOCAL_AG"]
    if "LOCAL_AG" not in {r["account_id"] for r in rows} and "LOCAL_AG" in _accounts(world):
        rows.append(evaluate_account(req, world, "LOCAL_AG"))
    ranked = _rank(rows, req)
    selected = next((r for r in ranked if r.get("dispatch_allowed")), None)
    if selected is None:
        selected = next((r for r in ranked if r.get("conditional")), None)
    result = _result_class(selected=selected, ranked=ranked, req=req)
    eligible = [r["account_id"] for r in ranked if r.get("eligible") or r.get("dispatch_allowed")]
    rejected = [{"account_id": r["account_id"], "reasons": r["reasons"], "auth_state": r["auth_state"]} for r in ranked if r.get("rejected")]
    conditional = [
        {"account_id": r["account_id"], "reasons": r["conditional_reasons"], "auth_state": r["auth_state"]}
        for r in ranked
        if r.get("conditional")
    ]
    probe = result == "CAPACITY_PROBE_REQUIRED" or (selected is not None and "CAPACITY_PROBE_REQUIRED" in (selected.get("conditional_reasons") or []))
    c1_req = result == "C1_AUTH_REQUIRED" or _needs_c1_for_paid(req)
    snapshot = {
        "request": {
            k: req[k]
            for k in (
                "request_id",
                "workload_class",
                "task_type",
                "cpu_requirement",
                "ram_requirement_gb",
                "gpu_required",
                "gpu_vram_min_gb",
                "persistence_required",
                "storage_required_gb",
                "paid_allowed",
                "preferred_resources",
                "prohibited_resources",
                "authority_context",
                "heavy_inference",
                "model_id",
            )
        },
        "auth": {aid: _auth_state(world, aid) for aid in CLOUD_ACCOUNTS},
        "vram": {aid: _live_vram(world, aid) for aid in CLOUD_ACCOUNTS},
        "policy": policy.get("version"),
    }
    decision_id = "PD-" + _digest(snapshot)[:20]
    selected_id = selected["account_id"] if selected else None
    reason = "NO_ELIGIBLE_RESOURCE"
    if selected:
        if result == "CAPACITY_PROBE_REQUIRED":
            reason = "LIVE_VRAM_UNOBSERVED_CAPACITY_PROBE_REQUIRED"
        elif result == "PLACED":
            reason = "POLICY_AND_LIVE_STATE"
        elif result == "CONDITIONAL":
            reason = "CONDITIONAL_LIVE_STATE"
        else:
            reason = result
    elif result == "C1_AUTH_REQUIRED":
        reason = "PAID_RESOURCE_REQUIRES_C1"
    failover = [a for a in _failover_order(req) if a != selected_id]
    if req.get("workload_class") in {"GPU_BURST", "MODEL_FACTORY"}:
        failover_proven = False
        gpu_failover = "NONE_PROVEN"
    else:
        failover_proven = False
        gpu_failover = policy["gpu"]["failover"]
    out = {
        "schema": SCHEMA,
        "kind": "PlacementDecision",
        "decision_id": decision_id,
        "request_id": req.get("request_id"),
        "result_class": result,
        "selected_resource": selected_id,
        "eligible_resources": eligible,
        "rejected_resources": rejected,
        "conditional_resources": conditional,
        "ranking": [{"account_id": r["account_id"], "dispatch_allowed": r["dispatch_allowed"], "reasons": r["reasons"] or r["conditional_reasons"]} for r in ranked],
        "evaluations": ranked,
        "decision_reason": reason,
        "cost_class": (selected or {}).get("cost_class", UNKNOWN),
        "auth_state": (selected or {}).get("auth_state", UNKNOWN),
        "capacity_confidence": (selected or {}).get("capacity_confidence", UNOBSERVED),
        "warm_asset_affinity": (selected or {}).get("warm_asset_affinity") or [],
        "failover_order": ([selected_id] if selected_id else []) + failover,
        "gpu_failover": gpu_failover,
        "gpu_failover_proven": failover_proven,
        "requires_capacity_probe": probe,
        "requires_c1_authorization": c1_req,
        "dispatch_allowed": bool(selected and selected.get("dispatch_allowed") and result == "PLACED"),
        "fit_engine": PLACEMENT_ENGINE,
        "fit_decision_kind": fit_decision.get("kind"),
        "provider_registry": PROVIDER_REGISTRY,
        "SECOND_PROVIDER_REGISTRY": False,
        "SECOND_SCHEDULER": False,
        "NINEROUTER_IS_RESOURCE_AUTHORITY": False,
        "MUTATION": False,
        "PAID_ACTIVATION": False,
        "GPU_SESSION_STARTED": False,
        "UNOBSERVED_NE_ABSENT": True,
        "policy_version": policy.get("version"),
    }
    return out


def plan_dispatch(decision: dict[str, Any], req: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
    """Map a placement decision onto existing job/lease/receipt/scheduler references.

    DRY_RUN never enqueues the V9 job ledger, never acquires a command-fabric lease,
    never writes a receipt, never starts GPU, and never creates paid resources.
    """
    if dry_run is not True:
        raise ValueError("LIVE_DISPATCH_NOT_IN_WAVE05")
    idem_src = {
        "decision_id": decision.get("decision_id"),
        "request_id": req.get("request_id") or decision.get("request_id"),
        "selected": decision.get("selected_resource"),
        "workload": req.get("workload_class"),
    }
    idem = "rf-" + _digest(idem_src)[:24]
    job_id = f"JOB-{idem}"
    lease_id = f"PLANNED-{idem}"
    selected = decision.get("selected_resource") or UNKNOWN
    allowed = bool(decision.get("dispatch_allowed") and dry_run)
    mode = "DRY_RUN" if dry_run else "LIVE"
    if not allowed:
        mode = "DRY_RUN_BLOCKED"
    lease = resource_lease(
        lease_id=lease_id,
        resource_id=str(selected),
        account_id=str(selected),
        owner_identity="C2-KAGGLE-CONTROL",
        state="PLANNED",
    )
    lease["acquired"] = False
    lease["adapter"] = EXISTING_LEASE_ADAPTER
    envelope = {
        "schema": SCHEMA,
        "kind": "DispatchPlan",
        "DRY_RUN": True,
        "dispatch_mode": mode,
        "dispatch_allowed": allowed,
        "PROVIDER_MUTATION": False,
        "GPU_SESSION_STARTED": False,
        "PAID_RESOURCE_CREATED": False,
        "MODEL_TRANSFER_EXECUTED": False,
        "provider_account": selected,
        "job": {
            "job_id": job_id,
            "op": f"resource_fabric.{req.get('workload_class')}",
            "ledger": EXISTING_JOB_LEDGER,
            "enqueued": False,
            "status": "PLANNED" if allowed else "BLOCKED",
        },
        "task_registry": EXISTING_TASK_REGISTRY,
        "lease": lease,
        "lease_system": EXISTING_LEASE_SYSTEM,
        "receipt": {
            "root": EXISTING_RECEIPT_ROOT,
            "module": EXISTING_RECEIPT_MODULE,
            "written": False,
            "idempotency_key": idem,
            "EXACTLY_ONCE_CLAIMED": False,
        },
        "scheduler": EXISTING_SCHEDULER,
        "nomadic_contract": EXISTING_NOMADIC_CONTRACT,
        "authority_context": req.get("authority_context"),
        "idempotency_key": idem,
        "resource_requirements": {
            "gpu_required": req.get("gpu_required"),
            "gpu_vram_min_gb": req.get("gpu_vram_min_gb"),
            "ram_requirement_gb": req.get("ram_requirement_gb"),
            "persistence_required": req.get("persistence_required"),
        },
        "cost_policy": {
            "paid_allowed": req.get("paid_allowed"),
            "cost_class": decision.get("cost_class"),
            "default": "DENY_PAID",
        },
        "fallback_chain": decision.get("failover_order") or [],
        "decision_id": decision.get("decision_id"),
        "request_id": req.get("request_id") or decision.get("request_id"),
        "SECOND_JOB_LEDGER": False,
        "SECOND_SCHEDULER": False,
        "SECOND_LEASE_SYSTEM": False,
        "SECOND_RECEIPT_SYSTEM": False,
        "SECOND_TASK_REGISTRY": False,
        "SECOND_PROVIDER_REGISTRY": False,
        "NINEROUTER_IS_RESOURCE_AUTHORITY": False,
    }
    return envelope


def reservoir_view(world: dict[str, Any], *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or DEFAULT_POLICY
    schedulable = [aid for aid in CLOUD_ACCOUNTS if aid in _accounts(world) and _authenticated(world, aid)]
    gpu_sched = [aid for aid in schedulable if _gpu_eligible(world, aid) and aid != "LOCAL_AG"]
    unpaid_gpu = [aid for aid in gpu_sched if aid not in PAID_GPU_ACCOUNTS]
    sku_known = [aid for aid in gpu_sched if _live_sku(world, aid) not in (UNKNOWN, UNOBSERVED) and not is_unknown(_live_sku(world, aid))]
    vram_known = [
        aid for aid in gpu_sched if _live_vram(world, aid) not in (UNKNOWN, UNOBSERVED) and not is_unknown(_live_vram(world, aid))
    ]
    cpu_pool = [aid for aid in schedulable]
    cpu_order = [aid for aid in ("MODAL_01", "KAGGLE_C1", "LIGHTNING_01") if aid in cpu_pool]
    lightning = _account_row(world, "LIGHTNING_01")
    lightning_probe = _probes(world).get("LIGHTNING_01") or {}
    studio_n = lightning_probe.get("studio_count")
    if studio_n is None:
        studio_n = lightning.get("studio_count")
    persistent_fo = "NONE_PROVEN"
    if "LIGHTNING_01" in schedulable and isinstance(studio_n, (int, float)) and int(studio_n) > 0:
        persistent_fo = "LIGHTNING_01"
    partner_ok = _authenticated(world, "KAGGLE_PARTNER")
    blocked = [aid for aid in ("KAGGLE_PARTNER", "ORACLE_01", "COLAB_01") if aid in _accounts(world) and not _authenticated(world, aid)]
    unproven_admitted = any(aid in schedulable for aid in BLOCKED_C1_ACCOUNTS)
    return {
        "schema": "raios.virtual-compute-reservoir.v1",
        "derived_from": "live_world",
        "wave04_policy_seed": True,
        "policy_version": policy.get("version"),
        "control_plane": {"primary": "LOCAL_AG", "router": "9ROUTER", "NINEROUTER_IS_RESOURCE_AUTHORITY": False},
        "currently_schedulable": schedulable,
        "gpu_pool": {
            "currently_schedulable": unpaid_gpu,
            "current_primary": unpaid_gpu[0] if unpaid_gpu else policy["gpu"]["current_primary"],
            "failover": "NONE_PROVEN" if len(unpaid_gpu) < 2 else unpaid_gpu[1:],
            "failover_proven": len(unpaid_gpu) >= 2,
            "live_gpu_sku_known": sku_known,
            "live_vram_known": vram_known,
            "paid_gpu_not_unpaid_failover": True,
            "policy": policy["gpu"],
        },
        "cpu_pool": {
            "currently_schedulable": cpu_pool,
            "remote_primary": cpu_order[0] if cpu_order else policy["remote_cpu"]["primary"],
            "failover": cpu_order[1] if len(cpu_order) > 1 else "NONE_PROVEN",
            "failover_proven": len(cpu_order) > 1,
            "policy": policy["remote_cpu"],
        },
        "storage_pool": {
            "primary_model_storage_candidate": "KAGGLE_C1" if "KAGGLE_C1" in schedulable else UNKNOWN,
            "backup_model_storage": "UNPROVEN",
            "local_model_weight_storage_allowed": False,
            "policy": policy["model_storage"],
        },
        "persistent_control": {
            "primary": "LOCAL_AG" if "LOCAL_AG" in schedulable else UNKNOWN,
            "failover": persistent_fo if persistent_fo != "NONE_PROVEN" else policy["persistent_control"]["failover"] if "LIGHTNING_01" in schedulable else "NONE_PROVEN",
            "failover_proven": ("LIGHTNING_01" in schedulable),
            "policy": policy["persistent_control"],
        },
        "pending_auth": [aid for aid in CLOUD_ACCOUNTS if aid in _accounts(world) and not _authenticated(world, aid)],
        "blocked_c1_action": blocked,
        "c1_action_queue": c1_action_queue(),
        "kaggle_partner_dispatch_allowed": partner_ok,
        "KAGGLE_C1_BOUND": "KAGGLE_C1" in schedulable,
        "LIGHTNING_01_BOUND": "LIGHTNING_01" in schedulable,
        "UNPROVEN_PROVIDER_ADMITTED": unproven_admitted,
        "RESOURCE_FACTORY_REUSED": True,
        "SECOND_RESOURCE_REGISTRY_CREATED": False,
        "FAILOVER_POLICY_UPDATED_FROM_PROVEN_CAPACITY": True,
        "BLOCKED_C1_ACTION_COUNT": len(C1_ACTION_QUEUE),
        "WAVE06_COMPLETE_WITH_BOUNDED_EXTERNAL_ACTION_QUEUE": True,
        "UNOBSERVED_NE_ABSENT": True,
        "STATIC_SNAPSHOT_NE_RUNTIME_AUTHORITY": True,
        "RF_C5_12": "BLOCKED_BY_GOVERNED_CHANNEL",
    }


def c1_action_queue() -> list[dict[str, Any]]:
    return [dict(item) for item in C1_ACTION_QUEUE]


def explain(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": "PlacementExplain",
        "decision_id": decision.get("decision_id"),
        "result_class": decision.get("result_class"),
        "selected_resource": decision.get("selected_resource"),
        "rejected_resources": decision.get("rejected_resources"),
        "conditional_resources": decision.get("conditional_resources"),
        "decision_reason": decision.get("decision_reason"),
        "failover_order": decision.get("failover_order"),
        "requires_capacity_probe": decision.get("requires_capacity_probe"),
        "requires_c1_authorization": decision.get("requires_c1_authorization"),
        "dispatch_allowed": decision.get("dispatch_allowed"),
    }


def evaluate_workload(workload_class: str, world: dict[str, Any], **kw: Any) -> dict[str, Any]:
    req = resource_request(workload_class=workload_class, **kw)
    decision = place(req, world)
    plan = plan_dispatch(decision, req, dry_run=True)
    return {"request": req, "decision": decision, "plan": plan, "explain": explain(decision)}
