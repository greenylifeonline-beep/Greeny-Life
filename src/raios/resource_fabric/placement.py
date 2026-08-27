"""Placement planner, model warehouse, market compare, recomposition. Planning only."""

from __future__ import annotations

from typing import Any

from .projection import project_accelerator, project_compute, project_storage, scores
from .schema import UNKNOWN, is_unknown, numeric_or_unknown

MODEL_WEIGHTS_LOCAL = False
WAREHOUSE_ID = "RAIOS_MODEL_WAREHOUSE"


def placement_request(**kw: Any) -> dict[str, Any]:
    return {
        "kind": "PlacementRequest",
        "requires_gpu": bool(kw.get("requires_gpu", False)),
        "min_gpu_vram_gb": kw.get("min_gpu_vram_gb", UNKNOWN),
        "min_ram_gb": kw.get("min_ram_gb", UNKNOWN),
        "storage_required_gb": kw.get("storage_required_gb", UNKNOWN),
        "persistent_output": bool(kw.get("persistent_output", False)),
        "max_cost_per_hour": kw.get("max_cost_per_hour", UNKNOWN),
        "min_runtime_hours": kw.get("min_runtime_hours", UNKNOWN),
        "public_endpoint": bool(kw.get("public_endpoint", False)),
        "preferred_capabilities": list(kw.get("preferred_capabilities") or []),
        "local_model_storage_prohibited": True,
        "MODEL_WEIGHTS_LOCAL": MODEL_WEIGHTS_LOCAL,
    }


