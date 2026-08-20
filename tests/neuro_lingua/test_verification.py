import pytest

from raios.neuro_lingua import NeuroLingua
from raios.risk import RiskLevel


@pytest.mark.asyncio
async def test_medium_includes_semantic_and_terminology(nl: NeuroLingua):
    result = await nl.interpret(
        text="أنا عملت migration بس الـreport مش بيتولد بعد الـexecutor",
        context={"domain": "software", "risk_level": RiskLevel.MEDIUM},
    )
    rendered = await nl.realize(
        result.meaning,
        "en",
        context={"risk_level": RiskLevel.MEDIUM},
    )
    names = [c["name"] for c in rendered.verification["checks"]]
    assert "semantic_equivalence" in names
    assert "terminology_preservation" in names
    assert "entity_preservation" in names


@pytest.mark.asyncio
async def test_critical_does_not_back_translate_by_default(nl: NeuroLingua):
    result = await nl.interpret(text="please resolve this today")
    rendered = await nl.realize(
        result.meaning,
        "en",
        context={"risk_level": RiskLevel.CRITICAL},
    )
    bt = next(c for c in rendered.verification["checks"] if c["name"] == "back_translation")
    assert bt["detail"] == "skipped_not_enabled"
    assert rendered.verification["used_back_translation"] is False


@pytest.mark.asyncio
async def test_high_records_missing_independent_verifier(nl: NeuroLingua):
    result = await nl.interpret(text="please resolve this today")
    rendered = await nl.realize(result.meaning, "en", context={"risk_level": RiskLevel.HIGH})
    indep = next(
        c for c in rendered.verification["checks"] if c["name"] == "independent_semantic_verification"
    )
    assert indep["passed"] is False
