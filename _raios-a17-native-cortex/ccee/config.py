"""CCEE identity, hashing, and write-boundary law.

RAIOS remains the organism. The Native Cortex is not identity.
This package may write its own CCEE runtime and A17.13 forensic receipts.
It must not mutate RAIOS/V9 or live harvest writers.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORGANISM_ID = "raios.organism.v9"
ORGANISM_NAME = "RAIOS"
ARCHITECTURE_GENERATION = "V9"
SCHEMA_VERSION = "a18-ccee.v1"
CORTEX_FAMILY = "Qwen"
CORTEX_TARGET = "qwen3.6:35b-a3b"
CORTEX_IS_IDENTITY = False
TEMPORARY_TEACHERS = ("granite4:3b", "qwen2.5-coder:3b", "deepseek-r1:1.5b")
PACKAGE_REL = Path("_raios-a17-native-cortex")
V9_REL = Path("RAIOS") / "V9"
HARVEST_REL = PACKAGE_REL / "experience" / "raw" / "teacher-harvest"
COGNITIVE_DB_REL = PACKAGE_REL / "store" / "a17-cognitive.db"

FORBIDDEN_SUCCESS_TOKENS = ("PASS", "SUCCESS", "CERTIFIED", "PROVEN", "COMPLETE")
LIVE_CLAIM_RE = (
    r'(?:STATUS|STATE)\s*[=:]\s*["\']?(?!NOT_LIVE)[A-Z0-9_]*LIVE\b'
    r'|"STATUS"\s*:\s*"(?!NOT_LIVE)[A-Z0-9_]*LIVE"'
    r"|GATEWAY_LIVE"
    r"|MULTIMODAL_GATEWAY_LIVE"
)
EPSILON = 1e-9


class FailClosed(RuntimeError):
    """Fail-closed safety exception. Reason codes are stable machine text."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_obj(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def require_sha256(value: str, name: str = "SHA256") -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise FailClosed(f"{name}_INVALID")
    return text


def deterministic_id(kind: str, *parts: str, extra: Any | None = None) -> str:
    return f"{kind}:{sha256_obj({'kind': kind, 'parts': list(parts), 'extra': extra})[:32]}"


def repo_root_from(start: Path | None = None) -> Path:
    current = Path(start or Path(__file__).resolve())
    for candidate in [current, *current.parents]:
        if (candidate / "RAIOS" / "V9").exists() and (candidate / ".git").exists():
            return candidate
        if (candidate / PACKAGE_REL).exists() and (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def native_root(repo_root: Path | None = None) -> Path:
    return (repo_root or repo_root_from()) / PACKAGE_REL


def assert_not_v9(path: Path, repo_root: Path | None = None) -> None:
    root = (repo_root or repo_root_from()).resolve()
    resolved = Path(path).resolve()
    v9 = (root / V9_REL).resolve()
    harvest = (root / HARVEST_REL).resolve()
    db = (root / COGNITIVE_DB_REL).resolve()
    for protected, code in ((v9, "RAIOS_V9_MUTATION_REJECTED"), (harvest, "PROTECTED_LIVE_HARVEST"), (db, "PROTECTED_LIVE_DB")):
        try:
            resolved.relative_to(protected)
        except ValueError:
            if resolved == protected:
                raise FailClosed(code)
            continue
        raise FailClosed(code)


def env_flag(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def contains_forbidden_success(text: str) -> list[str]:
    import re

    hits: list[str] = []
    upper = text.upper()
    for token in FORBIDDEN_SUCCESS_TOKENS:
        if re.search(rf"(?<![A-Z0-9_]){token}(?![A-Z0-9_])", upper):
            hits.append(token)
    if re.search(LIVE_CLAIM_RE, upper):
        hits.append("LIVE")
    return hits


def authoritative_exit(exit_code: Any, default: int = 1) -> int:
    """0 is success. Never coerce 0 to 1 via `or`."""
    if exit_code is None:
        return default
    return int(exit_code)
