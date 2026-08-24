"""Provider identity. A compute host is never C5 and never the persistent brain."""
from __future__ import annotations

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

    def as_dict(self) -> dict[str, Any]:
        row = dict(self.__dict__)
        row["model_cache"] = list(self.model_cache)
        row["task_classes"] = list(self.task_classes)
        return row


def normalize_resource_record(
    payload: ResourceCapabilityRecord | dict[str, Any],
) -> dict[str, Any]:

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

        # Absence of evidence is UNKNOWN.
        # It must never silently become numeric zero or False.
        if value is None:
            value = UNKNOWN

        if name in {"model_cache", "task_classes"}:
            if value == UNKNOWN:
                value = []
            elif isinstance(value, tuple):
                value = list(value)
            elif not isinstance(value, list):
                value = [str(value)]

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
