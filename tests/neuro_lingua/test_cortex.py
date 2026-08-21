from raios.neuro_lingua.cortex import (
    CORTEX_IDENTITY,
    gate_run,
    refuse_throw,
    treat,
)
from raios.neuro_lingua.governor import CognitiveResourceGovernor
from raios.neuro_lingua.qwen_runtime import generate


def test_c1_owns_cortex_hold_is_not_throw(monkeypatch):
    monkeypatch.delenv("C1_CORTEX_RUN", raising=False)
    monkeypatch.delenv("C1_CORTEX_THROW", raising=False)
    gov = CognitiveResourceGovernor()
    decision = gov.admit("SEMANTIC_INTERPRETATION")
    assert decision.admitted is False
    assert decision.reason == "CORTEX_HOLD_AWAITING_C1_RUN"
    assert gov.cortex_isolated is False
    assert gov.main_cortex_identity == CORTEX_IDENTITY
    gate = gate_run()
    assert gate["isolated_as_disposal"] is False
    assert gate["owner"] == "C1"
    assert "treat" in gate["verbs"]
    refused = generate("hello", model=CORTEX_IDENTITY)
    assert refused["ok"] is False
    assert refused["error"] == "CORTEX_HOLD_AWAITING_C1_RUN"
    assert refused["isolated_as_disposal"] is False


def test_executor_never_throws_cortex():
    rec = refuse_throw()
    assert rec["ok"] is False
    assert rec["error"] == "EXECUTOR_NE_THROW_CORTEX"


def test_explicit_receipt_names_qwen36_cortex():
    from raios.neuro_lingua.cortex import explicit_receipt

    rec = explicit_receipt()
    assert rec["identity"] == "qwen3.6:35b-a3b"
    assert "IDENTITY=qwen3.6:35b-a3b" in rec["text"]
    assert "STUDENT_NE_CORTEX=true" in rec["text"]
    assert "LOADED=false" in rec["text"]
    assert "GL005_PROVEN=false" in rec["text"]
    assert rec["sha256"]


def test_treat_does_not_load_or_throw():
    rec = treat()
    assert rec["ok"] is True
    assert rec["loaded"] is False
    assert rec["thrown"] is False
    assert rec["run"] is False
    assert rec["identity"] == "qwen3.6:35b-a3b"


def test_c1_run_on_this_host_still_blocked_without_gpu(monkeypatch):
    monkeypatch.setenv("C1_CORTEX_RUN", "true")
    monkeypatch.delenv("C1_CORTEX_THROW", raising=False)
    gate = gate_run()
    assert gate["run_granted"] is True
    assert gate["admitted"] is False
    assert gate["reason"] == "HOST_CANNOT_RUN_CORTEX"


def test_c1_run_and_capable_host_admits(monkeypatch):
    monkeypatch.setenv("C1_CORTEX_RUN", "1")
    monkeypatch.delenv("C1_CORTEX_THROW", raising=False)
    monkeypatch.setattr(
        "raios.neuro_lingua.cortex.host_can_run",
        lambda min_free_gb=24.0: (True, "HOST_CAN_RUN_CORTEX"),
    )
    gov = CognitiveResourceGovernor()
    decision = gov.admit("SEMANTIC_INTERPRETATION")
    assert decision.admitted is True
    assert decision.reason == "C1_CORTEX_RUN"
    local = gov.admit("LANGUAGE_ID")
    assert local.admitted is True
    assert local.reason == "DETERMINISTIC_OR_LOCAL"
