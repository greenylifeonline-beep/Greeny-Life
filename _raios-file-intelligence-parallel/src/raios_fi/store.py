"""SQLite + FTS5 metadata index. Heavy blobs stay on filesystem CAS."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import (
    CLASSIFIER_VERSION,
    FailClosed,
    PARSER_VERSION,
    PROVIDER_VERSION,
    assert_writable,
    canonical_json,
    sha256_bytes,
    utc_now,
)


class CasRecord:
    def __init__(self, sha256: str, path: Path) -> None:
        self.sha256 = sha256
        self.path = path


class ContentAddressedBlobs:
    """Local CAS patterned after the integration-wave store. Writes stay in this package."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, data: bytes, meta: dict[str, Any] | None = None) -> CasRecord:
        digest = sha256_bytes(data)
        dest = self.objects / digest[:2] / digest
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_bytes(data)
        if meta:
            dest.with_suffix(".meta.json").write_text(canonical_json(meta), encoding="utf-8")
        return CasRecord(digest, dest)

DDL = """
CREATE TABLE IF NOT EXISTS roots (
    root_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    file_id TEXT PRIMARY KEY,
    root_id TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size INTEGER NOT NULL,
    class TEXT NOT NULL,
    language TEXT,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS file_versions (
    sha256 TEXT NOT NULL,
    file_id TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    PRIMARY KEY (sha256, file_id)
);
CREATE TABLE IF NOT EXISTS content_types (
    sha256 TEXT PRIMARY KEY,
    class TEXT NOT NULL,
    mime TEXT,
    confidence REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    file_id TEXT PRIMARY KEY,
    text_sha256 TEXT,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS symbols (
    symbol_id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS relations (
    rel_id TEXT PRIMARY KEY,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    src_kind TEXT,
    src_id TEXT,
    dst_kind TEXT,
    dst_id TEXT,
    kind TEXT NOT NULL,
    state TEXT NOT NULL,
    confidence REAL NOT NULL,
    evidence TEXT
);
CREATE TABLE IF NOT EXISTS dependencies (
    dep_id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    spec TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis (
    analysis_id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS comparisons (
    comparison_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS repair_candidates (
    repair_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS archive_records (
    archive_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS parser_cache (
    sha256 TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    classifier_version TEXT NOT NULL,
    provider_version TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (sha256, parser_version, classifier_version, provider_version, kind)
);
CREATE TABLE IF NOT EXISTS disagreements (
    disagreement_id TEXT PRIMARY KEY,
    file_id TEXT,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS query_metrics (
    query_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(file_id, relative_path, body);
"""


