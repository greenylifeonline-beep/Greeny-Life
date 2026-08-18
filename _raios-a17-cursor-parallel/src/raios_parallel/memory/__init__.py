"""MemorySPI — RAIOS remains authoritative. External backends are not installed."""
from __future__ import annotations

from typing import Any

from ..identity import ORGANISM_ID, FailClosed, canonical_json, utc_now


class MemorySPI:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.authority = ORGANISM_ID

    def put(self, key: str, value: Any) -> dict[str, Any]:
        self.store.conn.execute(
            "INSERT INTO memory_items(key, payload_json, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at",
            (key, canonical_json({"value": value, "canonical": False}), utc_now()),
        )
        return {"key": key, "authoritative_backend": False, "raios_authority": self.authority}

    def get(self, key: str) -> Any:
        import json

        row = self.store.conn.execute("SELECT payload_json FROM memory_items WHERE key = ?", (key,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def search_text(self, query: str) -> list[Any]:
        import json

        rows = self.store.conn.execute("SELECT key, payload_json FROM memory_items").fetchall()
        return [json.loads(r["payload_json"]) for r in rows if query.lower() in r["payload_json"].lower()]

    def search_vector(self, vector: list[float]) -> list[Any]:
        return []

    def neighbors(self, key: str) -> list[Any]:
        return []

    def link(self, src: str, dst: str) -> dict[str, Any]:
        return {"src": src, "dst": dst, "linked": False, "reason": "GRAPH_LINK_IS_RKG"}

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "eidetic": False,
            "m3_memory": False,
            "mcp_memory": False,
            "installed_external": False,
            "raios_owns_identity": True,
        }

    def claim_authority(self, backend: str) -> None:
        raise FailClosed(f"EXTERNAL_MEMORY_CANNOT_BE_AUTHORITATIVE:{backend}")
