from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HEAVY_LOCAL_BYTES = 10 * 1024**3
SIZE_UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
MAIN_CORTEX_IDENTITY = "qwen3.6:35b-a3b"
MAIN_CORTEX_OWNER = "C1"
MAIN_CORTEX_STATE = "HOLD"
CATALOG_SAMPLE_LIMIT = 20
COPY_SYMBOL_LIMIT = 40
SYMBOL_MATRIX_PATH = Path(".ai-os/reports/inventory/RAIOS-DEEP-UNIQUE-VALUE-ASSIMILATION-C2/SYMBOL-LEVEL-MATRIX.json")
MODEL_HINTS = ("model", "ecology", "fabric", "ollama", "router", "qwen", "llm", "cortex")
ACCOUNT_IDS = (
    "KAGGLE_C1",
    "KAGGLE_PARTNER",
    "ORACLE_01",
    "LIGHTNING_01",
    "LIGHTNING_PARTNER",
    "COLAB_01",
    "MODAL_01",
    "MODAL_PARTNER",
    "LOCAL_AG",
)


def parse_size_text(value: str) -> int:
    parts = value.strip().upper().split()
    if len(parts) != 2 or parts[1] not in SIZE_UNITS:
        return 0
    try:
        return int(float(parts[0]) * SIZE_UNITS[parts[1]])
    except ValueError:
        return 0


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_main_cortex(name: str | None) -> bool:
    token = str(name or "").strip().lower()
    if not token:
        return False
    identity = MAIN_CORTEX_IDENTITY.lower()
    return token == identity or token.startswith("qwen3.6:35b")


def _live_accounts_enabled(explicit: bool | None) -> bool:
    if explicit is not None:
        return bool(explicit)
    return os.getenv("RAIOS_RESOURCE_LIVE", "").strip() == "1"


def _http_json(url: str, timeout: float = 2.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return {}


def _first_live_engine(payload: dict[str, Any]) -> str | None:
    direct = str(payload.get("model") or payload.get("student_model") or "").strip()
    if direct and not is_main_cortex(direct):
        return direct
    engines = payload.get("live_engines") or []
    if isinstance(engines, list):
        for item in engines:
            name = str(item or "").strip()
            if name and not is_main_cortex(name):
                return name
    return None


def c5_health() -> dict[str, Any]:
    return _http_json("http://127.0.0.1:8766/health", timeout=2.0)


def runtime_model() -> str | None:
    configured = os.getenv("RAIOS_C5_MODEL", "").strip() or os.getenv("RAIOS_STUDENT_MODEL", "").strip()
    if configured and not is_main_cortex(configured):
        return configured
    payload = c5_health()
    if payload:
        return _first_live_engine(payload)
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
    records = []
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        size_text = " ".join(parts[2:4])
        records.append({
            "name": parts[0],
            "size_text": size_text,
            "size_bytes": parse_size_text(size_text),
            "source_plane": "OLLAMA_LOCAL",
            "storage_location": "OLLAMA_LOCAL",
            "weight_present": True,
            "runtime_present": True,
        })
    return records


def _tcp_open(host: str, port: int, timeout: float = 0.8) -> bool:
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def ninerouter_catalog() -> dict[str, Any]:
    rec = {
        "health": "OFFLINE",
        "bind": "127.0.0.1:20128",
        "RESOURCE_AUTHORITY": False,
        "models_visible": 0,
        "catalog_sample": [],
        "executable_routed_models": 0,
        "paid_providers_connected": False,
        "catalog_ne_connected_providers": True,
        "tcp_open": _tcp_open("127.0.0.1", 20128),
    }
    if not rec["tcp_open"]:
        return rec
    health = _http_json("http://127.0.0.1:20128/api/health", timeout=8.0)
    models = _http_json("http://127.0.0.1:20128/v1/models", timeout=8.0)
    data = models.get("data") if isinstance(models.get("data"), list) else []
    names = [str(row.get("id") or "").strip() for row in data if isinstance(row, dict)]
    names = [name for name in names if name]
    rec["health"] = "ok" if health else "LISTENER_OK_HTTP_UNPROVEN"
    rec["models_visible"] = len(names) if names else int(health.get("models") or health.get("model_count") or 0)
    rec["catalog_sample"] = names[:CATALOG_SAMPLE_LIMIT]
    rec["http_health_present"] = bool(health)
    rec["tcp_ne_http_catalog"] = not bool(names)
    return rec


def copy_estate_model_symbols(repo_root: str | Path) -> list[dict[str, Any]]:
    path = Path(repo_root) / SYMBOL_MATRIX_PATH
    try:
        matrix = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return []
    rows = matrix.get("records") if isinstance(matrix, dict) else []
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("class") or "") != "UNIQUE_VALUE":
            continue
        blob = " ".join(str(row.get(k) or "") for k in ("id", "symbol", "path", "packet")).lower()
        if not any(hint in blob for hint in MODEL_HINTS):
            continue
        symbol = str(row.get("symbol") or row.get("id") or "").strip()
        if not symbol:
            continue
        out.append({
            "name": symbol,
            "model_id": symbol,
            "size_bytes": 0,
            "source_plane": "COPY_ESTATE_UNIQUE_VALUE",
            "storage_location": str(row.get("path") or "RETAINED_CATALOG"),
            "weight_present": False,
            "runtime_present": False,
            "copy_symbol_id": row.get("id"),
            "canonical_role_hint": "RETAINED_CATALOG",
        })
        if len(out) >= COPY_SYMBOL_LIMIT:
            break
    return out


