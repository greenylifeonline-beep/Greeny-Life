"""Hermes knowledge ingest beside absorb-digest.

Not a ninth MCP tool. Not a second WAL. Not Core. Provider adapter only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def profile(repo: Path) -> dict[str, Any]:
    row = _load(Path(repo) / ".ai-os" / "mcp" / "HERMES-PROVIDER.json", {})
    return row if isinstance(row, dict) else {}


def ingest(repo: Path, *, text: str | None = None, path: str | None = None, persist: bool = False) -> dict[str, Any]:
    repo = Path(repo).resolve()
    spec = profile(repo)
    result = {
        "schema": "raios.hermes-ingest.v1",
        "provider_id": spec.get("provider_id") or "hermes-knowledge-ingest",
        "ninth_mcp": False,
        "second_wal": False,
        "beside": "raios.absorb-digest.v2",
        "core": False,
    }
    if spec.get("ninth_mcp") is True:
        result.update(status="BLOCKED", reason="HERMES_MUST_NOT_BE_NINTH_MCP")
        return result
    if spec.get("authorized_by") != "C1" or spec.get("enabled") is not True:
        result.update(status="BLOCKED_DISCOVERY", reason="HERMES_PROVIDER_NOT_C1_ENABLED")
        return result
    if not text and not path:
        result.update(status="READY", reason="SLOT_WIRED_NO_PAYLOAD")
        return result
    from raios.neuro_lingua.kae import assimilate
    from raios.neuro_lingua.kae_libraries import assimilate_path

    if path:
        kae = assimilate_path(path, ingest=persist)
    else:
        kae = assimilate(str(text), source_kind="hermes_provider", external_calls=0, ingest=persist)
    result.update(status="ABSORBED" if kae.get("ok") else "FAILED", kae={
        "ok": bool(kae.get("ok")),
        "canonical": bool(kae.get("canonical")),
        "promoted": bool(kae.get("promoted")),
        "wal_written": bool(kae.get("wal_written")),
    })
    return result
