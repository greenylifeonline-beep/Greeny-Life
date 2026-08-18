"""MemorySPI — RAIOS owns authority. External backends are non-authoritative providers."""
from __future__ import annotations

from typing import Any, Protocol

from ..identity import FailClosed, ORGANISM_ID, deterministic_id, utc_now


class MemoryProvider(Protocol):
    def put(self, key: str, value: Any) -> dict[str, Any]: ...
    def get(self, key: str) -> Any: ...
    def search_text(self, query: str) -> list[Any]: ...
    def search_vector(self, vector: list[float]) -> list[Any]: ...
    def neighbors(self, key: str) -> list[Any]: ...
    def delete_candidate(self, key: str) -> dict[str, Any]: ...
    def health(self) -> dict[str, Any]: ...


class InMemoryProvider:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def put(self, key: str, value: Any) -> dict[str, Any]:
        self._data[key] = value
        return {"key": key, "stored": True, "authoritative": False}

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def search_text(self, query: str) -> list[Any]:
        q = query.lower()
        return [v for k, v in self._data.items() if q in k.lower() or q in str(v).lower()]

    def search_vector(self, vector: list[float]) -> list[Any]:
        return []

    def neighbors(self, key: str) -> list[Any]:
        return []

    def delete_candidate(self, key: str) -> dict[str, Any]:
        return {"key": key, "deleted": False, "reason": "DELETE_REQUIRES_RAIOS_GOVERNANCE"}

    def health(self) -> dict[str, Any]:
        return {"ok": True, "backend": "in-memory", "authoritative": False}


class MemorySPI:
    def __init__(self, store: Any, provider: MemoryProvider | None = None) -> None:
        self.store = store
        self.provider = provider or InMemoryProvider()
        self.authority = ORGANISM_ID

    def put(self, key: str, value: Any) -> dict[str, Any]:
        stored = self.provider.put(key, value)
        stored["raios_authority"] = self.authority
        stored["canonical"] = False
        return stored

    def get(self, key: str) -> Any:
        return self.provider.get(key)

    def search_text(self, query: str) -> list[Any]:
        return self.provider.search_text(query)

    def search_vector(self, vector: list[float]) -> list[Any]:
        return self.provider.search_vector(vector)

    def neighbors(self, key: str) -> list[Any]:
        return self.provider.neighbors(key)

    def delete_candidate(self, key: str) -> dict[str, Any]:
        return self.provider.delete_candidate(key)

    def health(self) -> dict[str, Any]:
        data = self.provider.health()
        data["eidetic_authoritative"] = False
        data["m3_memory_authoritative"] = False
        data["mcp_memory_authoritative"] = False
        data["raios_owns_identity"] = True
        return data

    def claim_authority(self, backend: str) -> None:
        raise FailClosed(f"EXTERNAL_MEMORY_CANNOT_BE_AUTHORITATIVE:{backend}")
