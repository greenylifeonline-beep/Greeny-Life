from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .identity import SCHEMA_VERSION, utc_now
from .identity import FailClosed

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=30, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.isolation_level = None
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.fts_enabled = False
        self.migrate()
        self._init_fts()

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        self.conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def migrate(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta ("
            "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, logical_version TEXT NOT NULL)"
        )
        current = self.conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_meta").fetchone()[0]
        for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = int(file.name.split("_", 1)[0])
            if version <= current:
                continue
            self.conn.executescript(file.read_text(encoding="utf-8"))
            self.conn.execute(
                "INSERT INTO schema_meta(version, applied_at, logical_version) VALUES (?, ?, ?)",
                (version, utc_now(), SCHEMA_VERSION),
            )

    def schema_version(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_meta").fetchone()
        return int(row[0])

    def logical_schema_version(self) -> str:
        return SCHEMA_VERSION

    def _init_fts(self) -> None:
        try:
            self.conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS fts_trusted USING fts5(doc_id, body, sha256 UNINDEXED)"
            )
            self.fts_enabled = True
        except sqlite3.OperationalError:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS fts_trusted (doc_id TEXT PRIMARY KEY, body TEXT, sha256 TEXT)"
            )
            self.fts_enabled = False

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    def loads(self, payload_json: str) -> dict[str, Any]:
        return json.loads(payload_json)
