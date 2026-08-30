"""C5 PUBLIC identity must answer without pydantic, NeuroLingua, or MCP Python imports."""
from __future__ import annotations

import builtins
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))

from raios_c5_whoami import named_cortex_from_registry, whoami  # noqa: E402
from raios_c5_screen import teach_reply  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def _block_neurolingua_and_mcp(monkeypatch):
    real_import = builtins.__import__

    def blocked(name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".", 1)[0]
        if root in {"raios", "pydantic"} or name.startswith("raios_mcp"):
            raise ModuleNotFoundError(name)
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked)


def test_registry_named_candidate_does_not_need_pydantic():
    assert named_cortex_from_registry() == "qwen3.6:35b-a3b"


def test_whoami_survives_missing_neurolingua_and_mcp(monkeypatch):
    _block_neurolingua_and_mcp(monkeypatch)
    rec = whoami()
    assert rec["ok"] is True
    assert rec["from"] == "C5"
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert rec["languages_customer_live_count"] >= 4
    assert rec["c5_bind"]["bind_degraded"] is True
    assert rec["c5_bind"]["mcp_reachable"] is False
    assert rec["c5_bind"]["mcp_tool_count"] == 8
    assert rec["c5_bind"]["cortex_model"] == "qwen3.6:35b-a3b"
    assert rec["c5_bind"]["duplicate_mcp"] is False


def test_screen_identity_arabic_without_pydantic(monkeypatch):
    _block_neurolingua_and_mcp(monkeypatch)
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = teach_reply("مين أنت", locale="ar-EG", lane="PUBLIC")
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["kind"] == "whoami"
    assert rec.get("error") != "ModuleNotFoundError"
    assert "C5" in rec["answer"]
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert before == after


def test_short_identity_typo_is_whoami(monkeypatch):
    _block_neurolingua_and_mcp(monkeypatch)
    rec = teach_reply("ين أنت")
    assert rec["kind"] == "whoami"
    assert rec["ok"] is True
    assert "C5" in rec["answer"]


def test_speak_without_pydantic_does_not_crash(monkeypatch):
    _block_neurolingua_and_mcp(monkeypatch)
    rec = teach_reply("عندكم عسل؟", locale="ar-EG", lane="PUBLIC")
    assert rec["ok"] is True
    assert rec["kind"] == "speak"
    assert rec.get("error") != "ModuleNotFoundError"
    assert rec.get("error") == "MODEL_MISSING"
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert "سعر" in rec["answer"] or "MODEL_MISSING" in rec["answer"]
