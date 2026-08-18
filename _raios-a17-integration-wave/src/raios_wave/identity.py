"""RAIOS organism identity and content-addressing primitives.

The Native Cortex is a replaceable Qwen-class provider. It is never RAIOS
identity. This module binds the organism identity independently of any model
name, adapter, or teacher.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "a17-integration-wave.v1"
SCHEMA_MAJOR = 1
SCHEMA_MINOR = 0

ORGANISM_ID = "raios.organism.v9"
ORGANISM_NAME = "RAIOS"
ARCHITECTURE_GENERATION = "V9"
CORTEX_FAMILY = "Qwen"
CORTEX_MASTER_CANDIDATE = "Qwen3.6-35B-A3B"
CORTEX_IS_IDENTITY = False

TEMPORARY_TEACHERS = (
    "granite4:3b",
    "qwen2.5-coder:3b",
    "deepseek-r1:1.5b",
)

PROTECTED_LIVE_WRITERS = (
    "_raios-a17-native-cortex/experience/raw/teacher-harvest",
    "_raios-a17-native-cortex/evidence",
    "_raios-a17-native-cortex/reports",
    "_raios-a17-native-cortex/store/a17-cognitive.db",
)

V9_IDENTITY_RELPATH = Path("RAIOS") / "V9" / "continuity" / "RAIOS-IDENTITY.json"
V9_STATE_RELPATH = Path("RAIOS") / "V9" / "continuity" / "RAIOS-CURRENT-STATE.json"

WAVE_PACKAGE = "_raios-a17-integration-wave"


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


def deterministic_id(kind: str, *parts: str, extra: Any | None = None) -> str:
    payload = {"kind": kind, "parts": list(parts), "extra": extra}
    return f"{kind}:{sha256_obj(payload)[:32]}"


def clamp_unit(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise FailClosed(f"{name}_BOOLEAN_INVALID")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise FailClosed(f"{name}_OUT_OF_RANGE:{number}")
    return number


def require_sha256(value: str, name: str = "SHA256") -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise FailClosed(f"{name}_INVALID")
    return text


def parse_schema_version(value: str) -> tuple[int, int]:
    if not isinstance(value, str) or ".v" not in value:
        raise FailClosed(f"UNKNOWN_SCHEMA_VERSION:{value}")
    tail = value.rsplit(".v", 1)[-1]
    parts = tail.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError as exc:
        raise FailClosed(f"UNKNOWN_SCHEMA_VERSION:{value}") from exc
    return major, minor


def assert_compatible_schema(value: str) -> None:
    major, minor = parse_schema_version(value)
    if major != SCHEMA_MAJOR:
        raise FailClosed(f"INCOMPATIBLE_SCHEMA_MAJOR:{value}")
    if minor > SCHEMA_MINOR:
        raise FailClosed(f"UNMIGRATED_SCHEMA_MINOR:{value}")


def repo_root_from(start: Path | None = None) -> Path:
    current = Path(start or Path(__file__).resolve())
    for candidate in [current, *current.parents]:
        if (candidate / "RAIOS" / "V9").exists() or (candidate / WAVE_PACKAGE).exists():
            if (candidate / ".git").exists() or (candidate / "RAIOS").exists():
                return candidate
    return Path.cwd()


def read_v9_identity(repo_root: Path | None = None) -> dict[str, Any]:
    """Read-only bind to the existing RAIOS identity. Never writes."""
    root = repo_root or repo_root_from()
    path = root / V9_IDENTITY_RELPATH
    if not path.is_file():
        return {
            "schema": "raios.identity.v9",
            "project": ORGANISM_NAME,
            "architecture_generation": ARCHITECTURE_GENERATION,
            "organism_id": ORGANISM_ID,
            "evidence_strength": {"identity_file": "UNKNOWN"},
            "binding": "WAVE_LOCAL_FALLBACK",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    data["organism_id"] = ORGANISM_ID
    data["binding"] = "V9_CONTINUITY_READ_ONLY"
    data["cortex_is_identity"] = False
    return data


def assert_not_protected_live_writer(path: Path, repo_root: Path | None = None) -> None:
    """Refuse writes that could collide with the running A17.4 harvest."""
    root = (repo_root or repo_root_from()).resolve()
    resolved = Path(path).resolve()
    for rel in PROTECTED_LIVE_WRITERS:
        protected = (root / rel).resolve()
        try:
            resolved.relative_to(protected)
        except ValueError:
            if resolved == protected:
                raise FailClosed(f"PROTECTED_LIVE_WRITER:{rel}")
            continue
        raise FailClosed(f"PROTECTED_LIVE_WRITER:{rel}")


def env_flag(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
