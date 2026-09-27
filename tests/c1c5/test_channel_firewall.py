from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANNEL = ROOT / ".ai-os" / "control" / "RAIOS-C1-C5-CHANNEL.py"


def _load():
    spec = importlib.util.spec_from_file_location("raios_c1_c5_channel", CHANNEL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_arabic_greeting_and_execution_firewall():
    ch = _load()
    assert ch.is_greeting("مرحبا")
    assert ch.is_now_execution_question("هل نفذت الآن GL-002 وGL-003 وGL-004؟")
    assert ch.is_evidence_question("ما الأدلة التي لديك على أي تنفيذ ذكرته في ردودك السابقة؟")
    visible, count, refs = ch.apply_claim_firewall("مرحبا", "ignored")
    assert "C5@AG" in visible
    assert count == 0
    assert refs == "EVIDENCE=NONE_AVAILABLE"
    blocked, blocked_count, _ = ch.apply_claim_firewall(
        "هل نفذت الآن GL-002 وGL-003 وGL-004؟", "executed everything"
    )
    assert blocked.lstrip().startswith("NOT_PROVEN")
    assert blocked_count == 0
    unclear, _, _ = ch.apply_claim_firewall("klnm", "whatever")
    assert "لم أفهم" in unclear
