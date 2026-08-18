"""Orchestrator. Analysis is read-only. Writes stay inside this package."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .architecture import ArchitectureReconstructor
from .archive import ArchiveEngine
from .classify import classify_path
from .cognition import shared_cognitive_state
from .config import FailClosed, PACKAGE, package_root, repo_root_from, sha256_text
from .discovery import FileDiscoveryProvider
from .disagreement import persist_disagreement, resolve_votes
from .duplicates import duplicate_groups
from .economy import ToolEconomy
from .extract import TextExtractionProvider
from .graph import FileKnowledgeGraph
from .identity import normalized_hash
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
            rec["extract_status"] = extracted.get("status")
            if extracted.get("text"):
                extracted_n += 1
            classified = classify_path(Path(rec["absolute_path"]))
            rec.update(
                {
                    "physical_type": classified.physical_type,
                    "logical_type": classified.logical_type,
                    "domain": classified.domain,
                    "subsystem": classified.subsystem,
                    "role": classified.role,
                    "authority_class": classified.authority_class,
                    "temporal_scope": classified.temporal_scope,
                    "verification_state": classified.verification_state,
                    "knowledge_state": classified.knowledge_state,
                    "lifecycle": classified.lifecycle,
                    "version_role": classified.version_role,
                    "criticality": classified.criticality,
                    "change_risk": classified.change_risk,
                    "active_state": classified.active_state,
                    "generated_state": classified.generated_state,
                    "provenance": classified.provenance,
                    "evidence_confidence": classified.evidence_confidence,
                }
            )
            ext_hint = Path(rec["absolute_path"]).suffix.lower()
            from .types import EXT_HINT

            ext_vote = (EXT_HINT.get(ext_hint) or ("UNKNOWN", "UNKNOWN"))[1] or (EXT_HINT.get(ext_hint) or ("UNKNOWN", None))[0]
            votes = {
                "path_rules": str(ext_vote or "UNKNOWN"),
                "signatures": str(rec.get("physical_type") or rec.get("class") or "UNAVAILABLE"),
                "magika": "UNAVAILABLE",
                "parser": str(parsed.language or rec.get("language") or "UNAVAILABLE"),
                "tree_sitter": "UNAVAILABLE",
                "ctags": "UNAVAILABLE",
                "dependency_graph": "UNAVAILABLE",
                "git": "UNAVAILABLE",
                "semantic_retrieval": "UNAVAILABLE",
                "qwen": "UNAVAILABLE",
                "teachers": "UNAVAILABLE",
            }
            disagree = resolve_votes(votes, file_id=rec["file_id"], relative_path=rec["relative_path"])
            rec["disagreement"] = disagree.resolution
            if disagree.disagreeing_providers:
                persist_disagreement(self.store, disagree)
            try:
                raw = Path(rec["absolute_path"]).read_bytes()
                rec["normalized_sha256"] = normalized_hash(raw)
            except OSError:
                rec["normalized_sha256"] = None
            if rec.get("class") == "CODE":
                names = sorted({s.qualified_name for s in parsed.symbols})
                blob = "|".join(names + ["#"] + sorted(parsed.imports))
                rec["symbol_fingerprint"] = sha256_text(blob) if names or parsed.imports else None
                rec["imports"] = parsed.imports
            self.store.upsert_file(rec)
            parsed_n += 1
        groups = duplicate_groups(self.store)
        result.update(
            {
                "parsed": parsed_n,
                "extracted_text": extracted_n,
                "unknown": unknown_n,
                "duplicate_groups": len(groups),
                "disagreements": len(self.store.disagreements()),
                "cache_hit_ratio": self.store.cache_hit_ratio(),
                "package": PACKAGE,
            }
        )
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
        groups = duplicate_groups(self.store)
        cognition = shared_cognitive_state(self.repo, self.store)
        classes = sorted({str(f.get("class")) for f in files if f.get("class")})
        doc_files = [
            f
            for f in files
            if f.get("class") in {"DOCUMENT", "DATA", "ARCHIVE"}
            or (f.get("language") or "") in {"pdf", "html", "xml", "markdown"}
        ]
        extracted_docs = sum(1 for f in doc_files if f.get("extract_status") in {"EXTRACTED", "MANIFEST"})
        parsed_ok = sum(1 for f in files if f.get("class") == "CODE" and f.get("parser") and f.get("parser") != "unavailable")
        return {
            "files": len(files),
            "types_recognized": classes,
            "text_searchable_pct": round(100.0 * text_n / n, 2),
            "code_structurally_parsed_pct": round(100.0 * parsed_ok / code_n, 2) if code_n else 0.0,
            "documents_extractable_pct": round(100.0 * extracted_docs / len(doc_files), 2) if doc_files else 0.0,
            "unknown": unknown_n,
            "code_files": code_n,
            "symbols": symbols,
            "relations": rels,
            "duplicate_groups": len(groups),
            "fts": True,
            "magika": self.types.health(),
            "tika": self.extract.health(),
            "parser": self.parser.health(),
            "cognition": {
                "organism_id": cognition["organism_id"],
                "shared_identity": cognition["shared_identity"],
                "ccee_wal_writes": cognition["ccee_wal_writes"],
                "canonical_writes": cognition["canonical_writes"],
                "teacher_harvest": cognition["teacher_harvest"]["status"],
                "status": cognition["status"],
            },
            "package": PACKAGE,
        }
