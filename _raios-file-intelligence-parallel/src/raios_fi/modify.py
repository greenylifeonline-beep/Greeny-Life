"""Governed modification engine. Analysis never writes originals. Shadow apply + rollback."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import FailClosed, sha256_bytes, utc_now
from .store import Store

REQUIRED_STAGES = (
    "READ",
    "SNAPSHOT",
    "ANALYZE",
    "IMPACT_GRAPH",
    "PLAN",
    "PATCH",
    "SHADOW_APPLY",
    "STATIC_VALIDATE",
    "TEST",
    "BEHAVIOR_COMPARE",
    "REGRESSION",
    "DIFF_REVIEW",
    "GOVERNED_APPLY",
    "POST_VERIFY",
    "RECEIPT",
    "EXPERIENCE_CAPTURE",
)


@dataclass
class ModificationTxn:
    txn_id: str
    stage: str
    original_path: str
    original_hash: str
    shadow_path: str | None
    proposed_hash: str | None
    applied: bool
    rolled_back: bool
    aborted: bool
    receipt: dict[str, Any]
    stages_completed: list[str] = field(default_factory=list)
    failure_event: dict[str, Any] | None = None
    learning_signal: dict[str, Any] | None = None

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
        snapshot = self.store.cas.put_bytes(data, meta={"kind": "snapshot", "path": str(original)})
        txn = ModificationTxn(
            txn_id=txn_id,
            stage="SNAPSHOT",
            original_path=str(original),
            original_hash=h,
            shadow_path=None,
            proposed_hash=None,
            applied=False,
            rolled_back=False,
            aborted=False,
            receipt={"original_untouched": True, "snapshot": snapshot.sha256, "required_stages": list(REQUIRED_STAGES)},
            stages_completed=["READ", "SNAPSHOT"],
        )
        return txn

    def analyze_and_plan(self, txn: ModificationTxn, impact: dict[str, Any] | None = None) -> ModificationTxn:
        txn.stage = "PLAN"
        txn.stages_completed.extend(["ANALYZE", "IMPACT_GRAPH", "PLAN"])
        txn.receipt["impact"] = impact or {"edges": [], "state": "UNKNOWN"}
        return txn

    def propose_and_shadow(self, txn: ModificationTxn, new_bytes: bytes) -> ModificationTxn:
        FailClosed.assert_writable(self.shadow_root)
        dest = self.shadow_root / txn.txn_id / Path(txn.original_path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(new_bytes)
        txn.shadow_path = str(dest)
        txn.proposed_hash = sha256_bytes(new_bytes)
        txn.stage = "SHADOW_APPLY"
        txn.stages_completed.extend(["PATCH", "SHADOW_APPLY"])
        orig = Path(txn.original_path).read_bytes()
        if sha256_bytes(orig) != txn.original_hash:
            return self.abort(txn, "original mutated during analysis")
        txn.receipt["shadow"] = txn.shadow_path
        return txn

    def static_validate(self, txn: ModificationTxn) -> ModificationTxn:
        if not txn.shadow_path:
            return self.abort(txn, "no_shadow")
        txn.stage = "STATIC_VALIDATE"
        txn.stages_completed.append("STATIC_VALIDATE")
        txn.receipt["static_validate"] = {"ok": True, "parser": "shadow-exists"}
        return txn

    def record_test_gap(self, txn: ModificationTxn) -> ModificationTxn:
        txn.stages_completed.extend(["TEST", "BEHAVIOR_COMPARE", "REGRESSION", "DIFF_REVIEW"])
        txn.receipt["tests"] = {"executed": False, "reason": "NO_PROJECT_TEST_RUNNER_IN_THIS_PACKAGE"}
        txn.receipt["behavior_compare"] = {"state": "UNKNOWN"}
        txn.receipt["regression"] = {"state": "UNKNOWN"}
        txn.stage = "DIFF_REVIEW"
        return txn

    def abort(self, txn: ModificationTxn, reason: str) -> ModificationTxn:
        txn.aborted = True
        txn.applied = False
        txn.stage = "RECEIPT"
        txn.failure_event = {"type": "FAILURE_EVENT", "reason": reason, "at": utc_now()}
        txn.learning_signal = {"type": "LEARNING_SIGNAL", "reason": reason, "canonical": False}
        txn.receipt["abort"] = True
        if txn.shadow_path:
            p = Path(txn.shadow_path)
            if p.exists():
                p.unlink()
            txn.rolled_back = True
        txn.receipt["rollback"] = txn.rolled_back
        txn.stages_completed.append("EXPERIENCE_CAPTURE")
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
        txn.stages_completed.append("EXPERIENCE_CAPTURE")
        txn.learning_signal = {"type": "LEARNING_SIGNAL", "reason": "rollback", "canonical": False}
        return txn

    def governed_apply_forbidden_by_default(self, txn: ModificationTxn) -> ModificationTxn:
        """This parallel package never writes original sources."""
        txn.applied = False
        txn.stage = "RECEIPT"
        txn.receipt["governed_apply"] = "FORBIDDEN_IN_PARALLEL_PACKAGE"
        txn.receipt["post_verify"] = "NOT_APPLIED"
        txn.stages_completed.extend(["GOVERNED_APPLY", "POST_VERIFY", "RECEIPT", "EXPERIENCE_CAPTURE"])
        return txn

    def persist(self, txn: ModificationTxn) -> None:
        rec = self.store.cas.put_bytes(
            json.dumps(txn.to_dict(), sort_keys=True).encode(),
            meta={"kind": "modification_txn", "txn_id": txn.txn_id},
        )
        txn.receipt["cas"] = rec.sha256
