"""Provider SPI. RAIOS selects by capability. LLM is not the default parser."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class Provider(Protocol):
    name: str

    def discover(self) -> dict[str, Any]: ...
    def health(self) -> dict[str, Any]: ...
    def supports(self, obj: dict[str, Any]) -> bool: ...
    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]: ...
    def evidence(self, obj: dict[str, Any]) -> dict[str, Any]: ...
    def cost(self) -> dict[str, Any]: ...
    def fallback(self) -> str | None: ...


class BaseProvider:
    name = "base"
    capability = "none"
    startup_cost = 0.0
    per_file_cost = 0.01
    accuracy = 0.5
    supported_types: tuple[str, ...] = ()
    risk = "LOW"

    def discover(self) -> dict[str, Any]:
        return {"name": self.name, "capability": self.capability, "available": True}

    def health(self) -> dict[str, Any]:
        return {"ok": True, "name": self.name}

    def supports(self, obj: dict[str, Any]) -> bool:
        kind = obj.get("class") or obj.get("language") or ""
        return not self.supported_types or kind in self.supported_types

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        return {"provider": self.name, "status": "NOOP"}

    def evidence(self, obj: dict[str, Any]) -> dict[str, Any]:
        return {"provider": self.name, "source_hash": obj.get("sha256")}

    def cost(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "startup_cost": self.startup_cost,
            "per_file_cost": self.per_file_cost,
            "accuracy": self.accuracy,
            "supported_types": list(self.supported_types),
            "risk": self.risk,
        }

    def fallback(self) -> str | None:
        return None


@dataclass(frozen=True)
class Cost:
    capability: str
    startup_cost: float
    per_file_cost: float
    accuracy: float
    supported_types: tuple[str, ...]
    risk: str


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: list[BaseProvider] = []

    def register(self, provider: BaseProvider) -> None:
        self._providers.append(provider)

    def cheapest(self, capability: str) -> list[tuple[str, BaseProvider, Cost]]:
        ranked: list[tuple[str, BaseProvider, Cost]] = []
        for provider in self._providers:
            if provider.capability != capability and capability not in (provider.name, provider.capability):
                continue
            payload = provider.cost()
            ranked.append(
                (
                    provider.name,
                    provider,
                    Cost(
                        capability=str(payload.get("capability") or provider.capability),
                        startup_cost=float(payload.get("startup_cost") or 0),
                        per_file_cost=float(payload.get("per_file_cost") or 0),
                        accuracy=float(payload.get("accuracy") or 0),
                        supported_types=tuple(payload.get("supported_types") or ()),
                        risk=str(payload.get("risk") or "LOW"),
                    ),
                )
            )
        ranked.sort(key=lambda item: (item[2].per_file_cost, -item[2].accuracy, item[2].startup_cost))
        return ranked

    def select(self, capability: str) -> BaseProvider | None:
        ranked = self.cheapest(capability)
        return ranked[0][1] if ranked else None
