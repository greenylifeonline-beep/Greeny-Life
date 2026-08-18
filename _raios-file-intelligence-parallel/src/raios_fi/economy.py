"""Tool economy: cheapest provider that satisfies the requirement. LLM not default parser."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from raios_fi.spi import Cost, ProviderRegistry
from raios_fi.tools import detect_tools


@dataclass(frozen=True)
class EconomyChoice:
    capability: str
    selected: str
    reason: str
    llm_used: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ToolEconomy:
    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry
        self.tools = detect_tools()

    def choose(self, capability: str, requirement: str) -> EconomyChoice:
        ranked = self.registry.cheapest(capability)
        if not ranked:
            return EconomyChoice(capability, "NONE", "no_provider", False)
        # Never pick LLM for parse/type/hash.
        for name, _p, cost in ranked:
            if "llm" in name.lower() or "qwen" in name.lower():
                if requirement in {"parse", "type", "hash", "extract"}:
                    continue
            return EconomyChoice(capability, name, f"cheapest_ok cost={cost.per_file_cost}", False)
        return EconomyChoice(capability, "NONE", "only_llm_left_rejected", False)
