from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Any


@dataclass(frozen=True)
class CapabilityRequirement:
    capability: str
    languages: tuple[str, ...] = ()
    offline_required: bool = False
    max_latency_ms: int | None = None
    min_quality: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderCapability:
    provider_id: str
    capabilities: tuple[str, ...]
    languages: tuple[str, ...]
    local: bool
    quality_score: float | None = None
    estimated_latency_ms: int | None = None


class LanguageProvider(Protocol):

    @property
    def capabilities(self) -> ProviderCapability:
        ...

    async def execute(
        self,
        capability: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        ...
