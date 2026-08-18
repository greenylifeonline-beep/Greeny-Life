"""Multi-stage search. LLM is last and only over selected evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import FailClosed, run
from .spi import BaseProvider
from .store import IndexStore


class SearchProvider(BaseProvider):
    name = "search"
    capability = "search"
    per_file_cost = 0.03
    accuracy = 0.8

    def __init__(self, store: IndexStore, repo: Path) -> None:
        self.store = store
        self.repo = repo

    def execute(self, query: str, *, allow_model: bool = False) -> dict[str, Any]:
        plan = {
            "query": query,
            "stages": [
                "metadata",
                "filename",
                "ripgrep",
                "symbol",
                "ast",
                "dependency",
                "fts5",
                "semantic_if_available",
                "qwen_synthesis_selected_only",
            ],
        }
        hits: list[dict[str, Any]] = []
        # stage 0/1 metadata + filename
        for rec in self.store.files():
            path = rec["relative_path"]
            if query.lower() in path.lower() or query.lower() in (rec.get("language") or ""):
                hits.append(_hit(rec, "filename", 0.9, "path/language metadata"))
        # stage 2 ripgrep
        rg = run(["rg", "-l", "--max-count", "1", query, str(self.repo)])
        if rg.returncode in {0, 1}:
            for line in rg.stdout.splitlines()[:50]:
                hits.append(
                    {
                        "relative_path": str(Path(line).relative_to(self.repo)) if Path(line).is_absolute() else line,
                        "provider": "rg",
                        "score": 0.8,
                        "why_selected": "lexical ripgrep",
                        "evidence": {"tool": "rg"},
                        "source_hash": None,
                    }
                )
        # stage 3 symbols
        rows = self.store.conn.execute(
            "SELECT payload_json FROM symbols WHERE name LIKE ?", (f"%{query}%",)
        ).fetchall()
        import json

        for row in rows:
            rec = json.loads(row["payload_json"])
            hits.append(
                {
                    "symbol": rec["name"],
                    "file_id": rec["file_id"],
                    "provider": "symbols",
                    "score": 0.85,
                    "why_selected": "symbol name",
                    "evidence": rec,
                    "source_hash": None,
                }
            )
        # stage 6 FTS5
        for row in self.store.fts(query):
            hits.append({**row, "provider": "fts5", "score": 0.7, "why_selected": "fts5", "evidence": row, "source_hash": None})
        if allow_model:
            raise FailClosed("QWEN_SYNTHESIS_REQUIRES_EXPLICIT_EVIDENCE_BUNDLE")
        return {"plan": plan, "hits": hits[:100], "model_used": False}


class SemanticSearchProvider(BaseProvider):
    name = "semantic"
    capability = "semantic-search"

    def health(self) -> dict[str, Any]:
        return {"ok": True, "vector": False, "fallback": "fts5/bm25"}

    def fallback(self) -> str | None:
        return "fts5"


def _hit(rec: dict[str, Any], provider: str, score: float, why: str) -> dict[str, Any]:
    return {
        "file_id": rec["file_id"],
        "relative_path": rec["relative_path"],
        "provider": provider,
        "score": score,
        "why_selected": why,
        "evidence": {"class": rec.get("class")},
        "source_hash": rec.get("sha256"),
    }
