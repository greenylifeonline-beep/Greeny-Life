# RIF Threat Model v1

## Classification
- TYPE: THREAT_MODEL
- SCOPE: RIF_EVALUATION_SYSTEM
- ASSUMPTION: RAIOS_INFRASTRUCTURE_TRUSTED

## Threat Inventory

### T01: Evidence Duplication Attack
- **Description**: Attacker submits same evidence through multiple channels to inflate perceived support
- **Impact**: False confidence in claim
- **Mitigation**: I03 (Duplicate lineage ≠ independent source), CORRELATION_GROUP tracking
- **Severity**: HIGH

### T02: Source Laundering
- **Description**: Evidence from untrusted source disguised as trusted source
- **Impact**: Trust inflation
- **Mitigation**: TrustLatticeAdapter, provenance verification, I16
- **Severity**: CRITICAL

### T03: Confidence Inflation
- **Description**: Systematic overstatement of confidence scores
- **Impact**: False promotion of unproven claims
- **Mitigation**: Confidence separation (6 separate fields), combination policy interface
- **Severity**: HIGH

### T04: Model Self-Confirmation
- **Description**: Model confirms its own previous outputs as evidence
- **Impact**: Circular reasoning, false validation
- **Mitigation**: ORIGIN_SOURCE_ID tracking, lineage verification, I03
- **Severity**: HIGH

### T05: Agent Collusion Through Shared Source
- **Description**: Multiple agents appear independent but share same underlying source
- **Impact**: False independence perception
- **Mitigation**: CORRELATION_GROUP, EVIDENCE_LINEAGE_ID, I03
- **Severity**: MEDIUM

### T06: Authority Self-Assertion
- **Description**: Component claims authority it does not have
- **Impact**: Unauthorized decisions
- **Mitigation**: I08 (Untrusted authority cannot grant), I16, I17
- **Severity**: CRITICAL

### T07: Semantic Contract Mismatch
- **Description**: A2A semantic contract incompatible with RIF requirements
- **Impact**: Silent semantic degradation
- **Mitigation**: I09 (Semantic mismatch fails closed), explicit compatibility assessment
- **Severity**: HIGH

### T08: Schema Downgrade
- **Description**: Older/worse schema silently accepted instead of required version
- **Impact**: Security/quality degradation
- **Mitigation**: Schema versioning, unknown_field_policy, I10
- **Severity**: HIGH

### T09: Provenance Truncation
- **Description**: Evidence lineage cut to hide origin
- **Impact**: Untrusted evidence appears trusted
- **Mitigation**: EvidenceStoreAdapter.lineage(), TrustLatticeAdapter
- **Severity**: CRITICAL

### T10: Receipt Tampering
- **Description**: Evaluation receipt modified after decision
- **Impact**: False audit trail
- **Mitigation**: I15 (Receipt must bind decision), WALAdapter, cryptographic binding
- **Severity**: CRITICAL

### T11: Infinite Reasoning Loop
- **Description**: Evaluation cycles indefinitely
- **Impact**: Resource exhaustion, denial of service
- **Mitigation**: MAX_ITERATIONS, REPEATED_STATE, CYCLIC_EVIDENCE_REQUEST, I13, I14
- **Severity**: HIGH

### T12: Cost Exhaustion
- **Description**: Evaluation consumes excessive resources
- **Impact**: Financial/resource damage
- **Mitigation**: MAX_COST, STOP_BUDGET, I13
- **Severity**: MEDIUM

### T13: Tool-Loop Amplification
- **Description**: Repeated tool calls amplify effect
- **Impact**: Unintended side effects
- **Mitigation**: REPEATED_TOOL_CALL, tool call history tracking
- **Severity**: HIGH

### T14: Stale Canonical Reference
- **Description**: Evaluation uses outdated canonical state
- **Impact**: Decisions based on old data
- **Mitigation**: CanonicalFingerprintProvider.schema_version(), version checks
- **Severity**: MEDIUM

### T15: Unknown-as-Zero Collapse
- **Description**: Unknown values treated as zero/false
- **Impact**: False negatives, missed risks
- **Mitigation**: I01 (Unknown ≠ zero), explicit UNKNOWN handling
- **Severity**: CRITICAL

### T16: Absence-as-Negative-Proof Error
- **Description**: Missing evidence treated as negative evidence
- **Impact**: False rejection of valid claims
- **Mitigation**: I02 (Absence of evidence ≠ evidence of absence)
- **Severity**: CRITICAL

### T17: Poisoned External Knowledge
- **Description**: External knowledge base contains malicious data
- **Impact**: Corrupted evaluation
- **Mitigation**: TrustLatticeAdapter, source verification, I03
- **Severity**: HIGH

### T18: Model Benchmark Overfitting
- **Description**: Model selected based on overfitted benchmarks
- **Impact**: Poor real-world performance
- **Mitigation**: M001 multi-role selection, scenario ranking, invalidation conditions
- **Severity**: MEDIUM

### T19: Single-Metric Model Selection
- **Description**: Model chosen by one arbitrary metric
- **Impact**: Suboptimal model for role
- **Mitigation**: M001 hard gates, Pareto frontier, scenario ranking
- **Severity**: MEDIUM

## Threat Matrix

| Threat | Severity | Likelihood | Risk | Key Invariant |
|--------|----------|------------|------|---------------|
| T01 | HIGH | MEDIUM | HIGH | I03 |
| T02 | CRITICAL | LOW | HIGH | I16, I08 |
| T03 | HIGH | MEDIUM | HIGH | Confidence Separation |
| T04 | HIGH | MEDIUM | HIGH | I03 |
| T05 | MEDIUM | LOW | MEDIUM | I03 |
| T06 | CRITICAL | LOW | HIGH | I08, I17 |
| T07 | HIGH | MEDIUM | HIGH | I09 |
| T08 | HIGH | LOW | MEDIUM | I10 |
| T09 | CRITICAL | LOW | HIGH | I15 |
| T10 | CRITICAL | LOW | HIGH | I15 |
| T11 | HIGH | MEDIUM | HIGH | I13, I14 |
| T12 | MEDIUM | MEDIUM | MEDIUM | I13 |
| T13 | HIGH | MEDIUM | HIGH | REPEATED_TOOL_CALL |
| T14 | MEDIUM | LOW | LOW | I16 |
| T15 | CRITICAL | HIGH | CRITICAL | I01 |
| T16 | CRITICAL | HIGH | CRITICAL | I02 |
| T17 | HIGH | MEDIUM | HIGH | TrustLattice |
| T18 | MEDIUM | MEDIUM | MEDIUM | M001 |
| T19 | MEDIUM | HIGH | HIGH | M001 |
