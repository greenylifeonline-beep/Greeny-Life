"""Governed local weight-merge backend for canonical V9 Model Lab.

Execution is opt-in, local-path only, CPU-only, and provenance-receipted.
No model download, provider dispatch, paid resource, or canonical promotion occurs.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

POLICY = "NO_BLIND_WEIGHT_MERGE"
ALLOW_ENV = "RAIOS_WEIGHT_MERGE_ALLOW_EXECUTE"


def _stable_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    for item in files:
        digest.update(item.relative_to(path).as_posix().encode() if path.is_dir() else item.name.encode())
        with item.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def discover_mergekit() -> dict[str, Any]:
    command = os.getenv("RAIOS_MERGEKIT_COMMAND", "").strip()
    found = command or shutil.which("mergekit-yaml") or shutil.which("mergekit")
    return {
        "available": bool(found),
        "source": "environment" if command else ("path" if found else "missing"),
        "command": found,
        "installed_by_raios": False,
        "network_acquisition": False,
    }


def _inputs(plan: dict[str, Any]) -> list[tuple[Path, float]]:
    rows: list[tuple[Path, float]] = []
    for item in plan.get("inputs") or []:
        raw = item.get("path") or item.get("model_id")
        path = Path(str(raw or "")).expanduser().resolve()
        if not raw or not path.exists():
            raise FileNotFoundError(raw or "missing model path")
        rows.append((path, float(item.get("weight", 0))))
    if len(rows) < 2:
        raise ValueError("At least two local model inputs are required")
    if sum(weight for _, weight in rows) <= 0:
        raise ValueError("Weight sum must be positive")
    return rows
def _tensor_files(root: Path) -> list[Path]:
    files = [root] if root.is_file() and root.suffix == ".safetensors" else sorted(root.rglob("*.safetensors"))
    if not files:
        raise FileNotFoundError(f"No safetensors found in {root}")
    return files


def _load(root: Path) -> dict[str, Any]:
    from safetensors import safe_open

    tensors: dict[str, Any] = {}
    for file in _tensor_files(root):
        with safe_open(str(file), framework="numpy") as handle:
            for key in handle.keys():
                if key in tensors:
                    raise ValueError(f"Duplicate tensor name: {key}")
                tensors[key] = handle.get_tensor(key)
    return tensors


def build_receipt(plan: dict[str, Any], rows: list[tuple[Path, float]], **state: Any) -> dict[str, Any]:
    public_plan = {
        "strategy": str(plan.get("strategy") or "LINEAR").upper(),
        "inputs": [{"path": str(path), "weight": weight} for path, weight in rows],
    }
    return {
        "schema": "raios.v9.weight-merge.receipt.v1",
        "policy": POLICY,
        "plan_hash": hashlib.sha256(_stable_json(public_plan)).hexdigest(),
        "inputs": [{"path": str(path), "sha256": sha256_path(path)} for path, _ in rows],
        "paid_resource_created": False,
        "gpu_session_started": False,
        "model_downloaded": False,
        "automatic_canonical_promotion": False,
        **state,
    }


def execute_cpu_linear(plan: dict[str, Any]) -> dict[str, Any]:
    strategy = str(plan.get("strategy") or "").upper()
    if strategy != "LINEAR":
        return {"ok": False, "executed": False, "reason": "UNSUPPORTED_LOCAL_STRATEGY", "weights_touched": False}
    try:
        rows = _inputs(plan)
    except (ValueError, TypeError, FileNotFoundError) as exc:
        return {"ok": False, "executed": False, "reason": str(exc), "weights_touched": False}

    dry_run = bool(plan.get("dry_run", True))
    allowed = bool(plan.get("allow_execute", False)) or os.getenv(ALLOW_ENV, "").lower() in {"1", "true", "yes"}
    receipt = build_receipt(plan, rows, status="DRY_RUN" if dry_run else "AWAITING_AUTHORITY", executed=False)
    if dry_run:
        return {"ok": True, "executed": False, "reason": "DRY_RUN", "weights_touched": False, "receipt": receipt}
    if not allowed:
        return {"ok": False, "executed": False, "reason": POLICY, "weights_touched": False, "receipt": receipt}

    output = Path(str(plan.get("output_path") or "")).expanduser().resolve()
    if not plan.get("output_path"):
        return {"ok": False, "executed": False, "reason": "OUTPUT_PATH_REQUIRED", "weights_touched": False, "receipt": receipt}
    import numpy as np
    from safetensors.numpy import save_file

    loaded = [_load(path) for path, _ in rows]
    keys = sorted(loaded[0])
    if any(set(tensors) != set(keys) for tensors in loaded[1:]):
        return {"ok": False, "executed": False, "reason": "TENSOR_KEYS_MISMATCH", "weights_touched": False, "receipt": receipt}
    weights = [weight / sum(row[1] for row in rows) for _, weight in rows]
    merged: dict[str, Any] = {}
    for key in keys:
        shapes = {tuple(tensors[key].shape) for tensors in loaded}
        if len(shapes) != 1:
            return {"ok": False, "executed": False, "reason": f"TENSOR_SHAPE_MISMATCH:{key}", "weights_touched": False, "receipt": receipt}
        merged[key] = sum(np.asarray(tensors[key], dtype=np.float32) * weight for tensors, weight in zip(loaded, weights))

    output.mkdir(parents=True, exist_ok=True)
    destination = output / "model.safetensors"
    save_file(merged, str(destination))
    receipt = build_receipt(
        plan,
        rows,
        status="MERGED",
        executed=True,
        backend="CPU_LINEAR",
        output_sha256=sha256_path(destination),
        tensor_count=len(merged),
    )
    receipt_path = output / "RAIOS-WEIGHT-MERGE-RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "executed": True,
        "reason": "EXPLICIT_LOCAL_CPU_LINEAR",
        "weights_touched": True,
        "output_path": str(output),
        "receipt_path": str(receipt_path),
        "receipt": receipt,
    }
