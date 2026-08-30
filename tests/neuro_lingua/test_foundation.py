import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_foundation import stamp  # noqa: E402
from raios_c5_whoami import whoami  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
STATE = ROOT / ".ai-os" / "state" / "FOUNDATION.json"


def test_foundation_ci_pass_does_not_flip_assimilation_or_gl005():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = stamp()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["facts"]["CI_1e28f84"] == "PASS"
    assert rec["facts"]["CI_68af867"] == "PASS"
    assert rec["facts"]["EXTRACTED_QWEN_GRANITE"] is False
    assert rec["facts"]["SAFE_TO_REMOVE_SOURCE"] is False
    assert rec["facts"]["GL005_PROVEN"] is False
    assert rec["facts"]["AUTHENTICATED_ORCHESTRATION_TASK"] is False
    assert rec["gl005_proven"] is False
    assert rec["extracted_qwen_granite"] is False
    assert rec["safe_to_remove_source"] is False
    assert rec["sources"]["extracted_qwen_granite"] is False
    assert rec["gl005"]["gl005_proven"] is False
    assert "CI_PASS_NE_ASSIMILATION" in rec["law"]
    assert before == after
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["facts"]["EXTRACTED_QWEN_GRANITE"] is False
    assert state["facts"]["GL005_PROVEN"] is False
    assert "CI(1e28f84)=PASS" in rec["text"]
    assert "CI(68af867)=PASS" in rec["text"]
    assert "EXTRACTED_QWEN_GRANITE=false" in rec["text"]
    assert "AUTHENTICATED_ORCHESTRATION_TASK=false" in rec["text"]
    assert "THEN_QWEN_GRANITE_ASSIMILATION" in rec["text"]


def test_whoami_carries_foundation_flags():
    rec = whoami()
    assert rec["gl005_proven"] is False
    assert rec["foundation"]["EXTRACTED_QWEN_GRANITE"] is False
    assert rec["foundation"]["SAFE_TO_REMOVE_SOURCE"] is False
    assert rec["foundation"]["AUTHENTICATED_ORCHESTRATION_TASK"] is False
    assert rec["foundation"]["CI_1e28f84"] == "PASS"
    assert rec["foundation"]["CI_68af867"] == "PASS"
