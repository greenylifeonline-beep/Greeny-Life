"""Governed modification engine. Analysis never writes originals. Shadow apply + rollback."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from raios_fi.config import FailClosed, sha256_bytes
from raios_fi.store import Store

Stage = Literal[
    "READ",
    "ANALYZE",
    "PLAN",
    "IMPACT_GRAPH",
    "PROPOSE_PATCH",
    "SHADOW_APPLY",
    "TEST",
    "DIFF_REVIEW",
    "GOVERNED_APPLY",
    "RECEIPT",
]


@dataclass
class ModificationTxn:
    txn_id: str
    stage: Stage
    original_path: str
    original_hash: str
    shadow_path: str | None
    proposed_hash: str | None
    applied: bool
    rolled_back: bool
    receipt: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModificationEngine:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.shadow_root = store.root / "shadow"

    def begin(self, original: Path) -> ModificationTxn:
        FailClosed.assert_writable(self.shadow_root)
        data = original.read_bytes()
        h = sha256_bytes(data)
        txn_id = sha256_bytes(f"{original}:{h}".encode())[:16]
        return ModificationTxn(
            txn_id=txn_id,
            stage="READ",
            original_path=str(original),
            original_hash=h,
            shadow_path=None,
            proposed_hash=None,
            applied=False,
            rolled_back=False,
            receipt={"original_untouched": True},
        )

    def propose_and_shadow(self, txn: ModificationTxn, new_bytes: bytes) -> ModificationTxn:
        FailClosed.assert_writable(self.shadow_root)
        dest = self.shadow_root / txn.txn_id / Path(txn.original_path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(new_bytes)
        txn.shadow_path = str(dest)
        txn.proposed_hash = sha256_bytes(new_bytes)
        txn.stage = "SHADOW_APPLY"
        # Original must still match.
        orig = Path(txn.original_path).read_bytes()
        if sha256_bytes(orig) != txn.original_hash:
            raise RuntimeError("original mutated during analysis")
        txn.receipt["shadow"] = txn.shadow_path
        return txn

    def rollback(self, txn: ModificationTxn) -> ModificationTxn:
        if txn.shadow_path:
            p = Path(txn.shadow_path)
            if p.exists():
                p.unlink()
        txn.stage = "RECEIPT"
        txn.rolled_back = True
        txn.applied = False
        txn.receipt["rollback"] = True
        return txn

    def governed_apply_forbidden_by_default(self, txn: ModificationTxn) -> ModificationTxn:
        """This parallel package never writes original sources."""
        txn.applied = False
        txn.stage = "RECEIPT"
        txn.receipt["governed_apply"] = "FORBIDDEN_IN_PARALLEL_PACKAGE"
        return txn

    def persist(self, txn: ModificationTxn) -> None:
        rec = self.store.cas.put_bytes(
            json.dumps(txn.to_dict(), sort_keys=True).encode(),
            meta={"kind": "modification_txn", "txn_id": txn.txn_id},
        )
        txn.receipt["cas"] = rec.sha256
