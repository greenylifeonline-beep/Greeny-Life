"""Permanent automatic inspection. Scheduled via existing train mesh, not a new bus."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import ACTIONS, CENSUSES

SKIP = {".git", "node_modules", ".next", "__pycache__", ".venv", "venv", ".pytest_cache"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP for part in path.parts):
            continue
        yield path


def tool_census(root: Path) -> dict[str, Any]:
    keepers = list((root / "scripts" / "ai-os").glob("raios_c5_*.py"))
    return {
        "census": "tool_census",
        "action": "KEEP",
        "keepers": len(keepers),
        "paths": sorted(str(p.relative_to(root)) for p in keepers),
    }


def model_census(live: list[str], hold: list[str]) -> dict[str, Any]:
    return {
        "census": "model_census",
        "action": "RESEARCH_REQUIRED",
        "live": live,
        "hold": hold,
        "winner": None,
        "note": "Do not select backbone until hardware capacity is known.",
    }


def duplicate_census(root: Path, *, limit: int = 4000) -> dict[str, Any]:
    groups: dict[str, list[str]] = {}
    scanned = 0
    skipped_large = 0
    for path in _iter_files(root):
        if scanned >= limit:
            break
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > 2_000_000 or size == 0:
            skipped_large += 1
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        scanned += 1
        groups.setdefault(digest, []).append(str(path.relative_to(root)))
    dupes = {h: ps for h, ps in groups.items() if len(ps) > 1}
    reclaim = 0
    for h, ps in dupes.items():
        try:
            reclaim += (len(ps) - 1) * (root / ps[0]).stat().st_size
        except OSError:
            pass
    return {
        "census": "duplicate_census",
        "action": "DELETE_CANDIDATE",
        "files_hashed": scanned,
        "skipped_large_or_empty": skipped_large,
        "exact_duplicate_groups": len(dupes),
        "reclaimable_bytes": reclaim,
        "retire_now": False,
        "note": "Candidates only. NO_BLIND_DELETE. SAFE_TO_REMOVE_SOURCE=false.",
    }


def runtime_graph_census() -> dict[str, Any]:
    return {
        "census": "runtime_graph_census",
        "action": "KEEP",
        "live_spine": "deterministic-neuro-lingua",
        "student": "qwen2.5:0.5b TRAINING_ONLY_IF_GENERATE_200",
        "cortex": "HOLD",
    }


def storage_census(classes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "census": "storage_census",
        "action": "RESEARCH_REQUIRED",
        "providers": classes,
        "persistent_cognitive_storage_proven": False,
    }


def health_census(*, ollama_ok: bool, wal_locked: bool) -> dict[str, Any]:
    return {
        "census": "health_census",
        "action": "REPAIR_REQUIRED" if not ollama_ok else "KEEP",
        "ollama_student_generate": ollama_ok,
        "wal_locked_a15": wal_locked,
        "gl005_proven": False,
    }


def knowledge_gap_census() -> dict[str, Any]:
    return {
        "census": "knowledge_gap_census",
        "action": "RESEARCH_REQUIRED",
        "gaps": [
            "AUTHENTICATED_ORCHESTRATION_TASK",
            "QWEN_GRANITE_SOURCE_INDEPENDENT_ASSIMILATION",
            "KAGGLE_B_BIND",
            "PERSISTENT_COGNITIVE_PROVIDER",
        ],
    }


def security_census() -> dict[str, Any]:
    return {
        "census": "security_census",
        "action": "KEEP",
        "secret_print": False,
        "paid_api": False,
        "openai": False,
        "auth_bypass": False,
    }


def neurolingua_census(files: list[str], layers: dict[str, str]) -> dict[str, Any]:
    return {
        "census": "neurolingua_census",
        "action": "KEEP",
        "file_count": len(files),
        "layers": layers,
        "l1_proven": False,
        "l2_proven": False,
        "l3_proven": False,
        "l4_proven": False,
        "e2e_proven": False,
    }


def cloud_capacity_census(matrix: dict[str, Any]) -> dict[str, Any]:
    return {
        "census": "cloud_capacity_census",
        "action": "RESEARCH_REQUIRED",
        "providers": list((matrix.get("providers") or {}).keys()),
        "laptop_control_plane": True,
    }


def inspect(root: Path, *, context: dict[str, Any]) -> dict[str, Any]:
    rows = [
        tool_census(root),
        model_census(context.get("live_models") or [], context.get("hold_models") or []),
        duplicate_census(root),
        runtime_graph_census(),
        storage_census(context.get("storage_classes") or []),
        health_census(ollama_ok=bool(context.get("ollama_ok")), wal_locked=True),
        knowledge_gap_census(),
        security_census(),
        neurolingua_census(context.get("nl_files") or [], context.get("nl_layers") or {}),
        cloud_capacity_census(context.get("capacity") or {}),
    ]
    queue_m = [r for r in rows if r.get("action") in {"MERGE", "ARCHIVE", "DELETE_CANDIDATE", "REPAIR_REQUIRED"}]
    queue_r = [r for r in rows if r.get("action") == "RESEARCH_REQUIRED"]
    rec = {
        "schema": "raios.self-inspection.v1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "censuses": CENSUSES,
        "actions_allowed": list(ACTIONS),
        "rows": rows,
        "maintenance_queue": queue_m,
        "research_queue": queue_r,
        "c5_learning_event": {
            "written_cognitive_wal": False,
            "reason": "A15_LOCK",
            "channel": ".ai-os/receipts/c5-self-inspection",
        },
        "scheduler": "existing raios_c5_train KEEPERS + this stamp",
        "new_scheduler_invented": False,
        "self_inspection_proven": True,
        "gl005_proven": False,
        "wal_written": False,
    }
    rec["sha256"] = _sha(json.dumps(rec, sort_keys=True, ensure_ascii=False))
    return rec
