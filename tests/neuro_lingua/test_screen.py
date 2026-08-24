import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_screen import (  # noqa: E402
    BIND_PORTS,
    C1_PORT,
    LANE_C1,
    LANE_PUBLIC,
    PAGE,
    PAGE_C1,
    history_path,
    lane_of_port,
    load_history,
    present_answer,
    screen_health,
    teach_reply,
)

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
    assert "شاشة الجميع" in PAGE
    assert "LangChain" in PAGE
    assert "127.0.0.1:8765" in PAGE
    assert "control-plane" in PAGE
    assert "SESSION_TEMP" in PAGE
    assert "raios_c5_screen.ps1 -Install" in PAGE
    assert "GL005" in PAGE
    assert "إرسال" in PAGE
    assert "data-fill=\"مين أنت\"" in PAGE
    assert "nb-NO" in PAGE
    assert "Delt skjerm" in PAGE
    assert "data-locale=\"nb-NO\"" in PAGE
    assert "lane-PUBLIC" in PAGE
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
    assert nb["lane"] == LANE_PUBLIC
    assert nb["flipped"] is False
    assert "RAIOS" in nb["answer"]
    assert "LangChain" in nb["answer"]
    assert "sønn" not in nb["answer"]
    en = teach_reply("Who are you")
    assert en["kind"] == "whoami"
    assert en["locale"] == "en"
    assert en["lane"] == LANE_PUBLIC
    assert en["flipped"] is False
    assert "son of C1" not in en["answer"]
    assert "shared" in en["answer"].lower() or "C5" in en["answer"]
    gulf = teach_reply("شلونك من أنت")
    assert gulf["kind"] == "whoami"
    assert gulf["locale"] == "ar-GULF"
    mixed = teach_reply("Hvem er du", locale="en")
    assert mixed["kind"] == "whoami"
    assert mixed["locale"] == "nb-NO"
    council = teach_reply("Hva er C4s rolle i rådet")
    assert council["kind"] == "ground"
    assert council["locale"] == "nb-NO"
    assert council["flipped"] is False
    assert "ASSESSOR" in council["answer"] or "DeepSeek" in council["answer"]
    assert council["gl005_proven"] is False
    assert council["wal_written"] is False
    rows = load_history()
    nb_seat = [row for row in rows if "C4s rolle" in str(row.get("decoded") or "")]
    assert nb_seat
    assert "Levende rolle" in nb_seat[-1]["answer"] or "ASSESSOR" in nb_seat[-1]["answer"]
    assert "hit_count=" not in nb_seat[-1]["answer"]


def test_c1_console_keeps_founder_identity_and_separate_history():
    c1 = teach_reply("Who are you", lane=LANE_C1)
    assert c1["kind"] == "whoami"
    assert c1["lane"] == LANE_C1
    assert "son of C1" in c1["answer"]
    nb = teach_reply("Hvem er du", lane=LANE_C1)
    assert "sønn" in nb["answer"] or "RAIOS" in nb["answer"]
    status = teach_reply("حالة الشاشة", lane=LANE_C1)
    assert status["kind"] == "status"
    assert "8876" in status["answer"]
    assert "duplicate_c5=false" in status["answer"]
    c1_rows = load_history(lane=LANE_C1)
    assert any(row.get("kind") == "whoami" for row in c1_rows)
    assert any(row.get("kind") == "status" for row in c1_rows)
    assert history_path(LANE_C1) != history_path(LANE_PUBLIC)


def test_same_c5_dual_bind_and_honest_health():
    assert BIND_PORTS == (8765, 8876)
    assert C1_PORT == 8876
    assert lane_of_port(8765) == LANE_PUBLIC
    assert lane_of_port(8876) == LANE_C1
    rec = screen_health(port=8876)
    assert rec["ok"] is True
    assert rec["http"] == 200
    assert rec["from"] == "C5"
    assert rec["lane"] == LANE_C1
    assert rec["duplicate_c5"] is False
    assert rec["public_url"].endswith(":8765")
    assert rec["c1_url"].endswith(":8876")
    assert rec["MODEL"] == "qwen3.6:35b-a3b"
    assert rec["NAMED_CANDIDATE"] == "qwen3.6:35b-a3b"
    assert rec["BOUND_MODEL"] == "qwen3.6:35b-a3b"
    assert rec["PERMANENT_IDENTITY"] is False
    assert rec["student_substituted"] is False
    assert rec["gl005_proven"] is False
    assert rec["MAIN_CORTEX"] is rec["main_cortex"]
    assert rec["LOCAL_WINNER"] is False
    assert rec["ROLE"] == "CORTEX_MODEL"
    assert rec["LAPTOP_IS_MODEL_HOST"] is False
    assert rec["OLLAMA_IS_DEV_FALLBACK"] is True
    assert rec["TRANSPORT"] == "openai-compatible"
    assert rec["cursor_session_ne_c5"] is True
    assert rec["screen_home"] in {"SESSION_TEMP", "CONTROL_PLANE"}
    assert rec["duplicate_c5"] is False
    assert "127.0.0.1:8765" in PAGE
    assert "lane-PUBLIC" in PAGE
    assert "lane-C1" in PAGE_C1
    assert "c1-only" in PAGE_C1
    ps1 = (ROOT / "scripts" / "ai-os" / "raios_c5_screen.ps1").read_text(encoding="utf-8")
    assert "RAIOS-C5-SCREEN" in ps1
    assert "-Install" in ps1
    assert "-Ensure" in ps1
    assert "-Go" in ps1
    assert "http://127.0.0.1:8876" in ps1
    assert (ROOT / "scripts" / "ai-os" / "raios_c5_screen_ensure.sh").is_file()


def test_serve_args_honor_host_flag_and_keep_dual_bind():
    from raios_c5_screen import resolve_serve_args

    host, ports = resolve_serve_args(["raios_c5_screen.py", "--host", "127.0.0.1"])
    assert host == "127.0.0.1"
    assert ports == (8765, 8876)
    host2, ports2 = resolve_serve_args(["raios_c5_screen.py", "--serve"])
    assert host2 in {"127.0.0.1", "0.0.0.0"} or host2
    assert ports2 == (8765, 8876)
