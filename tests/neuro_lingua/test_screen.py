import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_screen import PAGE, teach_reply  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def test_screen_is_standard_rtl_and_does_not_touch_wal():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = teach_reply("مين أنت")
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["from"] == "C5"
    assert rec["paid_api"] is False
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert before == after
    assert "C5" in rec["answer"]
    assert rec["kind"] == "whoami"
    assert "dir=\"rtl\"" in PAGE
    assert "شاشة النظام" in PAGE
    assert "LangChain" in PAGE
    assert (ROOT / "scripts" / "ai-os" / "raios_c5_screen.ps1").is_file()


def test_screen_decodes_flipped_keyboard_on_turn():
    rec = teach_reply("DULG AHAM")
    assert rec["flipped"] is True
    assert rec["decoded"] == "يعمل شاشة"
    assert rec["kind"] == "screen"
    assert "127.0.0.1" not in rec["answer"] or "شاشة" in rec["answer"]
    assert "33e431" not in rec["answer"]
