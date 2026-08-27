# RIF-RAIOS-COMPATIBILITY-DELTA-v1.1

## Document Classification
- TYPE: DESIGN_DELTA
- STATUS: AUTHORITATIVE_FOR_C7_DONOR
- RAIOS_INTEGRATION_CONSTRAINT: BIND_TO_EXISTING
- PARALLEL_ARCHITECTURE: FALSE

## Executive Summary
This delta transforms the historical RIF v1.0 sandbox package into a RAIOS-aware, reuse-first integration donor. C7 does NOT create parallel infrastructure. All canonical authority, evidence storage, policy enforcement, and state ownership remain with existing RAIOS systems.

## Canonicalization Redesign

### v1.0 Violation
- C7 defined `canonical_fingerprint` as authoritative
- C7 assumed ownership of canonicalization algorithm

### v1.1 Resolution
- RETIRE `canonical_fingerprint` → rename to `SANDBOX_REFERENCE_FINGERPRINT`
- C7 depends on RAIOS-provided canonicalization during integration
- Design `CanonicalFingerprintProvider` interface:
  - `canonicalize(object) -> CanonicalForm`
  - `fingerprint(object) -> Fingerprint`
  - `schema_version() -> String`
  - `algorithm_id() -> String`
- Tests MUST allow injecting deterministic fake provider for sandbox isolation
- **INVARIANT I16**: Fingerprint provider is externalized
- **INVARIANT I17**: Second canonicalizer is forbidden

## Schema Versioning Requirements

Every RIF schema MUST support:
- `schema_version`: SemVer string
- `producer`: Structured provenance (not free-form seat)
- `provenance_reference`: Chain of derivation
- `extensions`: Map of extension fields
- `unknown_field_policy`: `REJECT` | `WARN` | `PASS_THROUGH` | `DROP`

### Change Classification
- **backward_compatible**: New optional fields, wider acceptance
- **breaking**: Removed fields, changed semantics, narrower acceptance
- **migration_required**: Breaking change with automated migration path defined

### Identity Decomposition

v1.0 violation: `producer_seat="C7"`

v1.1 required:
- `producer_declared`: Self-claimed identity
- `producer_verified`: Cryptographically or administratively verified identity
- `producer_component`: Component within the producer system
- `producer_version`: Version of the producing component

No production identity authority from `producer_declared` alone.

## RAIOS Reuse Integration (TREE-001 Evidence)

### Reuse (5 items)
1. **NeuroLingua**: Semantic resolution — use via SemanticResolverAdapter
2. **WAL adapter**: Write-ahead logging — use via WALAdapter
3. **Unified Control Plane (UCP)**: Global task authority — use via ControlPlaneAdapter
4. **NATS**: Transport — use via TransportAdapter
5. **MCP**: Tool protocol — use via MCPToolAdapter

### Wrap (8 items)
1. **Capability Registry**: Wrap with adapter, delegate to existing
2. **Contracts**: Wrap with adapter, delegate to existing policy system
3. **StateGraph**: Wrap as evaluation-local state machine
4. **Risk Policy**: Wrap as assessment donor, feed to PolicyAdapter
5. **Observability**: Wrap as adapter/client to existing infrastructure
6. **RKG**: Use via ModelEcologyAdapter
7. **Model Ecology**: Use via ModelEcologyAdapter
8. **Model Factory**: Use via ModelFactoryAdapter

### Merge (1 item)
- **C7 claim/evidence lifecycle** WITH **existing RAIOS evidence-trust-lattice**
- C7 provides logical/evaluation view
- RAIOS provides canonical evidence store and trust lattice

### Donor-Only (2 items)
1. **Governor stop logic**: Pure decision logic, no backend ownership
2. **M001 selection logic**: Spec/harness only, no model ownership

### Conflict Resolution (1 item)
- **SANDBOX_REFERENCE_CANONICALIZATION**
- Resolution: Existing RAIOS canonicalization WINS
- C7 canonical_fingerprint retired to sandbox reference only

## Semantic Truth Constraints (Non-Negotiable)

1. `UNKNOWN != ZERO`
2. `absence_of_evidence != evidence_of_absence`
3. `MISSING != FALSE`
4. `UNVERIFIED != INVALID`
5. `TRANSPORT_SUCCESS != CLAIM_TRUE`
6. `CI_PASS != CAPABILITY_PROVEN`
7. `MULTIPLE_AGENTS_REPEAT_SAME_SOURCE != MULTIPLE_INDEPENDENT_SOURCES`

These are integration constraints, not suggestions.
