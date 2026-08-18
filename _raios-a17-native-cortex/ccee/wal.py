"""Append-only crash-safe Cognitive WAL. Hash-chained, idempotent, replayable."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

from .config import FailClosed, assert_not_v9, canonical_json, deterministic_id, sha256_obj, sha256_text, utc_now
from .schemas import EVENT_TYPES, CognitiveEvent, payload_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS wal_events (
    seq INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    timestamp TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    risk_class TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    parent_event_ids TEXT NOT NULL,
    causal_parent_ids TEXT NOT NULL,
    knowledge_state TEXT NOT NULL,
    confidence REAL NOT NULL,
    novelty REAL NOT NULL,
    contradiction_score REAL NOT NULL,
    utility_estimate REAL NOT NULL,
    cost_estimate REAL NOT NULL,
    canonical INTEGER NOT NULL DEFAULT 0 CHECK (canonical = 0),
    previous_hash TEXT,
    event_hash TEXT NOT NULL UNIQUE,
    idempotency_key TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_wal_idem ON wal_events(idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_wal_dedup ON wal_events(event_type, source, payload_hash);
CREATE TRIGGER IF NOT EXISTS wal_no_update BEFORE UPDATE ON wal_events
BEGIN SELECT RAISE(ABORT, 'WAL_EVENTS_ARE_APPEND_ONLY'); END;
CREATE TRIGGER IF NOT EXISTS wal_no_delete BEFORE DELETE ON wal_events
BEGIN SELECT RAISE(ABORT, 'WAL_EVENTS_ARE_APPEND_ONLY'); END;
"""


