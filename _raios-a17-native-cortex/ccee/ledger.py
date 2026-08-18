"""SQLite metadata ledger. Raw blobs stay on the filesystem."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import FailClosed, assert_not_v9, canonical_json, utc_now

DDL = """
CREATE TABLE IF NOT EXISTS episodes (
    episode_id TEXT PRIMARY KEY,
    content_sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS missions (
    mission_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    score REAL NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS strategies (
    strategy_id TEXT PRIMARY KEY,
    teacher TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge (
    knowledge_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
    ts TEXT NOT NULL,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    wal_offset INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class Ledger:
    def __init__(self, root: str | Path, repo_root: Path | None = None) -> None:
        self.root = Path(root)
        assert_not_v9(self.root, repo_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.root / "ccee.ledger.sqlite"), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.isolation_level = None
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(DDL)

    def close(self) -> None:
        self.conn.close()

    def put(self, table: str, key_col: str, key: str, payload: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
        allowed = {"episodes": "episode_id", "missions": "mission_id", "skills": "skill_id", "strategies": "strategy_id", "knowledge": "knowledge_id", "checkpoints": "checkpoint_id"}
        if table not in allowed:
            raise FailClosed(f"UNKNOWN_LEDGER_TABLE:{table}")
        cols = extra or {}
        payload_json = canonical_json(payload)
        now = utc_now()
        if table == "episodes":
            self.conn.execute(
                "INSERT OR REPLACE INTO episodes(episode_id, content_sha256, payload_json, created_at) VALUES (?,?,?,?)",
                (key, cols.get("content_sha256", ""), payload_json, now),
            )
        elif table == "missions":
            self.conn.execute(
                "INSERT OR REPLACE INTO missions(mission_id, state, score, payload_json, updated_at) VALUES (?,?,?,?,?)",
                (key, cols.get("state", "DISCOVERED"), float(cols.get("score") or 0), payload_json, now),
            )
        elif table == "skills":
            self.conn.execute(
                "INSERT OR REPLACE INTO skills(skill_id, kind, payload_json, updated_at) VALUES (?,?,?,?)",
                (key, cols.get("kind", "MICRO_SKILL"), payload_json, now),
            )
        elif table == "strategies":
            self.conn.execute(
                "INSERT OR REPLACE INTO strategies(strategy_id, teacher, payload_json, updated_at) VALUES (?,?,?,?)",
                (key, cols.get("teacher", "unknown"), payload_json, now),
            )
        elif table == "knowledge":
            self.conn.execute(
                "INSERT OR REPLACE INTO knowledge(knowledge_id, state, kind, payload_json, updated_at) VALUES (?,?,?,?,?)",
                (key, cols.get("state", "DISCOVERED"), cols.get("kind", "observation"), payload_json, now),
            )
        else:
            self.conn.execute(
                "INSERT OR REPLACE INTO checkpoints(checkpoint_id, wal_offset, payload_json, created_at) VALUES (?,?,?,?)",
                (key, int(cols.get("wal_offset") or 0), payload_json, now),
            )

    def get(self, table: str, key: str) -> dict[str, Any] | None:
        col = {"episodes": "episode_id", "missions": "mission_id", "skills": "skill_id", "strategies": "strategy_id", "knowledge": "knowledge_id", "checkpoints": "checkpoint_id"}[table]
        row = self.conn.execute(f"SELECT payload_json FROM {table} WHERE {col} = ?", (key,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list(self, table: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(f"SELECT payload_json FROM {table}").fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def add_metric(self, name: str, value: float, payload: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            "INSERT INTO metrics(ts, name, value, payload_json) VALUES (?,?,?,?)",
            (utc_now(), name, float(value), canonical_json(payload or {})),
        )
