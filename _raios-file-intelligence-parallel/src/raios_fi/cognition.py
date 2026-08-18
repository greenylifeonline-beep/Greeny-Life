"""Conscious/subconscious contract. Same organism identity; no CCEE WAL writes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ORGANISM_ID, PACKAGE, repo_root_from
from .duplicates import duplicate_groups
from .idle import IdleLoop
from .store import IndexStore


HARVEST_REL = "_raios-a17-native-cortex/experience/raw/teacher-harvest"
CCEE_WAL_REL = "_raios-a17-native-cortex/ccee/var"


def shared_cognitive_state(repo: Path | None = None, store: IndexStore | None = None) -> dict[str, Any]:
    repo = repo or repo_root_from()
    harvest = repo / HARVEST_REL
    harvest_present = harvest.exists() and any(harvest.rglob("*"))
    ccee = repo / CCEE_WAL_REL
    return {
        "organism_id": ORGANISM_ID,
        "package": PACKAGE,
        "conscious": {
            "owner": "qwen-cortex",
            "invoked": False,
            "reason": "OLLAMA_MISSING_OR_NOT_REQUESTED",
        },
        "subconscious": {
            "owner": "file-intelligence-index",
            "work": [
                "incremental_scan",
                "hashing",
                "type_detection",
                "symbol_refresh",
                "duplicate_detection",
                "version_comparison",
            ],
            "model_calls": 0,
        },
        "shared_identity": True,
        "ccee_wal_writes": False,
        "canonical_writes": False,
        "storage_merged_with_ccee": False,
        "ccee_var_path": str(ccee),
        "storage_note": "IDENTITY_SHARED_STORAGE_NOT_MERGED; collision guard blocks CCEE var",
        "teacher_harvest": {
            "path": str(harvest),
            "status": "PRESENT_READ_ONLY" if harvest_present else "MISSING",
            "observations_invented": False,
        },
        "duplicate_groups": duplicate_groups(store) if store is not None else [],
        "idle": IdleLoop().run_once(lambda: {"ok": True}),
        "status": "PENDING_RUNTIME_VALIDATION",
    }


@dataclass(frozen=True)
class SharedCognitiveState:
    organism: str
    ccee_wal_writes: bool
    canonical_writes: bool
    payload: dict[str, Any]

    @classmethod
    def snapshot(cls, repo: Path | None = None, store: IndexStore | None = None) -> "SharedCognitiveState":
        payload = shared_cognitive_state(repo, store)
        return cls(
            organism=str(payload["organism_id"]),
            ccee_wal_writes=bool(payload["ccee_wal_writes"]),
            canonical_writes=bool(payload["canonical_writes"]),
            payload=payload,
        )


def idle_continue(*, foreground_busy: bool = False) -> dict[str, Any]:
    loop = IdleLoop()
    if foreground_busy:
        result = loop.tick("user-foreground", foreground=True)
        return {"preempted": True, "result": result, "model_calls": 0, "qwen_invoked": False}
    return {
        "preempted": False,
        "result": loop.run_once(lambda: {"ok": True}),
        "model_calls": 0,
        "qwen_invoked": False,
    }
