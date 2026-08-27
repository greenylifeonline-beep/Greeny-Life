# RIF Deterministic Test Suite v1.1

## Metadata
- **Total Tests**: 56
- **Categories**: 14
- **LLM Required**: No
- **Paid API Required**: No
- **GPU Required**: No
- **Execution Proven**: No (defined only, pending execution)

## Categories

### 1. Contracts (4 tests)
T001-T004: Schema validation, identity, versioning

### 2. Fingerprints (4 tests)
T005-T008: External provider, sandbox reference, verification

### 3. State Transitions (5 tests)
T009-T013: Legal/illegal transitions, guards, failure paths

### 4. Evidence Lineage (5 tests)
T014-T018: Lineage tracking, duplicates, independence, derivation

### 5. Contradiction (4 tests)
T019-T022: Detection, blocking, resolution, silence prevention

### 6. Risk (4 tests)
T023-T026: Unknown handling, self-authorization, confidence separation

### 7. Governor (5 tests)
T027-T031: Purity, limits, progress, tool loops, precedence

### 8. Observability (3 tests)
T032-T034: Event fields, no second store, receipt binding

### 9. M001 (4 tests)
T035-T038: Hard gates, role separation, Pareto, machine readability

### 10. A2A Semantic Bridge (4 tests)
T039-T042: Mismatch detection, no downgrade, separation of concerns

### 11. Adapter Boundaries (4 tests)
T043-T046: No ownership of WAL, NATS, evidence, policy

### 12. Security Invariants (6 tests)
T047-T052: I01, I02, I06, I07, I08, I16

### 13. Provenance (3 tests)
T053-T055: Chain integrity, truncation, immutability

### 14. Failure Modes (3 tests)
T056: Dependency unavailability

## Execution Status

```
TEST_DEFINED=56
TEST_MATERIALIZED=56
TEST_EXECUTED=0
TEST_PASS=0
TEST_FAIL=0
TEST_EXECUTION_PROVEN=false
```

## Execution Requirements
- Deterministic test harness (no randomness)
- Mock adapters for all external dependencies
- State machine simulator
- Evidence store mock with lineage tracking
- Governor test harness with side-effect detection
