"""Evidence-based architecture reconstruction. Missing edges stay UNKNOWN."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from raios_fi.parse import parse_file
from raios_fi.store import Store


@dataclass(frozen=True)
class ArchEdge:
    src: str
    dst: str
    kind: str
    state: str  # PROVEN | INFERRED | UNKNOWN
    confidence: float
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArchitectureReconstructor:
    def __init__(self, store: Store | None = None) -> None:
        self.store = store

    def reconstruct(self, files: list[Path]) -> dict[str, Any]:
        entry_points: list[str] = []
        modules: list[str] = []
        routes: list[str] = []
        tests: list[str] = []
        edges: list[ArchEdge] = []
        for p in files:
            parsed = parse_file(p)
            rel = str(p)
            if p.name in {"page.tsx", "layout.tsx", "route.ts", "main.py", "__main__.py", "index.ts"}:
                entry_points.append(rel)
            if parsed.language in {"python", "typescript", "javascript"}:
                modules.append(rel)
            routes.extend(parsed.routes)
            if "test" in p.name.lower() or "/tests/" in rel.replace("\\", "/"):
                tests.append(rel)
            for imp in parsed.imports:
                edges.append(
                    ArchEdge(
                        src=rel,
                        dst=imp,
                        kind="IMPORTS",
                        state="PROVEN" if parsed.parser.startswith(("python-ast", "heuristic")) else "INFERRED",
                        confidence=parsed.confidence,
                        evidence=parsed.parser,
                    )
                )
                if self.store:
                    self.store.upsert_relation(
                        "FILE",
                        rel,
                        "MODULE",
                        imp,
                        "IMPORTS",
                        edges[-1].state,
                        edges[-1].confidence,
                        parsed.parser,
                    )
        return {
            "entry_points": sorted(set(entry_points)),
            "modules": sorted(set(modules))[:200],
            "layers": [],
            "services": [],
            "routes": sorted(set(routes)),
            "db_access": [],
            "events": [],
            "state_machines": [],
            "workflows": [],
            "external_apis": [],
            "agents": [],
            "models": [],
            "storage": [],
            "tests": sorted(set(tests)),
            "edges": [e.to_dict() for e in edges[:500]],
            "unclaimed_layers": "UNKNOWN",
        }
