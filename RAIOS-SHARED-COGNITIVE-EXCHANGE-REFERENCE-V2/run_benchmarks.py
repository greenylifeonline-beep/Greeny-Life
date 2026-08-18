#!/usr/bin/env python3
"""Measured load tests for the Cognitive Exchange reference package."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from cognitive_exchange import CognitiveExchange, Provenance, TrustStatus
from cognitive_exchange.identity import utc_now


def _timed(fn):
    start = time.perf_counter()
    fn()
    return round(time.perf_counter() - start, 4)


def run_benchmarks() -> dict:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name) / "bench"
    ex = CognitiveExchange(root)
    now = utc_now()

    def tasks_10k() -> None:
        with ex.store.transaction():
            ex.store.conn.executemany(
                "INSERT INTO tasks(task_id, idempotency_key, state, schema_version, payload_json, created_at, updated_at) "
                "VALUES (?, ?, 'CREATED', 'cognitive-exchange.v2', '{}', ?, ?)",
                ((f"task:bench:{i}", f"idem:task:{i}", now, now) for i in range(10_000)),
            )

    def metadata_100k_safe() -> None:
        ex.store.conn.execute(
            "CREATE TABLE IF NOT EXISTS bench_meta (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
        )
        with ex.store.transaction():
            ex.store.conn.executemany(
                "INSERT INTO bench_meta(payload) VALUES (?)",
                ((f"row-{i}",) for i in range(100_000)),
            )

    artifacts = {"created": 0}

    def artifacts_10k() -> None:
        for i in range(10_000):
            digest, created = ex.cas.ingest(f"artifact-payload-{i}".encode())
            artifacts["created"] += int(created)
            assert digest

    def dedup() -> None:
        payload = b"dedup-heavy"
        first, created1 = ex.cas.ingest(payload)
        second, created2 = ex.cas.ingest(payload)
        assert first == second
        assert created1 and not created2

    def fts() -> None:
        body = "benchmark searchable trusted document alpha"
        trusted = Provenance(
            producer_id="bench",
            producer_type="BENCH",
            source_type="LOCAL",
            generation_method="benchmark",
            observed_at=utc_now(),
            received_at=utc_now(),
            trust_state=TrustStatus.TRUSTED,
        )
        ex.ingest_artifact(
            body.encode(),
            idempotency_key="bench-fts",
            provenance=trusted,
            index_text=body,
            trust_status=TrustStatus.TRUSTED,
        )
        hits = ex.search("alpha")
        assert hits

    def replay() -> None:
        for i in range(50):
            ex.create_task(idempotency_key=f"bench-replay-{i}", title="b", scope=f"b{i}")
        ex.verify_event_chain()
        ex.replay()

    results = {
        "tasks_10k_seconds": _timed(tasks_10k),
        "metadata_100k_seconds": _timed(metadata_100k_safe),
        "artifacts_10k_seconds": _timed(artifacts_10k),
        "artifacts_10k_created": artifacts["created"],
        "dedup_seconds": _timed(dedup),
        "fts_seconds": _timed(fts),
        "event_replay_seconds": _timed(replay),
    }
    ex.close()
    tmp.cleanup()
    return results


if __name__ == "__main__":
    print(json.dumps(run_benchmarks(), indent=2))
