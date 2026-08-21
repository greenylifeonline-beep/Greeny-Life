import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_wave1 import ARTIFACTS, BOUND_HEAD, stamp  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORTS = ROOT / ".ai-os" / "reports"


def test_wave1_stamps_ten_artifacts_fail_closed_no_wal():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = stamp()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["from"] == "C2"
    assert rec["parent"] == "C1"
    assert rec["bound_head"] == BOUND_HEAD
    assert rec["bound_is_ancestor"] is True
    assert rec["no_reset"] is True
    assert rec["no_stash"] is True
    assert rec["no_source_deletion"] is True
    assert rec["no_auto_canonical"] is True
    assert rec["no_fake_pass"] is True
    assert rec["llm_fabric_proven"] is False
    assert rec["assimilation_proven"] is False
    assert rec["rsic_proven"] is False
    assert rec["aemc_proven"] is False
    assert rec["cetd_proven"] is False
    assert rec["extracted_qwen_granite"] is False
    assert rec["safe_to_remove_source"] is False
    assert rec["authenticated_orchestration_task"] is False
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert rec["next"] == "AUTHENTICATED_ORCHESTRATION_TASK"
    assert [row["name"] for row in rec["artifacts"]] == list(ARTIFACTS)
    assert all(len(row["sha256"]) == 64 for row in rec["artifacts"])
    assert before == after
    for name in ARTIFACTS:
        path = REPORTS / name
        assert path.is_file(), name
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload.get("gl005_proven") is False
        assert payload.get("canonical") is False
    assim = json.loads((REPORTS / "RAIOS-ASSIMILATION-E2E-PROOF.json").read_text(encoding="utf-8"))
    assert assim["wal_written"] is False
    assert assim["assimilation_proven"] is False
    assert assim["stop"] == "WAL"
    wal_stage = next(s for s in assim["stages"] if s["id"] == "WAL")
    assert wal_stage["status"] == "BLOCKED"
    memos = json.loads((REPORTS / "RAIOS-C5-MEMO-DECISION-MATRIX.json").read_text(encoding="utf-8"))
    assert memos["rejected"] == 8
    assert all(row["status"] == "REJECT" for row in memos["rows"])
    fabric = json.loads((REPORTS / "RAIOS-LLM-FABRIC-REALITY-AUDIT.json").read_text(encoding="utf-8"))
    assert fabric["llm_fabric_proven"] is False
    assert fabric["granite_sovereign_backbone"] is False
    erp = json.loads((REPORTS / "RAIOS-ERP-REALITY-MATRIX.json").read_text(encoding="utf-8"))
    assert erp["clone_odoo"] is False
    assert "Invoice" in erp["finance_gap"]
    assert any(d["domain"] == "sales" for d in erp["domains"])
    assert "GL005_PROVEN=false" in rec["text"]
    assert "LLM_FABRIC_PROVEN=false" in rec["text"]
    assert "NO_RESET=true" in rec["text"]
