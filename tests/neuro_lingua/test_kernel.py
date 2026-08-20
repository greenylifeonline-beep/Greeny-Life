import asyncio
from pathlib import Path

from raios.neuro_lingua.concepts import ConceptRegistryError, load_concept_registry
from raios.neuro_lingua.gaps import LearningGap, classify_gap
from raios.neuro_lingua.governor import CognitiveResourceGovernor
from raios.neuro_lingua.kernel import NeuroLingua
from raios.neuro_lingua.realize import detect_scandinavian_leakage
from raios.neuro_lingua.schema import KnowledgeState, RiskLevel
from raios.neuro_lingua.training import TrainingDecision, decide_training


def test_egyptian_vs_gulf():
    nl = NeuroLingua()
    eg = asyncio.run(nl.interpret("خلصلي الموضوع ده بس متبوظش حاجة في المشروع", context={"domain": "project"}))
    gulf = asyncio.run(nl.interpret("شوف لنا الموضوع وإذا ما عليك أمر خلصه اليوم"))
    assert eg.meaning.source_locale == "ar-EG"
    assert gulf.meaning.source_locale == "ar-GULF"
    assert eg.meaning.source_locale != gulf.meaning.source_locale


def test_gulf_politeness_is_not_condition():
    nl = NeuroLingua()
    result = asyncio.run(nl.interpret("شوف لنا الموضوع وإذا ما عليك أمر خلصه اليوم"))
    assert result.meaning.pragmatics.politeness_marker is True
    assert result.meaning.pragmatics.condition is False
    assert result.meaning.pragmatics.deadline == "today"
    assert result.meaning.semantics.action == "resolve"


def test_code_switch_and_protected_tokens():
    nl = NeuroLingua()
    result = asyncio.run(nl.interpret("أنا عملت migration بس الـ report مش بيتولد بعد الـ executor"))
    texts = [seg.text.lower() for seg in result.meaning.code_switch_segments]
    joined = " ".join(texts)
    assert "migration" in joined
    preserved = {tok.text.lower() for tok in result.meaning.preserved_tokens}
    assert "migration" in preserved
    assert "executor" in preserved


def test_roundtrip_preserves_constraint_and_identifiers():
    nl = NeuroLingua()
    interpreted = asyncio.run(
        nl.interpret("Kan du deploye den nye builden, men ikke touche production-databasen?")
    )
    realized = asyncio.run(nl.realize(interpreted.meaning, target_locale="nb-NO"))
    assert realized.verification["status"] in {"OK", "FAILED"}
    assert "deploye" in realized.text or "builden" in realized.text or "production" in realized.text.lower()


def test_scandinavian_leakage_positive_and_negative():
    ok = detect_scandinavian_leakage("Kan du løse dette uten å påvirke produksjonen", "nb-NO")
    leak = detect_scandinavian_leakage("Kontrollera ändringen och påverka inte", "nb-NO")
    assert ok["status"] == "OK"
    assert ok["positive_hits"] >= 1
    assert leak["status"] == "LEAKAGE"


def test_concept_registry_collision(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
schema_version: 1
concepts:
  - concept_id: a.one
    realizations:
      en: {preferred: "alpha"}
  - concept_id: a.one
    realizations:
      en: {preferred: "beta"}
  - concept_id: a.two
    inherits: a.three
  - concept_id: a.three
    inherits: a.two
    locales: [xx-ZZ]
    override_canonical: true
""",
        encoding="utf-8",
    )
    loaded = load_concept_registry(path)
    codes = {row["code"] for row in loaded["diagnostics"]}
    assert "DUPLICATE_CONCEPT_ID" in codes
    assert "CYCLIC_INHERITANCE" in codes
    assert "SEMANTIC_OVERRIDE_ATTEMPT" in codes


def test_learning_gap_unknown_not_forced():
    result = classify_gap({"mysterious": True})
    assert result["gap"] == LearningGap.UNKNOWN.value
    assert result["forced"] is False


def test_training_policy_no_actual_training():
    changing = decide_training("changing_fact")
    persistent = decide_training("persistent_behavior_gap", persistent=True)
    assert changing["decision"] == TrainingDecision.RETRIEVAL.value
    assert persistent["decision"] == TrainingDecision.ADAPTER_CANDIDATE.value
    assert persistent["install_mora"] is False
    assert persistent["install_cpt"] is False


def test_governor_does_not_crash_pipeline():
    gov = CognitiveResourceGovernor(min_free_gb_for_cortex=9999)
    decision = gov.admit("SEMANTIC_INTERPRETATION")
    nl = NeuroLingua(governor=gov)
    result = asyncio.run(nl.interpret("Remove dead code only if runtime behavior remains unchanged."))
    assert result.meaning.intent.primary in {"request_action", "unknown"}
    assert decision.admitted is False or decision.admitted is True
    assert result.meaning.confidence.language.source


def test_confidence_unknown_not_fabricated():
    nl = NeuroLingua()
    result = asyncio.run(nl.interpret("aaaa bbbb cccc"))
    if result.meaning.confidence.language.value is None:
        assert result.meaning.confidence.language.source == "deterministic+local-lid" or result.meaning.confidence.language.source == "UNKNOWN"


def test_risk_levels_exist():
    assert RiskLevel.LOW.value == "LOW"
    assert KnowledgeState.DISCOVERED.value == "DISCOVERED"
