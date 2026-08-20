import pytest

from raios.neuro_lingua import NeuroLingua
from raios.neuro_lingua.packet import CognitiveMeaningPacket
from raios.risk import RiskLevel


@pytest.mark.asyncio
async def test_golden_egyptian_request(nl: NeuroLingua):
    text = "شوف لنا الموضوع وإذا ما عليك أمر خلصه اليوم"
    result = await nl.interpret(text=text, context={"domain": "operations"})
    meaning = result.meaning
    assert isinstance(meaning, CognitiveMeaningPacket)
    assert meaning.pragmatics.action == "resolve"
    assert meaning.pragmatics.deadline == "today"
    assert meaning.pragmatics.politeness_marker is True
    assert meaning.detection.locale == "ar-EG"
    assert meaning.intent == "resolve_by_today"
    rendered = await nl.realize(meaning, "nb-NO")
    assert "løs" in rendered.text
    assert "i dag" in rendered.text
    assert "إذا ما عليك أمر" not in rendered.text


@pytest.mark.asyncio
async def test_golden_code_switch_ar_en(nl: NeuroLingua):
    text = "أنا عملت migration بس الـreport مش بيتولد بعد الـexecutor"
    result = await nl.interpret(text=text, context={"domain": "software"})
    assert result.meaning.detection.locale == "ar-EG"
    assert result.meaning.detection.code_switched is True
    locales = [s.locale for s in result.meaning.segments]
    assert any(loc.startswith("ar") for loc in locales)
    assert "en/technical" in locales


@pytest.mark.asyncio
async def test_golden_norwegian_deploy(nl: NeuroLingua):
    text = "Kan du deploye den nye builden, men ikke touche production-databasen?"
    result = await nl.interpret(text=text, context={"domain": "software"})
    assert result.meaning.detection.locale == "nb-NO"
    rendered = await nl.realize(result.meaning, "nb-NO", context={"risk_level": RiskLevel.MEDIUM})
    assert "deploye" in rendered.text
    assert "builden" in rendered.text
    assert "production-databasen" in rendered.text


@pytest.mark.asyncio
async def test_low_risk_skips_independent_and_backtranslation(nl: NeuroLingua):
    result = await nl.interpret(text="please resolve this today")
    rendered = await nl.realize(result.meaning, "en", context={"risk_level": RiskLevel.LOW})
    names = [c["name"] for c in rendered.verification["checks"]]
    assert "independent_semantic_verification" not in names
    assert "back_translation" not in names
    assert rendered.verification["used_back_translation"] is False
