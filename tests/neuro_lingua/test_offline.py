"""Kernel tests that must pass with no LLM, no GPU, and no network."""

import pytest

from raios.neuro_lingua import NeuroLingua
from raios.neuro_lingua.types import INITIAL_LOCALES


@pytest.mark.asyncio
async def test_offline_interpret_all_seed_languages(nl: NeuroLingua):
    samples = {
        "ar-EG": "مش بيتولد دلوقتي",
        "ar-GULF": "شلون الحال وايد زين الحين",
        "en": "please deploy the report today",
        "nb-NO": "Kan du løse saken, men ikke knekke noe?",
        "sv-SE": "Kan du lösa saken, men inte kanske något här?",
        "da-DK": "Kan du løse sagen, men ikke gøre noget?",
    }
    assert set(samples) == set(INITIAL_LOCALES)
    for locale, text in samples.items():
        result = await nl.interpret(text=text, context={"offline": True})
        assert result.metrics.llm_calls == 0
        assert result.meaning.detection.locale == locale


@pytest.mark.asyncio
async def test_meaning_is_canonical_boundary(nl: NeuroLingua):
    result = await nl.interpret(text="please resolve this today")
    dumped = result.meaning.to_dict()
    assert "packet_id" in dumped
    assert dumped["knowledge_state"] == "DISCOVERED"
    assert "openai" not in str(dumped).lower()
