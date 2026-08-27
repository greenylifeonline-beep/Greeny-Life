"""Deterministic cost estimator. Missing prices are UNKNOWN, never implied zero."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .schema import UNKNOWN, is_unknown, numeric_or_unknown

SCENARIOS = (
    "COST_IDLE",
    "COST_1H_DAY",
    "COST_8H_DAY",
    "COST_24_7",
    "COST_10_HOURS",
    "COST_100_HOURS",
    "COST_500_HOURS",
    "STORAGE_10GB",
    "STORAGE_50GB",
    "STORAGE_100GB",
    "STORAGE_500GB",
    "STORAGE_1TB",
    "EGRESS_10GB",
    "EGRESS_100GB",
    "EGRESS_1TB",
    "GPU_1H",
    "GPU_10H",
    "GPU_100H",
)

HOURS = {
    "COST_IDLE": 0.0,
    "COST_1H_DAY": 1.0 * 30,
    "COST_8H_DAY": 8.0 * 30,
    "COST_24_7": 24.0 * 30,
    "COST_10_HOURS": 10.0,
    "COST_100_HOURS": 100.0,
    "COST_500_HOURS": 500.0,
    "GPU_1H": 1.0,
    "GPU_10H": 10.0,
    "GPU_100H": 100.0,
}

STORAGE_GB = {
    "STORAGE_10GB": 10.0,
    "STORAGE_50GB": 50.0,
    "STORAGE_100GB": 100.0,
    "STORAGE_500GB": 500.0,
    "STORAGE_1TB": 1024.0,
}

EGRESS_GB = {
    "EGRESS_10GB": 10.0,
    "EGRESS_100GB": 100.0,
    "EGRESS_1TB": 1024.0,
}


def _add(a: Any, b: Any) -> Any:
    if is_unknown(a) or is_unknown(b):
        if (is_unknown(a) and is_unknown(b)) or is_unknown(a) and not is_unknown(b):
            return UNKNOWN if is_unknown(a) else UNKNOWN
        return UNKNOWN
    return float(a) + float(b)


def _mul(a: Any, b: float) -> Any:
    n = numeric_or_unknown(a)
    if n is UNKNOWN:
        return UNKNOWN
    return float(n) * b


def credit_effective(credit: dict[str, Any], *, now: datetime | None = None) -> Any:
    now = now or datetime.now(timezone.utc)
    remaining = numeric_or_unknown(credit.get("remaining_value"))
    exp = credit.get("expires_at")
    if exp and exp not in (None, "", UNKNOWN):
        try:
            rec = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
            if rec.tzinfo is None:
                rec = rec.replace(tzinfo=timezone.utc)
            if rec <= now:
                return 0.0
        except ValueError:
            return UNKNOWN
    return remaining


def estimate(
    *,
    scenario: str,
    compute_rate: Any = UNKNOWN,
    accelerator_rate: Any = UNKNOWN,
    storage_gb_month: Any = UNKNOWN,
    egress_gb_rate: Any = UNKNOWN,
    database_rate: Any = UNKNOWN,
    service_rate: Any = UNKNOWN,
    fixed: Any = 0,
    credits: list[dict[str, Any]] | None = None,
    free_tier_hours: Any = 0,
    free_tier_storage_gb: Any = 0,
    now: datetime | None = None,
) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError("UNKNOWN_SCENARIO")
    compute = UNKNOWN
    accelerator = UNKNOWN
    storage = UNKNOWN
    network = UNKNOWN
    if scenario in HOURS:
        hours = HOURS[scenario]
        free_h = numeric_or_unknown(free_tier_hours)
        bill_h = hours if free_h is UNKNOWN else max(0.0, hours - float(free_h))
        if scenario.startswith("GPU"):
            accelerator = _mul(accelerator_rate, bill_h)
            compute = 0.0
        else:
            compute = _mul(compute_rate, bill_h)
            accelerator = 0.0
        if scenario == "COST_IDLE":
            compute = 0.0 if not is_unknown(compute_rate) else UNKNOWN
            accelerator = 0.0
    if scenario in STORAGE_GB:
        gb = STORAGE_GB[scenario]
        free_s = numeric_or_unknown(free_tier_storage_gb)
        bill_gb = gb if free_s is UNKNOWN else max(0.0, gb - float(free_s))
        storage = _mul(storage_gb_month, bill_gb)
    if scenario in EGRESS_GB:
        network = _mul(egress_gb_rate, EGRESS_GB[scenario])

    database = 0.0
    service_c = 0.0
    if scenario.startswith("COST") and scenario not in {"COST_IDLE"}:
        database = numeric_or_unknown(database_rate)
        service_c = numeric_or_unknown(service_rate)
        if database is UNKNOWN:
            database = 0.0
        if service_c is UNKNOWN:
            service_c = 0.0
    storage = 0.0 if scenario not in STORAGE_GB else storage
    network = 0.0 if scenario not in EGRESS_GB else network
    if scenario in HOURS:
        if storage is UNKNOWN:
            storage = 0.0
        if network is UNKNOWN:
            network = 0.0
    if scenario in STORAGE_GB:
        compute = 0.0 if compute is UNKNOWN else compute
        accelerator = 0.0 if accelerator is UNKNOWN else accelerator
        network = 0.0
    if scenario in EGRESS_GB:
        compute = 0.0 if compute is UNKNOWN else compute
        accelerator = 0.0 if accelerator is UNKNOWN else accelerator
        storage = 0.0
    fixed_n = numeric_or_unknown(fixed)
    if fixed_n is UNKNOWN:
        fixed_n = 0.0

    offset = 0.0
    credit_unknown = False
    for c in credits or []:
        eff = credit_effective(c, now=now)
        if is_unknown(eff):
            credit_unknown = True
        else:
            offset += float(eff)

    parts = [compute, accelerator, storage, network, database, service_c, fixed_n]
    if any(is_unknown(p) for p in parts if p is not None):
        gross = UNKNOWN
    else:
        gross = sum(float(p) for p in parts if p is not UNKNOWN)

    free_offset = UNKNOWN
    if scenario in HOURS and not is_unknown(compute_rate) and not is_unknown(free_tier_hours):
        free_offset = float(min(HOURS[scenario], float(free_tier_hours))) * float(compute_rate)

    credits_offset: Any = UNKNOWN if credit_unknown else offset
    net: Any = UNKNOWN
    if gross is not UNKNOWN and credits_offset is not UNKNOWN:
        net = max(0.0, float(gross) - float(credits_offset))

    return {
        "scenario": scenario,
        "compute": compute,
        "accelerator": accelerator,
        "storage": storage,
        "network": network,
        "database": database,
        "service": service_c,
        "fixed": fixed_n,
        "variable": UNKNOWN if gross is UNKNOWN else float(gross) - float(fixed_n),
        "credits_offset": credits_offset,
        "free_tier_offset": free_offset,
        "gross": gross,
        "net": net,
        "FREE_TIER_NE_UNLIMITED": True,
        "CREDIT_NE_CASH": True,
        "MISSING_PRICE_IS_UNKNOWN": True,
    }


def effective_price(*, catalog: Any, account: Any, free_tier: Any, credit_adjusted: Any) -> dict[str, Any]:
    return {
        "CATALOG_PRICE": numeric_or_unknown(catalog),
        "ACCOUNT_SPECIFIC_PRICE": numeric_or_unknown(account),
        "FREE_TIER_PRICE": numeric_or_unknown(free_tier),
        "CREDIT_ADJUSTED_EFFECTIVE_PRICE": numeric_or_unknown(credit_adjusted),
    }
