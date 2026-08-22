"""Provider identity. A compute host is never C5 and never the persistent brain."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
            "law": list(LAWS),
        }


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
