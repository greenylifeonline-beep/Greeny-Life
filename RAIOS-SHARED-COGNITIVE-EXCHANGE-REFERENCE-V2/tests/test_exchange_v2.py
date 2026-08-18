from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cognitive_exchange import (  # noqa: E402
    CognitiveExchange,
    FailClosed,
    LeaseMode,
    PathSecurityError,
    Provenance,
    TaskState,
    TrustStatus,
    reject_unsafe_user_path,
)
from cognitive_exchange.identity import SCHEMA_VERSION, utc_now  # noqa: E402
from cognitive_exchange.paths import assert_contained, normalize_scope  # noqa: E402


def prov(*, source="LOCAL", trust=TrustStatus.UNTRUSTED) -> Provenance:
    now = utc_now()
    return Provenance(
        producer_id="producer-1",
        producer_type="TEST",
        source_type=source,
        generation_method="unit-test",
        observed_at=now,
        received_at=now,
        trust_state=trust,
        verification_state="UNVERIFIED",
    )


class ExchangeV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "exchange"
        self.ex = CognitiveExchange(self.root)

    def tearDown(self) -> None:
        self.ex.close()
        self.tmp.cleanup()

    def test_MODULE_IMPORT_PASS(self) -> None:
        import cognitive_exchange.cas as cas
        import cognitive_exchange.exchange as exchange
        import cognitive_exchange.identity as identity
        import cognitive_exchange.models as models
        import cognitive_exchange.paths as paths
        import cognitive_exchange.store as store
        import cognitive_exchange.transitions as transitions

        self.assertTrue(cas.ContentAddressedStore)
        self.assertTrue(exchange.CognitiveExchange)
        self.assertEqual(identity.SCHEMA_VERSION, SCHEMA_VERSION)
        self.assertTrue(models.TaskState)
        self.assertTrue(paths.normalize_scope)
        self.assertTrue(store.Store)
        self.assertTrue(transitions.TASK_TRANSITIONS)

    def test_DB_MIGRATION_PASS(self) -> None:
        self.assertEqual(self.ex.store.schema_version(), 1)
        self.assertEqual(self.ex.store.logical_schema_version(), SCHEMA_VERSION)
        enabled = self.ex.store.conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(int(enabled), 1)

    def test_OBJECT_ATOMIC_WRITE_PASS(self) -> None:
        digest, created = self.ex.cas.ingest(b"atomic-bytes")
        self.assertTrue(created)
        self.assertEqual(self.ex.cas.read(digest), b"atomic-bytes")
        self.assertFalse(list(self.ex.cas.tmp.glob("*.part")))

    def test_OBJECT_DUPLICATE_CONCURRENCY_PASS(self) -> None:
        payload = b"same-content-for-both-ingesters"
        results: list[str] = []
        errors: list[BaseException] = []
        barrier = threading.Barrier(2)

        def worker() -> None:
            local = CognitiveExchange(self.root)
            try:
                barrier.wait(timeout=5)
                obj = local.ingest_artifact(
                    payload,
                    idempotency_key=f"art:{threading.get_ident()}",
                    provenance=prov(trust=TrustStatus.UNTRUSTED),
                )
                results.append(obj["sha256"])
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                local.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        digest = results[0]
        files = [p for p in self.ex.cas.objects.rglob(digest) if p.is_file()]
        self.assertEqual(len(files), 1)

    def test_INTERRUPTED_OBJECT_RECOVERY_PASS(self) -> None:
        part = self.ex.cas.tmp / "dead.part"
        part.write_bytes(b"incomplete")
        report = self.ex.reconcile()
        self.assertGreaterEqual(report["interrupted_temp_removed"], 1)
        self.assertFalse(part.exists())

    def test_ORPHAN_RECONCILIATION_PASS(self) -> None:
        digest, _ = self.ex.cas.ingest(b"orphan-payload")
        report = self.ex.reconcile()
        self.assertIn(digest, report["orphans"])
        row = self.ex.store.fetchone("SELECT object_state FROM objects WHERE sha256 = ?", (digest,))
        self.assertEqual(row["object_state"], "ORPHAN")

    def test_METADATA_WITHOUT_OBJECT_DETECTED(self) -> None:
        obj = self.ex.ingest_artifact(b"to-delete", idempotency_key="meta-missing", provenance=prov())
        path = self.ex.cas.object_path(obj["sha256"])
        path.unlink()
        with self.assertRaises(FailClosed) as ctx:
            self.ex.read_artifact(obj["sha256"])
        self.assertEqual(str(ctx.exception), "METADATA_WITHOUT_OBJECT_DETECTED")

    def test_OBJECT_HASH_TAMPER_DETECTED(self) -> None:
        obj = self.ex.ingest_artifact(b"pure", idempotency_key="tamper", provenance=prov())
        path = self.ex.cas.object_path(obj["sha256"])
        path.write_bytes(b"tampered")
        with self.assertRaises(FailClosed) as ctx:
            self.ex.read_artifact(obj["sha256"])
        self.assertEqual(str(ctx.exception), "OBJECT_HASH_TAMPER_DETECTED")

    def test_PATH_TRAVERSAL_REJECTED(self) -> None:
        with self.assertRaises(PathSecurityError) as ctx:
            normalize_scope("../etc/passwd")
        self.assertEqual(str(ctx.exception), "PATH_TRAVERSAL_REJECTED")

    def test_WINDOWS_DRIVE_ESCAPE_REJECTED(self) -> None:
        with self.assertRaises(PathSecurityError) as ctx:
            reject_unsafe_user_path("C:\\Windows\\System32")
        self.assertEqual(str(ctx.exception), "WINDOWS_DRIVE_ESCAPE_REJECTED")

    def test_UNC_ESCAPE_REJECTED(self) -> None:
        with self.assertRaises(PathSecurityError) as ctx:
            reject_unsafe_user_path("\\\\server\\share\\secret")
        self.assertEqual(str(ctx.exception), "UNC_ESCAPE_REJECTED")

    def test_SYMLINK_OR_JUNCTION_ESCAPE_REJECTED(self) -> None:
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_bytes(b"secret")
        link = self.root / "escape-link"
        try:
            link.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlink unsupported: {exc}")
        with self.assertRaises(PathSecurityError) as ctx:
            assert_contained(self.root, "escape-link")
        self.assertEqual(str(ctx.exception), "SYMLINK_OR_JUNCTION_ESCAPE_REJECTED")

    def test_WINDOWS_CASE_COLLISION_HANDLED(self) -> None:
        self.assertEqual(normalize_scope("A/B/C"), normalize_scope("a/b/c"))
        task = self.ex.create_task(idempotency_key="case-task", title="case", scope="Work/Item")
        self.ex.issue_lease(task_id=task["task_id"], executor_id="w1", scope="Work/Item", mode=LeaseMode.WRITE)
        with self.assertRaises(FailClosed) as ctx:
            self.ex.issue_lease(task_id=task["task_id"], executor_id="w2", scope="work/item", mode=LeaseMode.WRITE)
        self.assertEqual(str(ctx.exception), "LEASE_OVERLAP_REJECTED")

    def test_TASK_ILLEGAL_TRANSITION_REJECTED(self) -> None:
        task = self.ex.create_task(idempotency_key="task-illegal", title="t", scope="alpha")
        with self.assertRaises(FailClosed) as ctx:
            self.ex.transition_task(task["task_id"], TaskState.COMPLETED)
        self.assertIn("TASK_ILLEGAL_TRANSITION", str(ctx.exception))

    def test_DUPLICATE_TASK_IDEMPOTENT(self) -> None:
        first = self.ex.create_task(idempotency_key="dup-task", title="one", scope="s")
        second = self.ex.create_task(idempotency_key="dup-task", title="one", scope="s")
        self.assertEqual(first["task_id"], second["task_id"])

    def test_RESULT_IDEMPOTENT(self) -> None:
        task = self.ex.create_task(idempotency_key="res-task", title="r", scope="s")
        first = self.ex.ingest_result(task_id=task["task_id"], idempotency_key="dup-result", status="ok", confidence=0.5)
        second = self.ex.ingest_result(task_id=task["task_id"], idempotency_key="dup-result", status="ok", confidence=0.5)
        self.assertEqual(first["result_id"], second["result_id"])

    def test_HANDOFF_IDEMPOTENT(self) -> None:
        task = self.ex.create_task(idempotency_key="ho-task", title="h", scope="s")
        first = self.ex.ingest_handoff(
            task_id=task["task_id"],
            idempotency_key="dup-handoff",
            from_executor="a",
            to_executor="b",
            reason="need review",
        )
        second = self.ex.ingest_handoff(
            task_id=task["task_id"],
            idempotency_key="dup-handoff",
            from_executor="a",
            to_executor="b",
            reason="need review",
        )
        self.assertEqual(first["handoff_id"], second["handoff_id"])

    def test_LEASE_OVERLAP_REJECTED(self) -> None:
        task = self.ex.create_task(idempotency_key="lease-overlap", title="l", scope="a/b")
        self.ex.issue_lease(task_id=task["task_id"], executor_id="w1", scope="a/b", mode=LeaseMode.WRITE)
        with self.assertRaises(FailClosed) as ctx:
            self.ex.issue_lease(task_id=task["task_id"], executor_id="w2", scope="a/b/c", mode=LeaseMode.WRITE)
        self.assertEqual(str(ctx.exception), "LEASE_OVERLAP_REJECTED")

    def test_LEASE_FENCING_PASS(self) -> None:
        task = self.ex.create_task(idempotency_key="fence-task", title="l", scope="fenced")
        lease = self.ex.issue_lease(task_id=task["task_id"], executor_id="w1", scope="fenced", mode=LeaseMode.WRITE)
        fenced = self.ex.fence_lease(lease["lease_id"])
        self.assertGreater(fenced["generation"], lease["generation"])
        with self.assertRaises(FailClosed) as ctx:
            self.ex.require_write(lease["lease_id"], lease["generation"], "w1")
        self.assertEqual(str(ctx.exception), "STALE_WORKER_REJECTED")

    def test_STALE_WORKER_REJECTED(self) -> None:
        task = self.ex.create_task(idempotency_key="stale-task", title="l", scope="stale")
        lease = self.ex.issue_lease(
            task_id=task["task_id"], executor_id="w1", scope="stale", mode=LeaseMode.WRITE, ttl_seconds=60
        )
        self.ex.store.conn.execute(
            "UPDATE leases SET expires_at = ? WHERE lease_id = ?",
            ("2000-01-01T00:00:00+00:00", lease["lease_id"]),
        )
        with self.assertRaises(FailClosed) as ctx:
            self.ex.require_write(lease["lease_id"], lease["generation"], "w1")
        self.assertEqual(str(ctx.exception), "STALE_WORKER_REJECTED")

    def test_READ_ONLY_VERIFIER_CONCURRENT_PASS(self) -> None:
        task = self.ex.create_task(idempotency_key="ro-task", title="l", scope="shared")
        writer = self.ex.issue_lease(task_id=task["task_id"], executor_id="w1", scope="shared", mode=LeaseMode.WRITE)
        verifier = self.ex.issue_lease(
            task_id=task["task_id"], executor_id="v1", scope="shared", mode=LeaseMode.READ_VERIFY
        )
        self.assertEqual(writer["mode"], "WRITE")
        self.assertEqual(verifier["mode"], "READ_VERIFY")

    def test_EVENT_APPEND_PASS(self) -> None:
        self.ex.create_task(idempotency_key="evt-task", title="e", scope="s")
        rows = self.ex.store.fetchall("SELECT * FROM collab_events ORDER BY sequence")
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0]["sequence"], 1)
        self.assertEqual(rows[0]["event_type"], "TASK_CREATED")

    def test_EVENT_CHAIN_INTEGRITY_PASS(self) -> None:
        self.ex.create_task(idempotency_key="chain-1", title="e", scope="s")
        self.ex.create_task(idempotency_key="chain-2", title="e", scope="s2")
        self.ex.verify_event_chain()

    def test_EVENT_CORRUPTION_DETECTED(self) -> None:
        self.ex.create_task(idempotency_key="corrupt-task", title="e", scope="s")
        last = self.ex.store.fetchone("SELECT sequence, event_hash FROM collab_events ORDER BY sequence DESC LIMIT 1")
        self.ex.store.conn.execute(
            """
            INSERT INTO collab_events(
                event_id, sequence, correlation_id, causation_id, event_type,
                payload_hash, previous_event_hash, event_hash, timestamp,
                idempotency_key, schema_version, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evt:corrupt",
                last["sequence"] + 1,
                "c",
                None,
                "TASK_CREATED",
                "deadbeef",
                last["event_hash"],
                "cafebabe",
                utc_now(),
                "idem-corrupt",
                SCHEMA_VERSION,
                '{"payload":{"x":1},"payload_hash":"deadbeef"}',
            ),
        )
        with self.assertRaises(FailClosed) as ctx:
            self.ex.verify_event_chain()
        self.assertEqual(str(ctx.exception), "EVENT_CORRUPTION_DETECTED")

    def test_REPLAY_PASS(self) -> None:
        t = self.ex.create_task(idempotency_key="replay-task", title="e", scope="s")
        self.ex.ingest_result(task_id=t["task_id"], idempotency_key="replay-res", status="ok", confidence=0.2)
        report = self.ex.replay()
        self.assertEqual(report["tasks"], 1)
        self.assertEqual(report["results"], 1)

    def test_REPLAY_IDEMPOTENCY_PASS(self) -> None:
        self.ex.create_task(idempotency_key="replay-idemp", title="e", scope="s")
        first = self.ex.replay()
        second = self.ex.replay()
        self.assertEqual(first["tasks"], second["tasks"])
        self.assertEqual(first["events"], second["events"])

    def test_CRASH_REPLAY_PASS(self) -> None:
        t = self.ex.create_task(idempotency_key="crash-task", title="e", scope="s")
        self.ex.ingest_handoff(
            task_id=t["task_id"],
            idempotency_key="crash-ho",
            from_executor="a",
            to_executor="b",
            reason="crash",
        )
        dest_root = Path(self.tmp.name) / "replay-dest"
        dest = CognitiveExchange(dest_root)
        self.ex.copy_events_to(dest)
        report = dest.replay()
        dest.close()
        self.assertEqual(report["tasks"], 1)
        self.assertEqual(report["handoffs"], 1)

    def test_QUARANTINE_ISOLATION_PASS(self) -> None:
        trusted = self.ex.ingest_artifact(
            b"trusted-doc secrettoken",
            idempotency_key="q-trust",
            provenance=prov(trust=TrustStatus.TRUSTED),
            index_text="trusted-doc secrettoken",
            trust_status=TrustStatus.TRUSTED,
        )
        hits = self.ex.search("secrettoken")
        self.assertEqual(len(hits), 1)
        self.ex.quarantine_object(
            trusted["sha256"],
            reason="policy",
            source="test",
            validation_failures=["schema"],
        )
        self.assertEqual(self.ex.search("secrettoken"), [])
        with self.assertRaises(FailClosed):
            self.ex.read_artifact(trusted["sha256"])

    def test_FTS_TRUST_FILTER_PASS(self) -> None:
        self.ex.ingest_artifact(
            b"untrusted leak candidate",
            idempotency_key="fts-untrusted",
            provenance=prov(source="EXTERNAL_MODEL", trust=TrustStatus.UNTRUSTED),
            index_text="untrusted leak candidate",
        )
        self.assertEqual(self.ex.search("leak"), [])
        self.ex.ingest_artifact(
            b"trusted visible candidate",
            idempotency_key="fts-trusted",
            provenance=prov(trust=TrustStatus.TRUSTED),
            index_text="trusted visible candidate",
            trust_status=TrustStatus.TRUSTED,
        )
        hits = self.ex.search("visible")
        self.assertEqual(len(hits), 1)
        self.assertTrue(hits[0]["retrieval_only"])

    def test_CONTEXT_CAPSULE_CANONICAL_HASH_PASS(self) -> None:
        obj = self.ex.ingest_artifact(b"cap", idempotency_key="cap-art", provenance=prov())
        ref = f"artifact://sha256/{obj['sha256']}"
        a = self.ex.create_capsule(task_id="task://t", refs=[ref], purpose="ctx")
        b = self.ex.create_capsule(task_id="task://t", refs=[ref], purpose="ctx")
        self.assertEqual(a.capsule_id, b.capsule_id)
        self.assertTrue(a.capsule_id.startswith("capsule:"))

    def test_RESTART_PERSISTENCE_PASS(self) -> None:
        task = self.ex.create_task(idempotency_key="persist-task", title="p", scope="p")
        obj = self.ex.ingest_artifact(b"persist-bytes", idempotency_key="persist-art", provenance=prov())
        self.ex.close()
        restarted = CognitiveExchange(self.root)
        row = restarted.store.fetchone("SELECT task_id FROM tasks WHERE task_id = ?", (task["task_id"],))
        self.assertIsNotNone(row)
        self.assertEqual(restarted.read_artifact(obj["sha256"]), b"persist-bytes")
        restarted.verify_event_chain()
        restarted.close()
        self.ex = CognitiveExchange(self.root)

    def test_UNKNOWN_EVENT_VERSION_REJECTED(self) -> None:
        self.ex.create_task(idempotency_key="ver-task", title="e", scope="s")
        last = self.ex.store.fetchone("SELECT sequence, event_hash FROM collab_events ORDER BY sequence DESC LIMIT 1")
        self.ex.store.conn.execute(
            """
            INSERT INTO collab_events(
                event_id, sequence, correlation_id, causation_id, event_type,
                payload_hash, previous_event_hash, event_hash, timestamp,
                idempotency_key, schema_version, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evt:badver",
                last["sequence"] + 1,
                "c",
                None,
                "TASK_CREATED",
                "00" * 32,
                last["event_hash"],
                "11" * 32,
                utc_now(),
                "idem-badver",
                "cognitive-exchange.v99",
                '{"payload":{}}',
            ),
        )
        with self.assertRaises(FailClosed) as ctx:
            self.ex.verify_event_chain()
        self.assertIn("INCOMPATIBLE_SCHEMA_MAJOR", str(ctx.exception))

    def test_OUT_OF_ORDER_EVENT_REJECTED(self) -> None:
        self.ex.create_task(idempotency_key="ooo-task", title="e", scope="s")
        last = self.ex.store.fetchone("SELECT sequence, event_hash FROM collab_events ORDER BY sequence DESC LIMIT 1")
        self.ex.store.conn.execute(
            """
            INSERT INTO collab_events(
                event_id, sequence, correlation_id, causation_id, event_type,
                payload_hash, previous_event_hash, event_hash, timestamp,
                idempotency_key, schema_version, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evt:ooo",
                last["sequence"] + 2,
                "c",
                None,
                "TASK_CREATED",
                "22" * 32,
                last["event_hash"],
                "33" * 32,
                utc_now(),
                "idem-ooo",
                SCHEMA_VERSION,
                '{"payload":{}}',
            ),
        )
        with self.assertRaises(FailClosed) as ctx:
            self.ex.verify_event_chain()
        self.assertEqual(str(ctx.exception), "EVENT_OUT_OF_ORDER")

    def test_EXTERNAL_MODEL_UNTRUSTED_DEFAULT(self) -> None:
        with self.assertRaises(FailClosed):
            self.ex.ingest_artifact(
                b"llm",
                idempotency_key="ext-bad",
                provenance=prov(source="EXTERNAL_MODEL", trust=TrustStatus.TRUSTED),
            )

    def test_NO_AUTO_DELETE(self) -> None:
        obj = self.ex.ingest_artifact(b"keep", idempotency_key="keep", provenance=prov())
        with self.assertRaises(sqlite3.IntegrityError):
            self.ex.store.conn.execute("DELETE FROM objects WHERE sha256 = ?", (obj["sha256"],))


if __name__ == "__main__":
    unittest.main()
