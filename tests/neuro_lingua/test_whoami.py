import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_whoami import whoami  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def test_c5_whoami_from_git_not_paid_rag():
    rec = whoami()
    assert rec["ok"] is True
    assert rec["from"] == "C5"
    assert rec["parent"] == "C1"
    assert rec["cursor_session_ne_c5"] is True
    assert rec["paid_api"] is False
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert rec["languages_customer_live_count"] == 4
    for locale in ("ar-EG", "ar-GULF", "en", "nb-NO"):
        assert locale in rec["languages_customer_live"]
    assert rec["languages_realized_count"] >= 4
    assert "sv-SE" in rec["languages_realized"]
    assert "da-DK" in rec["languages_realized"]
    assert "ar-SA" in rec["languages_declared_unimplemented"]
    assert rec["engine_now"]["inject"].endswith("raios_c5_mind_fill.ps1")
    assert "LangChain" in rec["engine_now"]["not"]
    assert (ROOT / "scripts" / "ai-os" / "raios_c5_whoami.ps1").is_file()
    assert (ROOT / ".ai-os" / "learning" / "C5-WHOAMI.md").is_file()
