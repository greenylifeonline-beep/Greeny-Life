"""C5 screen → NeuroLingua → ProviderRouter → cortex generate. No student swap. No WAL."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from raios.neuro_lingua.cortex import CORTEX_IDENTITY, CortexProvider
from raios.neuro_lingua.governor import CognitiveResourceGovernor
from raios.neuro_lingua.kernel import NeuroLingua
from raios.neuro_lingua.provider_contracts import CapabilityRequirement
from raios.neuro_lingua.qwen_runtime import generate, probe
from raios.neuro_lingua.router import ProviderRouter

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_screen import teach_reply  # noqa: E402
from raios_c5_speak import chat  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def _wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def test_router_tier0_offline_stays_deterministic():
    router = ProviderRouter()
    decision = router.route(
        CapabilityRequirement(capability="SEMANTIC_INTERPRETATION", offline_required=True)
    )
    assert decision["provider"] == "deterministic-neuro-lingua"
    assert decision["llm"] is False
    assert decision["model_name_bound"] is False
    assert router.metrics()["llm_calls"] == 0


def test_router_language_id_never_calls_cortex():
    router = ProviderRouter()
    decision = router.route(CapabilityRequirement(capability="LANGUAGE_ID", offline_required=False))
    assert decision["provider"] == "deterministic-neuro-lingua"
    assert decision["llm"] is False
    assert router.metrics()["llm_calls"] == 0


def test_live_probe_cortex_absent_is_model_missing_not_student():
    status = probe(use_cache=False)
    names = list(status.get("models") or [])
    if status.get("cortex_live"):
        assert any(n == CORTEX_IDENTITY or n.startswith(f"{CORTEX_IDENTITY}:") for n in names)
        return
    assert CORTEX_IDENTITY not in names
    rec = generate("hello", model=CORTEX_IDENTITY)
    assert rec["ok"] is False
    assert rec["error"] == "MODEL_MISSING"
    assert rec["model"] == CORTEX_IDENTITY
    assert rec["model_name_bound"] is False
    assert rec["student_substituted"] is False
    assert rec["llm_executed"] is False
    assert rec.get("cortex_used") is False


def test_router_semantic_online_binds_identity_and_execute_is_model_missing():
    router = ProviderRouter()
    decision = router.route(
        CapabilityRequirement(capability="SEMANTIC_INTERPRETATION", offline_required=False)
    )
    assert decision["provider"] == "main-cortex-capability"
    assert decision["error"] == "MODEL_MISSING"
    assert decision["model"] == CORTEX_IDENTITY
    assert decision["model_name_bound"] is False
    assert decision["student_substituted"] is False
    rec = router.execute(decision, {"text": "why is the shipment held?"})
    assert rec["ok"] is False
    assert rec["error"] == "MODEL_MISSING"
    assert rec["llm_executed"] is False
    assert rec["student_substituted"] is False
    assert rec["provider_execute_called"] is True
    assert router.metrics()["llm_calls"] == 0


def test_execute_rejects_student_as_cortex():
    router = ProviderRouter()
    rec = router.execute(
        {
            "provider": "main-cortex-capability",
            "model": "qwen2.5:0.5b",
            "model_name_bound": True,
            "llm": True,
        },
        {"text": "no"},
    )
    assert rec["ok"] is False
    assert rec["error"] == "STUDENT_NE_CORTEX"
    assert rec["llm_executed"] is False
    assert router.metrics()["llm_calls"] == 0


def test_mocked_live_cortex_execute_increments_llm_calls(monkeypatch):
    monkeypatch.setattr(
        "raios.neuro_lingua.qwen_runtime.probe",
        lambda *a, **k: {
            "cortex_live": True,
            "present": True,
            "models": [CORTEX_IDENTITY],
            "student_substituted": False,
        },
    )

    def fake_generate(prompt, **kwargs):
        assert kwargs.get("model") == CORTEX_IDENTITY
        return {
            "ok": True,
            "response": "cortex-bound-ok",
            "model": CORTEX_IDENTITY,
            "llm_executed": True,
            "model_name_bound": True,
            "student_substituted": False,
        }

    monkeypatch.setattr("raios.neuro_lingua.qwen_runtime.generate", fake_generate)
    router = ProviderRouter()
    decision = router.route(
        CapabilityRequirement(capability="SEMANTIC_INTERPRETATION", offline_required=False)
    )
    assert decision["llm"] is True
    assert decision["model_name_bound"] is True
    assert decision["model"] == CORTEX_IDENTITY
    rec = router.execute(decision, {"text": "reason about customs hold"})
    assert rec["ok"] is True
    assert rec["response"] == "cortex-bound-ok"
    assert rec["llm_executed"] is True
    assert rec["model_name_bound"] is True
    assert rec["model"] == CORTEX_IDENTITY
    assert rec["student_substituted"] is False
    assert rec["provider"] == "main-cortex-capability"
    assert rec["provider_execute_called"] is True
    assert router.metrics()["llm_calls"] == 1


def test_cortex_provider_is_language_provider_and_runs_generate(monkeypatch):
    monkeypatch.setattr(
        "raios.neuro_lingua.qwen_runtime.generate",
        lambda prompt, **kw: {
            "ok": True,
            "response": "via-provider",
            "model": CORTEX_IDENTITY,
            "llm_executed": True,
        },
    )
    provider = CortexProvider()
    assert provider.provider_id == "main-cortex-capability"
    rec = provider.run({"text": "hi"})
    assert rec["response"] == "via-provider"
    rec_async = asyncio.run(provider.execute("SEMANTIC_INTERPRETATION", {"text": "hi"}))
    assert rec_async["capability"] == "SEMANTIC_INTERPRETATION"


def test_kernel_default_interpret_stays_deterministic():
    nl = NeuroLingua(governor=CognitiveResourceGovernor())
    result = asyncio.run(nl.interpret("خلصلي الموضوع ده بس متبوظش حاجة"))
    assert result.metrics["llm_calls"] == 0
    routed = result.meaning.metadata["routing"]
    assert routed["llm"] is False
    assert routed["provider"] == "deterministic-neuro-lingua"


def test_kernel_online_missing_model_does_not_swap_student(monkeypatch):
    monkeypatch.setattr(
        "raios.neuro_lingua.qwen_runtime.probe",
        lambda *a, **k: {
            "cortex_live": False,
            "present": True,
            "models": ["qwen2.5:0.5b"],
            "student_substituted": False,
        },
    )
    nl = NeuroLingua()
    result = asyncio.run(nl.interpret("Why is the shipment on hold?", offline_required=False))
    routed = result.meaning.metadata["routing"]
    assert routed["error"] == "MODEL_MISSING"
    assert routed["model"] == CORTEX_IDENTITY
    assert routed["student_substituted"] is False
    assert result.metrics["llm_calls"] == 0
    assert result.meaning.metadata["provider_execute_called"] is True
    assert result.meaning.metadata["cortex_execution"] is not None
    assert result.meaning.metadata["cortex_execution"]["provider_execute_called"] is True
    semantic = next(s for s in result.stages if s.stage == "SEMANTIC_INTERPRETATION")
    assert semantic.payload.get("error") == "MODEL_MISSING"
    assert semantic.payload.get("student_substituted") is False
    assert semantic.payload.get("provider_execute_called") is True


def test_kernel_online_live_executes_cortex_generate(monkeypatch):
    monkeypatch.setattr(
        "raios.neuro_lingua.qwen_runtime.probe",
        lambda *a, **k: {
            "cortex_live": True,
            "present": True,
            "models": [CORTEX_IDENTITY],
            "student_substituted": False,
        },
    )
    monkeypatch.setattr(
        "raios.neuro_lingua.qwen_runtime.generate",
        lambda prompt, **kw: {
            "ok": True,
            "response": "held-for-missing-docs",
            "model": CORTEX_IDENTITY,
            "llm_executed": True,
            "model_name_bound": True,
            "student_substituted": False,
        },
    )
    nl = NeuroLingua()
    result = asyncio.run(nl.interpret("Why is the shipment on hold?", offline_required=False))
    assert result.metrics["llm_calls"] == 1
    assert result.meaning.metadata["provider_execute_called"] is True
    exec_rec = result.meaning.metadata["cortex_execution"]
    assert exec_rec["ok"] is True
    assert exec_rec["response"] == "held-for-missing-docs"
    assert exec_rec["model"] == CORTEX_IDENTITY
    assert exec_rec["model_name_bound"] is True
    assert exec_rec["llm_executed"] is True
    semantic = next(s for s in result.stages if s.stage == "SEMANTIC_INTERPRETATION")
    assert semantic.payload.get("cortex_response") == "held-for-missing-docs"


def test_chat_and_screen_generic_return_model_missing_without_wal():
    before = _wal_mtime()
    rec = asyncio.run(chat("Why is shipment H001 on customs hold?"))
    after = _wal_mtime()
    assert before == after
    assert rec["c5_to_neurolingua"] is True
    assert rec["neurolingua_to_provider"] is True
    assert rec["provider_to_model"] is True
    assert rec["model_response_to_c5"] is True
    assert rec["answer"] == "MODEL_MISSING"
    assert rec["error"] == "MODEL_MISSING"
    assert rec["model"] == CORTEX_IDENTITY
    assert rec["model_name_bound"] is False
    assert rec["llm_executed"] is False
    assert rec["student_substituted"] is False
    assert rec["provider_execute_called"] is True
    assert rec["cortex_model"] == CORTEX_IDENTITY
    assert rec["real_llm_execution"] is False
    assert rec["wal_mtime_unchanged"] is True
    assert rec["gl005_proven"] is False

    screen_before = _wal_mtime()
    screen = teach_reply("Why is shipment H001 on customs hold?")
    screen_after = _wal_mtime()
    assert screen_before == screen_after
    assert screen["kind"] == "speak"
    assert screen["answer"] == "MODEL_MISSING"
    assert screen["error"] == "MODEL_MISSING"
    assert screen["c5_to_neurolingua"] is True
    assert screen["model_response_to_c5"] is True
    assert screen["provider_execute_called"] is True
    assert screen["student_substituted"] is False
    assert screen["wal_mtime_unchanged"] is True
    assert screen["gl005_proven"] is False


def test_whoami_and_c4_seat_are_unchanged():
    who = teach_reply("مين أنت")
    assert who["kind"] == "whoami"
    assert "C5" in who["answer"]
    assert who.get("error") != "MODEL_MISSING"
    seat = teach_reply("ما دور C4 في المجلس")
    assert seat["kind"] == "ground"
    assert "ASSESSOR" in seat["answer"] or "مقيّم" in seat["answer"] or "DeepSeek" in seat["answer"]
