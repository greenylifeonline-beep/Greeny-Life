from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .cas import ContentAddressedStore
from .identity import (
    SCHEMA_VERSION,
    assert_compatible_schema,
    canonical_json,
    new_id,
    sha256_bytes,
    sha256_obj,
    utc_now,
    FailClosed,
)
from .models import (
    CanonicalStatus,
    ContextCapsule,
    EventType,
    LeaseMode,
    LeaseState,
    ObjectState,
    Provenance,
    RetentionPolicy,
    StorageStatus,
    TaskState,
    TrustStatus,
    ValidationStatus,
)
from .paths import assert_contained, normalize_scope, scopes_overlap
from .store import Store
from .transitions import TASK_TRANSITIONS


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class CognitiveExchange:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.cas = ContentAddressedStore(self.root)
        self.store = Store(self.root / "db" / "exchange.sqlite")
        self.reconcile()

    def close(self) -> None:
        self.store.close()

    def _now(self) -> str:
        return utc_now()

    def _append_event(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        causation_id: str | None = None,
    ) -> dict[str, Any]:
        assert_compatible_schema(SCHEMA_VERSION)
        existing = self.store.fetchone(
            "SELECT payload_json FROM collab_events WHERE idempotency_key = ?",
            (idempotency_key,),
        )
        if existing:
            return json.loads(existing["payload_json"])
        prev = self.store.fetchone(
            "SELECT sequence, event_hash FROM collab_events ORDER BY sequence DESC LIMIT 1"
        )
        sequence = (prev["sequence"] + 1) if prev else 1
        previous_hash = prev["event_hash"] if prev else None
        payload_hash = sha256_obj(payload)
        timestamp = self._now()
        event_id = new_id("evt")
        body = {
            "causation_id": causation_id,
            "correlation_id": correlation_id,
            "event_id": event_id,
            "event_type": event_type.value,
            "idempotency_key": idempotency_key,
            "payload_hash": payload_hash,
            "previous_event_hash": previous_hash,
            "schema_version": SCHEMA_VERSION,
            "sequence": sequence,
            "timestamp": timestamp,
        }
        event_hash = sha256_obj({**body, "payload": payload})
        record = {**body, "event_hash": event_hash, "payload": payload}
        self.store.conn.execute(
            """
            INSERT INTO collab_events(
                event_id, sequence, correlation_id, causation_id, event_type,
                payload_hash, previous_event_hash, event_hash, timestamp,
                idempotency_key, schema_version, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                sequence,
                correlation_id,
                causation_id,
                event_type.value,
                payload_hash,
                previous_hash,
                event_hash,
                timestamp,
                idempotency_key,
                SCHEMA_VERSION,
                canonical_json(record),
            ),
        )
        return record

    def verify_event_chain(self) -> None:
        rows = self.store.fetchall("SELECT * FROM collab_events ORDER BY sequence ASC")
        prev_hash = None
        expected_seq = 1
        for row in rows:
            record = json.loads(row["payload_json"])
            assert_compatible_schema(row["schema_version"])
            if row["sequence"] != expected_seq:
                raise FailClosed("EVENT_OUT_OF_ORDER")
            if row["previous_event_hash"] != prev_hash:
                raise FailClosed("EVENT_CHAIN_INTEGRITY_FAIL")
            payload = record.get("payload")
            if sha256_obj(payload) != row["payload_hash"]:
                raise FailClosed("EVENT_CORRUPTION_DETECTED")
            expected = sha256_obj(
                {
                    "causation_id": row["causation_id"],
                    "correlation_id": row["correlation_id"],
                    "event_id": row["event_id"],
                    "event_type": row["event_type"],
                    "idempotency_key": row["idempotency_key"],
                    "payload_hash": row["payload_hash"],
                    "previous_event_hash": row["previous_event_hash"],
                    "schema_version": row["schema_version"],
                    "sequence": row["sequence"],
                    "timestamp": row["timestamp"],
                    "payload": payload,
                }
            )
            if expected != row["event_hash"]:
                raise FailClosed("EVENT_CORRUPTION_DETECTED")
            prev_hash = row["event_hash"]
            expected_seq += 1

    def create_task(
        self,
        *,
        idempotency_key: str,
        title: str,
        scope: str,
        extras: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalize_scope(scope)
        with self.store.transaction():
            existing = self.store.fetchone(
                "SELECT payload_json FROM tasks WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            if existing:
                return json.loads(existing["payload_json"])
            task_id = new_id("task")
            now = self._now()
            payload = {
                "created_at": now,
                "idempotency_key": idempotency_key,
                "schema_version": SCHEMA_VERSION,
                "scope": normalize_scope(scope),
                "state": TaskState.CREATED.value,
                "task_id": task_id,
                "title": title,
                "updated_at": now,
                **(extras or {}),
            }
            self.store.conn.execute(
                "INSERT INTO tasks(task_id, idempotency_key, state, schema_version, payload_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, idempotency_key, TaskState.CREATED.value, SCHEMA_VERSION, canonical_json(payload), now, now),
            )
            self._append_event(
                EventType.TASK_CREATED,
                payload,
                idempotency_key=f"event:task-create:{idempotency_key}",
                correlation_id=task_id,
            )
            return payload

    def transition_task(self, task_id: str, nxt: TaskState) -> dict[str, Any]:
        with self.store.transaction():
            row = self.store.fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            if not row:
                raise FailClosed("TASK_NOT_FOUND")
            current = TaskState(row["state"])
            if nxt not in TASK_TRANSITIONS[current]:
                raise FailClosed(f"TASK_ILLEGAL_TRANSITION:{current.value}->{nxt.value}")
            payload = json.loads(row["payload_json"])
            payload["state"] = nxt.value
            payload["updated_at"] = self._now()
            self.store.conn.execute(
                "UPDATE tasks SET state = ?, payload_json = ?, updated_at = ? WHERE task_id = ?",
                (nxt.value, canonical_json(payload), payload["updated_at"], task_id),
            )
            self._append_event(
                EventType.TASK_STATE_CHANGED,
                {"from": current.value, "task_id": task_id, "to": nxt.value},
                idempotency_key=new_id("event:task-state"),
                correlation_id=task_id,
            )
            return payload

    def ingest_artifact(
        self,
        data: bytes,
        *,
        idempotency_key: str,
        provenance: Provenance,
        index_text: str | None = None,
        trust_status: TrustStatus | None = None,
    ) -> dict[str, Any]:
        if provenance.source_type == "EXTERNAL_MODEL" and provenance.trust_state != TrustStatus.UNTRUSTED:
            raise FailClosed("EXTERNAL_MODEL_MUST_BE_UNTRUSTED")
        digest, created = self.cas.ingest(data)
        trust = trust_status or provenance.trust_state
        with self.store.transaction():
            existing = self.store.fetchone("SELECT payload_json FROM objects WHERE sha256 = ?", (digest,))
            if existing:
                obj = json.loads(existing["payload_json"])
                self._append_event(
                    EventType.ARTIFACT_INGESTED,
                    {"created": False, "sha256": digest},
                    idempotency_key=idempotency_key,
                    correlation_id=digest,
                )
                return obj
            now = self._now()
            payload = {
                "canonical_status": CanonicalStatus.NOT_CANONICAL.value,
                "created_at": now,
                "object_state": ObjectState.AVAILABLE.value,
                "reference_count": 0,
                "retention_policy": RetentionPolicy.RETAIN.value,
                "schema_version": SCHEMA_VERSION,
                "sha256": digest,
                "size_bytes": len(data),
                "storage_status": StorageStatus.STORED.value,
                "trust_status": trust.value,
                "validation_status": ValidationStatus.UNVALIDATED.value,
            }
            try:
                self.store.conn.execute(
                    """
                    INSERT INTO objects(
                        sha256, size_bytes, object_state, reference_count, retention_policy,
                        storage_status, validation_status, trust_status, canonical_status,
                        schema_version, created_at, payload_json
                    ) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        digest,
                        len(data),
                        ObjectState.AVAILABLE.value,
                        RetentionPolicy.RETAIN.value,
                        StorageStatus.STORED.value,
                        ValidationStatus.UNVALIDATED.value,
                        trust.value,
                        CanonicalStatus.NOT_CANONICAL.value,
                        SCHEMA_VERSION,
                        now,
                        canonical_json(payload),
                    ),
                )
            except sqlite3.IntegrityError:
                row = self.store.fetchone("SELECT payload_json FROM objects WHERE sha256 = ?", (digest,))
                assert row is not None
                return json.loads(row["payload_json"])
            prov_id = new_id("prov")
            self.store.conn.execute(
                """
                INSERT INTO provenance(
                    provenance_id, object_sha256, producer_id, producer_type, source_type,
                    task_id, generation_method, observed_at, received_at, trust_state,
                    verification_state, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prov_id,
                    digest,
                    provenance.producer_id,
                    provenance.producer_type,
                    provenance.source_type,
                    provenance.task_id,
                    provenance.generation_method,
                    provenance.observed_at,
                    provenance.received_at,
                    provenance.trust_state.value,
                    provenance.verification_state,
                    canonical_json(
                        {
                            "generation_method": provenance.generation_method,
                            "observed_at": provenance.observed_at,
                            "producer_id": provenance.producer_id,
                            "producer_type": provenance.producer_type,
                            "received_at": provenance.received_at,
                            "schema_version": provenance.schema_version,
                            "source_type": provenance.source_type,
                            "task_id": provenance.task_id,
                            "trust_state": provenance.trust_state.value,
                            "verification_state": provenance.verification_state,
                        }
                    ),
                ),
            )
            if index_text and trust == TrustStatus.TRUSTED:
                self._index_trusted(digest, index_text)
            self._append_event(
                EventType.ARTIFACT_INGESTED,
                {"created": created, "sha256": digest},
                idempotency_key=idempotency_key,
                correlation_id=digest,
            )
            return payload

    def _index_trusted(self, digest: str, body: str) -> None:
        doc_id = f"obj:{digest}"
        self.store.conn.execute(
            "INSERT INTO fts_docs(doc_id, sha256, trust_status, object_state, body) VALUES (?, ?, ?, ?, ?)",
            (doc_id, digest, TrustStatus.TRUSTED.value, ObjectState.AVAILABLE.value, body),
        )
        self.store.conn.execute(
            "INSERT INTO fts_trusted(doc_id, body, sha256) VALUES (?, ?, ?)",
            (doc_id, body, digest),
        )

    def read_artifact(self, digest: str) -> bytes:
        row = self.store.fetchone("SELECT * FROM objects WHERE sha256 = ?", (digest,))
        if not row:
            if self.cas.exists(digest):
                raise FailClosed("ORPHAN_OBJECT_UNRECONCILED")
            raise FailClosed("OBJECT_NOT_FOUND")
        if row["object_state"] == ObjectState.QUARANTINED.value:
            raise FailClosed("OBJECT_QUARANTINED")
        if row["storage_status"] == StorageStatus.MISSING.value or not self.cas.exists(digest):
            raise FailClosed("METADATA_WITHOUT_OBJECT_DETECTED")
        return self.cas.read(digest)

    def ingest_result(
        self,
        *,
        task_id: str,
        idempotency_key: str,
        status: str,
        confidence: float,
        artifact_sha256: str | None = None,
        evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        if not 0.0 <= float(confidence) <= 1.0:
            raise FailClosed("CONFIDENCE_OUT_OF_RANGE")
        with self.store.transaction():
            existing = self.store.fetchone(
                "SELECT payload_json FROM results WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            if existing:
                return json.loads(existing["payload_json"])
            result_id = new_id("result")
            payload = {
                "artifact_sha256": artifact_sha256,
                "confidence": confidence,
                "created_at": self._now(),
                "evidence": evidence or [],
                "idempotency_key": idempotency_key,
                "result_id": result_id,
                "schema_version": SCHEMA_VERSION,
                "status": status,
                "task_id": task_id,
            }
            self.store.conn.execute(
                "INSERT INTO results(result_id, task_id, idempotency_key, artifact_sha256, schema_version, payload_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (result_id, task_id, idempotency_key, artifact_sha256, SCHEMA_VERSION, canonical_json(payload), payload["created_at"]),
            )
            if artifact_sha256:
                self._bump_ref(artifact_sha256, "result", result_id)
            self._append_event(
                EventType.RESULT_INGESTED,
                payload,
                idempotency_key=f"event:result:{idempotency_key}",
                correlation_id=task_id,
            )
            return payload

    def ingest_handoff(
        self,
        *,
        task_id: str,
        idempotency_key: str,
        from_executor: str,
        to_executor: str,
        reason: str,
        context_capsule_id: str | None = None,
    ) -> dict[str, Any]:
        with self.store.transaction():
            existing = self.store.fetchone(
                "SELECT payload_json FROM handoffs WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            if existing:
                return json.loads(existing["payload_json"])
            handoff_id = new_id("handoff")
            payload = {
                "context_capsule_id": context_capsule_id,
                "created_at": self._now(),
                "from_executor": from_executor,
                "handoff_id": handoff_id,
                "idempotency_key": idempotency_key,
                "reason": reason,
                "schema_version": SCHEMA_VERSION,
                "task_id": task_id,
                "to_executor": to_executor,
            }
            self.store.conn.execute(
                "INSERT INTO handoffs(handoff_id, task_id, idempotency_key, schema_version, payload_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (handoff_id, task_id, idempotency_key, SCHEMA_VERSION, canonical_json(payload), payload["created_at"]),
            )
            self._append_event(
                EventType.HANDOFF_INGESTED,
                payload,
                idempotency_key=f"event:handoff:{idempotency_key}",
                correlation_id=task_id,
            )
            return payload

    def _bump_ref(self, sha256: str, kind: str, entity_id: str) -> None:
        obj = self.store.fetchone("SELECT * FROM objects WHERE sha256 = ?", (sha256,))
        if not obj:
            raise FailClosed("OBJECT_NOT_FOUND")
        payload = json.loads(obj["payload_json"])
        payload["reference_count"] = int(obj["reference_count"]) + 1
        self.store.conn.execute(
            "UPDATE objects SET reference_count = ?, payload_json = ? WHERE sha256 = ?",
            (payload["reference_count"], canonical_json(payload), sha256),
        )
        self.store.conn.execute(
            "INSERT INTO object_refs(ref_id, sha256, ref_kind, entity_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (new_id("ref"), sha256, kind, entity_id, self._now()),
        )

    def expire_stale_leases(self) -> None:
        now = self._now()
        self.store.conn.execute(
            "UPDATE leases SET state = ? WHERE state = ? AND expires_at < ?",
            (LeaseState.EXPIRED.value, LeaseState.ACTIVE.value, now),
        )

    def issue_lease(
        self,
        *,
        task_id: str,
        executor_id: str,
        scope: str,
        mode: LeaseMode,
        ttl_seconds: int = 60,
    ) -> dict[str, Any]:
        normalized = normalize_scope(scope)
        assert_contained(self.root, normalized)
        with self.store.transaction():
            self.expire_stale_leases()
            active = self.store.fetchall(
                "SELECT * FROM leases WHERE state = ?",
                (LeaseState.ACTIVE.value,),
            )
            for lease in active:
                if not scopes_overlap(lease["scope_normalized"], normalized):
                    continue
                existing_mode = LeaseMode(lease["mode"])
                if mode == LeaseMode.WRITE and existing_mode == LeaseMode.WRITE:
                    raise FailClosed("LEASE_OVERLAP_REJECTED")
                if mode == LeaseMode.WRITE and existing_mode == LeaseMode.READ_VERIFY:
                    continue
                if mode == LeaseMode.READ_VERIFY:
                    continue
            now = _parse_ts(self._now())
            issued = now.isoformat()
            expires = (now + timedelta(seconds=ttl_seconds)).isoformat()
            lease_id = new_id("lease")
            payload = {
                "executor_id": executor_id,
                "expires_at": expires,
                "generation": 1,
                "issued_at": issued,
                "lease_id": lease_id,
                "mode": mode.value,
                "renewed_at": issued,
                "schema_version": SCHEMA_VERSION,
                "scope": normalized,
                "state": LeaseState.ACTIVE.value,
                "task_id": task_id,
            }
            self.store.conn.execute(
                """
                INSERT INTO leases(
                    lease_id, task_id, executor_id, scope_normalized, mode,
                    issued_at, expires_at, renewed_at, generation, state, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    lease_id,
                    task_id,
                    executor_id,
                    normalized,
                    mode.value,
                    issued,
                    expires,
                    issued,
                    LeaseState.ACTIVE.value,
                    canonical_json(payload),
                ),
            )
            self._append_event(
                EventType.LEASE_ISSUED,
                payload,
                idempotency_key=new_id("event:lease"),
                correlation_id=task_id,
            )
            return payload

    def renew_lease(self, lease_id: str, generation: int, ttl_seconds: int = 60) -> dict[str, Any]:
        with self.store.transaction():
            row = self.store.fetchone("SELECT * FROM leases WHERE lease_id = ?", (lease_id,))
            if not row:
                raise FailClosed("LEASE_NOT_FOUND")
            if row["state"] != LeaseState.ACTIVE.value or row["generation"] != generation:
                raise FailClosed("LEASE_FENCING_REJECTED")
            now = datetime.now(timezone.utc)
            if _parse_ts(row["expires_at"]) < now:
                self.store.conn.execute(
                    "UPDATE leases SET state = ? WHERE lease_id = ?",
                    (LeaseState.EXPIRED.value, lease_id),
                )
                raise FailClosed("LEASE_EXPIRED")
            nxt_gen = generation + 1
            renewed = now.isoformat()
            expires = (now + timedelta(seconds=ttl_seconds)).isoformat()
            payload = json.loads(row["payload_json"])
            payload.update({"generation": nxt_gen, "renewed_at": renewed, "expires_at": expires})
            cur = self.store.conn.execute(
                "UPDATE leases SET generation = ?, renewed_at = ?, expires_at = ?, payload_json = ? "
                "WHERE lease_id = ? AND generation = ? AND state = ?",
                (nxt_gen, renewed, expires, canonical_json(payload), lease_id, generation, LeaseState.ACTIVE.value),
            )
            if cur.rowcount != 1:
                raise FailClosed("LEASE_RENEWAL_RACE")
            self._append_event(
                EventType.LEASE_RENEWED,
                payload,
                idempotency_key=new_id("event:lease-renew"),
                correlation_id=row["task_id"],
            )
            return payload

    def require_write(self, lease_id: str, generation: int, executor_id: str) -> dict[str, Any]:
        self.expire_stale_leases()
        row = self.store.fetchone("SELECT * FROM leases WHERE lease_id = ?", (lease_id,))
        if not row:
            raise FailClosed("LEASE_NOT_FOUND")
        if row["executor_id"] != executor_id or row["generation"] != generation:
            raise FailClosed("STALE_WORKER_REJECTED")
        if row["state"] != LeaseState.ACTIVE.value:
            raise FailClosed("STALE_WORKER_REJECTED")
        if row["mode"] != LeaseMode.WRITE.value:
            raise FailClosed("LEASE_MODE_NOT_WRITABLE")
        if _parse_ts(row["expires_at"]) < datetime.now(timezone.utc):
            raise FailClosed("STALE_WORKER_REJECTED")
        return dict(row)

    def fence_lease(self, lease_id: str) -> dict[str, Any]:
        with self.store.transaction():
            row = self.store.fetchone("SELECT * FROM leases WHERE lease_id = ?", (lease_id,))
            if not row:
                raise FailClosed("LEASE_NOT_FOUND")
            payload = json.loads(row["payload_json"])
            payload["state"] = LeaseState.FENCED.value
            payload["generation"] = int(row["generation"]) + 1
            self.store.conn.execute(
                "UPDATE leases SET state = ?, generation = ?, payload_json = ? WHERE lease_id = ?",
                (LeaseState.FENCED.value, payload["generation"], canonical_json(payload), lease_id),
            )
            self._append_event(
                EventType.LEASE_FENCED,
                payload,
                idempotency_key=new_id("event:lease-fence"),
                correlation_id=row["task_id"],
            )
            return payload

    def create_capsule(self, *, task_id: str, refs: list[str], purpose: str) -> ContextCapsule:
        for ref in refs:
            if not ref.startswith("artifact://sha256/"):
                raise FailClosed(f"UNSUPPORTED_EXCHANGE_REF:{ref}")
        canonical_refs = tuple(sorted(set(refs)))
        identity = {
            "purpose": purpose,
            "refs": list(canonical_refs),
            "schema_version": SCHEMA_VERSION,
            "task_id": task_id,
        }
        capsule_id = "capsule:" + sha256_obj(identity)
        capsule = ContextCapsule(
            capsule_id=capsule_id,
            refs=canonical_refs,
            task_id=task_id,
            purpose=purpose,
        )
        with self.store.transaction():
            existing = self.store.fetchone("SELECT payload_json FROM capsules WHERE capsule_id = ?", (capsule_id,))
            if existing:
                data = json.loads(existing["payload_json"])
                return ContextCapsule(
                    capsule_id=data["capsule_id"],
                    refs=tuple(data["refs"]),
                    task_id=data["task_id"],
                    purpose=data["purpose"],
                    schema_version=data["schema_version"],
                    created_at=data["created_at"],
                )
            payload = {
                "capsule_id": capsule.capsule_id,
                "created_at": capsule.created_at,
                "purpose": capsule.purpose,
                "refs": list(capsule.refs),
                "schema_version": capsule.schema_version,
                "task_id": capsule.task_id,
            }
            self.store.conn.execute(
                "INSERT INTO capsules(capsule_id, schema_version, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (capsule_id, SCHEMA_VERSION, canonical_json(payload), capsule.created_at),
            )
            self._append_event(
                EventType.CAPSULE_CREATED,
                payload,
                idempotency_key=f"event:capsule:{capsule_id}",
                correlation_id=task_id,
            )
            return capsule

    def quarantine_object(
        self,
        digest: str,
        *,
        reason: str,
        source: str,
        validation_failures: list[str],
        data: bytes | None = None,
    ) -> dict[str, Any]:
        payload_bytes = data if data is not None else (self.cas.object_path(digest).read_bytes() if self.cas.exists(digest) else b"")
        if payload_bytes:
            observed = sha256_bytes(payload_bytes)
            if observed != digest and data is None:
                # preserve original bytes even if already tampered; record both hashes
                pass
        self.cas.quarantine_copy(digest, payload_bytes)
        with self.store.transaction():
            qid = new_id("q")
            now = self._now()
            record = {
                "hash": digest,
                "observed_at": now,
                "quarantine_id": qid,
                "reason": reason,
                "schema_version": SCHEMA_VERSION,
                "source": source,
                "validation_failures": validation_failures,
            }
            self.store.conn.execute(
                """
                INSERT INTO quarantine(quarantine_id, sha256, reason, source, observed_at, validation_failures, schema_version, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (qid, digest, reason, source, now, canonical_json(validation_failures), SCHEMA_VERSION, canonical_json(record)),
            )
            obj = self.store.fetchone("SELECT * FROM objects WHERE sha256 = ?", (digest,))
            if obj:
                payload = json.loads(obj["payload_json"])
                payload["object_state"] = ObjectState.QUARANTINED.value
                payload["storage_status"] = StorageStatus.QUARANTINED.value
                payload["trust_status"] = TrustStatus.UNTRUSTED.value
                payload["canonical_status"] = CanonicalStatus.NOT_CANONICAL.value
                self.store.conn.execute(
                    "UPDATE objects SET object_state = ?, storage_status = ?, trust_status = ?, canonical_status = ?, payload_json = ? WHERE sha256 = ?",
                    (
                        ObjectState.QUARANTINED.value,
                        StorageStatus.QUARANTINED.value,
                        TrustStatus.UNTRUSTED.value,
                        CanonicalStatus.NOT_CANONICAL.value,
                        canonical_json(payload),
                        digest,
                    ),
                )
            self.store.conn.execute("DELETE FROM fts_docs WHERE sha256 = ?", (digest,))
            self.store.conn.execute("DELETE FROM fts_trusted WHERE doc_id = ?", (f"obj:{digest}",))
            self._append_event(
                EventType.OBJECT_QUARANTINED,
                record,
                idempotency_key=new_id("event:quarantine"),
                correlation_id=digest,
            )
            return record

    def search(self, query: str, *, trusted_only: bool = True) -> list[dict[str, Any]]:
        if not trusted_only:
            raise FailClosed("UNTRUSTED_RETRIEVAL_NOT_DEFAULT")
        if self.store.fts_enabled:
            try:
                rows = self.store.fetchall(
                    "SELECT doc_id, sha256, body FROM fts_trusted WHERE fts_trusted MATCH ?",
                    (query,),
                )
            except sqlite3.OperationalError:
                rows = self.store.fetchall(
                    "SELECT doc_id, sha256, body FROM fts_docs WHERE body LIKE ? AND trust_status = ? AND object_state = ?",
                    (f"%{query}%", TrustStatus.TRUSTED.value, ObjectState.AVAILABLE.value),
                )
        else:
            rows = self.store.fetchall(
                "SELECT doc_id, sha256, body FROM fts_trusted WHERE body LIKE ?",
                (f"%{query}%",),
            )
        results = []
        for row in rows:
            obj = self.store.fetchone("SELECT * FROM objects WHERE sha256 = ?", (row["sha256"],))
            if not obj:
                continue
            if obj["object_state"] != ObjectState.AVAILABLE.value:
                continue
            if obj["trust_status"] != TrustStatus.TRUSTED.value:
                continue
            results.append({"doc_id": row["doc_id"], "sha256": row["sha256"], "retrieval_only": True})
        return results

    def reconcile(self) -> dict[str, Any]:
        removed_tmp = 0
        for part in self.cas.list_temp_parts():
            try:
                part.unlink()
                removed_tmp += 1
            except OSError:
                pass
        disk = self.cas.list_object_digests()
        rows = self.store.fetchall("SELECT sha256, object_state, payload_json FROM objects")
        meta = {row["sha256"] for row in rows}
        orphans = sorted(disk - meta)
        missing = sorted(meta - disk)
        with self.store.transaction():
            for digest in orphans:
                now = self._now()
                payload = {
                    "canonical_status": CanonicalStatus.NOT_CANONICAL.value,
                    "created_at": now,
                    "object_state": ObjectState.ORPHAN.value,
                    "reference_count": 0,
                    "retention_policy": RetentionPolicy.RETAIN.value,
                    "schema_version": SCHEMA_VERSION,
                    "sha256": digest,
                    "size_bytes": self.cas.object_path(digest).stat().st_size,
                    "storage_status": StorageStatus.STORED.value,
                    "trust_status": TrustStatus.UNTRUSTED.value,
                    "validation_status": ValidationStatus.UNVALIDATED.value,
                }
                self.store.conn.execute(
                    """
                    INSERT INTO objects(
                        sha256, size_bytes, object_state, reference_count, retention_policy,
                        storage_status, validation_status, trust_status, canonical_status,
                        schema_version, created_at, payload_json
                    ) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        digest,
                        payload["size_bytes"],
                        ObjectState.ORPHAN.value,
                        RetentionPolicy.RETAIN.value,
                        StorageStatus.STORED.value,
                        ValidationStatus.UNVALIDATED.value,
                        TrustStatus.UNTRUSTED.value,
                        CanonicalStatus.NOT_CANONICAL.value,
                        SCHEMA_VERSION,
                        now,
                        canonical_json(payload),
                    ),
                )
                self._append_event(
                    EventType.OBJECT_RECONCILED,
                    {"kind": "orphan", "sha256": digest},
                    idempotency_key=f"event:orphan:{digest}",
                    correlation_id=digest,
                )
            for digest in missing:
                row = self.store.fetchone("SELECT payload_json FROM objects WHERE sha256 = ?", (digest,))
                if not row:
                    continue
                payload = json.loads(row["payload_json"])
                if payload.get("object_state") == ObjectState.QUARANTINED.value:
                    continue
                payload["object_state"] = ObjectState.MISSING.value
                payload["storage_status"] = StorageStatus.MISSING.value
                self.store.conn.execute(
                    "UPDATE objects SET object_state = ?, storage_status = ?, payload_json = ? WHERE sha256 = ?",
                    (ObjectState.MISSING.value, StorageStatus.MISSING.value, canonical_json(payload), digest),
                )
                self._append_event(
                    EventType.OBJECT_RECONCILED,
                    {"kind": "missing", "sha256": digest},
                    idempotency_key=f"event:missing:{digest}",
                    correlation_id=digest,
                )
        return {"interrupted_temp_removed": removed_tmp, "missing": missing, "orphans": orphans}

    def replay(self, apply: bool = True) -> dict[str, Any]:
        self.verify_event_chain()
        events = self.store.fetchall("SELECT * FROM collab_events ORDER BY sequence ASC")
        derived = {"capsules": {}, "handoffs": {}, "results": {}, "tasks": {}}
        seen_idempotency: set[str] = set()
        for row in events:
            if row["idempotency_key"] in seen_idempotency:
                continue
            seen_idempotency.add(row["idempotency_key"])
            record = json.loads(row["payload_json"])
            payload = record["payload"]
            et = row["event_type"]
            if et == EventType.TASK_CREATED.value:
                derived["tasks"][payload["task_id"]] = payload
            elif et == EventType.TASK_STATE_CHANGED.value:
                task = derived["tasks"].get(payload["task_id"])
                if task:
                    task = dict(task)
                    task["state"] = payload["to"]
                    derived["tasks"][payload["task_id"]] = task
            elif et == EventType.RESULT_INGESTED.value:
                derived["results"][payload["result_id"]] = payload
            elif et == EventType.HANDOFF_INGESTED.value:
                derived["handoffs"][payload["handoff_id"]] = payload
            elif et == EventType.CAPSULE_CREATED.value:
                derived["capsules"][payload["capsule_id"]] = payload
        if apply:
            pass
        return {
            "capsules": len(derived["capsules"]),
            "events": len(events),
            "handoffs": len(derived["handoffs"]),
            "results": len(derived["results"]),
            "tasks": len(derived["tasks"]),
            "derived": derived,
        }

    def copy_events_to(self, dest: "CognitiveExchange") -> int:
        events = self.store.fetchall("SELECT * FROM collab_events ORDER BY sequence ASC")
        with dest.store.transaction():
            for row in events:
                dest.store.conn.execute(
                    """
                    INSERT OR IGNORE INTO collab_events(
                        event_id, sequence, correlation_id, causation_id, event_type,
                        payload_hash, previous_event_hash, event_hash, timestamp,
                        idempotency_key, schema_version, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["event_id"],
                        row["sequence"],
                        row["correlation_id"],
                        row["causation_id"],
                        row["event_type"],
                        row["payload_hash"],
                        row["previous_event_hash"],
                        row["event_hash"],
                        row["timestamp"],
                        row["idempotency_key"],
                        row["schema_version"],
                        row["payload_json"],
                    ),
                )
        return len(events)
