import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_reality import ARTIFACTS, stamp  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORTS = ROOT / ".ai-os" / "reports"


def test_c2_reality_stamp_writes_eight_artifacts_without_promoting():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = stamp()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["from"] == "C2"
    assert rec["parent"] == "C1"
    assert rec["c5"] == "git_not_this_session"
    assert rec["decision"] == "D-063"
    assert rec["canonical"] is False
    assert rec["new_kernel"] is False
    assert rec["platform_proven"] is False
    assert rec["gl005_proven"] is False
    assert rec["extracted_qwen_granite"] is False
    assert rec["safe_to_remove_source"] is False
    assert rec["authenticated_orchestration_task"] is False
    assert rec["wal_written"] is False
    assert rec["c6_c10_live"] is False
    assert rec["next"] == "AUTHENTICATED_ORCHESTRATION_TASK"
    assert [row["name"] for row in rec["artifacts"]] == list(ARTIFACTS)
    assert before == after
    for name in ARTIFACTS:
        path = REPORTS / name
        assert path.is_file(), name
        if name.endswith(".json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload.get("gl005_proven") is False
            assert payload.get("canonical") is False
            assert payload.get("from") == "C2"
    council = json.loads((REPORTS / "RAIOS-C1-C10-COUNCIL-ARCHITECTURE.json").read_text(encoding="utf-8"))
    assert council["live_count"] == 5
    assert council["not_seated"] == ["C6", "C7", "C8", "C9", "C10"]
    assert all(row["invented_this_slice"] is False for row in council["seats"])
    assert council["seats"][5]["status"] == "NOT_SEATED"
    graph = json.loads((REPORTS / "RAIOS-MASTER-EXECUTION-GRAPH.json").read_text(encoding="utf-8"))
    assert graph["no_skip"] is True
    assert graph["nodes"][1]["name"] == "AUTHENTICATED_ORCHESTRATION_TASK"
    assert graph["nodes"][1]["skip"] is False
    erp = json.loads((REPORTS / "RAIOS-ERP-REALITY-MATRIX.json").read_text(encoding="utf-8"))
    assert erp["clone_odoo"] is False
    assert erp["clone_celerp"] is False
    assert "Invoice" in erp["finance_gap"]
    assert "Payment" in erp["finance_gap"]
    assert any(d["domain"] == "sales" for d in erp["domains"])
    plan = (REPORTS / "RAIOS-STATE-OF-THE-ART-RESEARCH-PLAN.md").read_text(encoding="utf-8")
    assert "SCALE_BY_COMPRESSION_NOT_COMPLEXITY" in plan
    assert "GL005_PROVEN=false" in plan
    assert "LangChain" in plan
    assert "C6–C10" in plan or "C6-C10" in plan or "C6–C10" in rec["text"]
    assert "SCALE_BY_COMPRESSION_NOT_COMPLEXITY=true" in rec["text"]
    assert "GL005_PROVEN=false" in rec["text"]
    assert "C6_C10_NE_LIVE=true" in rec["text"]
