"""Provider identity. A compute host is never C5 and never the persistent brain."""
from __future__ import annotations
import math

from dataclasses import dataclass, field
from typing import Any

UNKNOWN = "UNKNOWN"

LAWS = (
    "PROVIDER_NE_C5",
    "WORKER_NE_C5",
    "KAGGLE_NE_PERSISTENT_BRAIN",
    "ACCOUNT_CAPABILITY_NE_SESSION_GPU",
)

ROLES = ("CONTROL_PLANE", "WORKER", "CACHE", "PERSISTENT_BRAIN", "FORBIDDEN")


@dataclass(frozen=True)
class ProviderContract:
    provider_id: str
    kind: str
    role: str
    is_c5: bool = False
    durable_state: bool = False
    session_ephemeral: bool = True
    quota_bypass_forbidden: bool = True
    notes: tuple[str, ...] = ()
    account: str = UNKNOWN
    workspace: str = UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        if self.is_c5:
            raise ValueError("PROVIDER_NE_C5")
        if self.role == "PERSISTENT_BRAIN" and self.kind in {"kaggle", "colab"}:
            raise ValueError("KAGGLE_NE_PERSISTENT_BRAIN")
        return {
            "provider_id": self.provider_id,
            "kind": self.kind,
            "role": self.role,
            "is_c5": False,
            "durable_state": self.durable_state,
            "session_ephemeral": self.session_ephemeral,
            "quota_bypass_forbidden": self.quota_bypass_forbidden,
            "notes": list(self.notes),
            "account": self.account,
            "workspace": self.workspace,
            "law": list(LAWS),
        }


@dataclass
class ResourceCapabilityRecord:
    provider: str
    worker_id: Any = UNKNOWN
    account: Any = UNKNOWN
    workspace: Any = UNKNOWN
    auth_state: Any = UNKNOWN
    control_plane_state: Any = UNKNOWN
    availability: Any = UNKNOWN
    cpu_type: Any = UNKNOWN
    cpu_available: Any = UNKNOWN
    ram_available: Any = UNKNOWN
    gpu_type: Any = UNKNOWN
    gpu_count: Any = UNKNOWN
    gpu_vram: Any = UNKNOWN
    max_concurrency: Any = UNKNOWN
    cold_start_ms: Any = UNKNOWN
    persistent_storage: Any = UNKNOWN
    ephemeral_storage: Any = UNKNOWN
    data_locality: Any = UNKNOWN
    free_credit: Any = UNKNOWN
    paid_credit: Any = UNKNOWN
    credit_expiry: Any = UNKNOWN
    estimated_burn_rate: Any = UNKNOWN
    projected_runway: Any = UNKNOWN
    price_cpu_second: Any = UNKNOWN
    price_gpu_second: Any = UNKNOWN
    price_storage_gb: Any = UNKNOWN
    egress_cost: Any = UNKNOWN
    model_availability: Any = UNKNOWN
    model_cache: tuple[str, ...] = ()
    task_classes: tuple[str, ...] = ()
    observed_latency: Any = UNKNOWN
    task_success_rate: Any = UNKNOWN
    verified_accuracy: Any = UNKNOWN
    failure_rate: Any = UNKNOWN
    last_probe: Any = UNKNOWN
    evidence_source: Any = UNKNOWN
    confidence: Any = UNKNOWN
    freshness: Any = UNKNOWN
    evidence_hash: Any = UNKNOWN
    capacity_bounds: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        row = dict(self.__dict__)
        row["model_cache"] = list(self.model_cache)
        row["task_classes"] = list(self.task_classes)
        return row


def normalize_resource_record(payload: ResourceCapabilityRecord | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, ResourceCapabilityRecord):
        source = payload.as_dict()
    elif isinstance(payload, dict):
        source = dict(payload)
    else:
        raise TypeError("RESOURCE_RECORD_MUST_BE_MAPPING")

    provider = source.get("provider")
    if provider in (None, "", UNKNOWN):
        raise ValueError("RESOURCE_PROVIDER_REQUIRED")

    result: dict[str, Any] = {}
    for name, field_def in ResourceCapabilityRecord.__dataclass_fields__.items():
        if name == "provider":
            result[name] = str(provider)
            continue
        value = source.get(name, UNKNOWN)
        if value is None:
            value = UNKNOWN
        if name in {"model_cache", "task_classes"}:
            if value == UNKNOWN:
                value = []
            elif isinstance(value, tuple):
                value = list(value)
            elif not isinstance(value, list):
                value = [str(value)]
        if name == "capacity_bounds":
            if value == UNKNOWN:
                value = {}
            elif not isinstance(value, dict):
                raise TypeError("CAPACITY_BOUNDS_MUST_BE_MAPPING")
        result[name] = value
    return result


