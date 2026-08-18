"""Parallel-wave identity. Reuses organism identity from the integration wave."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_WAVE_SRC = _REPO / "_raios-a17-integration-wave" / "src"
if _WAVE_SRC.is_dir() and str(_WAVE_SRC) not in sys.path:
    sys.path.insert(0, str(_WAVE_SRC))

from raios_wave.identity import (  # noqa: E402
    ARCHITECTURE_GENERATION,
    CORTEX_FAMILY,
    CORTEX_IS_IDENTITY,
    CORTEX_MASTER_CANDIDATE,
    FailClosed,
    ORGANISM_ID,
    ORGANISM_NAME,
    PROTECTED_LIVE_WRITERS,
    TEMPORARY_TEACHERS,
    V9_IDENTITY_RELPATH,
    assert_not_protected_live_writer as _assert_wave_protected,
    canonical_json,
    clamp_unit,
    deterministic_id,
    env_flag,
    read_v9_identity,
    repo_root_from,
    require_sha256,
    sha256_bytes,
    sha256_obj,
    sha256_text,
    utc_now,
)

SCHEMA_VERSION = "a17-cursor-parallel.v1"
SCHEMA_MAJOR = 1
SCHEMA_MINOR = 0
PACKAGE = "_raios-a17-cursor-parallel"
CORTEX_TARGET = "qwen3.6:35b-a3b"

# Additional live PowerShell writers that must not be mutated.
PROTECTED_LIVE_WRITERS_EXTRA = PROTECTED_LIVE_WRITERS + (
    "_raios-a17-native-cortex",
    "_raios-a17-native-cortex/store",
    "_raios-a17-native-cortex/runtime",
    "RAIOS/V9",
)


def assert_not_protected_live_writer(path: Path, repo_root: Path | None = None) -> None:
    """Refuse writes that could collide with live PowerShell or canonical V9."""
    _assert_wave_protected(path, repo_root)
    root = (repo_root or repo_root_from()).resolve()
    resolved = Path(path).resolve()
    for rel in PROTECTED_LIVE_WRITERS_EXTRA:
        protected = (root / rel).resolve()
        try:
            resolved.relative_to(protected)
        except ValueError:
            if resolved == protected:
                raise FailClosed(f"PROTECTED_LIVE_WRITER:{rel}")
            continue
        raise FailClosed(f"PROTECTED_LIVE_WRITER:{rel}")


__all__ = [
    "ARCHITECTURE_GENERATION",
    "CORTEX_FAMILY",
    "CORTEX_IS_IDENTITY",
    "CORTEX_MASTER_CANDIDATE",
    "CORTEX_TARGET",
    "FailClosed",
    "ORGANISM_ID",
    "ORGANISM_NAME",
    "PACKAGE",
    "PROTECTED_LIVE_WRITERS",
    "PROTECTED_LIVE_WRITERS_EXTRA",
    "SCHEMA_MAJOR",
    "SCHEMA_MINOR",
    "SCHEMA_VERSION",
    "TEMPORARY_TEACHERS",
    "V9_IDENTITY_RELPATH",
    "assert_not_protected_live_writer",
    "canonical_json",
    "clamp_unit",
    "deterministic_id",
    "env_flag",
    "read_v9_identity",
    "repo_root_from",
    "require_sha256",
    "sha256_bytes",
    "sha256_obj",
    "sha256_text",
    "utc_now",
]
