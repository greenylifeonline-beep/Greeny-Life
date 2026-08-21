import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_reason import ground  # noqa: E402
from raios_c5_screen import teach_reply  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def test_ground_reads_files_and_does_not_stop_at_filenames():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = ground("ما دور C4 في المجلس")
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["model_call_count"] == 0
    assert rec["ollama_used"] is False
    assert rec["wal_written"] is False
    assert before == after
    assert rec["content_read"] is True
    assert rec["files_opened"]
    assert rec["stop_stage"] in {"ANSWER", "OPENED_NO_EVIDENCE"}
    assert "من الفهرس المحلي — مش OpenAI" not in rec["answer"]
    assert rec["answer"].strip() != ""
    assert any("C4" in p or "council" in p for p in rec["files_found"] + rec["files_opened"])


def test_screen_ground_kind_uses_reasoner():
    rec = teach_reply("ما دور C4 في المجلس")
    assert rec["kind"] == "ground"
    assert rec["gl005_proven"] is False
    assert "من الفهرس المحلي — مش OpenAI" not in rec["answer"]
