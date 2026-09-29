"""Regression: C5 public identity must remain usable without optional pydantic/RAIOS provider imports."""
from __future__ import annotations

import builtins
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "ai-os"
sys.path.insert(0, str(SCRIPTS))

from raios_c5_whoami import whoami  # noqa: E402
from raios_c5_screen import teach_reply  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def _block_optional_runtime_imports(monkeypatch):
    real_import = builtins.__import__

    def blocked(name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".", 1)[0]
        if root == "pydantic" or name.startswith("raios_mcp"):
            raise ModuleNotFoundError(name)
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked)


def test_whoami_survives_without_optional_runtime_imports(monkeypatch):
    _block_optional_runtime_imports(monkeypatch)
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = whoami()
    after = WAL.stat().st_mtime if WAL.exists() else None

    assert rec["ok"] is True
    assert rec["from"] == "C5"
    assert rec["parent"] == "C1"
    assert rec["paid_api"] is False
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert rec["languages_customer_live_count"] >= 4
    assert rec["languages_realized_count"] >= 4
    assert before == after


def test_public_identity_survives_without_optional_runtime_imports(monkeypatch):
    _block_optional_runtime_imports(monkeypatch)
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = teach_reply("مين أنت", locale="ar-EG")
    after = WAL.stat().st_mtime if WAL.exists() else None

    assert rec["ok"] is True
    assert rec["kind"] == "whoami"
    assert "C5" in rec["answer"]
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert before == after
