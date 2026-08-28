"""C5 resource-awareness seam.

C5 reasons over the existing Resource Factory. This is not a second C5,
not a second registry, and not a second scheduler/lease/receipt system.
Live dispatch, GPU start, and paid create stay denied.
"""

from __future__ import annotations

from typing import Any

from .factory import (
    CLOUD_ACCOUNTS,
    evaluate_workload,
    place,
    plan_dispatch,
    reservoir_view,
    resource_request,
)
from .schema import UNKNOWN, UNOBSERVED

SCHEMA = "raios.c5-resource-awareness.v1"
SEAM = "raios.resource_fabric.factory"
C5_HEALTH = "http://127.0.0.1:8766/health"
C5_CHAT = "http://127.0.0.1:8766/v1/chat"

KNOWLEDGE_STATES = ("PROVEN", "UNOBSERVED", "AUTH_REQUIRED", "CONDITIONAL", "NOT_SUPPORTED")
AUTH_PROVEN = frozenset({"REACHABLE", "REACHABLE_CREDENTIAL_PRESENT"})
AUTH_REQUIRED_STATES = frozenset(
    {
        "AUTH_REQUIRED",
        "GOOGLE_AUTH_SETUP_REQUIRED",
        "LIVE_AUTH_UNPROVEN",
        "CURRENT_LIVE_AUTH_NOT_REPROVEN",
        "COLAB_ACCESS_UNPROVEN",
    }
)

NAIVE_ALWAYS_LOCAL = {
    "CONTROL": "LOCAL_AG",
    "DISCOVERY": "LOCAL_AG",
    "TEST_LIGHT": "LOCAL_AG",
    "BATCH_CPU": "LOCAL_AG",
    "GPU_BURST": "LOCAL_AG",
    "MODEL_STORAGE": "LOCAL_AG",
    "MODEL_FACTORY": "LOCAL_AG",
    "LONG_RUNNING_SERVICE": "LOCAL_AG",
}


def classify_auth(auth_state: str, *, authenticated: bool) -> str:
    if auth_state in AUTH_REQUIRED_STATES or not authenticated:
        return "AUTH_REQUIRED"
    if authenticated and auth_state in AUTH_PROVEN.union({"DECLARED", "PARTIAL", "LOCAL"}):
        return "PROVEN"
    if auth_state in AUTH_PROVEN:
        return "PROVEN"
    if auth_state in {"PARTIAL", "CONDITIONAL"}:
        return "CONDITIONAL"
    return "UNOBSERVED"


def classify_gpu(row: dict[str, Any]) -> dict[str, str]:
    aid = row.get("account_id")
    if aid == "LOCAL_AG":
        return {"eligibility": "NOT_SUPPORTED", "sku": "NOT_SUPPORTED", "vram": "NOT_SUPPORTED"}
    sku = row.get("live_gpu_sku")
    vram = row.get("live_gpu_vram")
    sku_state = "UNOBSERVED" if sku in (None, "", UNKNOWN, UNOBSERVED) else "PROVEN"
    vram_state = "UNOBSERVED" if vram in (None, "", UNKNOWN, UNOBSERVED) else "PROVEN"
    if not row.get("authenticated"):
        return {"eligibility": "AUTH_REQUIRED", "sku": sku_state, "vram": vram_state}
    if "PAID_GPU_DENIED" in (row.get("reasons") or []) or "C1_AUTH_REQUIRED" in (row.get("reasons") or []):
        elig = "NOT_SUPPORTED"
    elif "CATALOG_CAPABILITY_NE_ENTITLEMENT" in (row.get("reasons") or []) or "CATALOG_ONLY" in (
        row.get("conditional_reasons") or []
    ):
        elig = "CONDITIONAL"
    elif row.get("gpu_eligibility_proven"):
        elig = "PROVEN"
    else:
        elig = "UNOBSERVED"
    return {"eligibility": elig, "sku": sku_state, "vram": vram_state}


