"""Local Ollama is DEV/FALLBACK only. Cortex executes via role → endpoint → OpenAI-compat.

Laptop is not a model host. Do not treat local tags or RAM as the cortex criterion.
No OpenAI SDK. No paid api.openai.com. No weight download.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from .cortex import (
    CORTEX_IDENTITY,
    LAWS,
    cortex_candidate_models,
    endpoint_secret,
    named_cortex_model,
    openai_compat_chat_url,
    paid_openai_forbidden,
    public_fields,
    resolve_endpoint,
    status as cortex_status,
)

STUDENT_PREFERRED = "qwen2.5:0.5b"
_CACHE: dict[str, Any] = {"ts": 0.0, "row": None}
_CACHE_TTL_S = 3.0


def _ollama_host() -> str | None:
    raw = os.environ.get("OLLAMA_HOST", "").strip()
    return raw or None


def _base(host: str | None = None) -> str | None:
    raw = (host or _ollama_host() or "").strip()
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw.rstrip("/")
    return f"http://{raw.rstrip('/')}"


def _names(payload: dict[str, Any]) -> list[str]:
    models = payload.get("models") or []
    names: list[str] = []
    for row in models:
        name = str(row.get("name") or row.get("model") or "")
        if name:
            names.append(name)
    return names


def _is_cortex(name: str) -> bool:
    for cand in cortex_candidate_models():
        if name == cand or name.startswith(f"{cand}:"):
            return True
    return name == CORTEX_IDENTITY or name.startswith(f"{CORTEX_IDENTITY}:")


def _is_student(name: str) -> bool:
    lower = name.lower()
    return lower.startswith("qwen") and not _is_cortex(name)


def _student_from(names: list[str]) -> str | None:
    for name in names:
        if name == STUDENT_PREFERRED or name.startswith(f"{STUDENT_PREFERRED}-"):
            return name
    for name in names:
        if _is_student(name):
            return name
    return None


def _endpoint_public(endpoint: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": endpoint.get("kind"),
        "configured": bool(endpoint.get("configured")),
        "unbound": bool(endpoint.get("unbound")),
        "reason": endpoint.get("reason"),
        "base_url": endpoint.get("base_url"),
        "chat_url": endpoint.get("chat_url"),
        "protocol": endpoint.get("protocol") or "openai-compatible",
        "api_key_present": bool(endpoint.get("api_key_present")),
        "api_key_env": endpoint.get("api_key_env"),
        "model": endpoint.get("model"),
        "dev_fallback": bool(endpoint.get("dev_fallback")),
        "remote": bool(endpoint.get("remote")),
        "laptop_is_model_host": False,
        "source_patch_required": False,
        "paid_openai_api": False,
    }


def probe(*, host: str | None = None, timeout: float = 1.5, use_cache: bool = True) -> dict[str, Any]:
    now = time.monotonic()
    if use_cache and _CACHE["row"] is not None and now - float(_CACHE["ts"]) < _CACHE_TTL_S:
        return dict(_CACHE["row"])
    endpoint = resolve_endpoint("CORTEX_MODEL")
    st = cortex_status()
    target = _base(host)
    url = f"{target}/api/tags" if target else None
    row: dict[str, Any] = {
        "schema": "raios.qwen-runtime.v1",
        "present": False,
        "endpoint": url,
        "models": [],
        "student_preferred": STUDENT_PREFERRED,
        "student_model": None,
        "student_live": False,
        "cortex_live": False,
        "local_dev_present": False,
        "local_ollama_ne_cortex_criterion": True,
        "local_ram_ne_cortex_criterion": True,
        "laptop_is_model_host": False,
        "reason": "ENDPOINT_UNBOUND" if not endpoint.get("configured") else "ROLE_ENDPOINT",
        "provider_endpoint": _endpoint_public(endpoint),
        "law": list(LAWS),
        "gl005_proven": False,
        **public_fields(st),
    }
    if target:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            names = _names(payload if isinstance(payload, dict) else {})
            student = _student_from(names)
            local_has_cortex = any(_is_cortex(name) for name in names)
            row.update(
                {
                    "present": True,
                    "local_dev_present": True,
                    "models": names,
                    "student_model": student,
                    "student_live": student is not None,
                    "reason": (
                        "LOCAL_DEV_FALLBACK"
                        if endpoint.get("kind") == "LOCAL_DEV"
                        else (
                            "STUDENT_LIVE_CORTEX_HOLD"
                            if student
                            else ("OLLAMA_UP_NO_STUDENT" if names else "OLLAMA_UP_NO_MODELS")
                        )
                    ),
                }
            )
            if local_has_cortex and endpoint.get("kind") == "LOCAL_DEV":
                row["cortex_live"] = True
                row["reason"] = "LOCAL_DEV_CORTEX_PRESENT_NOT_WINNER"
                row.update(public_fields(st))
            else:
                row["cortex_live"] = False
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as err:
            row["error"] = type(err).__name__
            row["reason"] = "OLLAMA_ABSENT" if endpoint.get("kind") == "LOCAL_DEV" else row["reason"]
            row["cortex_live"] = False
    if endpoint.get("configured") and endpoint.get("kind") not in {None, "LOCAL_DEV"}:
        live = _openai_compat_live(endpoint, timeout=timeout)
        row["cortex_live"] = bool(live.get("ok"))
        row["reason"] = live.get("reason") or endpoint.get("reason")
        row["provider_endpoint"] = _endpoint_public(endpoint)
    _CACHE["ts"] = now
    _CACHE["row"] = dict(row)
    return row


def _openai_compat_live(endpoint: dict[str, Any], *, timeout: float = 1.5) -> dict[str, Any]:
    base = str(endpoint.get("base_url") or "")
    if not base or paid_openai_forbidden(base):
        return {"ok": False, "reason": "CLOUD_GATEWAY_NE_OPENAI" if paid_openai_forbidden(base) else "ENDPOINT_UNBOUND"}
    models_url = base + "/models" if base.endswith("/v1") else base + "/v1/models"
    headers = {"Accept": "application/json"}
    secret = endpoint_secret(endpoint)
    if secret:
        headers["Authorization"] = "Bearer " + secret
    req = urllib.request.Request(models_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ok = 200 <= int(resp.status) < 300
            return {"ok": ok, "reason": "ENDPOINT_LIVE" if ok else "ENDPOINT_HTTP"}
    except urllib.error.HTTPError as err:
        return {"ok": False, "reason": f"ENDPOINT_HTTP_{err.code}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as err:
        return {"ok": False, "reason": type(err).__name__}


def _openai_compat_generate(prompt: str, *, endpoint: dict[str, Any], model: str, timeout: float) -> dict[str, Any]:
    base = str(endpoint.get("base_url") or "")
    if paid_openai_forbidden(base):
        return {
            "ok": False,
            "error": "CLOUD_GATEWAY_NE_OPENAI",
            "model": model,
            "role": "CORTEX_MODEL",
            "local_winner": False,
            "response": "",
            "llm_executed": False,
            "model_name_bound": False,
            "student_substituted": False,
            "paid_openai_api": False,
            "gl005_proven": False,
            **public_fields(),
        }
    url = openai_compat_chat_url(base)
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": 32,
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    secret = endpoint_secret(endpoint)
    if secret:
        headers["Authorization"] = "Bearer " + secret
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        raw = ""
        try:
            raw = err.read().decode("utf-8", errors="replace")
        except OSError:
            raw = ""
        lowered = raw.lower()
        memory = any(token in lowered for token in ("memory", "oom", "allocat", "out of mem"))
        missing = err.code in {404, 400} or "not found" in lowered or "unknown model" in lowered
        return {
            "ok": False,
            "error": "MEMORY_ALLOCATION_FAILED" if memory else ("MODEL_MISSING" if missing else type(err).__name__),
            "http": err.code,
            "model": model,
            "role": "CORTEX_MODEL",
            "local_winner": False,
            "response": "",
            "cortex_used": False,
            "llm_executed": False,
            "model_name_bound": False,
            "student_substituted": False,
            "transport": "openai-compatible",
            "endpoint_kind": endpoint.get("kind"),
            "chat_url": url,
            "gl005_proven": False,
            **public_fields(),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as err:
        return {
            "ok": False,
            "error": type(err).__name__,
            "model": model,
            "role": "CORTEX_MODEL",
            "local_winner": False,
            "response": "",
            "cortex_used": False,
            "llm_executed": False,
            "model_name_bound": False,
            "student_substituted": False,
            "transport": "openai-compatible",
            "endpoint_kind": endpoint.get("kind"),
            "chat_url": url,
            "gl005_proven": False,
            **public_fields(),
        }
    choices = payload.get("choices") if isinstance(payload, dict) else None
    text = ""
    if isinstance(choices, list) and choices:
        message = (choices[0] or {}).get("message") or {}
        text = str(message.get("content") or payload.get("response") or "")
    else:
        text = str((payload or {}).get("response") or "")
    return {
        "ok": bool(text.strip()),
        "role": "CORTEX_MODEL",
        "model": model,
        "cortex_used": True,
        "llm_executed": bool(text.strip()),
        "model_name_bound": True,
        "local_winner": False,
        "winner_final": False,
        "student_substituted": False,
        "response": text,
        "transport": "openai-compatible",
        "endpoint_kind": endpoint.get("kind"),
        "chat_url": url,
        "laptop_is_model_host": False,
        "source_patch_required": False,
        "law": list(LAWS),
        "gl005_proven": False,
        **public_fields(),
    }


def generate(
    prompt: str,
    *,
    host: str | None = None,
    model: str | None = None,
    num_predict: int = 32,
    timeout: float = 120.0,
) -> dict[str, Any]:
    endpoint = resolve_endpoint("CORTEX_MODEL")
    named = named_cortex_model()
    chosen = model or endpoint.get("model") or named
    if _is_cortex(chosen):
        if endpoint.get("configured") and endpoint.get("kind") not in {None, "LOCAL_DEV"}:
            return _openai_compat_generate(prompt, endpoint=endpoint, model=str(chosen), timeout=timeout)
        if endpoint.get("kind") == "LOCAL_DEV" and endpoint.get("configured"):
            return _ollama_generate(
                prompt,
                host=host or endpoint.get("base_url"),
                model=str(chosen),
                num_predict=num_predict,
                timeout=timeout,
                cortex=True,
            )
        return {
            "ok": False,
            "error": "MODEL_MISSING",
            "reason": "ENDPOINT_UNBOUND",
            "model": named,
            "role": "CORTEX_MODEL",
            "local_winner": False,
            "model_name_bound": False,
            "student_substituted": False,
            "response": "",
            "cortex_used": False,
            "llm_executed": False,
            "endpoint_kind": endpoint.get("kind"),
            "endpoint_configured": False,
            "laptop_is_model_host": False,
            "local_ollama_ne_cortex_criterion": True,
            "transport": "openai-compatible",
            "law": list(LAWS),
            "gl005_proven": False,
            **public_fields(),
        }
    return _ollama_generate(
        prompt,
        host=host,
        model=str(chosen),
        num_predict=num_predict,
        timeout=timeout,
        cortex=False,
    )


def _ollama_generate(
    prompt: str,
    *,
    host: str | None,
    model: str,
    num_predict: int,
    timeout: float,
    cortex: bool,
) -> dict[str, Any]:
    target = _base(host)
    if not target:
        return {
            "ok": False,
            "error": "MODEL_MISSING" if cortex else "DEEP_PATH_UNAVAILABLE_NO_QWEN_OLLAMA",
            "reason": "LOCAL_DEV_UNBOUND",
            "model": model,
            "role": "CORTEX_MODEL" if cortex else "student",
            "local_winner": False,
            "student_live": False,
            "student_substituted": False,
            "response": "",
            "llm_executed": False,
            "model_name_bound": False,
            "gl005_proven": False,
            **public_fields(),
        }
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": int(num_predict), "temperature": 0},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{target}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        raw = ""
        try:
            raw = err.read().decode("utf-8", errors="replace")
        except OSError:
            raw = ""
        lowered = raw.lower()
        memory = any(token in lowered for token in ("memory", "oom", "allocat", "out of mem"))
        missing = err.code in {404} or "not found" in lowered
        return {
            "ok": False,
            "error": "MEMORY_ALLOCATION_FAILED" if memory else ("MODEL_MISSING" if missing or cortex else type(err).__name__),
            "model": model,
            "role": "CORTEX_MODEL" if cortex else "student",
            "local_winner": False,
            "response": "",
            "cortex_used": False,
            "llm_executed": False,
            "model_name_bound": False,
            "student_substituted": False,
            "endpoint_kind": "LOCAL_DEV",
            "gl005_proven": False,
            **public_fields(),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as err:
        return {
            "ok": False,
            "error": "MODEL_MISSING" if cortex else type(err).__name__,
            "model": model,
            "role": "CORTEX_MODEL" if cortex else "student",
            "local_winner": False,
            "response": "",
            "cortex_used": False,
            "llm_executed": False,
            "model_name_bound": False,
            "student_substituted": False,
            "endpoint_kind": "LOCAL_DEV",
            "gl005_proven": False,
            **public_fields(),
        }
    text = str(payload.get("response") or "")
    return {
        "ok": bool(text.strip()),
        "role": "CORTEX_MODEL" if cortex else "student",
        "model": model,
        "cortex_used": cortex,
        "llm_executed": bool(text.strip()),
        "model_name_bound": True,
        "local_winner": False,
        "winner_final": False,
        "student_substituted": False,
        "response": text,
        "eval_count": payload.get("eval_count"),
        "eval_duration": payload.get("eval_duration"),
        "done": payload.get("done"),
        "endpoint_kind": "LOCAL_DEV" if cortex else None,
        "law": list(LAWS),
        "gl005_proven": False,
        **public_fields(),
    }
