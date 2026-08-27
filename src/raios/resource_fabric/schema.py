"""Resource Fabric domain model. Canonical-independent; does not mutate frozen precanonical evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

UNKNOWN = "UNKNOWN"
UNOBSERVED = "UNOBSERVED"
SCHEMA = "raios.resource-fabric.v1"

EXISTING_LEASE_SYSTEM = ".ai-os/state/command-fabric/leases"
EXISTING_TASK_REGISTRY = ".ai-os/state/TASKS.json"
EXISTING_RECEIPT_ROOT = ".ai-os/receipts/command-fabric"
EXISTING_NOMADIC_CONTRACT = "RAIOS/V9/cloud/nomadic/provider_contract.py"
EXISTING_CAPACITY_CENSUS = "RAIOS/V9/autonomic/self_inspection/cloud_capacity_census.py"
EXISTING_FREE_RESOURCES = ".ai-os/learning/FREE-RESOURCES.json"
EXISTING_JOB_LEDGER = "RAIOS/V9/cloud/nomadic/job_ledger.py"

STORAGE_TYPES = (
    "ephemeral_disk",
    "persistent_block",
    "object_storage",
    "file_storage",
    "dataset_storage",
    "notebook_storage",
    "artifact_storage",
    "model_storage",
    "snapshot_storage",
    "backup_storage",
    "archive_storage",
    "database_storage",
)

SERVICE_CATEGORIES = (
    "VM",
    "CONTAINERS",
    "KUBERNETES",
    "SERVERLESS",
    "FUNCTIONS",
    "NOTEBOOK",
    "GPU_NOTEBOOK",
    "OBJECT_STORAGE",
    "BLOCK_STORAGE",
    "FILE_STORAGE",
    "SQL",
    "NOSQL",
    "VECTOR_DATABASE",
    "CACHE",
    "QUEUE",
    "EVENT_BUS",
    "STREAM",
    "MODEL_HOSTING",
    "MODEL_REGISTRY",
    "INFERENCE_ENDPOINT",
    "EMBEDDING_SERVICE",
    "SECRETS",
    "IAM",
    "IDENTITY",
    "LOGGING",
    "METRICS",
    "TRACING",
    "SCHEDULER",
    "WORKFLOW",
    "CI_CD",
    "ARTIFACT_REGISTRY",
    "PACKAGE_REGISTRY",
    "API_GATEWAY",
    "LOAD_BALANCER",
    "DNS",
    "CDN",
    "BACKUP",
    "SNAPSHOT",
    "ARCHIVE",
    "REMOTE_IDE",
    "DEV_ENVIRONMENT",
)

USAGE_CLASSES = (
    "ACTIVE_USED",
    "ACTIVE_IDLE",
    "AVAILABLE_UNUSED",
    "AVAILABLE_ZERO_QUOTA",
    "CREDIT_BACKED",
    "FREE_TIER",
    "PAID_UNUSED",
    "UNKNOWN",
)

CAPABILITY_CLASSES = (
    "PERSISTENT_CONTROL_NODE",
    "LIGHT_COMPUTE",
    "HEAVY_COMPUTE",
    "GPU_BURST",
    "GPU_PERSISTENT",
    "LIGHT_INFERENCE",
    "HEAVY_INFERENCE",
    "EMBEDDING",
    "TRAINING",
    "FINE_TUNING",
    "DISTILLATION",
    "MODEL_STORAGE",
    "ARTIFACT_STORAGE",
    "BACKUP_STORAGE",
    "VECTOR_STORAGE",
    "DATABASE",
    "QUEUE",
    "EVENT_BUS",
    "PUBLIC_ENDPOINT",
    "PRIVATE_ENDPOINT",
    "CI_WORKER",
    "BUILD_WORKER",
    "FAILOVER",
    "ARCHIVE",
)

PRICE_KINDS = (
    "CATALOG_PRICE",
    "ACCOUNT_SPECIFIC_PRICE",
    "FREE_TIER_PRICE",
    "CREDIT_ADJUSTED_EFFECTIVE_PRICE",
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_unknown(value: Any) -> bool:
    return value in (None, "", UNKNOWN, UNOBSERVED)


def numeric_or_unknown(value: Any) -> Any:
    if is_unknown(value):
        return UNKNOWN
    if isinstance(value, bool):
        return UNKNOWN
    try:
        return float(value)
    except (TypeError, ValueError):
        return UNKNOWN


def unknown_is_not_zero(value: Any) -> bool:
    return not (is_unknown(value) and value == 0)


def require_storage_invariant(rec: dict[str, Any]) -> None:
    total = numeric_or_unknown(rec.get("capacity_total_gb"))
    free = numeric_or_unknown(rec.get("capacity_free_gb"))
    used = numeric_or_unknown(rec.get("capacity_used_gb"))
    if total is UNKNOWN or free is UNKNOWN:
        return
    if float(free) > float(total) + 1e-9:
        raise ValueError("STORAGE_FREE_GT_TOTAL")
    if used is not UNKNOWN and abs(float(used) + float(free) - float(total)) > 1e-6:
        raise ValueError("STORAGE_USED_FREE_NE_TOTAL")


def provider(
    *,
    provider_id: str,
    provider_type: str,
    display_name: str,
    api_type: str = UNKNOWN,
    cli_type: str = UNKNOWN,
    supports_accounts: bool = True,
    supports_regions: bool = True,
    supports_compute: bool = True,
    supports_gpu: bool = False,
    supports_storage: bool = True,
    supports_serverless: bool = False,
    supports_notebooks: bool = False,
    supports_model_hosting: bool = False,
    supports_persistent_workers: bool = False,
    supports_api_probe: bool = False,
    supports_cli_probe: bool = False,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": "Provider",
        "provider_id": provider_id,
        "provider_type": provider_type,
        "display_name": display_name,
        "api_type": api_type,
        "cli_type": cli_type,
        "supports_accounts": supports_accounts,
        "supports_regions": supports_regions,
        "supports_compute": supports_compute,
        "supports_gpu": supports_gpu,
        "supports_storage": supports_storage,
        "supports_serverless": supports_serverless,
        "supports_notebooks": supports_notebooks,
        "supports_model_hosting": supports_model_hosting,
        "supports_persistent_workers": supports_persistent_workers,
        "supports_api_probe": supports_api_probe,
        "supports_cli_probe": supports_cli_probe,
        "PROVIDER_NE_ACCOUNT": True,
    }


def account(
    *,
    account_id: str,
    provider_id: str,
    account_alias: str,
    owner_alias: str,
    credential_ref: str,
    billing_mode: str = UNKNOWN,
    plan: str = UNKNOWN,
    status: str = "DECLARED",
    free_tier_status: str = UNKNOWN,
    trial_status: str = UNKNOWN,
    default_region: str = UNKNOWN,
    available_regions: list[str] | None = None,
    last_verified_at: str = UNKNOWN,
    provenance_refs: list[str] | None = None,
) -> dict[str, Any]:
    if any(k in credential_ref.lower() for k in ("password=", "token=", "secret=")):
        raise ValueError("SECRET_IN_CREDENTIAL_REF")
    return {
        "schema": SCHEMA,
        "kind": "Account",
        "account_id": account_id,
        "provider_id": provider_id,
        "account_alias": account_alias,
        "owner_alias": owner_alias,
        "credential_ref": credential_ref,
        "billing_mode": billing_mode,
        "plan": plan,
        "status": status,
        "free_tier_status": free_tier_status,
        "trial_status": trial_status,
        "default_region": default_region,
        "available_regions": list(available_regions or []),
        "last_verified_at": last_verified_at,
        "provenance_refs": list(provenance_refs or []),
        "CREDENTIALS_INLINE": False,
    }


def region(*, region_id: str, provider_id: str, display_name: str = "") -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": "Region",
        "region_id": region_id,
        "provider_id": provider_id,
        "display_name": display_name or region_id,
    }


def compute_resource(
    *,
    resource_id: str,
    provider_id: str,
    account_id: str,
    region: str = UNKNOWN,
    instance_type: str = UNKNOWN,
    vcpu: Any = UNKNOWN,
    ram_gb: Any = UNKNOWN,
    architecture: str = UNKNOWN,
    os: str = UNKNOWN,
    persistent: bool = False,
    ephemeral: bool = True,
    max_runtime: Any = UNKNOWN,
    idle_timeout: Any = UNKNOWN,
    background_process_allowed: Any = UNKNOWN,
    container_allowed: Any = UNKNOWN,
    docker_allowed: Any = UNKNOWN,
    ssh_allowed: Any = UNKNOWN,
    public_endpoint_allowed: bool = False,
    private_endpoint_allowed: bool = True,
    current_instances: Any = UNKNOWN,
    max_instances: Any = UNKNOWN,
    available_capacity: Any = UNKNOWN,
    price_per_hour: Any = UNKNOWN,
    free_hours: Any = UNKNOWN,
    spot_or_preemptible: Any = UNKNOWN,
) -> dict[str, Any]:
    if persistent and ephemeral:
        raise ValueError("EPHEMERAL_NE_PERSISTENT")
    return {
        "schema": SCHEMA,
        "kind": "ComputeResource",
        "resource_id": resource_id,
        "provider_id": provider_id,
        "account_id": account_id,
        "region": region,
        "instance_type": instance_type,
        "vcpu": numeric_or_unknown(vcpu),
        "ram_gb": numeric_or_unknown(ram_gb),
        "architecture": architecture,
        "os": os,
        "persistent": persistent,
        "ephemeral": ephemeral,
        "max_runtime": max_runtime,
        "idle_timeout": idle_timeout,
        "background_process_allowed": background_process_allowed,
        "container_allowed": container_allowed,
        "docker_allowed": docker_allowed,
        "ssh_allowed": ssh_allowed,
        "public_endpoint_allowed": public_endpoint_allowed,
        "private_endpoint_allowed": private_endpoint_allowed,
        "current_instances": numeric_or_unknown(current_instances),
        "max_instances": numeric_or_unknown(max_instances),
        "available_capacity": numeric_or_unknown(available_capacity),
        "price_per_hour": numeric_or_unknown(price_per_hour),
        "free_hours": numeric_or_unknown(free_hours),
        "spot_or_preemptible": spot_or_preemptible,
    }


def accelerator_resource(
    *,
    resource_id: str,
    provider_id: str,
    account_id: str,
    region: str = UNKNOWN,
    accelerator_type: str = "GPU",
    gpu_vendor: str = UNKNOWN,
    gpu_model: str = UNKNOWN,
    gpu_count: Any = UNKNOWN,
    gpu_vram_gb: Any = UNKNOWN,
    tpu_type: str = UNKNOWN,
    available: Any = UNKNOWN,
    quota: Any = UNKNOWN,
    concurrency: Any = UNKNOWN,
    session_limit: Any = UNKNOWN,
    weekly_quota: Any = UNKNOWN,
    monthly_quota: Any = UNKNOWN,
    price_per_hour: Any = UNKNOWN,
    free_quota: Any = UNKNOWN,
    credit_eligible: Any = UNKNOWN,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": "AcceleratorResource",
        "resource_id": resource_id,
        "provider_id": provider_id,
        "account_id": account_id,
        "region": region,
        "accelerator_type": accelerator_type,
        "gpu_vendor": gpu_vendor,
        "gpu_model": gpu_model,
        "gpu_count": numeric_or_unknown(gpu_count),
        "gpu_vram_gb": numeric_or_unknown(gpu_vram_gb),
        "tpu_type": tpu_type,
        "available": available if not isinstance(available, bool) else available,
        "quota": numeric_or_unknown(quota),
        "concurrency": numeric_or_unknown(concurrency),
        "session_limit": session_limit,
        "weekly_quota": numeric_or_unknown(weekly_quota),
        "monthly_quota": numeric_or_unknown(monthly_quota),
        "price_per_hour": numeric_or_unknown(price_per_hour),
        "free_quota": numeric_or_unknown(free_quota),
        "credit_eligible": credit_eligible,
        "ZERO_QUOTA_NE_UNAVAILABLE": True,
    }


def storage_resource(
    *,
    storage_id: str,
    provider_id: str,
    account_id: str,
    region: str = UNKNOWN,
    storage_type: str,
    capacity_total_gb: Any = UNKNOWN,
    capacity_used_gb: Any = UNKNOWN,
    capacity_free_gb: Any = UNKNOWN,
    quota_gb: Any = UNKNOWN,
    persistent: bool = True,
    durability_class: str = UNKNOWN,
    replication: str = UNKNOWN,
    mountable: Any = UNKNOWN,
    api_access: bool = True,
    cli_access: bool = False,
    read_bandwidth: Any = UNKNOWN,
    write_bandwidth: Any = UNKNOWN,
    ingress_policy: str = UNKNOWN,
    egress_policy: str = UNKNOWN,
    price_gb_month: Any = UNKNOWN,
    read_request_price: Any = UNKNOWN,
    write_request_price: Any = UNKNOWN,
    egress_price_gb: Any = UNKNOWN,
    free_quota_gb: Any = UNKNOWN,
    model_weights_suitable: bool = False,
    checkpoint_suitable: bool = False,
    artifact_suitable: bool = False,
    backup_suitable: bool = False,
) -> dict[str, Any]:
    if storage_type not in STORAGE_TYPES:
        raise ValueError("UNKNOWN_STORAGE_TYPE")
    rec = {
        "schema": SCHEMA,
        "kind": "StorageResource",
        "storage_id": storage_id,
        "provider_id": provider_id,
        "account_id": account_id,
        "region": region,
        "type": storage_type,
        "capacity_total_gb": numeric_or_unknown(capacity_total_gb),
        "capacity_used_gb": numeric_or_unknown(capacity_used_gb),
        "capacity_free_gb": numeric_or_unknown(capacity_free_gb),
        "quota_gb": numeric_or_unknown(quota_gb),
        "persistent": persistent,
        "ephemeral": not persistent,
        "durability_class": durability_class,
        "replication": replication,
        "mountable": mountable,
        "api_access": api_access,
        "cli_access": cli_access,
        "read_bandwidth": numeric_or_unknown(read_bandwidth),
        "write_bandwidth": numeric_or_unknown(write_bandwidth),
        "ingress_policy": ingress_policy,
        "egress_policy": egress_policy,
        "price_gb_month": numeric_or_unknown(price_gb_month),
        "read_request_price": numeric_or_unknown(read_request_price),
        "write_request_price": numeric_or_unknown(write_request_price),
        "egress_price_gb": numeric_or_unknown(egress_price_gb),
        "free_quota_gb": numeric_or_unknown(free_quota_gb),
        "model_weights_suitable": model_weights_suitable,
        "checkpoint_suitable": checkpoint_suitable,
        "artifact_suitable": artifact_suitable,
        "backup_suitable": backup_suitable,
    }
    require_storage_invariant(rec)
    return rec


def service(
    *,
    service_id: str,
    service_name: str,
    category: str,
    provider_id: str,
    account_id: str,
    enabled: bool = False,
    available: bool = True,
    quota_available: Any = UNKNOWN,
    region: str = UNKNOWN,
    free_tier: Any = UNKNOWN,
    free_quota: Any = UNKNOWN,
    current_usage: Any = UNKNOWN,
    hard_limit: Any = UNKNOWN,
    soft_limit: Any = UNKNOWN,
    pricing_model: str = UNKNOWN,
    estimated_current_cost: Any = UNKNOWN,
    estimated_monthly_cost: Any = UNKNOWN,
    api_available: bool = False,
    cli_available: bool = False,
    sdk_available: bool = False,
    persistent: Any = UNKNOWN,
    public_endpoint: bool = False,
    private_endpoint: bool = False,
    raios_value: str = UNKNOWN,
) -> dict[str, Any]:
    if category not in SERVICE_CATEGORIES:
        raise ValueError("UNKNOWN_SERVICE_CATEGORY")
    quota_n = numeric_or_unknown(quota_available)
    return {
        "schema": SCHEMA,
        "kind": "Service",
        "service_id": service_id,
        "service_name": service_name,
        "category": category,
        "provider_id": provider_id,
        "account_id": account_id,
        "enabled": enabled,
        "available": available,
        "quota_available": quota_n,
        "region": region,
        "free_tier": free_tier,
        "free_quota": numeric_or_unknown(free_quota),
        "current_usage": numeric_or_unknown(current_usage),
        "hard_limit": numeric_or_unknown(hard_limit),
        "soft_limit": numeric_or_unknown(soft_limit),
        "pricing_model": pricing_model,
        "estimated_current_cost": numeric_or_unknown(estimated_current_cost),
        "estimated_monthly_cost": numeric_or_unknown(estimated_monthly_cost),
        "api_available": api_available,
        "cli_available": cli_available,
        "sdk_available": sdk_available,
        "persistent": persistent,
        "public_endpoint": public_endpoint,
        "private_endpoint": private_endpoint,
        "RAIOS_value": raios_value,
        "ZERO_QUOTA_NE_UNAVAILABLE": True,
        "AVAILABLE_WITH_ZERO_QUOTA": bool(available and quota_n == 0.0),
    }


def quota(
    *,
    quota_id: str,
    provider_id: str,
    account_id: str,
    service_id: str,
    resource_type: str,
    limit: Any = UNKNOWN,
    used: Any = UNKNOWN,
    remaining: Any = UNKNOWN,
    unit: str = UNKNOWN,
    reset_period: str = UNKNOWN,
    reset_at: str = UNKNOWN,
    hard_or_soft: str = "HARD",
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": "Quota",
        "quota_id": quota_id,
        "provider_id": provider_id,
        "account_id": account_id,
        "service_id": service_id,
        "resource_type": resource_type,
        "limit": numeric_or_unknown(limit),
        "used": numeric_or_unknown(used),
        "remaining": numeric_or_unknown(remaining),
        "unit": unit,
        "reset_period": reset_period,
        "reset_at": reset_at,
        "hard_or_soft": hard_or_soft,
        "ZERO_REMAINING_NE_SERVICE_ABSENT": True,
    }


def credit(
    *,
    credit_id: str,
    provider_id: str,
    account_id: str,
    original_value: Any = UNKNOWN,
    remaining_value: Any = UNKNOWN,
    currency: str = "USD",
    granted_at: str = UNKNOWN,
    expires_at: str = UNKNOWN,
    eligible_services: list[str] | None = None,
    restrictions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": "Credit",
        "credit_id": credit_id,
        "provider_id": provider_id,
        "account_id": account_id,
        "original_value": numeric_or_unknown(original_value),
        "remaining_value": numeric_or_unknown(remaining_value),
        "currency": currency,
        "granted_at": granted_at,
        "expires_at": expires_at,
        "eligible_services": list(eligible_services or []),
        "restrictions": list(restrictions or []),
        "CREDIT_NE_CASH": True,
    }


def price(
    *,
    price_id: str,
    kind: str,
    provider_id: str,
    account_id: str = UNKNOWN,
    region: str = UNKNOWN,
    resource_type: str,
    amount: Any = UNKNOWN,
    currency: str = "USD",
    pricing_unit: str,
    source: str,
    observed_at: str,
    validity: str = UNKNOWN,
) -> dict[str, Any]:
    if kind not in PRICE_KINDS:
        raise ValueError("UNKNOWN_PRICE_KIND")
    return {
        "schema": SCHEMA,
        "kind": "Price",
        "price_id": price_id,
        "price_kind": kind,
        "provider_id": provider_id,
        "account_id": account_id,
        "region": region,
        "resource_type": resource_type,
        "amount": numeric_or_unknown(amount),
        "currency": currency,
        "pricing_unit": pricing_unit,
        "source": source,
        "observed_at": observed_at,
        "validity": validity,
        "MISSING_AMOUNT_IS_UNKNOWN": is_unknown(amount),
    }


def resource_lease(
    *,
    lease_id: str,
    resource_id: str,
    account_id: str,
    owner_identity: str,
    state: str = "PLANNED",
    provenance_ref: str = EXISTING_LEASE_SYSTEM,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": "ResourceLease",
        "lease_id": lease_id,
        "resource_id": resource_id,
        "account_id": account_id,
        "owner_identity": owner_identity,
        "state": state,
        "provenance_ref": provenance_ref,
        "EXISTING_LEASE_SYSTEM": EXISTING_LEASE_SYSTEM,
        "SECOND_LEASE_SYSTEM": False,
        "WAVE01_NO_ACQUIRE": True,
    }


def worker_endpoint(
    *,
    endpoint_id: str,
    provider_id: str,
    account_id: str,
    url: str,
    public: bool = False,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": "WorkerEndpoint",
        "endpoint_id": endpoint_id,
        "provider_id": provider_id,
        "account_id": account_id,
        "url": url,
        "public": public,
        "EXISTING_WORKER_CONTRACT": "RAIOS/V9/cloud/nomadic/worker_contract.py",
    }