def _fit_compute(req: dict[str, Any], row: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    met: list[str] = []
    failed: list[str] = []
    ram = numeric_or_unknown(row.get("ram_gb"))
    need = numeric_or_unknown(req.get("min_ram_gb"))
    if need is not UNKNOWN:
        if ram is UNKNOWN:
            failed.append("RAM_UNOBSERVED")
        elif float(ram) < float(need):
            failed.append("RAM_SHORT")
        else:
            met.append("RAM")
    if req.get("persistent_output") and not row.get("persistent"):
        failed.append("NOT_PERSISTENT")
    elif req.get("persistent_output"):
        met.append("PERSISTENT")
    if req.get("public_endpoint") and not row.get("public_endpoint_allowed"):
        failed.append("NO_PUBLIC_ENDPOINT")
    price = numeric_or_unknown(row.get("price_per_hour"))
    cap = numeric_or_unknown(req.get("max_cost_per_hour"))
    if cap is not UNKNOWN:
        if price is UNKNOWN:
            failed.append("PRICE_UNKNOWN")
        elif float(price) > float(cap):
            failed.append("OVER_BUDGET")
        else:
            met.append("BUDGET")
    return (not failed, met, failed)


def _fit_gpu(req: dict[str, Any], row: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    met: list[str] = []
    failed: list[str] = []
    if not req.get("requires_gpu"):
        return True, met, failed
    vram = numeric_or_unknown(row.get("gpu_vram_gb"))
    need = numeric_or_unknown(req.get("min_gpu_vram_gb"))
    if need is not UNKNOWN:
        if vram is UNKNOWN:
            failed.append("VRAM_UNOBSERVED")
        elif float(vram) < float(need):
            failed.append("VRAM_SHORT")
        else:
            met.append("VRAM")
    return (not failed, met, failed)


def decide(req: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    options: list[dict[str, Any]] = []
    computes = world.get("compute") or []
    gpus = world.get("accelerators") or []
    stores = world.get("storage") or []
    quotas = {(q.get("account_id"), q.get("resource_type")): q for q in world.get("quotas") or []}
    for gpu in gpus:
        ok_g, met_g, fail_g = _fit_gpu(req, gpu)
        for cmp in computes:
            if cmp.get("account_id") != gpu.get("account_id") and req.get("requires_gpu"):
                continue
            ok_c, met_c, fail_c = _fit_compute(req, cmp)
            failed = fail_g + fail_c
            met = met_g + met_c
            sc = scores({**cmp, **gpu})
            q = quotas.get((gpu.get("account_id"), "gpu_hours")) or {}
            options.append(
                {
                    "provider": gpu.get("provider_id") or cmp.get("provider_id"),
                    "account": gpu.get("account_id") or cmp.get("account_id"),
                    "region": gpu.get("region") or cmp.get("region"),
                    "resource": gpu.get("resource_id") or cmp.get("resource_id"),
                    "fit": ok_g and ok_c,
                    "constraints_met": met,
                    "constraints_failed": failed,
                    "estimated_cost": gpu.get("price_per_hour", UNKNOWN),
                    "quota_remaining": q.get("remaining", UNKNOWN),
                    "persistence": bool(cmp.get("persistent")),
                    "startup_time": UNKNOWN,
                    "confidence": "LOW" if failed else "MEDIUM",
                    "reason_codes": failed or ["CANDIDATE"],
                    "scores": sc,
                    "capabilities": list(set(project_compute(cmp) + project_accelerator(gpu))),
                }
            )
    if not req.get("requires_gpu"):
        for cmp in computes:
            ok_c, met_c, fail_c = _fit_compute(req, cmp)
            options.append(
                {
                    "provider": cmp.get("provider_id"),
                    "account": cmp.get("account_id"),
                    "region": cmp.get("region"),
                    "resource": cmp.get("resource_id"),
                    "fit": ok_c,
                    "constraints_met": met_c,
                    "constraints_failed": fail_c,
                    "estimated_cost": cmp.get("price_per_hour", UNKNOWN),
                    "quota_remaining": UNKNOWN,
                    "persistence": bool(cmp.get("persistent")),
                    "startup_time": UNKNOWN,
                    "confidence": "MEDIUM" if ok_c else "LOW",
                    "reason_codes": fail_c or ["CANDIDATE"],
                    "scores": scores(cmp),
                    "capabilities": project_compute(cmp),
                }
            )
    options.sort(key=lambda o: (not o["fit"], -len(o["constraints_met"])))
    fallbacks = [o for o in options if not o["fit"]][:3]
    return {
        "kind": "PlacementDecision",
        "request": req,
        "ranked": options,
        "fallbacks": fallbacks,
        "MUTATION": False,
        "PAID_ACTIVATION": False,
    }


def model_record(
    *,
    model_id: str,
    family: str,
    size_gb: float,
    sha256: str,
    quantization: str = UNKNOWN,
    min_ram: Any = UNKNOWN,
    recommended_ram: Any = UNKNOWN,
    min_vram: Any = UNKNOWN,
    recommended_vram: Any = UNKNOWN,
    context: Any = UNKNOWN,
    tool_support: Any = UNKNOWN,
    source: str = UNKNOWN,
    license_name: str = UNKNOWN,
    version: str = UNKNOWN,
    formats: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "family": family,
        "size_gb": size_gb,
        "sha256": sha256,
        "quantization": quantization,
        "min_ram": min_ram,
        "recommended_ram": recommended_ram,
        "min_vram": min_vram,
        "recommended_vram": recommended_vram,
        "context": context,
        "tool_support": tool_support,
        "source": source,
        "license": license_name,
        "version": version,
        "formats": list(formats or []),
        "storage_locations": [],
        "active_inference_locations": [],
    }


class ModelWarehouse:
    def __init__(self) -> None:
        self.models: dict[str, dict[str, Any]] = {}
        self.by_hash: dict[str, str] = {}

    def register(self, rec: dict[str, Any]) -> dict[str, Any]:
        digest = rec["sha256"]
        existing = self.by_hash.get(digest)
        if existing:
            return {"STATUS": "ALREADY_STORED", "model_id": existing, "DUPLICATE_TRANSFER": False}
        self.models[rec["model_id"]] = rec
        self.by_hash[digest] = rec["model_id"]
        return {"STATUS": "REGISTERED", "model_id": rec["model_id"], "DUPLICATE_TRANSFER": False}

    def add_location(self, model_id: str, location: dict[str, Any]) -> dict[str, Any]:
        rec = self.models[model_id]
        if location.get("kind") == "LOCAL" and MODEL_WEIGHTS_LOCAL is False:
            return {"STATUS": "DENIED", "code": "LOCAL_MODEL_STORAGE_PROHIBITED"}
        rec["storage_locations"].append(location)
        return {"STATUS": "ADDED", "locations": rec["storage_locations"]}


def model_placement(model: dict[str, Any], storage: dict[str, Any], inference: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    size = float(model["size_gb"])
    free = numeric_or_unknown(storage.get("capacity_free_gb"))
    can_store = free is UNKNOWN or float(free) >= size
    if storage.get("account_id") == "LOCAL_AG" or storage.get("region") == "local":
        if MODEL_WEIGHTS_LOCAL is False:
            can_store = False
    vram = numeric_or_unknown(inference.get("gpu_vram_gb"))
    need = numeric_or_unknown(model.get("min_vram"))
    rec = numeric_or_unknown(model.get("recommended_vram"))
    can_run = True
    can_eff = True
    if need is not UNKNOWN:
        if vram is UNKNOWN:
            can_run = False
        else:
            can_run = float(vram) >= float(need)
    if rec is not UNKNOWN and vram is not UNKNOWN:
        can_eff = float(vram) >= float(rec)
    elif rec is not UNKNOWN:
        can_eff = False
    persist = bool(inference.get("persistent") or storage.get("persistent"))
    return {
        "CONTROL_LOCATION": control.get("account_id") or control.get("resource_id"),
        "MODEL_STORAGE_LOCATION": storage.get("storage_id"),
        "MODEL_INFERENCE_LOCATION": inference.get("resource_id"),
        "CAN_STORE": can_store,
        "CAN_LOAD": can_store,
        "CAN_RUN": can_run,
        "CAN_RUN_EFFICIENTLY": can_eff and can_run,
        "CAN_SERVE_PERSISTENTLY": persist and can_run,
        "SPLIT_CONTROL_STORAGE_INFERENCE": True,
    }


def market_offer(**kw: Any) -> dict[str, Any]:
    return {
        "kind": "MarketOffer",
        "provider": kw.get("provider"),
        "service": kw.get("service"),
        "region": kw.get("region", UNKNOWN),
        "resource_type": kw.get("resource_type"),
        "spec": kw.get("spec") or {},
        "price": numeric_or_unknown(kw.get("price")),
        "free_tier": kw.get("free_tier", UNKNOWN),
        "credit_offer": kw.get("credit_offer", UNKNOWN),
        "storage": kw.get("storage", UNKNOWN),
        "egress": kw.get("egress", UNKNOWN),
        "observed_at": kw.get("observed_at", UNKNOWN),
        "source": kw.get("source", UNKNOWN),
    }


def compare_owned_vs_market(owned_effective: Any, market: Any) -> dict[str, Any]:
    o = numeric_or_unknown(owned_effective)
    m = numeric_or_unknown(market)
    delta = UNKNOWN if o is UNKNOWN or m is UNKNOWN else float(o) - float(m)
    return {
        "OWNED_ACCOUNT_EFFECTIVE_COST": o,
        "MARKET_COST": m,
        "DELTA": delta,
        "STALE_MARKET_HARDCODED": False,
    }


def recompose_v2(world: dict[str, Any]) -> dict[str, Any]:
    base = recompose(world)
    acc_status = {a.get("account_id"): a.get("status") for a in world.get("accounts") or []}
    live_gpu = [
        g
        for g in world.get("accelerators") or []
        if g.get("gpu_class") in {"CURRENT_ALLOCATABLE_GPU", "ACCOUNT_ELIGIBLE_GPU", "ACTIVE_SESSION_GPU"}
        and g.get("available") is True
    ]
    catalog_gpu = [g for g in world.get("accelerators") or [] if g.get("gpu_class") == "CATALOG_GPU"]
    stores = [
        s
        for s in world.get("storage") or []
        if s.get("persistent")
        and s.get("model_weights_suitable")
        and s.get("account_id") != "LOCAL_AG"
        and acc_status.get(s.get("account_id")) in {"REACHABLE", "REACHABLE_CREDENTIAL_PRESENT", "PARTIAL"}
    ]

    def _free(s: dict[str, Any]) -> tuple[int, float]:
        n = numeric_or_unknown(s.get("capacity_free_gb"))
        if n is UNKNOWN:
            return (1, 0.0)
        return (0, -float(n))

    ranked_store = sorted(stores, key=_free)
    burst = live_gpu[0] if live_gpu else (catalog_gpu[0] if catalog_gpu else None)
    heavy = None
    for g in live_gpu + catalog_gpu:
        vram = numeric_or_unknown(g.get("gpu_vram_gb"))
        if vram is not UNKNOWN and float(vram) >= 24:
            heavy = g
            break
    local_ok = acc_status.get("LOCAL_AG") in {"REACHABLE", "REACHABLE_CREDENTIAL_PRESENT", None, "DECLARED"}
    return {
        **base,
        "kind": "RESOURCE-RECOMPOSITION-V2",
        "CONTROL": "AG",
        "PERSISTENT_CONTROL": "LOCAL_AG" if local_ok else UNKNOWN,
        "MODEL_WAREHOUSE": (ranked_store[0].get("storage_id") if ranked_store else UNKNOWN),
        "HEAVY_INFERENCE": (heavy.get("resource_id") if heavy else UNKNOWN),
        "LIGHT_INFERENCE": "LOCAL_AG",
        "GPU_BURST": (burst.get("resource_id") if burst else UNKNOWN),
        "EMBEDDING": "LOCAL_AG",
        "BACKUP": base.get("BACKUP"),
        "FAILOVER": base.get("FAILOVER"),
        "CATALOG_NE_LIVE": True,
        "MULTI_PROVIDER": True,
        "PLANNING_ONLY": True,
        "PAID_RESOURCE_ACTIVATED": False,
        "MODEL_MIGRATION_EXECUTED": False,
        "NINEROUTER_IS_RESOURCE_AUTHORITY": False,
    }


def recompose(world: dict[str, Any]) -> dict[str, Any]:
    stores = [s for s in world.get("storage") or [] if s.get("persistent") and s.get("model_weights_suitable")]
    gpus = list(world.get("accelerators") or [])
    controls = [c for c in world.get("compute") or [] if c.get("persistent")]
    backups = [s for s in world.get("storage") or [] if s.get("backup_suitable") or s.get("type") in {"archive_storage", "backup_storage"}]
    def _vram_key(g: dict[str, Any]) -> tuple[int, float]:
        n = numeric_or_unknown(g.get("gpu_vram_gb"))
        if n is UNKNOWN:
            return (1, 0.0)
        return (0, -float(n))

    ranked_gpu = sorted(gpus, key=_vram_key)
    return {
        "kind": "RESOURCE-RECOMPOSITION-PLAN",
        "CONTROL_NODE": "AG",
        "MODEL_STORAGE": (stores[0].get("storage_id") if stores else UNKNOWN),
        "HEAVY_INFERENCE": (ranked_gpu[0].get("resource_id") if ranked_gpu else UNKNOWN),
        "BURST_GPU": (ranked_gpu[0].get("resource_id") if ranked_gpu else UNKNOWN),
        "BACKUP": (backups[0].get("storage_id") if backups else UNKNOWN),
        "FAILOVER": (ranked_gpu[1].get("resource_id") if len(ranked_gpu) > 1 else UNKNOWN),
        "PLANNING_ONLY": True,
        "PAID_RESOURCE_ACTIVATED": False,
        "MODEL_MIGRATION_EXECUTED": False,
    }
