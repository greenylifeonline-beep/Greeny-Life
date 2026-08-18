-- cognitive-exchange.v2 initial schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    logical_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS objects (
    sha256 TEXT PRIMARY KEY CHECK (length(sha256) = 64),
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    object_state TEXT NOT NULL CHECK (object_state IN (
        'AVAILABLE','QUARANTINED','MISSING','ORPHAN','RETAINED'
    )),
    reference_count INTEGER NOT NULL DEFAULT 0 CHECK (reference_count >= 0),
    retention_policy TEXT NOT NULL CHECK (retention_policy IN (
        'RETAIN','REVIEW','GOVERNED_CANDIDATE'
    )),
    storage_status TEXT NOT NULL CHECK (storage_status IN ('STORED','MISSING','QUARANTINED')),
    validation_status TEXT NOT NULL CHECK (validation_status IN ('UNVALIDATED','VALID','INVALID')),
    trust_status TEXT NOT NULL CHECK (trust_status IN ('UNTRUSTED','TRUSTED','CONTRADICTED')),
    canonical_status TEXT NOT NULL CHECK (canonical_status IN ('NOT_CANONICAL','CANDIDATE','CANONICAL')),
    schema_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS object_refs (
    ref_id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    ref_kind TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (sha256) REFERENCES objects(sha256)
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL CHECK (state IN (
        'CREATED','ADMITTED','LEASED','RUNNING','VERIFYING','COMPLETED','FAILED','CANCELLED','BLOCKED'
    )),
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    result_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    artifact_sha256 TEXT,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS handoffs (
    handoff_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leases (
    lease_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    executor_id TEXT NOT NULL,
    scope_normalized TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('WRITE','READ_VERIFY')),
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    renewed_at TEXT,
    generation INTEGER NOT NULL CHECK (generation >= 1),
    state TEXT NOT NULL CHECK (state IN ('ACTIVE','EXPIRED','RELEASED','FENCED')),
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS collab_events (
    event_id TEXT PRIMARY KEY,
    sequence INTEGER NOT NULL UNIQUE,
    correlation_id TEXT NOT NULL,
    causation_id TEXT,
    event_type TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    previous_event_hash TEXT,
    event_hash TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS capsules (
    capsule_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provenance (
    provenance_id TEXT PRIMARY KEY,
    object_sha256 TEXT NOT NULL,
    producer_id TEXT NOT NULL,
    producer_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    task_id TEXT,
    generation_method TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    trust_state TEXT NOT NULL,
    verification_state TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine (
    quarantine_id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    validation_failures TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fts_docs (
    doc_id TEXT PRIMARY KEY,
    sha256 TEXT,
    trust_status TEXT NOT NULL,
    object_state TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
CREATE INDEX IF NOT EXISTS idx_leases_scope ON leases(scope_normalized, state);
CREATE INDEX IF NOT EXISTS idx_leases_task ON leases(task_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON collab_events(event_type);
CREATE INDEX IF NOT EXISTS idx_objects_state ON objects(object_state);
CREATE INDEX IF NOT EXISTS idx_quarantine_sha ON quarantine(sha256);
CREATE INDEX IF NOT EXISTS idx_object_refs_sha ON object_refs(sha256);

CREATE TRIGGER IF NOT EXISTS objects_no_delete BEFORE DELETE ON objects
BEGIN
    SELECT RAISE(ABORT, 'OBJECTS_NOT_AUTO_DELETED');
END;

CREATE TRIGGER IF NOT EXISTS objects_identity_immutable BEFORE UPDATE OF sha256 ON objects
BEGIN
    SELECT RAISE(ABORT, 'OBJECT_IDENTITY_IMMUTABLE');
END;

CREATE TRIGGER IF NOT EXISTS collab_events_no_update BEFORE UPDATE ON collab_events
BEGIN
    SELECT RAISE(ABORT, 'COLLAB_WAL_APPEND_ONLY');
END;

CREATE TRIGGER IF NOT EXISTS collab_events_no_delete BEFORE DELETE ON collab_events
BEGIN
    SELECT RAISE(ABORT, 'COLLAB_WAL_APPEND_ONLY');
END;
