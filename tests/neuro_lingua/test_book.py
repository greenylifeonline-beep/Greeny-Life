import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_book import BOOK, cycle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORT = ROOT / ".ai-os" / "reports" / "C5-BOOK-CYCLE.json"


def test_c5_book_cycle_runs_nine_steps_and_does_not_promote():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = cycle()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["from"] == "C5"
    assert rec["parent"] == "C1"
    assert rec["book"] == list(BOOK)
    assert [row["name"] for row in rec["steps"]] == list(BOOK)
    assert rec["gl005_proven"] is False
    assert rec["extracted_qwen_granite"] is False
    assert rec["authenticated_orchestration_task"] is False
    assert rec["wal_written"] is False
    assert rec["self_promote"] is False
    assert rec["paid_api"] is False
    assert rec["experience"]["knowledge"] is False
    assert rec["experience"]["promoted"] is False
    assert rec["experience"]["reproduced"] is True
    assert rec["highest_weakness"] == "AUTHENTICATED_ORCHESTRATION_TASK"
    assert rec["stop"] == "AUTHENTICATED_ORCHESTRATION_TASK"
    assert "GL005_PROVEN=false" in rec["text"]
    assert before == after
    assert REPORT.is_file()
