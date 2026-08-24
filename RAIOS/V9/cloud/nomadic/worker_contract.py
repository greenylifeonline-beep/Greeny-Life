"""Worker identity and lifecycle. Workers execute leased jobs. They are not C5."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import LIFECYCLE, LAWS
from .provider_contract import UNKNOWN


@dataclass(frozen=True)
class WorkerContract:
    worker_id: str
    provider_id: str
    account_bound: bool
    is_c5: bool = False
    persistent_brain: bool = False
    workspace: str = UNKNOWN
    declared_capabilities: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        if self.is_c5 or self.persistent_brain:
            raise ValueError("WORKER_NE_C5")
        return {
            "worker_id": self.worker_id,
            "provider_id": self.provider_id,
            "account_bound": self.account_bound,
            "is_c5": False,
            "persistent_brain": False,
            "workspace": self.workspace,
            "declared_capabilities": list(self.declared_capabilities),
            "lifecycle": list(LIFECYCLE),
            "law": list(LAWS),
        }


WORKERS = (
    WorkerContract("KAGGLE_A", "kaggle-a", account_bound=False),
    WorkerContract("KAGGLE_B", "kaggle-b", account_bound=False),
    WorkerContract("LOCAL_SIM_A", "cursor-cloud-vm", account_bound=True),
    WorkerContract("LOCAL_SIM_B", "cursor-cloud-vm", account_bound=True),
)


def get_worker(worker_id: str) -> WorkerContract:
    for row in WORKERS:
        if row.worker_id == worker_id:
            return row
    raise KeyError(worker_id)


def bind_account(worker_id: str, bound: bool) -> dict[str, Any]:
    """Return a receipt. Does not invent live Kaggle auth."""
    worker = get_worker(worker_id)
    return {
        "worker_id": worker.worker_id,
        "provider_id": worker.provider_id,
        "account_bound": bool(bound),
        "is_c5": False,
        "proven_worker": False,
        "note": "Binding is a declaration. Proven requires a live session receipt.",
        "law": list(LAWS),
    }
