-- learning-fabric.v2 initial schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    result_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    prev_event_sha256 TEXT,
    event_sha256 TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS debts (
    debt_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'OPEN','ASSIGNED','STUDYING','PRACTICING','REPLAY_PENDING',
        'VALIDATION_PENDING','PAID','DEFERRED','INVALIDATED'
    )),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_objects (
    knowledge_id TEXT PRIMARY KEY,
    origin_class TEXT NOT NULL CHECK (origin_class IN ('REAL','SYNTHETIC','DERIVED')),
    maturity TEXT NOT NULL CHECK (maturity IN (
        'SEEN','UNDERSTOOD','CONNECTED','PRACTICED','VALIDATED','TRANSFERABLE','MASTERED'
    )),
    epistemic_state TEXT NOT NULL CHECK (epistemic_state IN (
        'UNVERIFIED','EVIDENCE_BOUNDED','VERIFIED','CONTRADICTED','DEPRECATED','QUARANTINED'
    )),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competency_nodes (
    capability_id TEXT PRIMARY KEY,
    score REAL NOT NULL CHECK (score >= 0.0 AND score <= 1.0),
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competency_proposals (
    proposal_id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teacher_dependencies (
    capability_id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK (state IN (
        'TEACHER_SOLVES','STUDENT_CO_SOLVES','STUDENT_SOLVES_TEACHER_VERIFIES',
        'STUDENT_INDEPENDENT','TEACHER_AUDIT_ONLY','RETIRED'
    )),
    task_count INTEGER NOT NULL DEFAULT 0 CHECK (task_count >= 0),
    distinct_contexts INTEGER NOT NULL DEFAULT 0 CHECK (distinct_contexts >= 0),
    transfer_successes INTEGER NOT NULL DEFAULT 0 CHECK (transfer_successes >= 0),
    verification_failures INTEGER NOT NULL DEFAULT 0 CHECK (verification_failures >= 0),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS training_candidates (
    candidate_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN (
        'SFT','PREFERENCE','DISTILLATION','TOOL_USE','FAILURE_RECOVERY',
        'ARCHITECTURE_DECISION','TRANSFER'
    )),
    state TEXT NOT NULL CHECK (state IN ('DRAFT','VALIDATED','PROMOTED','REJECTED','QUARANTINED')),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS harvest_items (
    harvest_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('OBSERVED_FACT','DERIVED_INFERENCE','UNVERIFIED_HYPOTHESIS')),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compression_nodes (
    node_id TEXT PRIMARY KEY,
    layer TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_traces_idempotency ON traces(idempotency_key);
CREATE UNIQUE INDEX IF NOT EXISTS idx_traces_content ON traces(content_sha256, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_traces_task ON traces(task_id);

CREATE TRIGGER IF NOT EXISTS traces_immutable_update
BEFORE UPDATE ON traces
BEGIN
    SELECT RAISE(ABORT, 'LEARNING_TRACES_ARE_APPEND_ONLY');
END;

CREATE TRIGGER IF NOT EXISTS traces_immutable_delete
BEFORE DELETE ON traces
BEGIN
    SELECT RAISE(ABORT, 'LEARNING_TRACES_ARE_APPEND_ONLY');
END;

CREATE TRIGGER IF NOT EXISTS audit_events_immutable_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'AUDIT_EVENTS_ARE_APPEND_ONLY');
END;

CREATE TRIGGER IF NOT EXISTS audit_events_immutable_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'AUDIT_EVENTS_ARE_APPEND_ONLY');
END;
CREATE INDEX IF NOT EXISTS idx_events_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_entity ON audit_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_debts_state ON debts(state);
CREATE INDEX IF NOT EXISTS idx_knowledge_maturity ON knowledge_objects(maturity);
CREATE INDEX IF NOT EXISTS idx_knowledge_epistemic ON knowledge_objects(epistemic_state);
CREATE INDEX IF NOT EXISTS idx_training_state ON training_candidates(state);
