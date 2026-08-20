import pytest

from raios.neuro_lingua import NeuroLingua


@pytest.mark.asyncio
async def test_swedish_output_does_not_contain_norwegian_ikke(nl: NeuroLingua):
    result = await nl.interpret(
        text="Kan du løse saken i dag, vær så snill",
        context={"domain": "operations"},
    )
    rendered = await nl.realize(result.meaning, target_locale="sv-SE")
    assert "ikke" not in rendered.text.split()
    assert "och" in rendered.text or "lösa" in rendered.text or "i dag" in rendered.text
    assert rendered.leakage == [] or "ikke" not in rendered.leakage


@pytest.mark.asyncio
async def test_norwegian_output_does_not_contain_swedish_inte(nl: NeuroLingua):
    result = await nl.interpret(
        text="Please resolve the matter today",
        context={"domain": "operations"},
    )
    rendered = await nl.realize(result.meaning, target_locale="nb-NO")
    assert "inte" not in rendered.text.split()
    assert "och" not in rendered.text.split()
    assert "løs" in rendered.text or "i dag" in rendered.text


@pytest.mark.asyncio
async def test_danish_isolated_from_swedish(nl: NeuroLingua):
    result = await nl.interpret(text="Please resolve the matter today")
    rendered = await nl.realize(result.meaning, target_locale="da-DK")
    assert "inte" not in rendered.text.split()
    assert "och" not in rendered.text.split()
    assert "knække" not in rendered.text  # regression term not requested


@pytest.mark.asyncio
async def test_no_mixed_scandinavian_language(nl: NeuroLingua):
    result = await nl.interpret(text="Please resolve this today")
    nb = await nl.realize(result.meaning, "nb-NO")
    sv = await nl.realize(result.meaning, "sv-SE")
    da = await nl.realize(result.meaning, "da-DK")
    assert nb.text != sv.text
    assert sv.text != da.text
    assert nb.text != da.text
