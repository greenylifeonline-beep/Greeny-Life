"""Orchestrator. Analysis is read-only. Writes stay inside this package."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .architecture import ArchitectureReconstructor
from .archive import ArchiveEngine
from .classify import classify_path
from .config import FailClosed, PACKAGE, package_root, repo_root_from
from .discovery import FileDiscoveryProvider
from .economy import ToolEconomy
from .extract import TextExtractionProvider
from .graph import FileKnowledgeGraph
from .idle import IdleLoop
from .parse import CodeParserProvider, parse_file
from .providers import default_registry
from .query import compile_query
from .search import SearchProvider
from .store import IndexStore
from .types import FileTypeProvider


class FileIntelligenceRuntime:
    def __init__(self, var_root: Path | None = None, repo: Path | None = None) -> None:
        self.repo = repo or repo_root_from()
        self.pkg = package_root(self.repo)
        self.var = Path(var_root or (self.pkg / "var" / "index"))
        FailClosed.assert_writable(self.var, self.repo)
        self.store = IndexStore(self.var, repo=self.repo)
        self.discovery = FileDiscoveryProvider(self.repo)
        self.types = FileTypeProvider()
        self.extract = TextExtractionProvider()
        self.parser = CodeParserProvider()
        self.search = SearchProvider(self.store, self.repo)
        self.graph = FileKnowledgeGraph(self.store)
        self.archive = ArchiveEngine(self.store)
        self.registry = default_registry(self.store)
        self.economy = ToolEconomy(self.registry)
        self.idle = IdleLoop()

    def close(self) -> None:
        self.store.close()

    def ingest(self, root: Path, kind: str = "workspace", limit: int | None = 200) -> dict[str, Any]:
        result = self.discovery.ingest_root(self.store, root, kind, limit=limit)
        parsed_n = 0
        extracted_n = 0
        unknown_n = 0
        for rec in self.store.files():
            if rec.get("class") == "UNKNOWN":
                unknown_n += 1
            parsed = parse_file(Path(rec["absolute_path"]), file_id=rec["file_id"], store=self.store)
            rec["parser"] = parsed.parser
            rec["symbol_provider"] = parsed.parser
            for sym in parsed.symbols:
                self.store.add_symbol(sym.to_dict())
            for imp in parsed.imports:
                self.graph.add_edge("FILE", rec["relative_path"], "MODULE", imp, "IMPORTS", "PROVEN", parsed.confidence, parsed.parser)
            extracted = self.extract.analyze(rec)
            rec["extractor"] = extracted.get("extractor")
            if extracted.get("text"):
                extracted_n += 1
            classify_path(Path(rec["absolute_path"]))
            parsed_n += 1
        result.update({"parsed": parsed_n, "extracted_text": extracted_n, "unknown": unknown_n, "package": PACKAGE})
        return result

    def plan_query(self, natural: str) -> dict[str, Any]:
        return compile_query(natural, [str(self.repo)]).to_dict()

    def search_query(self, query: str) -> dict[str, Any]:
        return self.search.execute(query, allow_model=False)

    def architecture(self, files: list[Path]) -> dict[str, Any]:
        return ArchitectureReconstructor(self.store).reconstruct(files)

    def health(self) -> dict[str, Any]:
        files = self.store.files()
        n = len(files) or 1
        text_n = sum(1 for f in files if f.get("is_text"))
        code_n = sum(1 for f in files if f.get("class") == "CODE")
        unknown_n = sum(1 for f in files if f.get("class") == "UNKNOWN")
        symbols = self.store.conn.execute("SELECT COUNT(*) AS c FROM symbols").fetchone()["c"]
        rels = self.store.conn.execute("SELECT COUNT(*) AS c FROM relations").fetchone()["c"]
        return {
            "files": len(files),
            "text_searchable_pct": round(100.0 * text_n / n, 2),
            "unknown": unknown_n,
            "code_files": code_n,
            "symbols": symbols,
            "relations": rels,
            "fts": True,
            "package": PACKAGE,
        }
