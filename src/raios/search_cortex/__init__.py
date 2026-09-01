"""Unified RAIOS Search Cortex.

Shared retrieval surface for Live Brain, Executive Manager and Evolution Brain.
The indexes are derived caches only; canonical truth remains in existing RAIOS
state, Cognitive WAL, repository and governed sources.
"""
from __future__ import annotations

from typing import Any

from .engine import plan_query, refresh_repo_index, search


class SearchCortex:
    def search(
        self,
        query: str,
        *,
        public_allowed: bool = False,
        public_query: str | None = None,
        official_allowed: bool = False,
        limit: int = 20,
        deep: bool = False,
        trace: bool = True,
    ) -> dict[str, Any]:
        result = search(
            query,
            public_query=public_query,
            allow_public=public_allowed,
            include_history=deep,
            include_official=official_allowed,
            limit=limit,
            emit_trace=trace,
        )
        return {
            **result,
            "mechanisms": result.get("sources", []),
            "deep_history_used": bool(deep),
            "shared_cortex": True,
        }

    def refresh(self) -> dict[str, Any]:
        return refresh_repo_index()


__all__ = ["SearchCortex", "search", "plan_query", "refresh_repo_index"]
