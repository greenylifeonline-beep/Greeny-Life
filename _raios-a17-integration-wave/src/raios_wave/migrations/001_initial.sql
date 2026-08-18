-- a17-integration-wave.v1
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS identity_state (
    organism_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS objects (
    sha256 TEXT PRIMARY KEY,
    bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    teacher_id TEXT NOT NULL,
    model TEXT NOT NULL,
    task_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    verification_state TEXT NOT NULL,
    canonical INTEGER NOT NULL DEFAULT 0 CHECK (canonical = 0),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_obs_source ON observations(source_sha256, teacher_id, task_id, capability);

CREATE TABLE IF NOT EXISTS quarantined_artifacts (
    quarantine_id TEXT PRIMARY KEY,
    source_artifact TEXT NOT NULL,
    reason TEXT NOT NULL,
    sha256 TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS differentials (
    differential_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    outcome TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    candidate_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    capability TEXT,
    authority_state TEXT NOT NULL CHECK (authority_state IN ('CANDIDATE','VALIDATED','REJECTED','QUARANTINED')),
    canonical INTEGER NOT NULL DEFAULT 0 CHECK (canonical = 0),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competency (
    capability_id TEXT PRIMARY KEY,
    knowledge_score REAL NOT NULL,
    execution_score REAL NOT NULL,
    transfer_score REAL NOT NULL,
    reliability_score REAL NOT NULL,
    independence_score REAL NOT NULL,
    retention_score REAL NOT NULL,
    teacher_intervention_rate REAL NOT NULL,
    verifier_failure_rate REAL NOT NULL,
    repeated_validations INTEGER NOT NULL,
    distinct_transfer_domains INTEGER NOT NULL,
    regression_gate TEXT NOT NULL,
    retention_gate TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teacher_capability (
    teacher_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    model TEXT NOT NULL,
    lifecycle TEXT NOT NULL,
    unique_capability INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (teacher_id, capability)
);

CREATE TABLE IF NOT EXISTS experiences (
    experience_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_records (
    knowledge_id TEXT PRIMARY KEY,
    source_sha256 TEXT NOT NULL,
    state TEXT NOT NULL,
    authority_state TEXT NOT NULL,
    canonical INTEGER NOT NULL DEFAULT 0 CHECK (canonical = 0),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_debt (
    debt_id TEXT PRIMARY KEY,
    concept TEXT NOT NULL,
    status TEXT NOT NULL,
    priority REAL NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_debt (
    debt_id TEXT PRIMARY KEY,
    capability TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rkg_nodes (
    node_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rkg_edges (
    edge_id TEXT PRIMARY KEY,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    relation TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(src, dst, relation)
);

CREATE TABLE IF NOT EXISTS loop_runs (
    run_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    seq INTEGER NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    prev_event_sha256 TEXT,
    event_sha256 TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS governance_actions (
    action_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    allowed INTEGER NOT NULL,
    reason TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    knowledge_id,
    claim,
    source
);

CREATE VIRTUAL TABLE IF NOT EXISTS experience_fts USING fts5(
    experience_id,
    goal,
    lesson
);

CREATE TRIGGER IF NOT EXISTS observations_immutable_update
BEFORE UPDATE ON observations
BEGIN
    SELECT RAISE(ABORT, 'OBSERVATIONS_ARE_APPEND_ONLY');
END;

CREATE TRIGGER IF NOT EXISTS observations_immutable_delete
BEFORE DELETE ON observations
BEGIN
    SELECT RAISE(ABORT, 'OBSERVATIONS_ARE_APPEND_ONLY');
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

CREATE TRIGGER IF NOT EXISTS experiences_immutable_update
BEFORE UPDATE ON experiences
BEGIN
    SELECT RAISE(ABORT, 'EXPERIENCES_ARE_APPEND_ONLY');
END;

CREATE TRIGGER IF NOT EXISTS experiences_immutable_delete
BEFORE DELETE ON experiences
BEGIN
    SELECT RAISE(ABORT, 'EXPERIENCES_ARE_APPEND_ONLY');
END;

CREATE INDEX IF NOT EXISTS idx_candidates_kind ON candidates(kind, authority_state);
CREATE INDEX IF NOT EXISTS idx_knowledge_state ON knowledge_records(state);
CREATE INDEX IF NOT EXISTS idx_events_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_teacher_cap_lifecycle ON teacher_capability(lifecycle);
