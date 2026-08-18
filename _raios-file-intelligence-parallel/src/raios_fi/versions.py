"""Two-version intelligence. Never assume old/new without evidence."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import deterministic_id, repo_root_from
from .discovery import FileDiscoveryProvider
from .store import IndexStore


@dataclass
class VersionRoot:
    root_id: str
    path: str
    kind: str
    evidence: list[str]
    score: int
    assumed_newer: bool = False
    assumed_older: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VersionDifferential:
    root_a: dict[str, Any]
    root_b: dict[str, Any]
    assumed_newer: bool
    only_in_a: list[str]
    only_in_b: list[str]
    shared_files: list[str]
    same_hash: list[str]
    modified: list[str]
    renamed_or_moved: list[dict[str, Any]]
    semantic_equivalent_candidates: list[dict[str, Any]]
    counts: dict[str, int]
    renamed_candidate: list[dict[str, Any]] = field(default_factory=list)
    moved_candidate: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VersionDetector:
    def __init__(self, repo: Path | None = None) -> None:
        self.repo = repo or repo_root_from()

    def roots(self) -> list[dict[str, Any]]:
        candidates = []
        mapping = [
            (self.repo / "app", "application", ["package.json", "page.tsx", "layout.tsx"]),
            (self.repo / "canonical", "canonical-data", ["system_manifest.json"]),
            (
                self.repo / "archive" / "old_folders" / "GREENY-LIFE-EOS-PRODUCTION",
                "archive-eos",
                ["production-manifest-v1.json"],
            ),
            (self.repo / "application", "application-alt", []),
            (self.repo / "RAIOS" / "V9", "raios-organism", ["continuity"]),
        ]
        pkg = self.repo / "package.json"
        if pkg.exists():
            candidates.append(
                {
                    "root_id": deterministic_id("root", str(self.repo)),
                    "path": str(self.repo),
                    "kind": "repo-manifest",
                    "evidence": ["package.json"],
                    "score": 2,
                    "assumed_newer": False,
                    "assumed_older": False,
                }
            )
        for path, kind, evidence_names in mapping:
            if not path.exists():
                continue
            evidence = []
            for name in evidence_names:
                if (path / name).exists():
                    evidence.append(name)
                    continue
                try:
                    if any(path.rglob(name)):
                        evidence.append(name)
                except OSError:
                    pass
            score = (2 if evidence else 1) + (1 if path.is_dir() else 0)
            candidates.append(
                {
                    "root_id": deterministic_id("root", str(path)),
                    "path": str(path),
                    "kind": kind,
                    "evidence": evidence,
                    "score": score,
                    "assumed_newer": False,
                    "assumed_older": False,
                }
            )
        return sorted(candidates, key=lambda row: row["score"], reverse=True)

    def pair(self) -> tuple[dict[str, Any], dict[str, Any]] | None:
        roots = [row for row in self.roots() if row["kind"] not in {"raios-organism", "repo-manifest"}]
        if len(roots) < 2:
            return None
        return roots[0], roots[1]


def differential(
    store: IndexStore,
    root_a: Path,
    root_b: Path,
    discovery: FileDiscoveryProvider,
    limit: int = 400,
) -> VersionDifferential:
    a = discovery.ingest_root(store, root_a, "version-a", limit=limit)
    b = discovery.ingest_root(store, root_b, "version-b", limit=limit)
    files = store.files()
    by_root: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in files:
        by_root[rec["root_id"]].append(rec)
    map_a = {_relkey(rec): rec for rec in by_root.get(a["root_id"], [])}
    map_b = {_relkey(rec): rec for rec in by_root.get(b["root_id"], [])}
    names_a, names_b = set(map_a), set(map_b)
    only_a = sorted(names_a - names_b)
    only_b = sorted(names_b - names_a)
    shared = sorted(names_a & names_b)
    same_hash = [name for name in shared if map_a[name]["sha256"] == map_b[name]["sha256"]]
    modified = [name for name in shared if map_a[name]["sha256"] != map_b[name]["sha256"]]
    renamed: list[dict[str, Any]] = []
    moved: list[dict[str, Any]] = []
    used_b: set[str] = set()
    for name in only_a:
        digest = map_a[name]["sha256"]
        for other, rec in map_b.items():
            if other in used_b:
                continue
            if rec["sha256"] == digest:
                item = {"a": name, "b": other, "sha256": digest, "kind": "MOVED_OR_RENAMED"}
                renamed.append(item)
                parent_a = "/".join(name.split("/")[:-1])
                parent_b = "/".join(other.split("/")[:-1])
                if Path(name).name == Path(other).name and parent_a != parent_b:
                    moved.append({**item, "kind": "MOVED"})
                used_b.add(other)
                break
    return VersionDifferential(
        root_a=a,
        root_b=b,
        assumed_newer=False,
        only_in_a=only_a,
        only_in_b=only_b,
        shared_files=shared,
        same_hash=same_hash,
        modified=modified,
        renamed_or_moved=renamed,
        semantic_equivalent_candidates=renamed,
        counts={
            "a": len(map_a),
            "b": len(map_b),
            "shared": len(shared),
            "modified": len(modified),
        },
        renamed_candidate=renamed,
        moved_candidate=moved,
    )


def _relkey(rec: dict[str, Any]) -> str:
    rel = rec.get("root_relative") or rec["relative_path"]
    parts = rel.split("/")
    return "/".join(parts[-3:])