PROVIDERS = (
    ProviderContract(
        provider_id="kaggle-a",
        kind="kaggle",
        role="WORKER",
        durable_state=False,
        session_ephemeral=True,
        notes=("Independent authorized worker domain A.", "GPU must be measured per session."),
    ),
    ProviderContract(
        provider_id="kaggle-b",
        kind="kaggle",
        role="WORKER",
        durable_state=False,
        session_ephemeral=True,
        notes=("Independent authorized worker domain B.", "Not a quota bypass for A.", "Not bound until authenticated."),
    ),
    ProviderContract(
        provider_id="colab",
        kind="colab",
        role="WORKER",
        durable_state=False,
        notes=("Gym muscle. Not C5.",),
    ),
    ProviderContract(
        provider_id="cursor-cloud-vm",
        kind="cursor",
        role="WORKER",
        durable_state=False,
        notes=("This executor VM. Temporary C2. Not C5.",),
    ),
    ProviderContract(
        provider_id="founder-laptop",
        kind="laptop",
        role="CONTROL_PLANE",
        session_ephemeral=False,
        notes=("Control plane only. Not the persistent brain.",),
    ),
)


def get_provider(provider_id: str) -> ProviderContract:
    for row in PROVIDERS:
        if row.provider_id == provider_id:
            return row
    raise KeyError(provider_id)


def catalog() -> list[dict[str, Any]]:
    return [row.as_dict() for row in PROVIDERS]


NOT_PROVEN = "NOT_PROVEN"
RUNTIME_UNCERTAIN = "RUNTIME_UNCERTAIN"


def _capacity_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result):
        return None
    if result < 0:
        return None
    return result


def derive_capacity_bound(
    *,
    quota_available: Any = UNKNOWN,
    free_entitlement: Any = UNKNOWN,
    policy_budget: Any = UNKNOWN,
    unit: str = "COUNT",
) -> dict[str, Any]:
    quota = _capacity_number(quota_available)
    entitlement = _capacity_number(free_entitlement)
    budget = _capacity_number(policy_budget)
    if quota is None or entitlement is None or budget is None:
        allocatable: Any = NOT_PROVEN
    else:
        allocatable = min(quota, entitlement, budget)
    return {
        "unit": unit,
        "quota_available": quota_available,
        "free_entitlement": free_entitlement,
        "policy_budget": policy_budget,
        "allocatable": allocatable,
        "physical_capacity_state": RUNTIME_UNCERTAIN,
        "observed_runtime_capacity": UNKNOWN,
        "schedulable": NOT_PROVEN,
        "laws": [
            "QUOTA_AVAILABLE_NE_FREE_ENTITLEMENT",
            "FREE_ENTITLEMENT_NE_PHYSICAL_CAPACITY",
            "PHYSICAL_CAPACITY_NE_WORKER_READY",
            "ALLOCATABLE_REQUIRES_ALL_BOUNDS_PROVEN",
            "RUNTIME_CAPACITY_REQUIRES_RUNTIME_EVIDENCE",
            "UNKNOWN_NE_ZERO",
            "NOT_PROVEN_NE_FALSE",
        ],
    }


def apply_runtime_capacity(bound: dict[str, Any], observed_runtime_capacity: Any) -> dict[str, Any]:
    result = dict(bound)
    observed = _capacity_number(observed_runtime_capacity)
    allocatable = _capacity_number(result.get("allocatable"))
    if observed is None:
        result["physical_capacity_state"] = RUNTIME_UNCERTAIN
        result["observed_runtime_capacity"] = UNKNOWN
        result["schedulable"] = NOT_PROVEN
        return result
    result["physical_capacity_state"] = "RUNTIME_PROVEN"
    result["observed_runtime_capacity"] = observed
    if allocatable is None:
        result["schedulable"] = NOT_PROVEN
    else:
        result["schedulable"] = min(allocatable, observed)
    return result


def normalize_capacity_bounds(bounds: dict[str, Any] | None) -> dict[str, Any]:
    if bounds is None:
        return {}
    if not isinstance(bounds, dict):
        raise TypeError("CAPACITY_BOUNDS_MUST_BE_MAPPING")
    result: dict[str, Any] = {}
    for dimension, payload in bounds.items():
        if not isinstance(payload, dict):
            raise TypeError("CAPACITY_BOUND_MUST_BE_MAPPING::" + str(dimension))
        result[str(dimension)] = derive_capacity_bound(
            quota_available=payload.get("quota_available", UNKNOWN),
            free_entitlement=payload.get("free_entitlement", UNKNOWN),
            policy_budget=payload.get("policy_budget", UNKNOWN),
            unit=str(payload.get("unit", "COUNT")),
        )
    return result