def _fsync_path(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class CognitiveWAL:
    def __init__(self, root: str | Path, run_id: str | None = None, repo_root: Path | None = None) -> None:
        self.root = Path(root)
        assert_not_v9(self.root, repo_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "cognitive.wal.sqlite"
        self.jsonl_path = self.root / "cognitive.wal.jsonl"
        self.run_id = run_id or deterministic_id("run", utc_now())
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.isolation_level = None
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.executescript(SCHEMA)
        self._recover_jsonl()

    def close(self) -> None:
        self.conn.close()

    def append(self, event_type: str, source: str, payload: dict[str, Any], **kwargs: Any) -> CognitiveEvent:
        if event_type not in EVENT_TYPES:
            raise FailClosed(f"UNKNOWN_EVENT_TYPE:{event_type}")
        body = dict(payload)
        p_hash = payload_hash(body)
        idem = kwargs.get("idempotency_key") or deterministic_id("idm", event_type, source, p_hash)
        with self._lock:
            existing = self.conn.execute(
                "SELECT event_id FROM wal_events WHERE idempotency_key = ? OR (event_type = ? AND source = ? AND payload_hash = ?)",
                (idem, event_type, source, p_hash),
            ).fetchone()
            if existing:
                return self.get(existing["event_id"])
            prev = self.conn.execute("SELECT seq, event_hash FROM wal_events ORDER BY seq DESC LIMIT 1").fetchone()
            seq = (prev["seq"] + 1) if prev else 1
            previous_hash = prev["event_hash"] if prev else None
            event_id = deterministic_id("evt", event_type, source, str(seq), p_hash)
            event = CognitiveEvent(
                event_id=event_id,
                timestamp=utc_now(),
                monotonic_sequence=seq,
                run_id=self.run_id,
                source=source,
                event_type=event_type,
                risk_class=str(kwargs.get("risk_class") or "LOW"),
                payload_hash=p_hash,
                payload=body,
                parent_event_ids=list(kwargs.get("parent_event_ids") or []),
                causal_parent_ids=list(kwargs.get("causal_parent_ids") or []),
                knowledge_state=kwargs.get("knowledge_state") or "DISCOVERED",
                confidence=float(kwargs.get("confidence") or 0.0),
                novelty=float(kwargs.get("novelty") or 0.0),
                contradiction_score=float(kwargs.get("contradiction_score") or 0.0),
                utility_estimate=float(kwargs.get("utility_estimate") or 0.0),
                cost_estimate=float(kwargs.get("cost_estimate") or 0.0),
                canonical=False,
                previous_hash=previous_hash,
                event_hash="",
                idempotency_key=idem,
            )
            chain = {
                "event_id": event.event_id,
                "seq": event.monotonic_sequence,
                "event_type": event.event_type,
                "payload_hash": event.payload_hash,
                "previous_hash": event.previous_hash,
                "timestamp": event.timestamp,
            }
            event.event_hash = sha256_obj(chain)
            self._durable_write(event)
            return event

    def _durable_write(self, event: CognitiveEvent) -> None:
        dumped = event.model_dump()
        line = canonical_json(dumped) + "\n"
        tmp = self.jsonl_path.with_suffix(".jsonl.part")
        existing = self.jsonl_path.read_bytes() if self.jsonl_path.exists() else b""
        payload = existing + line.encode("utf-8")
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, self.jsonl_path)
        _fsync_path(self.jsonl_path.parent)
        self.conn.execute("BEGIN")
        try:
            self.conn.execute(
                """
                INSERT INTO wal_events(
                    seq, event_id, timestamp, run_id, source, event_type, risk_class,
                    payload_hash, payload_json, parent_event_ids, causal_parent_ids,
                    knowledge_state, confidence, novelty, contradiction_score,
                    utility_estimate, cost_estimate, canonical, previous_hash, event_hash, idempotency_key
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?)
                """,
                (
                    event.monotonic_sequence,
                    event.event_id,
                    event.timestamp,
                    event.run_id,
                    event.source,
                    event.event_type,
                    event.risk_class,
                    event.payload_hash,
                    canonical_json(event.payload),
                    canonical_json(event.parent_event_ids),
                    canonical_json(event.causal_parent_ids),
                    event.knowledge_state,
                    event.confidence,
                    event.novelty,
                    event.contradiction_score,
                    event.utility_estimate,
                    event.cost_estimate,
                    event.previous_hash,
                    event.event_hash,
                    event.idempotency_key,
                ),
            )
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def _recover_jsonl(self) -> None:
        if not self.jsonl_path.exists():
            return
        sqlite_ids = {r["event_id"] for r in self.conn.execute("SELECT event_id FROM wal_events")}
        for raw in self.jsonl_path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            data = json.loads(raw)
            if data["event_id"] in sqlite_ids:
                continue
            event = CognitiveEvent.model_validate(data)
            self.conn.execute("BEGIN")
            try:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO wal_events(
                        seq, event_id, timestamp, run_id, source, event_type, risk_class,
                        payload_hash, payload_json, parent_event_ids, causal_parent_ids,
                        knowledge_state, confidence, novelty, contradiction_score,
                        utility_estimate, cost_estimate, canonical, previous_hash, event_hash, idempotency_key
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?)
                    """,
                    (
                        event.monotonic_sequence,
                        event.event_id,
                        event.timestamp,
                        event.run_id,
                        event.source,
                        event.event_type,
                        event.risk_class,
                        event.payload_hash,
                        canonical_json(event.payload),
                        canonical_json(event.parent_event_ids),
                        canonical_json(event.causal_parent_ids),
                        event.knowledge_state,
                        event.confidence,
                        event.novelty,
                        event.contradiction_score,
                        event.utility_estimate,
                        event.cost_estimate,
                        event.previous_hash,
                        event.event_hash,
                        event.idempotency_key,
                    ),
                )
                self.conn.execute("COMMIT")
                sqlite_ids.add(event.event_id)
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def get(self, event_id: str) -> CognitiveEvent:
        row = self.conn.execute("SELECT * FROM wal_events WHERE event_id = ?", (event_id,)).fetchone()
        if not row:
            raise FailClosed("WAL_EVENT_UNKNOWN")
        return self._row_event(row)

    def replay(self) -> Iterable[CognitiveEvent]:
        rows = self.conn.execute("SELECT * FROM wal_events ORDER BY seq").fetchall()
        for row in rows:
            yield self._row_event(row)

    def verify_chain(self) -> dict[str, Any]:
        prev = None
        count = 0
        tip = None
        for event in self.replay():
            if sha256_obj(event.payload) != event.payload_hash:
                raise FailClosed(f"PAYLOAD_HASH_MISMATCH:{event.event_id}")
            chain = {
                "event_id": event.event_id,
                "seq": event.monotonic_sequence,
                "event_type": event.event_type,
                "payload_hash": event.payload_hash,
                "previous_hash": event.previous_hash,
                "timestamp": event.timestamp,
            }
            if sha256_obj(chain) != event.event_hash:
                raise FailClosed(f"EVENT_HASH_MISMATCH:{event.event_id}")
            if event.previous_hash != prev:
                raise FailClosed(f"EVENT_CHAIN_BREAK:{event.event_id}")
            prev = event.event_hash
            tip = prev
            count += 1
        return {"ok": True, "count": count, "tip": tip}

    def offset(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(seq), 0) AS n FROM wal_events").fetchone()
        return int(row["n"])

    def _row_event(self, row: sqlite3.Row) -> CognitiveEvent:
        return CognitiveEvent(
            event_id=row["event_id"],
            timestamp=row["timestamp"],
            monotonic_sequence=row["seq"],
            run_id=row["run_id"],
            source=row["source"],
            event_type=row["event_type"],
            risk_class=row["risk_class"],
            payload_hash=row["payload_hash"],
            payload=json.loads(row["payload_json"]),
            parent_event_ids=json.loads(row["parent_event_ids"]),
            causal_parent_ids=json.loads(row["causal_parent_ids"]),
            knowledge_state=row["knowledge_state"],
            confidence=row["confidence"],
            novelty=row["novelty"],
            contradiction_score=row["contradiction_score"],
            utility_estimate=row["utility_estimate"],
            cost_estimate=row["cost_estimate"],
            canonical=False,
            previous_hash=row["previous_hash"],
            event_hash=row["event_hash"],
            idempotency_key=row["idempotency_key"],
        )
