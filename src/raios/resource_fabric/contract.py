"""Read-only provider adapter contract. No mutating methods in Wave-01."""

from __future__ import annotations

from typing import Any, Protocol

CAPABILITIES = (
    "IDENTIFY",
    "DISCOVER_ACCOUNTS",
    "DISCOVER_REGIONS",
    "DISCOVER_COMPUTE",
    "DISCOVER_ACCELERATORS",
    "DISCOVER_STORAGE",
    "DISCOVER_SERVICES",
    "DISCOVER_QUOTAS",
    "DISCOVER_CREDITS",
    "DISCOVER_USAGE",
    "DISCOVER_PRICING",
    "HEALTH",
    "CAPABILITIES",
    "PLAN_PLACEMENT",
)

PROBE_STATUSES = (
    "SUCCESS",
    "PARTIAL",
    "UNAVAILABLE",
    "AUTH_REQUIRED",
    "ZERO_QUOTA",
    "RATE_LIMITED",
    "OFFLINE",
    "UNKNOWN",
)


class ProviderAdapter(Protocol):
    provider_id: str

    def identify(self) -> dict[str, Any]: ...
    def discover_accounts(self) -> list[dict[str, Any]]: ...
    def discover_regions(self, account_id: str) -> list[dict[str, Any]]: ...
    def discover_compute(self, account_id: str) -> list[dict[str, Any]]: ...
    def discover_accelerators(self, account_id: str) -> list[dict[str, Any]]: ...
    def discover_storage(self, account_id: str) -> list[dict[str, Any]]: ...
    def discover_services(self, account_id: str) -> list[dict[str, Any]]: ...
    def discover_quotas(self, account_id: str) -> list[dict[str, Any]]: ...
    def discover_credits(self, account_id: str) -> list[dict[str, Any]]: ...
    def discover_usage(self, account_id: str) -> list[dict[str, Any]]: ...
    def discover_pricing(self, account_id: str) -> list[dict[str, Any]]: ...
    def health(self, account_id: str) -> dict[str, Any]: ...
    def capabilities(self) -> tuple[str, ...]: ...
    def plan_placement(self, request: dict[str, Any]) -> dict[str, Any]: ...
