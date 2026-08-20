from raios.neuro_lingua.risk import verification_plan
from raios.neuro_lingua.schema import RiskLevel


def test_low_risk_has_no_back_translation():

    plan = verification_plan(RiskLevel.LOW)

    assert plan.back_translation is False


def test_critical_risk_has_full_verification():

    plan = verification_plan(RiskLevel.CRITICAL)

    assert plan.semantic_similarity
    assert plan.entity_lock
    assert plan.number_lock
    assert plan.terminology_lock
    assert plan.independent_verification
    assert plan.back_translation
