import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_p0 import GATE_ORDER  # noqa: E402
from raios_c5_phase0 import WORLD_CLASS_IS_NOT, stamp  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
MAP_JSON = ROOT / ".ai-os" / "reports" / "RAIOS-PHASE-ZERO-MAP.json"
MAP_MD = ROOT / ".ai-os" / "reports" / "RAIOS-PHASE-ZERO-MAP.md"


def test_phase0_map_is_discovery_not_kernel_and_does_not_flip_locks():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = stamp()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["canonical"] is False
    assert rec["new_kernel"] is False
    assert rec["gl005_proven"] is False
    assert rec["extracted_qwen_granite"] is False
    assert rec["safe_to_remove_source"] is False
    assert rec["source_deleted"] is False
    assert rec["decision"] == "D-061"
    assert rec["execution"][0]["name"] == "PHASE_ZERO_MAP"
    assert rec["execution"][1]["name"] == GATE_ORDER[0]
    assert rec["execution"][2]["name"] == GATE_ORDER[1]
    assert rec["execution"][3]["name"] == GATE_ORDER[2]
    assert rec["execution"][1]["status"] in {"BLOCKED", "FAIL"}
    assert rec["p0"]["gate1"]["mock"] is False
    assert rec["p0"]["extracted_qwen_granite"] is False
    claims = {row["claim"] for row in rec["reject"]}
    assert "Celerp" in claims
    assert "CI_PASS_AS_INTELLIGENCE" in WORLD_CLASS_IS_NOT
    egypt = next(b for b in rec["brains"] if b["id"] == "GREENY_LIFE_EGYPT")
    uae = next(b for b in rec["brains"] if b["id"] == "GREENS_NATURE_UAE")
    norway = next(b for b in rec["brains"] if b["id"] == "GREEN_LINES_NORWAY_EU")
    assert egypt["fill_from_this_slice"] is False
    assert uae["fill_from_this_slice"] is False
    assert norway["fill_from_this_slice"] is False
    assert uae["gap_open"] is True
    assert norway["gap_open"] is True
    assert egypt["gap_open"] is False
    assert "PHASE_ZERO_MAP_NE_NEW_KERNEL=true" in rec["text"]
    assert "GL005_PROVEN=false" in rec["text"]
    assert before == after
    assert MAP_JSON.is_file()
    assert MAP_MD.is_file()
    dumped = json.loads(MAP_JSON.read_text(encoding="utf-8"))
    assert dumped["gl005_proven"] is False
    assert dumped["extracted_qwen_granite"] is False
    assert dumped["p0"]["gate1_status"] in {"BLOCKED", "FAIL"}
    assert dumped["execution"][0]["status"] == "DONE_DISCOVERED"
    assert all("name" in row and "path" in row for row in rec["keepers"])
    assert any(row["name"] == "phase0" and row["exists"] for row in rec["keepers"])
    assert "WORLD-CLASS DISCOVERY" in MAP_MD.read_text(encoding="utf-8")
