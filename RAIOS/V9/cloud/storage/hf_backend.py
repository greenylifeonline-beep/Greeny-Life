"""Hugging Face backend. Token presence only. Never print secrets. No weight download."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def token_present() -> bool:
    env = (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or "").strip()
    files = (
        Path.home() / ".cache" / "huggingface" / "token",
        Path.home() / ".huggingface" / "token",
    )
    return bool(env) or any(p.is_file() for p in files)


def _token() -> str | None:
    env = (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or "").strip()
    if env:
        return env
    for p in (Path.home() / ".cache" / "huggingface" / "token", Path.home() / ".huggingface" / "token"):
        if p.is_file():
            return p.read_text(encoding="utf-8").strip() or None
    return None


def whoami() -> dict[str, Any]:
    tok = _token()
    if not tok:
        return {"ok": False, "code": None, "reason": "BLOCKED_AUTH", "authenticated": False}
    req = urllib.request.Request(
        "https://huggingface.co/api/whoami-v2",
        headers={"Authorization": "Bearer " + tok, "User-Agent": "raios-c5-storage", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            raw = resp.read(80_000)
            body = json.loads(raw.decode("utf-8", "replace"))
            name = body.get("name") or (body.get("user") or {}).get("name")
            return {
                "ok": True,
                "code": resp.status,
                "authenticated": True,
                "name_present": bool(name),
                "reason": "WHOAMI_OK",
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "code": exc.code, "authenticated": False, "reason": "HTTP_ERROR"}
    except Exception as exc:
        return {"ok": False, "code": None, "authenticated": False, "reason": type(exc).__name__}


class HfBackend:
    backend_id = "huggingface"
    category = "DATASET_STORAGE"

    def classify(self) -> dict[str, Any]:
        present = token_present()
        states = ["REFERENCED"]
        if present:
            states.append("AUTHENTICATED")
        else:
            states.append("BLOCKED_AUTH")
        states.append("CAPACITY_UNKNOWN")
        return {
            "backend": self.backend_id,
            "category": self.category,
            "token_present": present,
            "states": states,
            "write_test": "SKIPPED_NO_CLEAR_WRITE_PERMISSION" if not present else "SKIPPED_UNTIL_DEDICATED_TEST_REPO",
            "persistent_brain": False,
            "law": ["NO_SECRET_PRINT", "HF_DATASET_NE_SECOND_WAL", "NO_WEIGHT_DOWNLOAD"],
        }

    def put(self, content: bytes, *, name: str) -> dict[str, Any]:
        return {"ok": False, "reason": "HF_WRITE_BLOCKED_NO_DEDICATED_TEST_REPO", "bytes": len(content), "name": name}

    def get(self, object_id: str) -> dict[str, Any]:
        return {"ok": False, "reason": "HF_READ_NOT_BOUND", "object_id": object_id}

    def delete(self, object_id: str) -> dict[str, Any]:
        return {"ok": False, "reason": "HF_DELETE_BLOCKED", "object_id": object_id}
