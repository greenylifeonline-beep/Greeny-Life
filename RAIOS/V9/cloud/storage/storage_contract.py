"""Provider-neutral storage contract. Never print secrets."""
from __future__ import annotations

from typing import Any, Protocol

STATES = (
    "ABSENT",
    "REFERENCED",
    "AUTHENTICATED",
    "READABLE",
    "WRITABLE",
    "CAPACITY_KNOWN",
    "CAPACITY_UNKNOWN",
    "LIVE_TESTED",
    "BLOCKED_AUTH",
    "WORKER_CACHE",
)

CATEGORIES = (
    "COMPUTE",
    "MODEL_HOSTING",
    "OBJECT_STORAGE",
    "DATASET_STORAGE",
    "SOURCE_CONTROL",
    "PERSISTENT_STATE",
    "BACKUP",
    "EPHEMERAL_SCRATCH",
)


class StorageBackend(Protocol):
    backend_id: str
    category: str

    def classify(self) -> dict[str, Any]:
        ...

    def put(self, content: bytes, *, name: str) -> dict[str, Any]:
        ...

    def get(self, object_id: str) -> dict[str, Any]:
        ...

    def delete(self, object_id: str) -> dict[str, Any]:
        ...
