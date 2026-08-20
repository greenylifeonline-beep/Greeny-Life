import pytest

from raios.neuro_lingua import NeuroLingua
from raios.neuro_lingua.types import InterpretationContext


@pytest.mark.asyncio
async def test_politeness_is_not_a_logical_condition(nl: NeuroLingua):
    text = "شوف لنا الموضوع وإذا ما عليك أمر خلصه اليوم"
    result = await nl.interpret(text=text, context={"domain": "operations"})
    prag = result.meaning.pragmatics
    assert prag.action == "resolve"
    assert prag.deadline == "today"
    assert prag.politeness_marker is True
    assert any("إذا ما عليك أمر" in item or "اذا ما عليك امر" in item for item in prag.not_logical_condition)
    rendered = await nl.realize(result.meaning, target_locale="en")
    assert "if" not in rendered.text.lower() or "please" in rendered.text.lower()
    assert "إذا ما عليك أمر" not in rendered.text


@pytest.mark.asyncio
async def test_egyptian_idiom_system_regression_needs_software_context(nl: NeuroLingua):
    text = "الدنيا هتبوظ"
    without = await nl.interpret(text=text, context=InterpretationContext())
    assert not any(c.concept_id == "system.regression" for c in without.meaning.concepts)

    with_ctx = await nl.interpret(
        text=text,
        context=InterpretationContext(domain="software"),
    )
    assert any(c.concept_id == "system.regression" for c in with_ctx.meaning.concepts)
    assert with_ctx.meaning.intent == "report_system_regression"
