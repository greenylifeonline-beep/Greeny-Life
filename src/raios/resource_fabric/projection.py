"""Capability projection, unused-value classification, and dimensional scores."""

from __future__ import annotations

from typing import Any

from .schema import CAPABILITY_CLASSES, UNKNOWN, USAGE_CLASSES, is_unknown, numeric_or_unknown


def project_compute(row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if row.get("persistent") and not row.get("ephemeral"):
        out.append("PERSISTENT_CONTROL_NODE")
        out.append("HEAVY_COMPUTE")
    else:
        out.append("LIGHT_COMPUTE")
        out.append("CI_WORKER")
    ram = numeric_or_unknown(row.get("ram_gb"))
    if ram is not UNKNOWN and float(ram) >= 32:
        if "HEAVY_COMPUTE" not in out:
            out.append("HEAVY_COMPUTE")
    if row.get("public_endpoint_allowed"):
        out.append("PUBLIC_ENDPOINT")
    if row.get("private_endpoint_allowed"):
        out.append("PRIVATE_ENDPOINT")
    return [c for c in out if c in CAPABILITY_CLASSES]


def project_accelerator(row: dict[str, Any]) -> list[str]:
    out = ["GPU_BURST"]
    vram = numeric_or_unknown(row.get("gpu_vram_gb"))
    if vram is not UNKNOWN and float(vram) >= 24:
        out.extend(["HEAVY_INFERENCE", "FINE_TUNING", "TRAINING"])
    elif vram is not UNKNOWN:
        out.extend(["LIGHT_INFERENCE", "EMBEDDING"])
    persist = row.get("session_limit") in (None, "", UNKNOWN)
    if persist:
        out.append("GPU_PERSISTENT")
    return [c for c in out if c in CAPABILITY_CLASSES]


def project_storage(row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if row.get("model_weights_suitable"):
        out.append("MODEL_STORAGE")
    if row.get("artifact_suitable"):
        out.append("ARTIFACT_STORAGE")
    if row.get("backup_suitable") or row.get("type") in {"backup_storage", "archive_storage"}:
        out.append("BACKUP_STORAGE")
        out.append("ARCHIVE")
        out.append("FAILOVER")
    if row.get("type") == "database_storage":
        out.append("DATABASE")
        out.append("VECTOR_STORAGE")
    return [c for c in out if c in CAPABILITY_CLASSES]


def project_service(row: dict[str, Any]) -> list[str]:
    cat = row.get("category")
    mapping = {
        "QUEUE": ["QUEUE"],
        "EVENT_BUS": ["EVENT_BUS"],
        "STREAM": ["EVENT_BUS"],
        "INFERENCE_ENDPOINT": ["LIGHT_INFERENCE", "PUBLIC_ENDPOINT" if row.get("public_endpoint") else "PRIVATE_ENDPOINT"],
        "VECTOR_DATABASE": ["VECTOR_STORAGE", "DATABASE"],
        "SQL": ["DATABASE"],
        "NOSQL": ["DATABASE"],
        "CI_CD": ["CI_WORKER", "BUILD_WORKER"],
        "GPU_NOTEBOOK": ["GPU_BURST", "LIGHT_INFERENCE"],
    }
    raw = mapping.get(str(cat), [])
    return [c for c in raw if c in CAPABILITY_CLASSES]


def classify_unused(row: dict[str, Any]) -> str:
    enabled = row.get("enabled")
    available = row.get("available", True)
    quota = numeric_or_unknown(row.get("quota_available", row.get("remaining")))
    usage = numeric_or_unknown(row.get("current_usage", row.get("capacity_used_gb")))
    if not available:
        return "UNKNOWN"
    if quota == 0.0:
        return "AVAILABLE_ZERO_QUOTA"
    if row.get("free_tier") is True or row.get("price_kind") == "FREE_TIER_PRICE":
        if usage == 0.0 or is_unknown(usage):
            return "FREE_TIER"
    if enabled and (usage == 0.0):
        return "ACTIVE_IDLE"
    if enabled and not is_unknown(usage) and float(usage) > 0:
        return "ACTIVE_USED"
    if available and not enabled:
        return "AVAILABLE_UNUSED"
    if row.get("CREDIT_BACKED"):
        return "CREDIT_BACKED"
    if row.get("paid") and (is_unknown(usage) or usage == 0.0):
        return "PAID_UNUSED"
    if "AVAILABLE_UNUSED" in USAGE_CLASSES and available:
        return "AVAILABLE_UNUSED"
    return "UNKNOWN"


def scores(row: dict[str, Any]) -> dict[str, Any]:
    def dim(name: str, value: Any) -> Any:
        n = numeric_or_unknown(value)
        if n is UNKNOWN:
            return UNKNOWN
        return max(0.0, min(1.0, float(n)))

    gpu = 0.0
    vram = numeric_or_unknown(row.get("gpu_vram_gb"))
    if vram is not UNKNOWN:
        gpu = min(1.0, float(vram) / 80.0)
    else:
        gpu = UNKNOWN
    persist = 1.0 if row.get("persistent") else (0.0 if row.get("ephemeral") else UNKNOWN)
    cost = numeric_or_unknown(row.get("price_per_hour", row.get("price_gb_month")))
    cost_score = UNKNOWN if cost is UNKNOWN else max(0.0, 1.0 - min(1.0, float(cost) / 10.0))
    avail = UNKNOWN
    if row.get("available") is True:
        avail = 0.7
    if row.get("available") is False:
        avail = 0.0
    quota_n = numeric_or_unknown(row.get("quota_available", row.get("remaining")))
    quota_s = UNKNOWN if quota_n is UNKNOWN else (0.0 if float(quota_n) <= 0 else 0.8)
    dims = {
        "availability_score": avail,
        "cost_score": cost_score,
        "persistence_score": persist,
        "compute_score": dim("compute", row.get("vcpu", 0.3 if persist == 1 else UNKNOWN)),
        "gpu_score": gpu,
        "storage_score": dim("storage", row.get("capacity_free_gb")),
        "network_score": UNKNOWN,
        "service_score": 0.5 if row.get("kind") == "Service" else UNKNOWN,
        "reliability_score": UNKNOWN,
        "quota_score": quota_s,
        "credit_score": UNKNOWN,
    }
    known = [float(v) for v in dims.values() if v is not UNKNOWN]
    raios = UNKNOWN if not known else sum(known) / len(known)
    dims["RAIOS_VALUE_SCORE"] = raios
    dims["OPAQUE_SINGLE_SCORE_ONLY"] = False
    return dims
