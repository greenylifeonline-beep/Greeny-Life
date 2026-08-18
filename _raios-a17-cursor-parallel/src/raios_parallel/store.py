"""Isolated SQLite + CAS store for the parallel wave."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .identity import (  # noqa: F401
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
from raios_wave.cas import ContentAddressedStore

from .models import DegradedMode

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class Store:
    def __init__(self, root: str | Path, repo_root: Path | None = None) -> None:
        self.root = Path(root)
        assert_not_protected_live_writer(self.root, repo_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.cas = ContentAddressedStore(self.root / "cas")
        self.db_path = self.root / "parallel.sqlite"
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.isolation_level = None
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.migrate()
        self._bind_identity(repo_root)

    def close(self) -> None:
        self.conn.close()

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
            "SELECT 1 FROM identity_state WHERE organism_id = ?", (ORGANISM_ID,)
        ).fetchone()
        if existing:
            return
        self.conn.execute(
            "INSERT INTO identity_state(organism_id, payload_json, degraded_mode, updated_at) VALUES (?, ?, ?, ?)",
            (ORGANISM_ID, canonical_json(identity), DegradedMode.DETERMINISTIC_ONLY.value, utc_now()),
        )
        self.append_event("IDENTITY_BOUND", ORGANISM_ID, {"binding": identity.get("binding")})

    def identity(self) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT payload_json, degraded_mode FROM identity_state WHERE organism_id = ?",
            (ORGANISM_ID,),
        ).fetchone()
        if not row:
            raise FailClosed("IDENTITY_MISSING")
        data = json.loads(row["payload_json"])
        data["degraded_mode"] = row["degraded_mode"]
        return data

    def set_mode(self, mode: DegradedMode) -> dict[str, Any]:
        ident = self.identity()
        self.conn.execute(
            "UPDATE identity_state SET degraded_mode = ?, updated_at = ? WHERE organism_id = ?",
            (mode.value, utc_now(), ORGANISM_ID),
        )
        after = self.identity()
        if after["organism_id"] != ident["organism_id"]:
            raise FailClosed("IDENTITY_MUTATED_ON_MODE_CHANGE")
        return after

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.conn.execute("BEGIN")
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def append_event(
        self,
        event_type: str,
        entity_id: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> str:
        if idempotency_key:
            hit = self.conn.execute(
                "SELECT event_id FROM audit_events WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if hit:
                return hit["event_id"]
        prev = self.conn.execute(
            "SELECT seq, event_hash FROM audit_events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prev_hash = prev["event_hash"] if prev else None
        seq = (prev["seq"] + 1) if prev else 1
        created = utc_now()
        payload_hash = sha256_obj(payload)
        event_id = deterministic_id("evt", event_type, entity_id, str(seq))
        body = {
            "event_id": event_id,
            "seq": seq,
            "event_type": event_type,
            "entity_id": entity_id,
            "idempotency_key": idempotency_key,
            "payload_hash": payload_hash,
            "created_at": created,
            "previous_hash": prev_hash,
        }
        event_hash = sha256_obj(body)
        self.conn.execute(
            """
            INSERT INTO audit_events(
                event_id, seq, event_type, entity_id, idempotency_key, payload_json,
                created_at, previous_hash, payload_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                seq,
                event_type,
                entity_id,
                idempotency_key,
                canonical_json(payload),
                created,
                prev_hash,
                payload_hash,
                event_hash,
            ),
        )
        return event_id

    def verify_event_chain(self) -> dict[str, Any]:
        rows = self.conn.execute(
            "SELECT event_id, seq, event_type, entity_id, idempotency_key, payload_json, "
            "created_at, previous_hash, payload_hash, event_hash FROM audit_events ORDER BY seq"
        ).fetchall()
        prev = None
        for row in rows:
            payload = json.loads(row["payload_json"])
            if sha256_obj(payload) != row["payload_hash"]:
                raise FailClosed(f"PAYLOAD_HASH_MISMATCH:{row['event_id']}")
            body = {
                "event_id": row["event_id"],
                "seq": row["seq"],
                "event_type": row["event_type"],
                "entity_id": row["entity_id"],
                "idempotency_key": row["idempotency_key"],
                "payload_hash": row["payload_hash"],
                "created_at": row["created_at"],
                "previous_hash": row["previous_hash"],
            }
            if sha256_obj(body) != row["event_hash"]:
                raise FailClosed(f"EVENT_HASH_MISMATCH:{row['event_id']}")
            if row["previous_hash"] != prev:
                raise FailClosed(f"EVENT_CHAIN_BREAK:{row['event_id']}")
            prev = row["event_hash"]
        return {"ok": True, "count": len(rows), "tip": prev}

    def put_bytes(self, data: bytes) -> str:
        digest, _ = self.cas.ingest(data)
        self.conn.execute(
            "INSERT OR IGNORE INTO objects(sha256, bytes, created_at) VALUES (?, ?, ?)",
            (digest, len(data), utc_now()),
        )
        return digest

    def integrity_check(self) -> str:
        result = self.conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise FailClosed(f"SQLITE_INTEGRITY_FAILED:{result}")
        return result