class IndexStore:
    def __init__(self, root: str | Path, repo: Path | None = None) -> None:
        self.root = Path(root)
        assert_writable(self.root, repo)
        self.root.mkdir(parents=True, exist_ok=True)
        self.cas = ContentAddressedBlobs(self.root / "cas")
        self.conn = sqlite3.connect(str(self.root / "fileintel.sqlite"))
        self.conn.row_factory = sqlite3.Row
        self.conn.isolation_level = None
        self.conn.execute("PRAGMA journal_mode=WAL")
        opts = [r[0] for r in self.conn.execute("PRAGMA compile_options")]
        if not any("FTS5" in str(o).upper() for o in opts):
            raise FailClosed("FTS5_UNAVAILABLE")
        self.conn.executescript(DDL)
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(parser_cache)")}
        if "classifier_version" not in cols or "kind" not in cols:
            self.conn.execute("DROP TABLE IF EXISTS parser_cache")
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS parser_cache (
                    sha256 TEXT NOT NULL,
                    parser_version TEXT NOT NULL,
                    classifier_version TEXT NOT NULL,
                    provider_version TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (sha256, parser_version, classifier_version, provider_version, kind)
                );
                """
            )
        self.cache_hits = 0
        self.cache_misses = 0

    def close(self) -> None:
        self.conn.close()

    def put_blob(self, data: bytes) -> str:
        return self.cas.put_bytes(data).sha256

    def cache_get(self, digest: str, kind: str = "parse") -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT payload_json FROM parser_cache
            WHERE sha256=? AND parser_version=? AND classifier_version=? AND provider_version=? AND kind=?
            """,
            (digest, PARSER_VERSION, CLASSIFIER_VERSION, PROVIDER_VERSION, kind),
        ).fetchone()
        if row:
            self.cache_hits += 1
            return json.loads(row["payload_json"])
        self.cache_misses += 1
        return None

    def cache_put(self, digest: str, payload: dict[str, Any], kind: str = "parse") -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO parser_cache(
                sha256, parser_version, classifier_version, provider_version, kind, payload_json
            ) VALUES (?,?,?,?,?,?)
            """,
            (digest, PARSER_VERSION, CLASSIFIER_VERSION, PROVIDER_VERSION, kind, canonical_json(payload)),
        )

    def cache_hit_ratio(self) -> float:
        total = self.cache_hits + self.cache_misses
        if not total:
            return 0.0
        return round(self.cache_hits / total, 4)

    def insert_disagreement(self, rec: dict[str, Any]) -> None:
        from .config import deterministic_id

        did = rec.get("disagreement_id") or deterministic_id("disagree", rec.get("file_id", ""), rec.get("kind", ""))
        self.conn.execute(
            "INSERT OR REPLACE INTO disagreements(disagreement_id, file_id, payload_json) VALUES (?,?,?)",
            (did, rec.get("file_id"), canonical_json(rec)),
        )

    def disagreements(self) -> list[dict[str, Any]]:
        return [json.loads(r["payload_json"]) for r in self.conn.execute("SELECT payload_json FROM disagreements")]

    def insert_query_metrics(self, rec: dict[str, Any]) -> None:
        from .config import deterministic_id

        qid = rec.get("query_id") or deterministic_id("query", rec.get("natural", ""), utc_now())
        self.conn.execute(
            "INSERT OR REPLACE INTO query_metrics(query_id, payload_json) VALUES (?,?)",
            (qid, canonical_json(rec)),
        )

    def upsert_file(self, rec: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO files(file_id, root_id, relative_path, sha256, size, class, language, payload_json)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                rec["file_id"],
                rec["root_id"],
                rec["relative_path"],
                rec["sha256"],
                rec["size"],
                rec["class"],
                rec.get("language"),
                canonical_json(rec),
            ),
        )
        self.conn.execute(
            "INSERT OR IGNORE INTO file_versions(sha256, file_id, seen_at) VALUES (?,?,?)",
            (rec["sha256"], rec["file_id"], utc_now()),
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO content_types(sha256, class, mime, confidence) VALUES (?,?,?,?)",
            (rec["sha256"], rec["class"], rec.get("mime"), float(rec.get("confidence") or 0)),
        )

    def index_text(self, file_id: str, relative_path: str, body: str) -> None:
        self.conn.execute("INSERT INTO search_index(file_id, relative_path, body) VALUES (?,?,?)", (file_id, relative_path, body))

    def fts(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        try:
            rows = self.conn.execute(
                "SELECT file_id, relative_path FROM search_index WHERE search_index MATCH ? LIMIT ?",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [dict(r) for r in rows]

    def add_symbol(self, rec: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO symbols(symbol_id, file_id, kind, name, payload_json) VALUES (?,?,?,?,?)",
            (rec["symbol_id"], rec["file_id"], rec["kind"], rec["name"], canonical_json(rec)),
        )

    def add_relation(
        self,
        rel_id: str,
        src: str,
        dst: str,
        kind: str,
        state: str,
        confidence: float,
        *,
        src_kind: str | None = None,
        dst_kind: str | None = None,
        evidence: str = "",
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO relations(
                rel_id, src, dst, src_kind, src_id, dst_kind, dst_id, kind, state, confidence, evidence
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (rel_id, src, dst, src_kind, src, dst_kind, dst, kind, state, confidence, evidence),
        )

    def upsert_relation(
        self,
        src_kind: str,
        src: str,
        dst_kind: str,
        dst: str,
        kind: str,
        state: str,
        confidence: float,
        evidence: str = "",
    ) -> None:
        from .config import deterministic_id

        rel_id = deterministic_id("rel", src_kind, src, kind, dst_kind, dst)
        self.add_relation(
            rel_id,
            src,
            dst,
            kind,
            state,
            confidence,
            src_kind=src_kind,
            dst_kind=dst_kind,
            evidence=evidence,
        )

    def insert_archive(self, rec: dict[str, Any]) -> None:
        from .config import deterministic_id

        archive_id = rec.get("archive_id") or deterministic_id("archive", rec.get("original_path", ""), rec.get("sha256", ""))
        self.conn.execute(
            "INSERT OR REPLACE INTO archive_records(archive_id, payload_json) VALUES (?,?)",
            (archive_id, canonical_json(rec)),
        )

    def insert_repair(self, rec: dict[str, Any]) -> None:
        from .config import deterministic_id

        repair_id = rec.get("repair_id") or deterministic_id("repair", rec.get("kind", ""), rec.get("root_cause", ""))
        self.conn.execute(
            "INSERT OR REPLACE INTO repair_candidates(repair_id, payload_json) VALUES (?,?)",
            (repair_id, canonical_json(rec)),
        )

    def add_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO events(event_type, payload_json, created_at) VALUES (?,?,?)",
            (event_type, canonical_json(payload), utc_now()),
        )

    def files(self) -> list[dict[str, Any]]:
        return [json.loads(r["payload_json"]) for r in self.conn.execute("SELECT payload_json FROM files")]


Store = IndexStore
