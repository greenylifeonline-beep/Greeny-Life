"""Local Qwen student via Ollama. Main Cortex stays isolated. No identity swap. No repo weights."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

CORTEX_IDENTITY = "qwen3.6:35b-a3b"
STUDENT_PREFERRED = "qwen2.5:0.5b"
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
_CACHE: dict[str, Any] = {"ts": 0.0, "row": None}
_CACHE_TTL_S = 3.0

LAWS = (
    "MAIN_CORTEX_ISOLATED_DANGEROUS_WEAK",
    "STUDENT_NE_MAIN_CORTEX",
    "TINY_QWEN_NE_CORTEX_IDENTITY",
    "CUSTOMER_LANGUAGE_NE_CORTEX",
    "HF_WEIGHTS_NE_IN_SECRET_REPO",
)


def _base(host: str | None = None) -> str:
    raw = (host or DEFAULT_HOST).strip()
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


def probe(*, host: str | None = None, timeout: float = 1.5, use_cache: bool = True) -> dict[str, Any]:
    now = time.monotonic()
    if use_cache and _CACHE["row"] is not None and now - float(_CACHE["ts"]) < _CACHE_TTL_S:
        return dict(_CACHE["row"])
    url = f"{_base(host)}/api/tags"
    row: dict[str, Any] = {
        "schema": "raios.qwen-runtime.v1",
        "present": False,
        "endpoint": url,
        "models": [],
        "cortex_identity": CORTEX_IDENTITY,
        "cortex_live": False,
        "cortex_isolated": True,
        "student_preferred": STUDENT_PREFERRED,
        "student_model": None,
        "student_live": False,
        "reason": "OLLAMA_ABSENT",
        "law": list(LAWS),
        "gl005_proven": False,
    }
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        names = _names(payload if isinstance(payload, dict) else {})
        student = _student_from(names)
        cortex_live = any(_is_cortex(name) for name in names)
        row.update(
            {
                "present": True,
                "models": names,
                "cortex_live": cortex_live,
                "student_model": student,
                "student_live": student is not None,
                "reason": (
                    "STUDENT_LIVE_CORTEX_ISOLATED"
                    if student
                    else ("OLLAMA_UP_NO_STUDENT" if names else "OLLAMA_UP_NO_MODELS")
                ),
            }
        )
        if cortex_live:
            row["reason"] = "CORTEX_PRESENT_STILL_ISOLATED"
            row["cortex_isolated"] = True
            row["cortex_live"] = True
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as err:
        row["error"] = type(err).__name__
        row["reason"] = "OLLAMA_ABSENT"
    _CACHE["ts"] = now
    _CACHE["row"] = dict(row)
    return row


def generate(
    prompt: str,
    *,
    host: str | None = None,
    model: str | None = None,
    num_predict: int = 32,
    timeout: float = 120.0,
) -> dict[str, Any]:
    status = probe(host=host, use_cache=False)
    chosen = model or status.get("student_model") or STUDENT_PREFERRED
    if _is_cortex(chosen):
        return {
            "ok": False,
            "error": "MAIN_CORTEX_ISOLATED_DANGEROUS_WEAK",
            "cortex_identity": CORTEX_IDENTITY,
            "cortex_isolated": True,
            "student_live": status.get("student_live"),
            "response": "",
            "law": list(LAWS),
            "gl005_proven": False,
        }
    if not status.get("present"):
        return {
            "ok": False,
            "error": "DEEP_PATH_UNAVAILABLE_NO_QWEN_OLLAMA",
            "cortex_isolated": True,
            "student_live": False,
            "response": "",
            "probe": status,
            "gl005_proven": False,
        }
    body = json.dumps(
        {
            "model": chosen,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": int(num_predict), "temperature": 0},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{_base(host)}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as err:
        return {
            "ok": False,
            "error": type(err).__name__,
            "model": chosen,
            "role": "student",
            "cortex_isolated": True,
            "response": "",
            "gl005_proven": False,
        }
    text = str(payload.get("response") or "")
    return {
        "ok": bool(text.strip()),
        "role": "student",
        "model": chosen,
        "cortex_identity": CORTEX_IDENTITY,
        "cortex_isolated": True,
        "cortex_used": False,
        "response": text,
        "eval_count": payload.get("eval_count"),
        "eval_duration": payload.get("eval_duration"),
        "done": payload.get("done"),
        "law": list(LAWS),
        "gl005_proven": False,
    }
