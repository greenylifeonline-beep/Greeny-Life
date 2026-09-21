from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .traces import redact_secrets


def load_lightning_api_key() -> str | None:
    path = Path.home() / ".raios" / "accounts" / "lightning" / "partner" / "model-api.json"
    try:
        cred = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    key = str(cred.get("api_key") or "").strip()
    return key or None


def load_deepseek_api_key() -> str | None:
    env = str(os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if env:
        return env
    for rel in (
        Path.home() / ".raios" / "accounts" / "deepseek" / "api.json",
        Path.home() / ".raios" / "accounts" / "deepseek" / "credentials.json",
    ):
        try:
            cred = json.loads(rel.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        key = str(cred.get("api_key") or cred.get("DEEPSEEK_API_KEY") or "").strip()
        if key:
            return key
    return None


def openai_compatible_chat(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int = 64,
    temperature: float = 0.2,
    timeout: float = 60.0,
    user_agent: str = "RAIOS-AI-Gateway/1.0",
) -> dict[str, Any]:
    """POST OpenAI-compatible chat/completions. Never returns the API key."""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(500000)
            parsed = json.loads(raw.decode("utf-8", errors="replace")) if raw[:1] in (b"{", b"[") else None
            return redact_secrets({"ok": True, "http": resp.status, "json": parsed, "error": None})
    except urllib.error.HTTPError as exc:
        return {"ok": False, "http": exc.code, "json": None, "error": f"HTTP_{exc.code}"}
    except Exception as exc:
        return {"ok": False, "http": None, "json": None, "error": type(exc).__name__}


def ollama_chat(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    num_predict: int = 64,
    temperature: float = 0.2,
    timeout: float = 60.0,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(500000)
            parsed = json.loads(raw.decode("utf-8", errors="replace")) if raw[:1] in (b"{", b"[") else None
            return {"ok": True, "http": resp.status, "json": parsed, "error": None}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "http": exc.code, "json": None, "error": f"HTTP_{exc.code}"}
    except Exception as exc:
        return {"ok": False, "http": None, "json": None, "error": type(exc).__name__}