def classify_accounts(world: dict[str, Any], *, workload: str = "CONTROL") -> list[dict[str, Any]]:
    req = resource_request(workload_class=workload, request_id=f"C5-CLS-{workload}")
    decision = place(req, world)
    by_id = {r["account_id"]: r for r in decision.get("evaluations") or []}
    out = []
    for aid in CLOUD_ACCOUNTS:
        row = by_id.get(aid) or {"account_id": aid, "authenticated": False, "auth_state": "AUTH_REQUIRED", "reasons": []}
        gpu = classify_gpu(row)
        auth = classify_auth(str(row.get("auth_state") or ""), authenticated=bool(row.get("authenticated")))
        rec = {
            "account_id": aid,
            "auth": auth,
            "gpu_eligibility": gpu["eligibility"],
            "gpu_sku": gpu["sku"],
            "gpu_vram": gpu["vram"],
            "dispatch_allowed": bool(row.get("dispatch_allowed")),
            "result_hint": "PROVEN"
            if row.get("dispatch_allowed")
            else ("CONDITIONAL" if row.get("conditional") else ("AUTH_REQUIRED" if auth == "AUTH_REQUIRED" else "NOT_SUPPORTED")),
            "quota_account": row.get("quota_account", aid),
            "NINEROUTER_IS_RESOURCE_AUTHORITY": False,
            "CATALOG_NE_ENTITLEMENT": True,
            "UNOBSERVED_NE_ABSENT": True,
        }
        out.append(rec)
    return out


def resource_context(world: dict[str, Any]) -> dict[str, Any]:
    view = reservoir_view(world)
    gpu_pool = view.get("gpu_pool") or {}
    failover_gpu = gpu_pool.get("failover")
    if failover_gpu in (None, [], "NONE_PROVEN") or gpu_pool.get("failover_proven") is False:
        gpu_failover = "NONE_PROVEN"
    else:
        gpu_failover = failover_gpu
    return {
        "schema": SCHEMA,
        "seam": SEAM,
        "SECOND_RESOURCE_REGISTRY": False,
        "SECOND_C5": False,
        "NINEROUTER_IS_RESOURCE_AUTHORITY": False,
        "PAID_RESOURCE_ALLOWED": False,
        "GPU_SESSION_STARTED": False,
        "REMOTE_MUTATION": False,
        "currently_schedulable": list(view.get("currently_schedulable") or []),
        "gpu_primary": gpu_pool.get("current_primary") or UNKNOWN,
        "gpu_failover": gpu_failover,
        "gpu_failover_proven": bool(gpu_pool.get("failover_proven")),
        "remote_cpu_primary": (view.get("cpu_pool") or {}).get("remote_primary") or UNKNOWN,
        "model_storage_primary": (view.get("storage_pool") or {}).get("primary_model_storage_candidate") or UNKNOWN,
        "model_storage_backup": (view.get("storage_pool") or {}).get("backup_model_storage") or "UNPROVEN",
        "accounts": classify_accounts(world),
        "kaggle_partner_dispatch_allowed": bool(view.get("kaggle_partner_dispatch_allowed")),
        "pending_auth": list(view.get("pending_auth") or []),
    }


