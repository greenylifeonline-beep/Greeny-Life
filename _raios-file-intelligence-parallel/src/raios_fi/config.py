"""File Intelligence identity and write boundaries."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORGANISM_ID = "raios.organism.v9"
PACKAGE = "_raios-file-intelligence-parallel"
SCHEMA_VERSION = "file-intelligence.v1"
PARSER_VERSION = "fi-parser.v1"

FORBIDDEN_WRITE = (
    "RAIOS/V9",
    "_raios-a17-native-cortex/experience/raw/teacher-harvest",
    "_raios-a17-native-cortex/store",
    "_raios-a17-native-cortex/ccee/var",
    "_raios-a17-native-cortex/reports",
)

SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".next", "ccee/var"}
MAX_INDEX_BYTES = 5 * 1024 * 1024


class FailClosed(RuntimeError):
    @staticmethod
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise FailClosed(message)

    @staticmethod
    def assert_writable(path: Path, repo: Path | None = None) -> None:
        assert_writable(path, repo)


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


def deterministic_id(kind: str, *parts: str) -> str:
    return f"{kind}:{sha256_obj({'kind': kind, 'parts': list(parts)})[:32]}"


def repo_root_from(start: Path | None = None) -> Path:
    current = Path(start or Path(__file__).resolve())
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() and (candidate / "RAIOS").exists():
            return candidate
    return Path.cwd()


def package_root(repo: Path | None = None) -> Path:
    return (repo or repo_root_from()) / PACKAGE


def assert_writable(path: Path, repo: Path | None = None) -> None:
    root = (repo or repo_root_from()).resolve()
    resolved = Path(path).resolve()
    for rel in FORBIDDEN_WRITE:
        protected = (root / rel).resolve()
        try:
            resolved.relative_to(protected)
            raise FailClosed(f"PROTECTED_LIVE_WRITER:{rel}")
        except ValueError:
            if resolved == protected:
                raise FailClosed(f"PROTECTED_LIVE_WRITER:{rel}")
    v9 = (root / "RAIOS" / "V9").resolve()
    try:
        resolved.relative_to(v9)
        raise FailClosed("RAIOS_V9_MUTATION_REJECTED")
    except ValueError:
        pass


def which(name: str) -> str | None:
    return shutil.which(name)


def run(cmd: list[str], cwd: Path | None = None, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout)


def env_flag(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
