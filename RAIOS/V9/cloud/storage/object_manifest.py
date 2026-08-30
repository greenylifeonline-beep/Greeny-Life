"""Object namespaces. Architecture is provider-neutral."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .content_addressing import object_id

HOT = ("wal", "jobs", "leases", "queues", "runtime-state")
WARM = ("knowledge", "skills", "experience", "graphs", "indexes", "council-wal", "receipts", "checkpoints")
COLD = ("books", "raw-documents", "datasets", "research", "model-artifacts", "archives")

NAMESPACES = {"HOT": HOT, "WARM": WARM, "COLD": COLD}


@dataclass(frozen=True)
class ObjectManifest:
    object_id: str
    namespace: str
    name: str
    bytes: int
    provider: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "namespace": self.namespace,
            "name": self.name,
            "bytes": self.bytes,
            "provider": self.provider,
        }


def classify_name(name: str) -> str:
    for tier, names in NAMESPACES.items():
        if name in names:
            return tier
    return "UNKNOWN"


def manifest_for(content: bytes, *, name: str, provider: str | None = None) -> ObjectManifest:
    tier = classify_name(name)
    ns = name if tier != "UNKNOWN" else f"UNKNOWN/{name}"
    return ObjectManifest(
        object_id=object_id(content),
        namespace=ns,
        name=name,
        bytes=len(content),
        provider=provider,
    )
