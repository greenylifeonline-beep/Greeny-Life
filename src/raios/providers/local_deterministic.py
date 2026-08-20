"""Deterministic local provider. Always available. Never calls a network."""

from __future__ import annotations

from raios.providers.contracts import (
    Capability,
    CapabilityContract,
    ProviderRequest,
    ProviderResponse,
)


class LocalDeterministicProvider:
    provider_id = "local.deterministic"

    def contracts(self) -> tuple[CapabilityContract, ...]:
        shared = dict(
            cost_class="deterministic",
            requires_network=False,
            requires_gpu=False,
            languages=("*",),
            provider_id=self.provider_id,
        )
        return (
            CapabilityContract(capability=Capability.LANGUAGE_IDENTIFICATION, **shared),
            CapabilityContract(capability=Capability.DIALECT_CLASSIFICATION, **shared),
            CapabilityContract(capability=Capability.CODE_SWITCH_SEGMENTATION, **shared),
            CapabilityContract(capability=Capability.SEMANTIC_INTERPRETATION, **shared),
            CapabilityContract(capability=Capability.SEMANTIC_REALIZATION, **shared),
            CapabilityContract(capability=Capability.SEMANTIC_VERIFICATION, **shared),
        )

    async def execute(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(
            ok=True,
            payload={"delegated": True, "capability": request.capability.value},
            provider_id=self.provider_id,
            capability=request.capability,
            cost_class="deterministic",
            used_llm=False,
        )
