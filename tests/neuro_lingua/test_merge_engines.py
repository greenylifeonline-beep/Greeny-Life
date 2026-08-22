import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_merge_engines import ARTIFACTS, CATALOG, stamp  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORTS = ROOT / ".ai-os" / "reports"


def test_merge_engines_inventory_fail_closed_no_wal_no_execution():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = stamp()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["from"] == "C2"
    assert rec["c5"] == "git"
    assert rec["merged_now"] is False
    assert rec["destructive_merge"] is False
    assert rec["brain_py_executed"] is False
    assert rec["archive_plan_executed"] is False
    assert rec["new_kernel"] is False
    assert rec["openai"] is False
    assert rec["langchain"] is False
    assert rec["wal_written"] is False
    assert rec["gl005_proven"] is False
    assert rec["canonical"] is False
    assert before == after
    ids = {row["id"] for row in rec["engines"]}
    assert "mind-fill" in ids
    assert "kae" in ids
    assert "cognitive-wal" in ids
    assert "brain-discover-merge" in ids
    assert "workflow-engine" in ids
    brain = next(row for row in rec["engines"] if row["id"] == "brain-discover-merge")
    assert brain["status"] == "DO_NOT_RUN"
    assert brain["exists"] is True
    live = rec["live_ids"]
    assert "mind-fill" in live
    assert "kae" in live
    assert "brain-discover-merge" not in live
    md = (REPORTS / "RAIOS-MERGE-ENGINES-INVENTORY.md").read_text(encoding="utf-8")
    assert "حقن العقل" in md
    assert "DO_NOT_RUN" in md
    assert "GL005_PROVEN=false" in md
    for name in ARTIFACTS:
        path = REPORTS / name
        assert path.is_file(), name
        if name.endswith(".json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload.get("gl005_proven") is False
            assert payload.get("merged_now") is False


def test_catalog_does_not_invent_langchain_or_second_wal():
    ids = {row["id"] for row in CATALOG}
    assert "langchain" not in ids
    assert "openai" not in ids
    assert "chroma" not in ids
    wal_rows = [row for row in CATALOG if "wal" in row["id"] or row["id"] == "cognitive-wal"]
    assert any(row["id"] == "cognitive-wal" for row in wal_rows)
    assert any(row["id"] == "nl-wal-adapter" for row in wal_rows)
    adapter = next(row for row in CATALOG if row["id"] == "nl-wal-adapter")
    assert adapter["merge_target"] == "RAIOS/V9/runtime/cognitive_event_bus.py"
