"""Main Cortex belongs to C1: treat, run, or throw.

Executor isolation is not disposal. Executor never throws. Identity is not swapped
to a tiny student. This host does not load cortex weights.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from .provider_contracts import ProviderCapability

CORTEX_IDENTITY = "qwen3.6:35b-a3b"
OWNER = "C1"
VERBS = ("treat", "run", "throw")
MIN_RAM_GB_FOR_CORTEX = 24.0
ARENAS = ("ROUTER", "CORTEX", "CODE", "REASONING", "EMBEDDING", "RERANKER")
ROLE_KEYS = (
    "ROUTER_MODEL",
    "CORTEX_MODEL",
    "CODE_MODEL",
    "REASONING_MODEL",
    "EMBEDDING_MODEL",
    "RERANKER_MODEL",
    "FRONTIER_TEACHER_MODEL",
)
ENDPOINT_KINDS = (
    "LOCAL_DEV",
    "KAGGLE_WORKER",
    "LIGHTNING_WORKER",
    "HF_ENDPOINT",
    "FRONTIER_PROVIDER",
)
CHAT_PATH = "/v1/chat/completions"

LAWS = (
    "C1_OWNS_CORTEX_TREAT_RUN_THROW",
    "EXECUTOR_NE_THROW_CORTEX",
    "EXECUTOR_NE_ISOLATE_AS_DISPOSAL",
    "HOLD_NE_THROW",
    "CORTEX_RUN_REQUIRES_C1",
    "STUDENT_NE_MAIN_CORTEX",
    "TINY_QWEN_NE_CORTEX_IDENTITY",
    "CUSTOMER_LANGUAGE_NE_CORTEX",
    "HF_WEIGHTS_NE_IN_SECRET_REPO",
    "CURRENT_WINNERS_ARE_NOT_FINAL",
    "ROLE_NE_CROWNED_WINNER",
    "RAIOS_NE_ONE_MODEL",
    "LAPTOP_IS_CONTROL_PLANE",
    "LAPTOP_NE_MODEL_HOST",
    "OLLAMA_IS_DEV_FALLBACK",
    "LOCAL_RAM_NE_CORTEX_CRITERION",
    "LOCAL_OLLAMA_NE_CORTEX_CRITERION",
    "OPENAI_COMPAT_TRANSPORT",
    "CLOUD_GATEWAY_NE_OPENAI",
    "SOURCE_PATCH_NE_PROVIDER_SWITCH",
)

_TRUE = {"1", "true", "yes", "on"}


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUE


def _registry_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".ai-os" / "MODEL-REGISTRY.json"
        if candidate.is_file():
            return candidate
    return Path.cwd() / ".ai-os" / "MODEL-REGISTRY.json"


def load_model_registry() -> dict[str, Any]:
    path = _registry_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_role(role: str) -> str:
    raw = str(role or "").strip().upper().replace("-", "_")
    if raw in ARENAS:
        return f"{raw}_MODEL"
    if raw in ROLE_KEYS:
        return raw
    if raw.endswith("_MODEL"):
        return raw
    return raw


def _role_env_prefix(role_key: str) -> str:
    return "RAIOS_" + str(role_key).removesuffix("_MODEL")


def _env(*names: str | None) -> str | None:
    for name in names:
        if not name:
            continue
        value = os.environ.get(str(name), "").strip()
        if value:
            return value
    return None


def _normalize_base_url(raw: str | None) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if "://" not in text:
        text = "http://" + text
    return text.rstrip("/")


def _host_of(url: str) -> str:
    rest = url.split("://", 1)[-1]
    return rest.split("/", 1)[0].lower()


def paid_openai_forbidden(url: str | None) -> bool:
    host = _host_of(str(url or ""))
    return host == "api.openai.com" or host.endswith(".openai.com") or "openai.azure.com" in host


def openai_compat_chat_url(base_url: str) -> str:
    base = _normalize_base_url(base_url) or ""
    if base.endswith("/v1"):
        return base + "/chat/completions"
    if base.endswith("/chat/completions"):
        return base
    return base + CHAT_PATH


def resolve_role(role: str) -> dict[str, Any]:
    """Select a role from the existing Model Registry. Does not crown a winner."""
    key = _normalize_role(role)
    registry = load_model_registry()
    roles = registry.get("roles") or {}
    models = registry.get("models") or {}
    row = dict(roles.get(key) or {})
    ids = [str(item) for item in (row.get("candidates") or [])]
    candidate_models: list[str] = []
    for mid in ids:
        entry = models.get(mid) if isinstance(models.get(mid), dict) else {}
        name = str((entry or {}).get("model") or mid)
        if name:
            candidate_models.append(name)
    named = row.get("named_candidate") or (candidate_models[0] if candidate_models else None)
    if key == "CORTEX_MODEL" and not named:
        named = CORTEX_IDENTITY
    selected = row.get("selected")
    local_winner = bool(row.get("local_winner")) and selected is not None
    if registry.get("winners_are_final") is False:
        local_winner = False
    if key == "CORTEX_MODEL":
        local_winner = False
    reason = row.get("reason") or (
        "CURRENT_WINNERS_ARE_NOT_FINAL" if not local_winner else "ROLE_SELECTED"
    )
    return {
        "role": key,
        "arena": row.get("arena"),
        "candidates": ids,
        "candidate_models": candidate_models,
        "selected": selected,
        "model": named,
        "local_winner": local_winner,
        "winner_final": False,
        "reason": reason,
        "bridge": row.get("bridge"),
        "class": row.get("class"),
        "not_current_local_winner": bool(row.get("not_current_local_winner")) or key == "CORTEX_MODEL",
        "registry": ".ai-os/MODEL-REGISTRY.json",
        "duplicate_registry": False,
        "gl005_proven": False,
    }


def endpoint_secret(endpoint: dict[str, Any] | None = None) -> str | None:
    """Read API key from env names. Never persist. Never print."""
    row = endpoint or {}
    return _env(
        row.get("api_key_env"),
        row.get("api_key_env_alt"),
        "HF_TOKEN" if row.get("kind") == "HF_ENDPOINT" else None,
        "HUGGING_FACE_HUB_TOKEN" if row.get("kind") == "HF_ENDPOINT" else None,
    )


def resolve_endpoint(role: str = "CORTEX_MODEL") -> dict[str, Any]:
    """Role → provider endpoint from existing registry/env. No second registry. No source patch to switch."""
    key = _normalize_role(role)
    registry = load_model_registry()
    roles = registry.get("roles") or {}
    kinds_cfg = registry.get("provider_endpoints") or {}
    row = dict(roles.get(key) or {})
    prefix = _role_env_prefix(key)
    kind_raw = _env(f"{prefix}_ENDPOINT", row.get("endpoint_kind_env")) or row.get("endpoint_kind")
    kind = str(kind_raw).strip().upper() if kind_raw else None
    if kind == "FRONTIER_TEACHER":
        kind = "FRONTIER_PROVIDER"
    if kind and kind not in ENDPOINT_KINDS:
        kind = None
    kind_row = dict(kinds_cfg.get(kind) or {}) if kind else {}
    base_url = _normalize_base_url(
        _env(
            f"{prefix}_BASE_URL",
            row.get("base_url_env"),
            kind_row.get("base_url_env"),
        )
    )
    fallback_kind = str(row.get("fallback_endpoint_kind") or "LOCAL_DEV").upper()
    used_fallback = False
    if not base_url and (kind in {None, "LOCAL_DEV"} or not kind):
        local = _normalize_base_url(_env("OLLAMA_HOST", (kinds_cfg.get("LOCAL_DEV") or {}).get("base_url_env")))
        if local:
            kind = "LOCAL_DEV"
            base_url = local
            used_fallback = True
            kind_row = dict(kinds_cfg.get("LOCAL_DEV") or {})
    if kind is None and base_url:
        kind = "FRONTIER_PROVIDER"
        kind_row = dict(kinds_cfg.get(kind) or {})
    api_key_env = (
        f"{prefix}_API_KEY"
        if _env(f"{prefix}_API_KEY")
        else (row.get("api_key_env") or kind_row.get("api_key_env") or (f"{prefix}_API_KEY" if prefix else None))
    )
    api_key_env_alt = kind_row.get("api_key_env_alt") or ("HF_TOKEN" if kind == "HF_ENDPOINT" else None)
    model = _env(f"{prefix}_MODEL", row.get("model_env"), kind_row.get("model_env")) or row.get("named_candidate")
    if not model:
        model = CORTEX_IDENTITY if key == "CORTEX_MODEL" else None
    configured = bool(base_url)
    forbidden = paid_openai_forbidden(base_url) if base_url else False
    chat_url = openai_compat_chat_url(base_url) if base_url and not forbidden else None
    remote = bool(kind and kind != "LOCAL_DEV")
    return {
        "role": key,
        "kind": kind,
        "configured": configured and not forbidden,
        "unbound": not (configured and not forbidden),
        "reason": (
            "CLOUD_GATEWAY_NE_OPENAI"
            if forbidden
            else ("LOCAL_DEV_FALLBACK" if used_fallback else ("ENDPOINT_READY" if configured else "ENDPOINT_UNBOUND"))
        ),
        "base_url": None if forbidden else base_url,
        "chat_url": chat_url,
        "chat_path": CHAT_PATH,
        "protocol": "openai-compatible",
        "api_key_env": api_key_env,
        "api_key_env_alt": api_key_env_alt,
        "api_key_present": bool(
            endpoint_secret(
                {
                    "kind": kind,
                    "api_key_env": api_key_env,
                    "api_key_env_alt": api_key_env_alt,
                }
            )
        ),
        "model": model,
        "dev_fallback": kind == "LOCAL_DEV",
        "used_fallback": used_fallback,
        "remote": remote,
        "laptop_is_model_host": False,
        "local_ram_ne_cortex_criterion": True,
        "local_ollama_ne_cortex_criterion": True,
        "source_patch_required": False,
        "paid_openai_api": False,
        "sdk": False,
        "registry": ".ai-os/MODEL-REGISTRY.json",
        "duplicate_registry": False,
        "duplicate_router": False,
        "gl005_proven": False,
    }


def named_cortex_model() -> str:
    return str(resolve_role("CORTEX_MODEL").get("model") or CORTEX_IDENTITY)


def cortex_candidate_models() -> tuple[str, ...]:
    row = resolve_role("CORTEX_MODEL")
    names = list(row.get("candidate_models") or [])
    named = str(row.get("model") or CORTEX_IDENTITY)
    if named not in names:
        names.insert(0, named)
    return tuple(dict.fromkeys(names))


def model_in_role(model: str, role: str) -> bool:
    name = str(model or "")
    row = resolve_role(role)
    allowed = list(row.get("candidate_models") or [])
    named = str(row.get("model") or "")
    if named:
        allowed.append(named)
    return any(name == item or (item and name.startswith(f"{item}:")) for item in allowed if item)


def execution_bridges() -> dict[str, Any]:
    """RAIOS/MCP = control. OpenCode = coding execution bridge. Probe only. No install."""
    binary = shutil.which("opencode")
    registry = load_model_registry()
    declared = ((registry.get("bridges") or {}).get("execution") or {})
    return {
        "control": {
            "id": "raios-mcp",
            "role": "control/orchestration",
            "path": "scripts/ai-os/raios_mcp/server.py",
            "gateway": "scripts/ai-os/raios_mcp/gateway.py",
            "endpoint": "http://127.0.0.1:8787/mcp",
            "health": "http://127.0.0.1:8787/health",
            "tools": 8,
            "not": "model-execution",
        },
        "execution": {
            "id": "opencode",
            "role": "coding/model-execution-bridge",
            "uses_role": "CODE_MODEL",
            "present": binary is not None,
            "binary": binary,
            "install": False,
            "duplicate_mcp": False,
            "not_control_plane": True,
            "status": "BINARY_PRESENT_NOT_WIRED" if binary else str(declared.get("status") or "PREP_NOT_INSTALLED"),
            "integration_points": list(
                declared.get("integration_points")
                or [
                    ".ai-os/MODEL-REGISTRY.json bridges.execution",
                    "roles.CODE_MODEL.bridge=opencode",
                    "shutil.which('opencode') probe only",
                    "do not add MCP tools",
                    "do not download",
                ]
            ),
        },
        "local_infer": {
            "id": "ollama",
            "role": "DEV_FALLBACK",
            "path": "src/raios/neuro_lingua/qwen_runtime.py",
            "generate": "qwen_runtime.generate",
            "probe": "qwen_runtime.probe",
            "uses_role": "CORTEX_MODEL",
            "base_url_env": "OLLAMA_HOST",
            "not_cortex_host": True,
            "not_final_criterion": True,
        },
        "transport": {
            "path": [
                "C5",
                "NeuroLingua",
                "MODEL_ROLE",
                "PROVIDER_ENDPOINT",
                "openai-compatible /v1/chat/completions",
                "response",
            ],
            "protocol": "openai-compatible",
            "chat_path": CHAT_PATH,
            "sdk": False,
            "paid_openai_api": False,
            "source_patch_required": False,
        },
        "endpoint_kinds": list(ENDPOINT_KINDS),
        "laptop_is_model_host": False,
        "duplicate_mcp": False,
        "duplicate_registry": False,
        "gl005_proven": False,
    }


def _linux_memory() -> dict[str, float] | None:
    try:
        info: dict[str, float] = {}
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                parts = rest.split()
                if not parts:
                    continue
                info[key] = float(parts[0]) / (1024 ** 2)
        total = info.get("MemTotal")
        free_gb = info.get("MemAvailable")
        if free_gb is None:
            free_gb = info.get("MemFree")
        if total is None and free_gb is None:
            return None
        return {"total_gb": total, "free_gb": free_gb}
    except OSError:
        return None


def _gpu_present() -> bool:
    nvidia = Path("/proc/driver/nvidia/gpus")
    if nvidia.is_dir() and any(nvidia.iterdir()):
        return True
    return shutil.which("nvidia-smi") is not None


def host_can_run(*, min_free_gb: float = MIN_RAM_GB_FOR_CORTEX) -> tuple[bool, str]:
    if not _gpu_present():
        return False, "HOST_NO_GPU"
    mem = _linux_memory()
    free_gb = None if mem is None else mem.get("free_gb")
    if free_gb is None:
        return False, "HOST_RAM_UNKNOWN"
    if float(free_gb) < float(min_free_gb):
        return False, "HOST_RAM_INSUFFICIENT"
    return True, "HOST_CAN_RUN_CORTEX"


def status(*, min_free_gb: float = MIN_RAM_GB_FOR_CORTEX) -> dict[str, Any]:
    thrown = _flag("C1_CORTEX_THROW")
    run_granted = _flag("C1_CORTEX_RUN")
    can, host_reason = host_can_run(min_free_gb=min_free_gb)
    hold = (not thrown) and not (run_granted and can)
    mem = _linux_memory()
    return {
        "schema": "raios.cortex.v1",
        "owner": OWNER,
        "verbs": list(VERBS),
        "identity": CORTEX_IDENTITY,
        "role": "CORTEX_MODEL",
        "local_winner": False,
        "winner_final": False,
        "laptop_is_model_host": False,
        "local_ram_ne_cortex_criterion": True,
        "local_ollama_ne_cortex_criterion": True,
        "isolated_as_disposal": False,
        "hold": hold,
        "thrown": thrown,
        "run_granted": run_granted,
        "host_can_run": can,
        "host_reason": host_reason,
        "ram_total_gb": None if mem is None else mem.get("total_gb"),
        "ram_free_gb": None if mem is None else mem.get("free_gb"),
        "gpu": _gpu_present(),
        "law": list(LAWS),
        "gl005_proven": False,
    }


def gate_run(*, min_free_gb: float = MIN_RAM_GB_FOR_CORTEX) -> dict[str, Any]:
    st = status(min_free_gb=min_free_gb)
    if st["thrown"]:
        reason = "CORTEX_THROWN_BY_C1"
        admitted = False
    elif not st["run_granted"]:
        reason = "CORTEX_HOLD_AWAITING_C1_RUN"
        admitted = False
    elif not st["host_can_run"]:
        reason = "HOST_CANNOT_RUN_CORTEX"
        admitted = False
    else:
        reason = "C1_CORTEX_RUN"
        admitted = True
    return {
        "admitted": admitted,
        "reason": reason,
        "fallback": None if admitted else "deterministic_pipeline",
        **st,
    }


def treat() -> dict[str, Any]:
    """C1 treat path: diagnose weakness. Does not load weights, run, or throw."""
    st = status()
    gate = gate_run()
    return {
        "schema": "raios.cortex-treat.v1",
        "ok": True,
        "verb": "treat",
        "owner": OWNER,
        "identity": CORTEX_IDENTITY,
        "loaded": False,
        "thrown": False,
        "run": False,
        "isolated_as_disposal": False,
        "weakness": [
            "used_as_silent_live_spine_without_c1_run",
            "identity_swap_temptation_tiny_qwen",
            "this_host_cannot_load_35b",
        ],
        "repair": [
            "c1_owns_treat_run_throw",
            "hold_is_not_throw",
            "deterministic_neurolingua_until_c1_run",
            "student_ne_cortex_identity",
        ],
        "status": st,
        "gate": {k: gate[k] for k in ("admitted", "reason", "fallback")},
        "law": list(LAWS),
        "gl005_proven": False,
    }


def refuse_throw() -> dict[str, Any]:
    return {
        "ok": False,
        "verb": "throw",
        "error": "EXECUTOR_NE_THROW_CORTEX",
        "owner": OWNER,
        "identity": CORTEX_IDENTITY,
        "isolated_as_disposal": False,
        "law": list(LAWS),
        "gl005_proven": False,
    }


def explicit_receipt(
    *,
    verb: str = "status",
    student_model: str = "qwen2.5:0.5b",
    student_live: bool = False,
    loaded: bool = False,
) -> dict[str, Any]:
    """Plain KEY=VALUE receipt. Identity is never implied."""
    import hashlib

    gate = gate_run()
    st = status()
    lines = [
        "############################################################",
        "# RAIOS C1 MAIN CORTEX RECEIPT",
        "############################################################",
        f"IDENTITY={CORTEX_IDENTITY}",
        "ROLE=CORTEX_MODEL",
        "LOCAL_WINNER=false",
        "WINNERS_ARE_FINAL=false",
        "LAPTOP_IS_MODEL_HOST=false",
        "OLLAMA_IS_DEV_FALLBACK=true",
        "AVAILABILITY=MEMORY_ALLOCATION_FAILED",
        f"OWNER={OWNER}",
        "VERBS=treat,run,throw",
        f"VERB={verb}",
        f"STUDENT={student_model}",
        f"STUDENT_LIVE={str(student_live).lower()}",
        "STUDENT_NE_CORTEX=true",
        f"LOADED={str(bool(loaded)).lower()}",
        f"HOLD={str(bool(st['hold'])).lower()}",
        f"THROWN={str(bool(st['thrown'])).lower()}",
        "ISOLATED_AS_DISPOSAL=false",
        f"C1_CORTEX_RUN={str(bool(st['run_granted'])).lower()}",
        f"HOST_CAN_RUN={str(bool(st['host_can_run'])).lower()}",
        f"HOST_REASON={st['host_reason']}",
        f"GATE={gate['reason']}",
        "WAL_WRITTEN=false",
        "PAID_API_USED=false",
        "GL005_PROVEN=false",
        "############################################################",
        "",
    ]
    text = "\n".join(lines)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "schema": "raios.cortex-explicit-receipt.v1",
        "ok": True,
        "identity": CORTEX_IDENTITY,
        "role": "CORTEX_MODEL",
        "local_winner": False,
        "owner": OWNER,
        "text": text,
        "sha256": digest,
        "gate": gate["reason"],
        "loaded": False,
        "gl005_proven": False,
    }


class CortexProvider:
    """LanguageProvider for the CORTEX_MODEL role. Executes via qwen_runtime.generate.

    Bound to the role, not a crowned winner. No student swap.
    """

    provider_id = "main-cortex-capability"

    @property
    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id=self.provider_id,
            capabilities=("SEMANTIC_INTERPRETATION", "SEMANTIC_REALIZATION", "SEMANTIC_VERIFICATION"),
            languages=("ar-EG", "ar-GULF", "en", "nb-NO", "sv-SE", "da-DK"),
            local=True,
            quality_score=0.95,
            estimated_latency_ms=8000,
        )

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        from .qwen_runtime import generate as qwen_generate

        text = str(payload.get("text") or payload.get("prompt") or "").strip()
        role = resolve_role("CORTEX_MODEL")
        endpoint = resolve_endpoint("CORTEX_MODEL")
        requested = str(payload.get("model") or endpoint.get("model") or role.get("model") or CORTEX_IDENTITY)
        if not model_in_role(requested, "CORTEX_MODEL"):
            return {
                "ok": False,
                "error": "STUDENT_NE_CORTEX",
                "model": requested,
                "role": "CORTEX_MODEL",
                "local_winner": False,
                "llm_executed": False,
                "model_name_bound": False,
                "student_substituted": False,
                "laptop_is_model_host": False,
                "response": "",
                "gl005_proven": False,
            }
        rec = qwen_generate(text, model=requested)
        rec["role"] = "CORTEX_MODEL"
        rec["local_winner"] = False
        rec["winner_final"] = False
        rec["endpoint_kind"] = endpoint.get("kind")
        rec["endpoint_configured"] = bool(endpoint.get("configured"))
        rec["laptop_is_model_host"] = False
        rec["source_patch_required"] = False
        return rec

    async def execute(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        rec = self.run(payload)
        rec["capability"] = capability
        return rec


def public_fields(st: dict[str, Any] | None = None) -> dict[str, Any]:
    row = st or status()
    return {
        "cortex_identity": CORTEX_IDENTITY,
        "cortex_role": "CORTEX_MODEL",
        "local_winner": False,
        "laptop_is_model_host": False,
        "cortex_owner": OWNER,
        "cortex_verbs": list(VERBS),
        "isolated_as_disposal": False,
        "cortex_hold": bool(row.get("hold")),
        "cortex_thrown": bool(row.get("thrown")),
        "cortex_isolated": False,
        "run_granted": bool(row.get("run_granted")),
        "host_can_run": bool(row.get("host_can_run")),
        "host_reason": row.get("host_reason"),
    }
