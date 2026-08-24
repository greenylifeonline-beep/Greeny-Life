import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / ".ai-os" / "receipts" / "c5-unrepairable-gc" / "LAST.json"


def test_unrepairable_receipt_flags_and_deleted_paths_are_gone():
    rec = json.loads(REC.read_text(encoding="utf-8"))
    assert rec["new_engine_created"] is False
    assert rec["new_bus_created"] is False
    assert rec["wal_written"] is False
    assert rec["gl005_proven"] is False
    assert rec["deleted_count"] == 60
    for row in rec["deleted"]:
        assert not (ROOT / row["path"]).exists(), row["path"]


def test_skipped_empty_ledgers_gitkeeps_and_gl003_remain():
    rec = json.loads(REC.read_text(encoding="utf-8"))
    kept = {row["path"] for row in rec["skipped"]}
    assert "guardrails/guardrails.jsonl" in kept
    assert "canonical/data/administration-master.json" in kept
    assert "greenlines_brain/dna/schema.json" in kept
    assert (
        "RAIOS/V9/evidence/quarantined-certifications/"
        "raios_v9.ZERO-BYTE.e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.py"
    ) in kept
    assert (ROOT / "canonical/data/administration-master.json").exists()
    assert (ROOT / "run_brain_cli_backup.py").stat().st_size > 100
    assert not (ROOT / "run_brain_cli.py").exists()
    wal = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
    assert wal.is_file()
    assert wal.stat().st_size > 0
