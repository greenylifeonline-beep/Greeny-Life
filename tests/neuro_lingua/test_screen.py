import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_screen import PAGE, load_history, present_answer, teach_reply  # noqa: E402

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
    assert "127.0.0.1:8765" in PAGE
    assert "port-forward" in PAGE
    assert "GL005" in PAGE
    assert "إرسال" in PAGE
    assert "data-fill=\"مين أنت\"" in PAGE
    assert "nb-NO" in PAGE
    assert "Systemskjerm" in PAGE
    assert "data-locale=\"nb-NO\"" in PAGE
    assert (ROOT / "scripts" / "ai-os" / "raios_c5_screen.ps1").is_file()


def test_screen_decodes_flipped_keyboard_on_turn():
    rec = teach_reply("DULG AHAM")
    assert rec["flipped"] is True
    assert rec["decoded"] == "يعمل شاشة"
    assert rec["kind"] == "screen"
    assert "hit_count=" not in rec["answer"]
    assert "LangChain" in rec["answer"]
    for row in load_history():
        assert "hit_count=" not in (row.get("answer") or "")
        assert "33e431" not in (row.get("answer") or "")


def test_screen_presents_seat_card_not_index_dump():
    rec = teach_reply("ما دور C4 في المجلس")
    assert rec["kind"] == "ground"
    assert rec["gl005_proven"] is False
    assert "hit_count=" not in rec["answer"]
    assert "من الفهرس المحلي — مش OpenAI" not in rec["answer"]
    assert "ASSESSOR" in rec["answer"] or "مقيّم" in rec["answer"] or "DeepSeek" in rec["answer"]
    assert rec["answer"].count('"') < 8
    assert "33e431" not in rec["answer"]


def test_present_answer_strips_hex_and_telemetry():
    raw = (
        "من الفهرس المحلي\n"
        "— 33e4311255f95d8db7f14bc269d90f31b85e04d371d666586ee6f660db9085d7\n"
        "hit_count=13 · paid_api=false · GL005_PROVEN=false\n"
        "C4 actor_role=ASSESSOR\n"
        "SEAL C2 GL-COUNCIL-4a11023c3c321b6f CHAL-c02ec6b915caac01"
    )
    cleaned = present_answer(raw)
    assert "33e431" not in cleaned
    assert "hit_count=" not in cleaned
    assert "SEAL" not in cleaned
    assert "ASSESSOR" in cleaned


def test_empty_turn_is_not_whoami_and_skips_history():
    rec = teach_reply("   ")
    assert rec["kind"] == "empty"
    assert rec["stored"] is False
    assert rec["wal_written"] is False
    assert rec["gl005_proven"] is False


def test_short_identity_typo_is_whoami_not_index_dump():
    rec = teach_reply("ين أنت")
    assert rec["kind"] == "whoami"
    assert "SEAL" not in rec["answer"]
    assert "C5" in rec["answer"]
    assert rec["gl005_proven"] is False


def test_history_collapses_repeats_and_shows_seat_card():
    rows = load_history()
    decoded = [str(row.get("decoded") or "") for row in rows]
    assert decoded.count("مين أنت") <= 1
    assert decoded.count("يعمل شاشة") <= 1
    for row in rows:
        answer = row.get("answer") or ""
        assert "hit_count=" not in answer
        assert "33e431" not in answer
        assert "SEAL" not in answer
        if "ما دور C4" in str(row.get("decoded") or ""):
            assert "ASSESSOR" in answer or "مقيّم" in answer or "DeepSeek" in answer
            assert "METHOD.md" not in answer
            assert '"instance_role"' not in answer


def test_screen_norwegian_and_english_identity():
    nb = teach_reply("Hvem er du")
    assert nb["kind"] == "whoami"
    assert nb["locale"] == "nb-NO"
    assert nb["flipped"] is False
    assert "sønn" in nb["answer"] or "RAIOS" in nb["answer"]
    assert "LangChain" in nb["answer"]
    en = teach_reply("Who are you")
    assert en["kind"] == "whoami"
    assert en["locale"] == "en"
    assert en["flipped"] is False
    assert "son of C1" in en["answer"]
    gulf = teach_reply("شلونك من أنت")
    assert gulf["kind"] == "whoami"
    assert gulf["locale"] == "ar-GULF"
    council = teach_reply("Hva er C4s rolle i rådet")
    assert council["kind"] == "ground"
    assert council["locale"] == "nb-NO"
    assert council["flipped"] is False
    assert "ASSESSOR" in council["answer"] or "DeepSeek" in council["answer"]
    assert council["gl005_proven"] is False
    assert council["wal_written"] is False
