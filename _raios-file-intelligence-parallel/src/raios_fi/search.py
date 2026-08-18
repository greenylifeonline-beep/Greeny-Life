"""Multi-stage search. Only selected stages run. LLM is last and evidence-only."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .config import FailClosed, run
from .query import QueryPlan, compile_query
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
        self.last_metrics: dict[str, Any] = {}

    def execute(self, query: str, *, allow_model: bool = False, plan: QueryPlan | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        plan = plan or compile_query(query, [str(self.repo)])
        selected = set(plan.selected_stages)
        hits: list[dict[str, Any]] = []
        files_scanned = 0
        files_parsed = 0
        model_calls = 0
        teacher_calls = 0
        files_read = 0

        if "STAGE_0_METADATA" in selected or "STAGE_1_FILENAME" in selected:
            for rec in self.store.files():
                files_scanned += 1
                path = rec["relative_path"]
                if query.lower() in path.lower() or query.lower() in (rec.get("language") or ""):
                    hits.append(_hit(rec, "filename", 0.9, "path/language metadata"))

        if "STAGE_2_RIPGREP" in selected:
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
                    files_read += 1

        if "STAGE_3_SYMBOL" in selected:
            import json

            rows = self.store.conn.execute(
                "SELECT payload_json FROM symbols WHERE name LIKE ?", (f"%{query}%",)
            ).fetchall()
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

        if "STAGE_6_FTS5" in selected:
            for row in self.store.fts(query):
                hits.append({**row, "provider": "fts5", "score": 0.7, "why_selected": "fts5", "evidence": row, "source_hash": None})

        if allow_model or "STAGE_8_QWEN" in selected:
            raise FailClosed("QWEN_SYNTHESIS_REQUIRES_EXPLICIT_EVIDENCE_BUNDLE")

        latency = time.perf_counter() - started
        metrics = {
            "query_cost": plan.estimated_cost,
            "files_scanned": files_scanned,
            "files_parsed": files_parsed,
            "model_calls": model_calls,
            "teacher_calls": teacher_calls,
            "latency": round(latency, 4),
            "cache_hits": self.store.cache_hits,
            "selected_stages": plan.selected_stages,
            "skipped_stages": plan.skipped_stages,
            "files_read": files_read,
        }
        self.last_metrics = metrics
        self.store.insert_query_metrics({"natural": query, **metrics})
        return {
            "plan": plan.to_dict(),
            "hits": hits[:100],
            "model_used": False,
            "metrics": metrics,
        }


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
