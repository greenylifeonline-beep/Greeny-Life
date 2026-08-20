"""Capability-based provider registry.

Selection order: deterministic → cheap local → specialized local → general LLM.
Offline mode never selects a network or GPU provider.
"""

from __future__ import annotations

from typing import Iterable

from raios.providers.contracts import (
    COST_RANK,
    Capability,
    CapabilityContract,
    NoCapableProvider,
    ProviderRequest,
    ProviderResponse,
    SemanticProvider,
)


class ProviderRegistry:
    def __init__(self, providers: Iterable[SemanticProvider] | None = None) -> None:
        self._providers: list[SemanticProvider] = list(providers or [])

    def register(self, provider: SemanticProvider) -> None:
        self._providers.append(provider)

    def list_contracts(self) -> list[CapabilityContract]:
        contracts: list[CapabilityContract] = []
        for provider in self._providers:
            contracts.extend(provider.contracts())
        return contracts

    def select(
        self,
        capability: Capability,
        *,
        offline: bool = True,
        locale: str | None = None,
        allow_llm: bool = False,
    ) -> SemanticProvider | None:
        ranked: list[tuple[int, SemanticProvider, CapabilityContract]] = []
        for provider in self._providers:
            for contract in provider.contracts():
                if contract.capability is not capability:
                    continue
                if not contract.supports_language(locale):
                    continue
                if offline and (contract.requires_network or contract.requires_gpu):
                    continue
                if contract.cost_class == "general_llm" and not allow_llm:
                    continue
                ranked.append((COST_RANK[contract.cost_class], provider, contract))
        if not ranked:
            return None
        ranked.sort(key=lambda item: item[0])
        return ranked[0][1]

    async def execute(self, request: ProviderRequest, *, allow_llm: bool = False) -> ProviderResponse:
        provider = self.select(
            request.capability,
            offline=request.offline,
            locale=request.locale,
            allow_llm=allow_llm,
        )
        if provider is None:
            raise NoCapableProvider(
                f"No provider for capability {request.capability.value} "
                f"(offline={request.offline}, locale={request.locale})"
            )
        response = await provider.execute(request)
        response.capability = request.capability
        return response
