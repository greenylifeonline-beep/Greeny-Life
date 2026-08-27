"""Read-only census and snapshot assembly."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .adapters import ADAPTERS
from .cost import estimate
from .live import bind_live_accounts
from .observations import observation
from .placement import decide, placement_request, recompose
from .probe import ResourceProbeRunner
from .projection import classify_unused, project_accelerator, project_compute, project_service, project_storage, scores
from .schema import UNKNOWN, SCHEMA
from .secrets import assert_no_secrets, mask_record

ROOT = Path(__file__).resolve().parents[3]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def collect_world(adapters: dict[str, Any] | None = None) -> dict[str, Any]:
    adapters = adapters or ADAPTERS
    world: dict[str, Any] = {
        "providers": [],
        "accounts": [],
        "regions": [],
        "compute": [],
        "accelerators": [],
        "storage": [],
        "services": [],
        "quotas": [],
        "credits": [],
        "pricing": [],
        "usage": [],
        "probes": [],
    }
    for adapter in adapters.values():
        ident = adapter.identify()
        world["providers"].append(ident)
        accounts = adapter.discover_accounts()
        world["accounts"].extend(accounts)
        for acc in accounts:
            aid = acc["account_id"]
            world["regions"].extend(adapter.discover_regions(aid))
            world["compute"].extend(adapter.discover_compute(aid))
            world["accelerators"].extend(adapter.discover_accelerators(aid))
            world["storage"].extend(adapter.discover_storage(aid))
            world["services"].extend(adapter.discover_services(aid))
            world["quotas"].extend(adapter.discover_quotas(aid))
            world["credits"].extend(adapter.discover_credits(aid))
            world["pricing"].extend(adapter.discover_pricing(aid))
            world["usage"].extend(adapter.discover_usage(aid))
    return world


def run_safe_probes(world: dict[str, Any], runner: ResourceProbeRunner | None = None, *, live: bool | None = None) -> list[dict[str, Any]]:
    runner = runner or ResourceProbeRunner(timeout_seconds=3.0)
    probes = [runner.probe_local_control()]
    bind_live_accounts(world, live=live)
    live_probes = world.get("live_probes") if isinstance(world.get("live_probes"), dict) else {}
    for account_id, rec in live_probes.items():
        if not isinstance(rec, dict):
            continue
        wrapped = observation(
            provider=str(rec.get("provider") or rec.get("account_id") or "unknown"),
            account=str(account_id),
            resource_or_service=f"probe:{account_id}",
            value={"status": rec.get("status"), "UNOBSERVED_NE_ABSENT": True, "KAGGLE_JSON_ABSENT_NE_ACCOUNT_ABSENT": True},
            source="live.bind_live_accounts",
            probe_id=str(account_id),
            confidence="MEDIUM" if rec.get("status") == "REACHABLE" else "LOW",
        )
        wrapped["status"] = rec.get("status") or "UNKNOWN"
        wrapped["PROBE_FAIL_NE_ABSENT"] = True
        probes.append(wrapped)
    for p in probes:
        assert_no_secrets(p)
    world["probes"] = probes
    return probes


def capability_projection(world: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for rec in world["compute"]:
        rows.append({"resource": rec.get("resource_id"), "account": rec.get("account_id"), "classes": project_compute(rec), "scores": scores(rec)})
    for rec in world["accelerators"]:
        rows.append({"resource": rec.get("resource_id"), "account": rec.get("account_id"), "classes": project_accelerator(rec), "scores": scores(rec)})
    for rec in world["storage"]:
        rows.append({"resource": rec.get("storage_id"), "account": rec.get("account_id"), "classes": project_storage(rec), "scores": scores(rec)})
    for rec in world["services"]:
        rows.append({"resource": rec.get("service_id"), "account": rec.get("account_id"), "classes": project_service(rec), "scores": scores(rec)})
    return rows


def unused_capabilities(world: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for rec in world["services"] + world["storage"] + world["accelerators"]:
        cls = classify_unused(rec)
        out.append(
            {
                "id": rec.get("service_id") or rec.get("storage_id") or rec.get("resource_id"),
                "account_id": rec.get("account_id"),
                "class": cls,
                "kind": rec.get("kind"),
            }
        )
    return out


def status_view(world: dict[str, Any]) -> dict[str, Any]:
    probes = world.get("probes") or []
    reachable = sum(1 for a in world["accounts"] if a.get("status") in {"REACHABLE_CREDENTIAL_PRESENT", "REACHABLE"})
    auth_req = sum(1 for a in world["accounts"] if a.get("status") == "AUTH_REQUIRED")
    partial = sum(1 for a in world["accounts"] if a.get("status") == "PARTIAL")
    cpu = [c.get("vcpu") for c in world["compute"] if c.get("vcpu") not in (None, UNKNOWN)]
    ram = [c.get("ram_gb") for c in world["compute"] if c.get("ram_gb") not in (None, UNKNOWN)]
    vram = [g.get("gpu_vram_gb") for g in world["accelerators"] if g.get("gpu_vram_gb") not in (None, UNKNOWN)]
    pstore = [s for s in world["storage"] if s.get("persistent")]
    estore = [s for s in world["storage"] if s.get("ephemeral")]

    def _sum(vals: list[Any]) -> Any:
        nums = [float(v) for v in vals if isinstance(v, (int, float))]
        return sum(nums) if nums else UNKNOWN

    credits_by = {}
    for c in world["credits"]:
        cur = c.get("currency") or "USD"
        credits_by.setdefault(cur, UNKNOWN)

    unused = unused_capabilities(world)
    enabled = [s for s in world["services"] if s.get("enabled")]
    unused_svc = [u for u in unused if u.get("class") in {"AVAILABLE_UNUSED", "ACTIVE_IDLE", "FREE_TIER"}]
    return {
        "schema": SCHEMA,
        "providers_total": len(world["providers"]),
        "accounts_total": len(world["accounts"]),
        "accounts_reachable": reachable,
        "accounts_auth_required": auth_req,
        "accounts_partial": partial,
        "cpu_total": _sum(cpu),
        "ram_total": _sum(ram),
        "gpu_resources_total": len(world["accelerators"]),
        "gpu_vram_total_observed": _sum(vram),
        "persistent_storage_total_gb": _sum([s.get("capacity_total_gb") for s in pstore]),
        "persistent_storage_free_gb": _sum([s.get("capacity_free_gb") for s in pstore]),
        "ephemeral_storage_total_gb": _sum([s.get("capacity_total_gb") for s in estore]),
        "credits_total_by_currency": credits_by,
        "services_enabled_total": len(enabled),
        "services_unused_total": len(unused_svc),
        "estimated_free_capacity": UNKNOWN,
        "last_census": utc(),
        "probes": len(probes),
        "UNOBSERVED_NE_ABSENT": True,
    }


def snapshots(world: dict[str, Any]) -> dict[str, Any]:
    req = placement_request(requires_gpu=True, min_gpu_vram_gb=24, persistent_output=True, preferred_capabilities=["HEAVY_INFERENCE"])
    return mask_record(
        {
            "RESOURCE-CENSUS.json": {"schema": SCHEMA, "generated_at": utc(), "status": status_view(world), "world_counts": {k: len(v) if isinstance(v, list) else v for k, v in world.items()}},
            "PROVIDERS.json": world["providers"],
            "ACCOUNTS.json": world["accounts"],
            "COMPUTE.json": world["compute"],
            "ACCELERATORS.json": world["accelerators"],
            "STORAGE.json": world["storage"],
            "SERVICES.json": world["services"],
            "QUOTAS.json": world["quotas"],
            "CREDITS.json": world["credits"],
            "PRICING.json": world["pricing"],
            "CAPABILITY-PROJECTION.json": capability_projection(world),
            "UNUSED-CAPABILITIES.json": unused_capabilities(world),
            "PLACEMENT-SNAPSHOT.json": decide(req, world),
            "RESOURCE-RECOMPOSITION-PLAN.json": recompose(world),
            "COST-SAMPLES.json": {
                "GPU_10H_unknown_rate": estimate(scenario="GPU_10H", accelerator_rate=UNKNOWN),
                "STORAGE_100GB_unknown": estimate(scenario="STORAGE_100GB", storage_gb_month=UNKNOWN),
            },
        }
    )


def write_package(dest: Path, snaps: dict[str, Any]) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name, payload in snaps.items():
        path = dest / name
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        assert_no_secrets(payload)
