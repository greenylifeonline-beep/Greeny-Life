PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS identity_state (
    organism_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    degraded_mode TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS objects (
    sha256 TEXT PRIMARY KEY,
    bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantined (
    quarantine_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    sha256 TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    teacher_id TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    verification_state TEXT NOT NULL,
    canonical INTEGER NOT NULL DEFAULT 0 CHECK (canonical = 0),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_obs_hash ON observations(source_sha256, teacher_id);

CREATE TABLE IF NOT EXISTS live_sessions (
    session_id TEXT PRIMARY KEY,
    capability TEXT NOT NULL,
    state TEXT NOT NULL,
    baseline_frozen INTEGER NOT NULL DEFAULT 0,
    teacher_visible INTEGER NOT NULL DEFAULT 0,
    contamination_token TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verifier_results (
    result_id TEXT PRIMARY KEY,
    session_id TEXT,
    outcome TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competency (
    capability_id TEXT PRIMARY KEY,
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
    state TEXT NOT NULL,
    canonical INTEGER NOT NULL DEFAULT 0 CHECK (canonical = 0),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_debt (
    debt_id TEXT PRIMARY KEY,
    concept TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    capability TEXT,
    lifecycle TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS training (
    candidate_id TEXT PRIMARY KEY,
    lifecycle TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS adapters (
    adapter_id TEXT PRIMARY KEY,
    lifecycle TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS compute_jobs (
    job_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    gpu_value_per_minute REAL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS maintenance_events (
    event_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_items (
    key TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    seq INTEGER NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    idempotency_key TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    previous_hash TEXT,
    payload_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS governance_actions (
    action_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    allowed INTEGER NOT NULL,
    reason TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(knowledge_id, claim, source);
CREATE VIRTUAL TABLE IF NOT EXISTS experience_fts USING fts5(experience_id, goal, lesson);

CREATE TRIGGER IF NOT EXISTS observations_no_update BEFORE UPDATE ON observations
BEGIN SELECT RAISE(ABORT, 'OBSERVATIONS_ARE_APPEND_ONLY'); END;
CREATE TRIGGER IF NOT EXISTS observations_no_delete BEFORE DELETE ON observations
BEGIN SELECT RAISE(ABORT, 'OBSERVATIONS_ARE_APPEND_ONLY'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'AUDIT_EVENTS_ARE_APPEND_ONLY'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'AUDIT_EVENTS_ARE_APPEND_ONLY'); END;
CREATE TRIGGER IF NOT EXISTS exp_no_update BEFORE UPDATE ON experiences
BEGIN SELECT RAISE(ABORT, 'EXPERIENCES_ARE_APPEND_ONLY'); END;
CREATE TRIGGER IF NOT EXISTS exp_no_delete BEFORE DELETE ON experiences
BEGIN SELECT RAISE(ABORT, 'EXPERIENCES_ARE_APPEND_ONLY'); END;
