"""Generic LLM provider adapter.

Vendor-agnostic: talks to a callable or HTTP-like endpoint supplied at
runtime. Instantiating this class does not select OpenAI/Qwen/etc. If no
endpoint is configured the provider reports unavailable instead of guessing.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from raios.providers.contracts import (
    Capability,
    CapabilityContract,
    ProviderRequest,
    ProviderResponse,
    ProviderUnavailable,
)


LLMCallable = Callable[[ProviderRequest], Awaitable[dict[str, Any]]]


class GenericLLMProvider:
    provider_id = "llm.generic"

    def __init__(self, invoke: LLMCallable | None = None) -> None:
        self._invoke = invoke

    def contracts(self) -> tuple[CapabilityContract, ...]:
        shared = dict(
            cost_class="general_llm",
            requires_network=True,
            requires_gpu=False,
            languages=("*",),
            provider_id=self.provider_id,
        )
        return (
            CapabilityContract(capability=Capability.SEMANTIC_ADJUDICATION, **shared),
            CapabilityContract(capability=Capability.SEMANTIC_INTERPRETATION, **shared),
            CapabilityContract(capability=Capability.SEMANTIC_REALIZATION, **shared),
            CapabilityContract(capability=Capability.SEMANTIC_VERIFICATION, **shared),
            CapabilityContract(capability=Capability.BACK_TRANSLATION, **shared),
        )

    async def execute(self, request: ProviderRequest) -> ProviderResponse:
        if request.offline or self._invoke is None:
            raise ProviderUnavailable(
                "Generic LLM provider has no invoke callable or is in offline mode."
            )
        try:
            payload = await self._invoke(request)
        except Exception as exc:  # noqa: BLE001 — surface as provider failure
            return ProviderResponse(
                ok=False,
                error=str(exc),
                provider_id=self.provider_id,
                capability=request.capability,
                cost_class="general_llm",
                used_llm=True,
            )
        return ProviderResponse(
            ok=True,
            payload=payload,
            provider_id=self.provider_id,
            capability=request.capability,
            cost_class="general_llm",
            used_llm=True,
        )
