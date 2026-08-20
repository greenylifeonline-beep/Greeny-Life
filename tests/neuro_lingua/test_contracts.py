import pytest

from raios.neuro_lingua import NeuroLingua, create_neuro_lingua
from raios.neuro_lingua.packet import CognitiveMeaningPacket
from raios.neuro_lingua.pipeline import PIPELINE_STAGES
from raios.neuro_lingua.types import INITIAL_LOCALES
from raios.providers import Capability, LocalDeterministicProvider, ProviderRegistry
from raios.risk import RiskLevel


@pytest.mark.asyncio
async def test_public_api_hides_providers(nl: NeuroLingua):
    result = await nl.interpret(text="please resolve this today")
    assert isinstance(result.meaning, CognitiveMeaningPacket)
    assert "openai" not in result.meaning.provider_trace[0].lower()
    assert "qwen" not in "".join(result.meaning.provider_trace).lower()
    rendered = await nl.realize(result.meaning, target_locale="nb-NO")
    assert rendered.target_locale == "nb-NO"
    assert "verification" in rendered.to_dict()


def test_pipeline_stages_match_spec():
    assert PIPELINE_STAGES[0] == "raw_input"
    assert "cognitive_meaning_packet" in PIPELINE_STAGES
    assert PIPELINE_STAGES[-1] == "output"


def test_risk_level_mirrors_gl_dos():
    assert [level.value for level in RiskLevel] == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_capability_contracts_are_vendor_neutral():
    provider = LocalDeterministicProvider()
    names = {c.capability for c in provider.contracts()}
    assert Capability.SEMANTIC_INTERPRETATION in names
    assert all("openai" not in c.provider_id for c in provider.contracts())


def test_factory_offline_by_default(repo_root, tmp_path):
    kernel = create_neuro_lingua(repo_root, wal_path=tmp_path / "wal.jsonl")
    assert kernel.config.offline is True
    assert set(INITIAL_LOCALES) <= set(kernel.config.extra.get("languages") or INITIAL_LOCALES)


def test_registry_exposes_contracts():
    registry = ProviderRegistry([LocalDeterministicProvider()])
    assert registry.list_contracts()
