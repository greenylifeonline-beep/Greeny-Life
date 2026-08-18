"""Discovery: git ls-files first, then filesystem delta. Deterministic FileObject IDs."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator

from .config import MAX_INDEX_BYTES, SKIP_DIR_NAMES, deterministic_id, repo_root_from, run, sha256_bytes
from .spi import BaseProvider
from .store import IndexStore
from .types import FileTypeProvider


class FileDiscoveryProvider(BaseProvider):
    name = "discovery"
    capability = "enumerate"
    per_file_cost = 0.005
    accuracy = 0.99

    def __init__(self, repo: Path | None = None) -> None:
        self.repo = repo or repo_root_from()
        self.types = FileTypeProvider()

    def tracked(self) -> set[str]:
        proc = run(["git", "ls-files", "-z"], cwd=self.repo)
        if proc.returncode != 0:
            return set()
        return {p for p in proc.stdout.split("\x00") if p}

    def iter_files(self, root: Path, include_untracked: bool = False) -> Iterator[Path]:
        tracked = self.tracked()
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".git")]
            for name in filenames:
                path = Path(dirpath) / name
                try:
                    rel = str(path.relative_to(self.repo)).replace("\\", "/")
                except ValueError:
                    rel = str(path.relative_to(root)).replace("\\", "/")
                if not include_untracked and tracked and rel not in tracked:
                    if root.resolve() == Path(self.repo).resolve():
                        continue
                yield path

    def file_object(self, path: Path, root: Path, root_id: str) -> dict[str, Any]:
        st = path.stat()
        try:
            rel = str(path.relative_to(self.repo))
        except ValueError:
            rel = str(path.relative_to(root))
        rel = rel.replace("\\", "/")
        root_rel = str(path.relative_to(root)).replace("\\", "/")
        data = b""
        digest = None
        if st.st_size <= MAX_INDEX_BYTES:
            data = path.read_bytes()
            digest = sha256_bytes(data)
        else:
            digest = sha256_bytes(f"size:{st.st_size}:{rel}".encode())
        tracked = rel in self.tracked()
        rec = {
            "file_id": deterministic_id("file", root_id, rel, digest),
            "root_id": root_id,
            "relative_path": rel,
            "root_relative": root_rel,
            "absolute_path": str(path),
            "sha256": digest,
            "size": st.st_size,
            "mtime": int(st.st_mtime),
            "git_state": "TRACKED" if tracked else "UNTRACKED",
            "tracked": tracked,
            "archive_parent": None,
            "duplicate_group": digest,
            "version_lineage": root_id,
            "parser": None,
            "extractor": None,
            "symbol_provider": None,
            "evidence": {"stat": True, "hash": st.st_size <= MAX_INDEX_BYTES},
        }
        typed = self.types.analyze(rec)
        rec.update(typed)
        rec["content_type"] = rec.get("class")
        return rec

    def ingest_root(self, store: IndexStore, root: Path, kind: str, limit: int | None = None) -> dict[str, Any]:
        root_id = deterministic_id("root", str(root))
        store.conn.execute(
            "INSERT OR REPLACE INTO roots(root_id, path, kind, payload_json) VALUES (?,?,?,?)",
            (root_id, str(root), kind, f'{{"kind":"{kind}"}}'),
        )
        n = 0
        for path in self.iter_files(root):
            rec = self.file_object(path, root, root_id)
            prior = store.conn.execute(
                "SELECT 1 FROM content_types WHERE sha256=?", (rec["sha256"],)
            ).fetchone()
            rec["from_cache"] = bool(prior)
            store.upsert_file(rec)
            if rec.get("is_text") and rec["size"] <= MAX_INDEX_BYTES:
                try:
                    text = Path(rec["absolute_path"]).read_text(encoding=rec.get("encoding") or "utf-8")
                except (OSError, UnicodeError):
                    text = Path(rec["absolute_path"]).read_bytes().decode(rec.get("encoding") or "utf-16", errors="replace")
                store.index_text(rec["file_id"], rec["relative_path"], text[:20000])
            n += 1
            if limit and n >= limit:
                break
        store.add_event("ROOT_INGESTED", {"root_id": root_id, "files": n})
        return {"root_id": root_id, "files": n, "kind": kind, "path": str(root)}
