"""Capability contracts. Providers are selected by capability, never by vendor.

Do not hard-code Qwen, DeepSeek, OpenAI, Ollama, or Hugging Face. A provider
is admitted only if it publishes a CapabilityContract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Protocol, Sequence


CostClass = Literal["deterministic", "cheap_local", "specialized_local", "general_llm"]


class Capability(str, Enum):
    LANGUAGE_IDENTIFICATION = "language_identification"
    DIALECT_CLASSIFICATION = "dialect_classification"
    CODE_SWITCH_SEGMENTATION = "code_switch_segmentation"
    SEMANTIC_INTERPRETATION = "semantic_interpretation"
    SEMANTIC_REALIZATION = "semantic_realization"
    SEMANTIC_VERIFICATION = "semantic_verification"
    SEMANTIC_ADJUDICATION = "semantic_adjudication"
    BACK_TRANSLATION = "back_translation"


COST_RANK = {
    "deterministic": 0,
    "cheap_local": 1,
    "specialized_local": 2,
    "general_llm": 3,
}


@dataclass(frozen=True)
class CapabilityContract:
    capability: Capability
    cost_class: CostClass
    requires_network: bool = False
    requires_gpu: bool = False
    languages: Sequence[str] = ("*",)
    provider_id: str = "unnamed"

    def supports_language(self, locale: str | None) -> bool:
        if "*" in self.languages:
            return True
        if locale is None:
            return False
        return locale in self.languages or locale.split("-")[0] in self.languages


@dataclass
class ProviderRequest:
    capability: Capability
    payload: dict[str, Any]
    offline: bool = True
    locale: str | None = None


@dataclass
class ProviderResponse:
    ok: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    provider_id: str = ""
    capability: Capability | None = None
    cost_class: CostClass | None = None
    used_llm: bool = False


class SemanticProvider(Protocol):
    def contracts(self) -> Sequence[CapabilityContract]:
        ...

    async def execute(self, request: ProviderRequest) -> ProviderResponse:
        ...


class ProviderError(RuntimeError):
    pass


class ProviderUnavailable(ProviderError):
    pass


class NoCapableProvider(ProviderError):
    pass
