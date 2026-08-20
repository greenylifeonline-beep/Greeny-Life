import pytest

from raios.neuro_lingua import NeuroLingua
from raios.providers import (
    GenericLLMProvider,
    NoCapableProvider,
    ProviderRegistry,
    ProviderRequest,
    ProviderUnavailable,
    Capability,
)
from raios.providers.local_deterministic import LocalDeterministicProvider


@pytest.mark.asyncio
async def test_offline_never_calls_llm(nl: NeuroLingua):
    result = await nl.interpret(text="please resolve this today", context={"offline": True, "allow_llm": False})
    assert result.metrics.llm_calls == 0
    assert result.metrics.local_execution_ratio == 1.0


@pytest.mark.asyncio
async def test_generic_llm_unavailable_without_callable():
    provider = GenericLLMProvider(invoke=None)
    with pytest.raises(ProviderUnavailable):
        await provider.execute(
            ProviderRequest(
                capability=Capability.SEMANTIC_ADJUDICATION,
                payload={"text": "hi"},
                offline=False,
            )
        )


@pytest.mark.asyncio
async def test_provider_failure_is_surfaced():
    async def boom(_request):
        raise RuntimeError("upstream down")

    provider = GenericLLMProvider(invoke=boom)
    response = await provider.execute(
        ProviderRequest(
            capability=Capability.SEMANTIC_REALIZATION,
            payload={},
            offline=False,
        )
    )
    assert response.ok is False
    assert "upstream down" in (response.error or "")


@pytest.mark.asyncio
async def test_registry_fallback_skips_network_when_offline():
    registry = ProviderRegistry([GenericLLMProvider(), LocalDeterministicProvider()])
    selected = registry.select(Capability.SEMANTIC_INTERPRETATION, offline=True, allow_llm=False)
    assert selected is not None
    assert selected.provider_id == "local.deterministic"


@pytest.mark.asyncio
async def test_no_provider_for_back_translation_offline():
    registry = ProviderRegistry([LocalDeterministicProvider()])
    with pytest.raises(NoCapableProvider):
        await registry.execute(
            ProviderRequest(
                capability=Capability.BACK_TRANSLATION,
                payload={},
                offline=True,
            ),
            allow_llm=False,
        )