def factory_source_index(runtime_root: str | Path) -> dict[str, Any]:
    path = Path(runtime_root) / "FACTORY-FABRIC-LATEST.json"
    empty = {"present": False, "factories": [], "status": "UNOBSERVED"}
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return empty
    factories = report.get("factories") if isinstance(report.get("factories"), dict) else {}
    return {
        "present": True,
        "status": report.get("status"),
        "factories": sorted(str(k) for k in factories.keys()),
        "generated_at": report.get("generated_at"),
        "paid_resource_created": False,
    }


def account_model_records(probes: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    kaggle = probes.get("KAGGLE_C1") or {}
    catalog = kaggle.get("qwen_public_model_catalog") if isinstance(kaggle.get("qwen_public_model_catalog"), dict) else {}
    for ref in (catalog.get("model_refs") or [])[:CATALOG_SAMPLE_LIMIT]:
        name = str(ref or "").strip()
        if not name:
            continue
        records.append({
            "name": name,
            "size_bytes": 0,
            "source_plane": "KAGGLE_C1",
            "storage_location": "KAGGLE_PUBLIC_CATALOG",
            "weight_present": False,
            "runtime_present": False,
            "account_owned": False,
        })
    lightning = probes.get("LIGHTNING_PARTNER") or {}
    model_id = str(lightning.get("model_id") or lightning.get("target_model") or "lightning-ai/Qwen3.8-27B").strip()
    if lightning:
        records.append({
            "name": model_id,
            "size_bytes": 0,
            "source_plane": "LIGHTNING_PARTNER",
            "storage_location": "LIGHTNING_MODEL_API",
            "weight_present": False,
            "runtime_present": False,
            "dispatch_allowed": bool(lightning.get("DISPATCH_ALLOWED")),
        })
    return records


def account_bindings(probes: dict[str, Any]) -> list[dict[str, Any]]:
    bound_ok = {
        "REACHABLE",
        "PARTIAL",
        "REACHABLE_CREDENTIAL_PRESENT",
        "AUTHENTICATED_NOT_ENTITLED",
        "REACHABLE_PRIOR_PROOF_ONLY",
    }
    out = []
    for account_id in ACCOUNT_IDS:
        row = probes.get(account_id) or {}
        status = str(row.get("status") or row.get("AUTH_RESULT") or "UNOBSERVED")
        out.append({
            "account_id": account_id,
            "status": status,
            "bound": status in bound_ok,
            "IDENTITY_PROOF": row.get("IDENTITY_PROOF"),
            "DISPATCH_ALLOWED": bool(row.get("DISPATCH_ALLOWED")),
            "PAID_RESOURCE_CREATED": False,
            "GPU_SESSION_STARTED": False,
        })
    ninerouter = probes.get("NINEROUTER") or {}
    out.append({
        "account_id": "NINEROUTER",
        "status": ninerouter.get("health") or "UNOBSERVED",
        "bound": str(ninerouter.get("health") or "") in {"ok", "DEGRADED"},
        "RESOURCE_AUTHORITY": False,
        "models_visible": ninerouter.get("models_visible"),
        "PAID_RESOURCE_CREATED": False,
        "GPU_SESSION_STARTED": False,
    })
    return out


def classify_records(records: list[dict[str, Any]], *, runtime_model: str | None) -> list[dict[str, Any]]:
    output = []
    student = runtime_model if runtime_model and not is_main_cortex(runtime_model) else None
    for record in records:
        name = str(record.get("name") or record.get("model_id") or "")
        size = int(record.get("size_bytes") or 0)
        weight_present = bool(record.get("weight_present", True))
        runtime_present = bool(record.get("runtime_present", True))
        cortex = is_main_cortex(name)
        required = bool(student and name == student and not cortex)
        heavy = size >= HEAVY_LOCAL_BYTES
        migration_proven = bool(record.get("migration_proven", False))
        if cortex:
            role = "MAIN_CORTEX_C1_OWNED"
            execution_class = "HOLD_C1_OWNED"
        elif required:
            role = "ACTIVE_RUNTIME_MODEL"
        elif str(record.get("canonical_role_hint") or "") == "RETAINED_CATALOG":
            role = "RETAINED_CATALOG"
        elif not weight_present:
            role = "REMOTE_ACCOUNT_VISIBLE" if record.get("source_plane") not in {None, "OLLAMA_LOCAL"} else "IDENTITY_HOLD_WEIGHTS_ABSENT"
        elif heavy:
            role = "REMOTE_MIGRATION_CANDIDATE"
        else:
            role = "LOCAL_MODEL_ASSET_PENDING_BENCHMARK"
        if cortex:
            execution_class = "HOLD_C1_OWNED"
        elif heavy:
            execution_class = "REMOTE_EXECUTION_REQUIRED"
        elif size >= 4 * 1024**3:
            execution_class = "LOCAL_MEMORY_RISK"
        elif size >= 1500 * 1024**2:
            execution_class = "LOCAL_CONSTRAINED"
        elif not weight_present:
            execution_class = "CATALOG_NOT_EXECUTABLE"
        else:
            execution_class = "LOCAL_SAFE"
        family = name.split(":", 1)[0].split("-", 1)[0]
        output.append({
            **record,
            "model_id": name,
            "name": name,
            "family": family,
            "kind": "EMBEDDING" if "embedding" in name.lower() else "GENERATIVE",
            "parameter_count": record.get("parameter_count", "UNOBSERVED"),
            "quantization": record.get("quantization", "UNOBSERVED"),
            "size_bytes": size,
            "storage_location": record.get("storage_location") or "OLLAMA_LOCAL",
            "source_plane": record.get("source_plane") or record.get("storage_location") or "OLLAMA_LOCAL",
            "weight_present": weight_present,
            "runtime_present": runtime_present,
            "currently_bound": required,
            "student_forbidden": cortex,
            "owner": MAIN_CORTEX_OWNER if cortex else record.get("owner", "UNOBSERVED"),
            "main_cortex_state": MAIN_CORTEX_STATE if cortex else None,
            "local_execution_class": execution_class,
            "assimilation_state": (
                "C1_OWNED_HOLD" if cortex
                else record.get("assimilation_state", "WEIGHT_PRESENT_NOT_ASSIMILATED" if weight_present else "CATALOG_ONLY")
            ),
            "heavy_local": False if cortex else heavy,
            "runtime_required": required,
            "remote_migration_required": False if cortex else (heavy and not migration_proven),
            "source_removable": False if cortex else (migration_proven and not required),
            "benchmark_required": False if cortex or required else (weight_present and not required),
            "canonical_role": role,
        })
    return output


def _dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in records:
        key = str(record.get("name") or record.get("model_id") or "").strip()
        if not key:
            continue
        existing = seen.get(key)
        if existing is None:
            seen[key] = dict(record)
            order.append(key)
            continue
        if record.get("weight_present") and not existing.get("weight_present"):
            merged = dict(record)
            merged["source_plane"] = f"{existing.get('source_plane')}+{record.get('source_plane')}"
            seen[key] = merged
    return [seen[key] for key in order]


def classify_local_models(
    repo_root: str | Path,
    runtime_root: str | Path,
    *,
    live_accounts: bool | None = None,
) -> dict[str, Any]:
    runtime_root = Path(runtime_root).expanduser().resolve()
    report_dir = runtime_root / "model-ecology"
    report_dir.mkdir(parents=True, exist_ok=True)
    live = _live_accounts_enabled(live_accounts)
    student = runtime_model()
    health = c5_health()
    router = ninerouter_catalog()
    factories = factory_source_index(runtime_root)
    probes: dict[str, Any] = {}
    if live:
        from raios.resource_fabric.live import run_live_probes

        probes = (run_live_probes(live=True) or {}).get("probes") or {}
    records = []
    records.extend(ollama_models())
    records.extend(copy_estate_model_symbols(repo_root))
    records.extend(account_model_records(probes))
    for name in router.get("catalog_sample") or []:
        if is_main_cortex(name):
            continue
        records.append({
            "name": name,
            "size_bytes": 0,
            "source_plane": "NINEROUTER_CATALOG",
            "storage_location": "127.0.0.1:20128",
            "weight_present": False,
            "runtime_present": False,
            "canonical_role_hint": None,
        })
    records = _dedupe(records)
    if not any(is_main_cortex(str(row.get("name") or "")) for row in records):
        records.append({
            "name": MAIN_CORTEX_IDENTITY,
            "size_bytes": 0,
            "source_plane": "C1_IDENTITY",
            "storage_location": "IDENTITY_HOLD_WEIGHTS_ABSENT",
            "weight_present": False,
            "runtime_present": False,
        })
    rows = classify_records(records, runtime_model=student)
    bindings = account_bindings(probes) if live else []
    if not live:
        bindings = [{"account_id": aid, "status": "SKIPPED_OFFLINE", "bound": False, "PAID_RESOURCE_CREATED": False} for aid in ACCOUNT_IDS]
        bindings.append({
            "account_id": "NINEROUTER",
            "status": router.get("health"),
            "bound": router.get("health") == "ok",
            "RESOURCE_AUTHORITY": False,
            "models_visible": router.get("models_visible"),
            "PAID_RESOURCE_CREATED": False,
        })
    result = {
        "schema": "raios.model-ecology.v2",
        "generated_at": utc(),
        "canonical_repo": str(Path(repo_root).resolve()),
        "runtime_root": str(runtime_root),
        "live_accounts": live,
        "local_model_count": len(rows),
        "heavy_local_count": sum(bool(x["heavy_local"]) for x in rows),
        "runtime_dependency_count": sum(bool(x["runtime_required"]) for x in rows),
        "remote_migration_required_count": sum(bool(x["remote_migration_required"]) for x in rows),
        "source_removable_true_count": sum(bool(x["source_removable"]) for x in rows),
        "main_cortex": {
            "identity": MAIN_CORTEX_IDENTITY,
            "owner": MAIN_CORTEX_OWNER,
            "state": MAIN_CORTEX_STATE,
            "student_forbidden": True,
            "currently_bound": False,
            "weights_present": any(is_main_cortex(x["model_id"]) and x.get("weight_present") for x in rows),
            "law": "MAIN_CORTEX_NE_STUDENT",
        },
        "student_runtime_model": student,
        "model_fabric": {
            "ready": bool(health.get("model_fabric_ready") or health.get("model_fabric")),
            "c5_status": health.get("status"),
            "live_engines": health.get("live_engines") or [],
            "live_engine_count": health.get("live_engine_count"),
        },
        "ninerouter": router,
        "factories_fed": factories,
        "account_bindings": bindings,
        "copy_estate_model_symbols": sum(1 for x in rows if x.get("source_plane") == "COPY_ESTATE_UNIQUE_VALUE"),
        "models": rows,
        "canonical_repo_mutation": False,
        "model_deleted": False,
        "model_downloaded": False,
        "PAID_RESOURCE_CREATED": False,
        "GPU_SESSION_STARTED": False,
        "copy_estate_source_cutover": False,
        "SAFE_TO_REMOVE_SOURCE": False,
        "law": [
            "MAIN_CORTEX_C1_OWNED_HOLD",
            "STUDENT_NE_MAIN_CORTEX",
            "EXISTING_ACCOUNTS_ONLY",
            "NO_PAID_RESOURCE_CREATED",
            "NINEROUTER_NE_RESOURCE_AUTHORITY",
            "CATALOG_NE_EXECUTABLE",
            "COPY_ESTATE_EXTRACT_NE_DELETE",
        ],
    }
    report = report_dir / "MODEL-ECOLOGY.json"
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result["report_path"] = str(report)
    return result
