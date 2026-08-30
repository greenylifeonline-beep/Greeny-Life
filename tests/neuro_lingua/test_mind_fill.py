import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_mind_fill import fill, important_paths  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def test_mind_fill_injects_important_files_not_wal():
    rels = {str(path.relative_to(ROOT)).replace("\\", "/") for path in important_paths()}
    assert ".ai-os/CORE-CONTRACT.md" in rels
    assert "canonical/inventory/stock-levels.json" in rels
    assert all("RAIOS/V9" not in rel for rel in rels)
    rec = fill()
    assert rec["ok"] is True
    assert rec["files"] >= 8
    assert rec["wal_written"] is False
    assert rec["gl005_proven"] is False
    assert rec["mind_laws"] >= 1
    assert rec["put"]["digests"] == ".ai-os/learning/DIGESTS.jsonl"
    assert "C5_MIND_FILL_IMPORTANT_ONLY" in rec["law"]
