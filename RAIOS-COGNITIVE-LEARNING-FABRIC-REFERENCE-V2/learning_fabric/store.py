from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .identity import SCHEMA_VERSION, canonical_json, new_id, sha256_obj, utc_now
from .models import EventType, FailClosed

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

ALLOWED_TABLES = {
    "debts": "debt_id",
    "knowledge_objects": "knowledge_id",
    "competency_nodes": "capability_id",
    "competency_proposals": "proposal_id",
    "teacher_dependencies": "capability_id",
    "training_candidates": "candidate_id",
    "harvest_items": "harvest_id",
    "compression_nodes": "node_id",
    "traces": "trace_id",
}


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        # Explicit transactions only. No hidden autocommit of DML.
        self.conn.isolation_level = None
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.migrate()

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.conn.execute("BEGIN")
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def migrate(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        current = self.conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_meta").fetchone()[0]
        files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for file in files:
            version = int(file.name.split("_", 1)[0])
            if version <= current:
                continue
            sql = file.read_text(encoding="utf-8")
            # executescript issues its own COMMIT; apply meta insert immediately after.
            self.conn.executescript(sql)
            self.conn.execute(
                "INSERT INTO schema_meta(version, applied_at) VALUES (?, ?)",
                (version, utc_now()),
            )

    def schema_version(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_meta").fetchone()
        return int(row[0])

    def logical_schema_version(self) -> str:
        return SCHEMA_VERSION

    def append_event(self, event_type: EventType, entity_id: str, payload: dict[str, Any]) -> str:
        prev = self.conn.execute(
            "SELECT event_sha256 FROM audit_events ORDER BY created_at DESC, event_id DESC LIMIT 1"
        ).fetchone()
        prev_hash = prev["event_sha256"] if prev else None
        event_id = new_id("evt")
        created = utc_now()
        body = {
            "event_id": event_id,
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
                event_id, event_type, entity_id, payload_json, created_at, prev_event_sha256, event_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event_type.value,
                entity_id,
                canonical_json(payload),
                created,
                prev_hash,
                digest,
            ),
        )
        return event_id

    def insert_trace(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.conn.execute(
            "SELECT payload_json, content_sha256 FROM traces WHERE idempotency_key = ?",
            (payload["idempotency_key"],),
        ).fetchone()
        if existing:
            if existing["content_sha256"] != payload["content_sha256"]:
                raise FailClosed("IDEMPOTENCY_KEY_PAYLOAD_CONFLICT")
            return json.loads(existing["payload_json"])
        self.conn.execute(
            """
            INSERT INTO traces(
                trace_id, task_id, result_id, idempotency_key, schema_version,
                content_sha256, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["trace_id"],
                payload["task_id"],
                payload["result_id"],
                payload["idempotency_key"],
                payload["schema_version"],
                payload["content_sha256"],
                canonical_json(payload),
                payload["created_at"],
            ),
        )
        return payload

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM traces WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

    def get_trace_by_idempotency(self, idempotency_key: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM traces WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

    def list_events(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT event_id, event_type, entity_id, payload_json, created_at, prev_event_sha256, event_sha256 "
            "FROM audit_events ORDER BY created_at ASC, event_id ASC"
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            out.append(item)
        return out

    def fetch_one(self, table: str, key_col: str, key: str) -> dict[str, Any] | None:
        if table not in ALLOWED_TABLES or ALLOWED_TABLES[table] != key_col:
            raise FailClosed("UNSAFE_TABLE_ACCESS")
        row = self.conn.execute(
            f"SELECT payload_json FROM {table} WHERE {key_col} = ?",
            (key,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])