def reason(workload_class: str, world: dict[str, Any], **kw: Any) -> dict[str, Any]:
    packed = evaluate_workload(workload_class, world, **kw)
    decision = packed["decision"]
    plan = packed["plan"]
    if plan.get("DRY_RUN") is not True:
        raise RuntimeError("C5_RESOURCE_SEAM_REQUIRES_DRY_RUN")
    result = str(decision.get("result_class") or "")
    knowledge = "PROVEN"
    if result == "CAPACITY_PROBE_REQUIRED":
        knowledge = "UNOBSERVED"
    elif result == "C1_AUTH_REQUIRED":
        knowledge = "NOT_SUPPORTED"
    elif result == "NO_ELIGIBLE_RESOURCE":
        knowledge = "NOT_SUPPORTED"
    elif result == "CONDITIONAL":
        knowledge = "CONDITIONAL"
    elif result == "PLACED":
        knowledge = "PROVEN"
    return {
        "schema": SCHEMA,
        "kind": "C5ResourceReasoning",
        "seam": SEAM,
        "workload_class": workload_class,
        "knowledge_state": knowledge,
        "selected_resource": decision.get("selected_resource"),
        "result_class": result,
        "dispatch_allowed": bool(decision.get("dispatch_allowed")),
        "requires_capacity_probe": bool(decision.get("requires_capacity_probe")),
        "requires_c1_authorization": bool(decision.get("requires_c1_authorization")),
        "gpu_failover": decision.get("gpu_failover"),
        "gpu_failover_proven": bool(decision.get("gpu_failover_proven")),
        "cost_class": decision.get("cost_class"),
        "capacity_confidence": decision.get("capacity_confidence"),
        "abstain": result in {"CAPACITY_PROBE_REQUIRED", "C1_AUTH_REQUIRED", "NO_ELIGIBLE_RESOURCE"},
        "decision": decision,
        "plan": plan,
        "explain": packed.get("explain"),
        "SECOND_RESOURCE_REGISTRY": False,
        "PAID_RESOURCE_CREATED": False,
        "GPU_SESSION_STARTED": False,
        "REMOTE_MUTATION": False,
        "CANONICAL_PROMOTION": False,
    }


def naive_reason(workload_class: str) -> dict[str, Any]:
    """Pre-seam C5-like heuristic: always local, never abstain, treat catalog as owned."""
    selected = NAIVE_ALWAYS_LOCAL.get(workload_class, "LOCAL_AG")
    return {
        "selected_resource": selected,
        "result_class": "PLACED",
        "dispatch_allowed": True,
        "abstain": False,
        "gpu_failover": "ORACLE_01",
        "treats_credits_as_cash": True,
        "treats_catalog_as_entitlement": True,
        "merges_kaggle_quotas": True,
    }


