import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_p0 import (  # noqa: E402
    ASSIMILATION_CHAIN,
    GATE_ORDER,
    classify_sources,
    extracted_from_chain,
    stage,
    stamp,
)

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
STATE = ROOT / ".ai-os" / "state" / "FOUNDATION.json"


def test_student_is_not_qwen_granite_source():
    row = classify_sources(["qwen2.5:0.5b"])
    assert row["source_present"] is False
    assert row["student_present"] is True
    assert row["qwen_cortex_present"] is False
    assert row["granite_present"] is False
    assert row["student_ne_extraction"] is True
    assert row["reason"] == "STUDENT_ONLY_NOT_SOURCE"


def test_cortex_plus_granite_is_source_present():
    row = classify_sources(["qwen3.6:35b-a3b", "granite4:3b"])
    assert row["source_present"] is True
    assert row["qwen_cortex_present"] is True
    assert row["granite_present"] is True


def test_extracted_requires_full_chain():
    incomplete = [stage(name, "UNREACHED", "blocked") for name in ASSIMILATION_CHAIN]
    incomplete[0] = stage("SOURCE_PRESENT", "FAIL", "absent")
    assert extracted_from_chain(incomplete) is False
    complete = [stage(name, "PASS", "ok") for name in ASSIMILATION_CHAIN]
    assert extracted_from_chain(complete) is True
    shuffled = list(reversed(complete))
    assert extracted_from_chain(shuffled) is False


def test_p0_live_fail_closed_does_not_flip_locked_facts():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = stamp()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["order"] == list(GATE_ORDER)
    assert rec["authenticated_orchestration_task"] is False
    assert rec["extracted_qwen_granite"] is False
    assert rec["safe_to_remove_source"] is False
    assert rec["gl005_proven"] is False
    assert rec["source_deleted"] is False
    assert rec["facts"]["EXTRACTED_QWEN_GRANITE"] is False
    assert rec["facts"]["GL005_PROVEN"] is False
    assert rec["facts"]["SAFE_TO_REMOVE_SOURCE"] is False
    assert rec["facts"]["AUTHENTICATED_ORCHESTRATION_TASK"] is False
    assert rec["facts"]["CI_1e28f84"] == "PASS"
    assert rec["facts"]["CI_68af867"] == "PASS"
    assert rec["gate1"]["mock"] is False
    assert rec["gate1"]["side_test_path"] is False
    assert rec["gate1"]["path"] == "product"
    assert rec["gate1"]["minted_secret"] is False
    assert rec["gate1"]["forged_session"] is False
    assert rec["gate1"]["authenticated_orchestration_task"] is False
    assert rec["gate1"]["status"] in {"BLOCKED", "FAIL"}
    assert rec["gate1"]["session"].get("authenticated") in (False, None)
    if rec["gate1"]["unauthenticated_post"].get("code") == 401:
        assert rec["gate1"]["classification"] == "CAPABILITY_PROTECTED"
        assert rec["gate1"]["authenticated_post"] is None
    if rec["gate1"]["before"].get("code") == 500:
        assert rec["gate1"]["status"] == "BLOCKED"
    assert rec["gate2"]["extracted_qwen_granite"] is False
    assert isinstance(rec["gate2"]["sources"]["source_present"], bool)
    if rec["gate2"]["sources"]["source_present"]:
        assert rec["gate2"]["stop_stage"] in {"CAPABILITY_EXECUTES", "SOURCE_DISABLED_OR_ISOLATED", "C5_EXECUTES_SAME_CAPABILITY", "SOURCE_HASH_GONE_AND_C5_STILL_PASSES"}
    else:
        assert rec["gate2"]["stop_stage"] == "SOURCE_PRESENT"
    if rec["gate2"]["sources"]["source_present"]:
        assert rec["gate2"]["chain"][0]["status"] == "PASS"
    else:
        assert rec["gate2"]["chain"][0]["status"] == "FAIL"
    assert rec["gate2"]["student_ne_extraction"] is True
    assert rec["gate3"]["status"] == "UNREACHED"
    assert rec["gate3"]["gl005_proven"] is False
    assert rec["stop"] == "AUTHENTICATED_ORCHESTRATION_TASK"
    assert "AUTHENTICATED_ORCHESTRATION_TASK=false" in rec["text"]
    assert "EXTRACTED_QWEN_GRANITE=false" in rec["text"]
    assert "GL005_PROVEN=false" in rec["text"]
    assert "SAFE_TO_REMOVE_SOURCE=false" in rec["text"]
    assert "CI_PASS_NE_ASSIMILATION=true" in rec["text"]
    assert "STUDENT_NE_EXTRACTION=true" in rec["text"]
    assert "SOURCE_DELETED=false" in rec["text"]
    assert "MOCK=false" in rec["text"]
    assert before == after
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert state["facts"]["EXTRACTED_QWEN_GRANITE"] is False
    assert state["facts"]["GL005_PROVEN"] is False
    assert state["facts"]["AUTHENTICATED_ORCHESTRATION_TASK"] is False
    assert state["p0"]["order"] == list(GATE_ORDER)
    assert state["p0_decision"] == "D-060"
