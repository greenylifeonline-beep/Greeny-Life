from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HEAVY_LOCAL_BYTES = 10 * 1024**3


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def runtime_model() -> str | None:
    configured = os.getenv("RAIOS_C5_MODEL", "").strip()
    if configured:
        return configured
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/health", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload.get("model") or "").strip() or None
    except Exception:
        return None


def ollama_models() -> list[dict[str, Any]]:
    try:
        proc = subprocess.run(
            ["ollama", "list"], text=True, capture_output=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    return [
        {"name": parts[0], "size_text": " ".join(parts[2:4])}
        for line in proc.stdout.splitlines()[1:]
        if (parts := line.split())
    ]


def classify_records(records: list[dict[str, Any]], *, runtime_model: str | None) -> list[dict[str, Any]]:
    output = []
    for record in records:
        name = str(record.get("name") or "")
        size = int(record.get("size_bytes") or 0)
        required = bool(runtime_model and name == runtime_model)
        output.append({
            **record,
            "name": name,
            "size_bytes": size,
            "heavy_local": size >= HEAVY_LOCAL_BYTES,
            "runtime_required": required,
            "remote_migration_required": size >= HEAVY_LOCAL_BYTES,
            "source_removable": not required,
            "canonical_role": "ACTIVE_RUNTIME_MODEL" if required else "LOCAL_MODEL_ASSET",
        })
    return output


def classify_local_models(repo_root: str | Path, runtime_root: str | Path) -> dict[str, Any]:
    runtime_root = Path(runtime_root).expanduser().resolve()
    report_dir = runtime_root / "model-ecology"
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = classify_records(ollama_models(), runtime_model=runtime_model())
    result = {
        "schema": "raios.model-ecology.v1",
        "generated_at": utc(),
        "canonical_repo": str(Path(repo_root).resolve()),
        "runtime_root": str(runtime_root),
        "local_model_count": len(rows),
        "heavy_local_count": sum(bool(x["heavy_local"]) for x in rows),
        "runtime_dependency_count": sum(bool(x["runtime_required"]) for x in rows),
        "remote_migration_required_count": sum(bool(x["remote_migration_required"]) for x in rows),
        "source_removable_true_count": sum(bool(x["source_removable"]) for x in rows),
        "models": rows,
        "canonical_repo_mutation": False,
        "model_deleted": False,
        "model_downloaded": False,
    }
    report = report_dir / "MODEL-ECOLOGY.json"
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result["report_path"] = str(report)
    return result
