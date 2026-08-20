from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .governor import CognitiveResourceGovernor
from .provider_contracts import CapabilityRequirement, LanguageProvider, ProviderCapability


CAPABILITIES = (
    "LANGUAGE_ID",
    "DIALECT_CLASSIFICATION",
    "CODE_SWITCH_CLASSIFICATION",
    "SEMANTIC_INTERPRETATION",
    "SEMANTIC_REALIZATION",
    "SEMANTIC_VERIFICATION",
    "TERMINOLOGY_ADJUDICATION",
    "PRAGMATIC_INTERPRETATION",
)


class DeterministicProvider:
    provider_id = "deterministic-neuro-lingua"

    @property
    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id=self.provider_id,
            capabilities=CAPABILITIES,
            languages=("ar-EG", "ar-GULF", "en", "nb-NO", "sv-SE", "da-DK"),
            local=True,
            quality_score=0.7,
            estimated_latency_ms=5,
        )

    async def execute(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "DEFERRED_TO_KERNEL", "capability": capability, "payload_keys": sorted(payload)}


@dataclass
class ProviderRouter:
    governor: CognitiveResourceGovernor = field(default_factory=CognitiveResourceGovernor)
    providers: list[LanguageProvider] = field(default_factory=list)
    llm_calls: int = 0
    provider_calls: int = 0
    deterministic_resolutions: int = 0

    def __post_init__(self) -> None:
        if not self.providers:
            self.providers = [DeterministicProvider()]

    def route(self, requirement: CapabilityRequirement) -> dict[str, Any]:
        self.provider_calls += 1
        admission = self.governor.admit(requirement.capability)
        cortex_needed = requirement.capability in {
            "SEMANTIC_INTERPRETATION",
            "SEMANTIC_REALIZATION",
            "SEMANTIC_VERIFICATION",
        }
        if cortex_needed and not admission.admitted:
            self.deterministic_resolutions += 1
            return {
                "provider": "deterministic-neuro-lingua",
                "fallback_used": True,
                "reason": admission.reason,
                "llm": False,
            }
        if requirement.offline_required or not cortex_needed:
            self.deterministic_resolutions += 1
            return {
                "provider": "deterministic-neuro-lingua",
                "fallback_used": False,
                "reason": "TIER0_OR_TIER1",
                "llm": False,
            }
        # Main Cortex is never hard-coded as identity; only requested as capability.
        self.llm_calls += 1
        return {
            "provider": "main-cortex-capability",
            "fallback_used": False,
            "reason": "TIER3_SEMANTIC",
            "llm": True,
            "model_name_bound": False,
        }

    def metrics(self) -> dict[str, Any]:
        total = max(self.provider_calls, 1)
        return {
            "provider_calls": self.provider_calls,
            "llm_calls": self.llm_calls,
            "deterministic_resolution_ratio": round(self.deterministic_resolutions / total, 4),
            "local_execution_ratio": round((total - self.llm_calls) / total, 4),
        }
