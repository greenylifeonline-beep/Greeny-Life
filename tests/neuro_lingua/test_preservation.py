import pytest

from raios.neuro_lingua import NeuroLingua
from raios.risk import RiskLevel


@pytest.mark.asyncio
async def test_numbers_preserved(nl: NeuroLingua):
    text = "Bump replica-count to 12 and keep timeout 3.5"
    result = await nl.interpret(text=text)
    surfaces = {span.surface for span in result.meaning.numbers}
    assert "12" in surfaces
    assert "3.5" in surfaces
    rendered = await nl.realize(result.meaning, "en", context={"risk_level": RiskLevel.MEDIUM})
    assert "12" in rendered.text
    assert "3.5" in rendered.text
    checks = {c["name"]: c for c in rendered.verification["checks"]}
    assert checks["number_preservation"]["passed"] is True


@pytest.mark.asyncio
async def test_arabic_indic_numbers_preserved(nl: NeuroLingua):
    text = "العدد ١٢ في report"
    result = await nl.interpret(text=text)
    assert any(span.surface == "١٢" for span in result.meaning.numbers)
    rendered = await nl.realize(result.meaning, "ar-EG")
    assert "١٢" in rendered.text or "12" in rendered.text


@pytest.mark.asyncio
async def test_identifiers_preserved_through_realize(nl: NeuroLingua):
    text = "أنا عملت migration بس الـreport مش بيتولد بعد الـexecutor"
    result = await nl.interpret(text=text, context={"domain": "software"})
    rendered = await nl.realize(result.meaning, "nb-NO", context={"risk_level": RiskLevel.MEDIUM})
    assert "migration" in rendered.text
    assert "report" in rendered.text
    assert "executor" in rendered.text


@pytest.mark.asyncio
async def test_uuid_and_filename_preserved(nl: NeuroLingua):
    text = "Job 550e8400-e29b-41d4-a716-446655440000 failed in kernel.py"
    result = await nl.interpret(text=text, context={"domain": "software"})
    blob = " ".join(result.meaning.preserved_surfaces())
    assert "550e8400-e29b-41d4-a716-446655440000" in blob or any(
        "550e8400" in span.surface for span in result.meaning.identifiers
    )
    assert any("kernel.py" in span.surface for span in result.meaning.identifiers + result.meaning.terminology)