def score_placement(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    fields = ["result_class", "dispatch_allowed", "abstain"]
    if expected.get("selected_resource") is not None:
        fields = ["selected_resource", *fields]
    hits = 0
    for field in fields:
        if expected.get(field) == actual.get(field):
            hits += 1
    return {"hits": hits, "total": len(fields), "accuracy": hits / len(fields) if fields else 0.0}


def expected_for_fixture(workload: str, **kw: Any) -> dict[str, Any]:
    if workload == "CONTROL":
        return {"selected_resource": "LOCAL_AG", "result_class": "PLACED", "dispatch_allowed": True, "abstain": False}
    if workload == "GPU_BURST" and kw.get("gpu_vram_min_gb") == 24:
        return {
            "selected_resource": "KAGGLE_C1",
            "result_class": "CAPACITY_PROBE_REQUIRED",
            "dispatch_allowed": False,
            "abstain": True,
        }
    if workload == "GPU_BURST" and kw.get("paid_allowed") and kw.get("authority_context") == "C2":
        return {
            "selected_resource": None,
            "result_class": "C1_AUTH_REQUIRED",
            "dispatch_allowed": False,
            "abstain": True,
        }
    if workload == "GPU_BURST":
        return {"selected_resource": "KAGGLE_C1", "result_class": "PLACED", "dispatch_allowed": True, "abstain": False}
    if workload == "MODEL_STORAGE":
        return {"selected_resource": "KAGGLE_C1", "result_class": "PLACED", "dispatch_allowed": True, "abstain": False}
    if workload == "BATCH_CPU":
        return {"selected_resource": "MODAL_01", "result_class": "PLACED", "dispatch_allowed": True, "abstain": False}
    if workload == "DISCOVERY":
        return {"selected_resource": "LOCAL_AG", "result_class": "PLACED", "dispatch_allowed": True, "abstain": False}
    return {"selected_resource": UNKNOWN, "result_class": UNKNOWN, "dispatch_allowed": False, "abstain": True}


def shadow_cases() -> list[dict[str, Any]]:
    return [
        {"id": "A", "workload": "CONTROL", "kw": {}},
        {"id": "C", "workload": "GPU_BURST", "kw": {"paid_allowed": False}},
        {"id": "D", "workload": "GPU_BURST", "kw": {"gpu_vram_min_gb": 24, "paid_allowed": False}},
        {"id": "E", "workload": "MODEL_STORAGE", "kw": {}},
        {"id": "I", "workload": "BATCH_CPU", "kw": {}},
        {
            "id": "J",
            "workload": "GPU_BURST",
            "kw": {
                "paid_allowed": True,
                "authority_context": "C2",
                "preferred_resources": ["MODAL_01"],
                "prohibited_resources": ["KAGGLE_C1", "LOCAL_AG"],
            },
        },
        {"id": "DISC", "workload": "DISCOVERY", "kw": {}},
    ]


def run_shadow(world: dict[str, Any]) -> dict[str, Any]:
    rows = []
    naive_hits = 0
    seam_hits = 0
    field_total = 0
    for case in shadow_cases():
        expected = expected_for_fixture(case["workload"], **case["kw"])
        naive = naive_reason(case["workload"])
        actual = reason(case["workload"], world, request_id=case["id"], **case["kw"])
        nscore = score_placement(expected, naive)
        ascore = score_placement(expected, actual)
        naive_hits += nscore["hits"]
        seam_hits += ascore["hits"]
        field_total += nscore["total"]
        rows.append(
            {
                "id": case["id"],
                "workload": case["workload"],
                "expected": expected,
                "naive": {k: naive.get(k) for k in ("selected_resource", "result_class", "dispatch_allowed", "abstain")},
                "seam": {
                    "selected_resource": actual.get("selected_resource"),
                    "result_class": actual.get("result_class"),
                    "dispatch_allowed": actual.get("dispatch_allowed"),
                    "abstain": actual.get("abstain"),
                    "knowledge_state": actual.get("knowledge_state"),
                    "cost_class": actual.get("cost_class"),
                    "gpu_failover": actual.get("gpu_failover"),
                    "PAID_RESOURCE_CREATED": actual.get("PAID_RESOURCE_CREATED"),
                    "GPU_SESSION_STARTED": actual.get("GPU_SESSION_STARTED"),
                },
                "naive_accuracy": nscore["accuracy"],
                "seam_accuracy": ascore["accuracy"],
            }
        )
    return {
        "schema": SCHEMA,
        "cases": rows,
        "before_hits": naive_hits,
        "after_hits": seam_hits,
        "field_total": field_total,
        "before_accuracy": naive_hits / field_total if field_total else 0.0,
        "after_accuracy": seam_hits / field_total if field_total else 0.0,
        "gain": (seam_hits - naive_hits) / field_total if field_total else 0.0,
        "SECOND_RESOURCE_REGISTRY": False,
        "PAID_RESOURCE_CREATED": False,
        "GPU_SESSION_STARTED": False,
    }


def contradiction_free_resources(world: dict[str, Any], free_records: list[dict[str, Any]] | None) -> dict[str, Any]:
    """FREE-RESOURCES.json is a projection, not live factory authority."""
    ctx = resource_context(world)
    by_auth = {a["account_id"]: a["auth"] for a in ctx["accounts"]}
    conflicts = []
    for rec in free_records or []:
        provider = str(rec.get("provider") or "")
        auth_state = str(rec.get("auth_state") or "")
        if provider.startswith("oracle") and auth_state == "PROVEN" and by_auth.get("ORACLE_01") == "AUTH_REQUIRED":
            conflicts.append(
                {
                    "projection": "FREE-RESOURCES.json:oracle-primary",
                    "claimed": "PROVEN",
                    "factory": "AUTH_REQUIRED",
                    "winner": "factory.place/live overlay",
                    "STATIC_SNAPSHOT_NE_RUNTIME_AUTHORITY": True,
                }
            )
    return {
        "conflicts": conflicts,
        "factory_wins": True,
        "projection_is_source_of_truth": False,
        "UNOBSERVED_NE_ABSENT": True,
    }
