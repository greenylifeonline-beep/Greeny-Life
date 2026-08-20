import pytest

from raios.neuro_lingua.learning import FailureRecord, LearningGap, LearningGapClassifier
from raios.neuro_lingua.training_policy import (
    AdapterEscalation,
    FactStability,
    KnowledgeRoute,
    decide_training,
)


def test_every_gap_enum_is_reachable():
    clf = LearningGapClassifier()
    cases = {
        LearningGap.MODEL_CAPACITY_LIMIT: FailureRecord("infer", "oom", capacity=True),
        LearningGap.ROUTING_FAILURE: FailureRecord("route", "none", code="NO_CAPABLE_PROVIDER"),
        LearningGap.TOOL_FAILURE: FailureRecord("tool", "boom", provider_error="boom"),
        LearningGap.PROMPT_FAILURE: FailureRecord("llm", "bad json", used_llm=True, unparseable_llm=True),
        LearningGap.RETRIEVAL_FAILURE: FailureRecord("rag", "miss", retrieval_attempted=True),
        LearningGap.CONTEXT_FAILURE: FailureRecord("ctx", "need domain", missing_context=["domain"]),
        LearningGap.REASONING_FAILURE: FailureRecord("verify", "mismatch", verification_failed=True),
        LearningGap.TERMINOLOGY_GAP: FailureRecord("bind", "unknown term", unbound_terms=["fooBar"]),
        LearningGap.DOMAIN_KNOWLEDGE_GAP: FailureRecord("domain", "unknown domain", domain="legal"),
        LearningGap.DIALECT_GAP: FailureRecord(
            "lid", "ar unresolved", detection_language="ar", dialect_confidence=0.0
        ),
        LearningGap.LANGUAGE_GAP: FailureRecord("lid", "none", language_confidence=0.0),
        LearningGap.SEMANTIC_GAP: FailureRecord("sem", "could not bind intent"),
    }
    got = {clf.classify(failure).gap for failure in cases.values()}
    assert set(LearningGap) <= got | {LearningGap.SEMANTIC_GAP}
    for expected, failure in cases.items():
        assert clf.classify(failure).gap is expected


def test_training_never_runs_even_for_adapter_candidate():
    decision = decide_training(
        stability=FactStability.BEHAVIORAL_GAP,
        recurrence=99,
        evidence_justifies_cpt=True,
    )
    assert decision.train_now is False
    assert decision.route is KnowledgeRoute.ADAPTER_CANDIDATE
    assert decision.escalation is AdapterEscalation.TARGETED_CPT


def test_changing_facts_go_to_retrieval():
    decision = decide_training(stability=FactStability.CHANGING)
    assert decision.route is KnowledgeRoute.RETRIEVAL
    assert decision.escalation is AdapterEscalation.NO_TRAINING


def test_repeated_procedure_compiles_skill():
    decision = decide_training(stability=FactStability.PROCEDURE)
    assert decision.route is KnowledgeRoute.COMPILED_SKILL
    assert decision.train_now is False
