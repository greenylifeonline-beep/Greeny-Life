"""Remaining SPI providers. Thin adapters over existing engines."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .archive import ArchiveEngine
from .compare import ComparisonEngine
from .config import sha256_bytes
from .merge import MergeIntelligence
from .parse import parse_file
from .repair import mine_repairs
from .spi import BaseProvider
from .store import IndexStore


class DependencyProvider(BaseProvider):
    name = "dependencies"
    capability = "dependencies"
    per_file_cost = 0.04
    accuracy = 0.7

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        path = Path(obj["absolute_path"])
        parsed = parse_file(path, file_id=obj.get("file_id"))
        return {
            "provider": self.name,
            "imports": parsed.imports,
            "exports": parsed.exports,
            "parser": parsed.parser,
            "qwen_used": False,
        }


class DiffProvider(BaseProvider):
    name = "diff"
    capability = "diff"
    per_file_cost = 0.05
    accuracy = 0.9

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        a = Path(obj["path_a"])
        b = Path(obj["path_b"])
        engine = ComparisonEngine()
        text = engine.text_diff(a, b)
        symbols = engine.symbol_diff(a, b)
        return {"text": text.to_dict(), "symbols": symbols.to_dict(), "provider": self.name}


class MergeProvider(BaseProvider):
    name = "merge"
    capability = "merge"
    per_file_cost = 0.06
    accuracy = 0.5
    risk = "MEDIUM"

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        return {"provider": self.name, "status": "CANDIDATES_ONLY", "auto_apply": False}


class RepairProvider(BaseProvider):
    name = "repair"
    capability = "repair"
    per_file_cost = 0.07
    accuracy = 0.6
    risk = "HIGH"

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        path = Path(obj["absolute_path"])
        return {"candidates": [c.to_dict() for c in mine_repairs(path)], "applied": False}


class ValidationProvider(BaseProvider):
    name = "validation"
    capability = "validate"
    per_file_cost = 0.02
    accuracy = 0.99
    risk = "LOW"

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        path = Path(obj["absolute_path"])
        before = obj.get("sha256")
        after = sha256_bytes(path.read_bytes())
        return {
            "immutable": before == after if before else True,
            "source_hash": after,
            "writes": False,
        }


def default_registry(store: IndexStore | None = None) -> Any:
    from .discovery import FileDiscoveryProvider
    from .extract import ArchiveProvider, TextExtractionProvider
    from .parse import CodeParserProvider, SymbolProvider
    from .search import SearchProvider, SemanticSearchProvider
    from .spi import ProviderRegistry
    from .types import FileTypeProvider

    registry = ProviderRegistry()
    for provider in (
        FileDiscoveryProvider(),
        FileTypeProvider(),
        TextExtractionProvider(),
        CodeParserProvider(),
        SymbolProvider(),
        SemanticSearchProvider(),
        DependencyProvider(),
        DiffProvider(),
        MergeProvider(),
        ArchiveProvider(),
        RepairProvider(),
        ValidationProvider(),
    ):
        registry.register(provider)
    if store is not None:
        from .config import repo_root_from

        registry.register(SearchProvider(store, repo_root_from()))
    return registry
