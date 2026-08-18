"""SQLite metadata store + hash-chained logical WAL for the integration wave."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from ..cas import ContentAddressedStore
from ..identity import (
    ORGANISM_ID,
    SCHEMA_VERSION,
    FailClosed,
    assert_not_protected_live_writer,
    canonical_json,
    deterministic_id,
    read_v9_identity,
    repo_root_from,
    sha256_obj,
    utc_now,
)
from ..models import EventType

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


class Store:
    def __init__(self, root: str | Path, repo_root: Path | None = None) -> None:
        self.root = Path(root)
        assert_not_protected_live_writer(self.root, repo_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.cas = ContentAddressedStore(self.root / "cas")
        self.db_path = self.root / "wave.sqlite"
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.isolation_level = None
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._assert_fts5()
        self.migrate()
        self._bind_identity(repo_root)

    def close(self) -> None:
        self.conn.close()

    def _assert_fts5(self) -> None:
        compile_opts = [row[0] for row in self.conn.execute("PRAGMA compile_options")]
        if not any("FTS5" in opt.upper() for opt in compile_opts):
            try:
                self.conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)")
                self.conn.execute("DROP TABLE IF EXISTS _fts5_probe")
            except sqlite3.OperationalError as exc:
                raise FailClosed("FTS5_UNAVAILABLE") from exc

    def migrate(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        current = self.conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_meta").fetchone()[0]
        for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = int(file.name.split("_", 1)[0])
            if version <= current:
                continue
            self.conn.executescript(file.read_text(encoding="utf-8"))
            self.conn.execute(
                "INSERT INTO schema_meta(version, applied_at) VALUES (?, ?)",
                (version, utc_now()),
            )

    def _bind_identity(self, repo_root: Path | None) -> None:
        identity = read_v9_identity(repo_root or repo_root_from())
        identity["organism_id"] = ORGANISM_ID
        identity["schema_version"] = SCHEMA_VERSION
        identity["cortex_is_identity"] = False
        existing = self.conn.execute(
            "SELECT payload_json FROM identity_state WHERE organism_id = ?",
            (ORGANISM_ID,),
        ).fetchone()
        if existing:
            return
        self.conn.execute(
            "INSERT INTO identity_state(organism_id, payload_json, updated_at) VALUES (?, ?, ?)",
            (ORGANISM_ID, canonical_json(identity), utc_now()),
        )
        self.append_event(EventType.IDENTITY_BOUND, ORGANISM_ID, {"binding": identity.get("binding")})

    def identity(self) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT payload_json FROM identity_state WHERE organism_id = ?",
            (ORGANISM_ID,),
        ).fetchone()
        if not row:
            raise FailClosed("IDENTITY_MISSING")
        return json.loads(row["payload_json"])

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.conn.execute("BEGIN")
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def append_event(self, event_type: EventType, entity_id: str, payload: dict[str, Any]) -> str:
        prev = self.conn.execute(
            "SELECT seq, event_sha256 FROM audit_events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prev_hash = prev["event_sha256"] if prev else None
        seq = (prev["seq"] + 1) if prev else 1
        created = utc_now()
        event_id = deterministic_id("evt", event_type.value, entity_id, str(seq), created)
        body = {
            "event_id": event_id,
            "seq": seq,
            "event_type": event_type.value,
            "entity_id": entity_id,
            "payload": payload,
            "created_at": created,
            "prev_event_sha256": prev_hash,
        }
        digest = sha256_obj(body)
        self.conn.execute(
            """
            INSERT INTO audit_events(
                event_id, seq, event_type, entity_id, payload_json, created_at,
                prev_event_sha256, event_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                seq,
                event_type.value,
                entity_id,
                canonical_json(payload),
                created,
                prev_hash,
                digest,
            ),
        )
        return event_id

    def verify_event_chain(self) -> dict[str, Any]:
        rows = self.conn.execute(
            "SELECT event_id, seq, event_type, entity_id, payload_json, created_at, "
            "prev_event_sha256, event_sha256 FROM audit_events ORDER BY seq ASC"
        ).fetchall()
        prev_hash = None
        for row in rows:
            body = {
                "event_id": row["event_id"],
                "seq": row["seq"],
                "event_type": row["event_type"],
                "entity_id": row["entity_id"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
                "prev_event_sha256": row["prev_event_sha256"],
            }
            expected = sha256_obj(body)
            if expected != row["event_sha256"]:
                raise FailClosed(f"EVENT_HASH_MISMATCH:{row['event_id']}")
            if row["prev_event_sha256"] != prev_hash:
                raise FailClosed(f"EVENT_CHAIN_BREAK:{row['event_id']}")
            prev_hash = row["event_sha256"]
        return {"ok": True, "count": len(rows), "tip": prev_hash}

    def put_json(self, obj: Any) -> str:
        digest, _created = self.cas.ingest(canonical_json(obj).encode("utf-8"))
        self.conn.execute(
            "INSERT OR IGNORE INTO objects(sha256, bytes, created_at) VALUES (?, ?, ?)",
            (digest, len(canonical_json(obj).encode("utf-8")), utc_now()),
        )
        return digest

    def put_bytes(self, data: bytes) -> str:
        digest, _created = self.cas.ingest(data)
        self.conn.execute(
            "INSERT OR IGNORE INTO objects(sha256, bytes, created_at) VALUES (?, ?, ?)",
            (digest, len(data), utc_now()),
        )
        return digest

    def integrity_check(self) -> str:
        row = self.conn.execute("PRAGMA integrity_check").fetchone()
        result = row[0]
        if result != "ok":
            raise FailClosed(f"SQLITE_INTEGRITY_FAILED:{result}")
        return result
