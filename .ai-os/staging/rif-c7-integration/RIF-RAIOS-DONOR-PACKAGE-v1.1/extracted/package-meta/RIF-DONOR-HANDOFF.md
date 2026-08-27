# RIF Donor Package Handoff v1.1

## From
- **Seat**: C7-CLOUD-SANDBOX
- **Role**: OFF_HOST_ARCHITECTURE_AND_ARTIFACT_WORKER
- **Wave**: RAIOS-RIF-DONOR-HARDENING-WAVE-02

## To
- **Expected**: C2-KAGGLE-CONTROL, C6-AG-REMOTE-RECON
- **Purpose**: Integration into RAIOS canonical systems

## Package Contents

This package contains:
1. **7 historical artifacts** (v1.0) with v1.1 adaptation notes
2. **Compatibility delta** (D-B) binding to RAIOS constraints
3. **12 adapter contracts** (D-C) for RAIOS integration
4. **StateGraph adaptation** (D-D) as evaluation-local state machine
5. **Evidence/Claim merge** (D-D) as logical view over RAIOS store
6. **Risk assessment donor** (D-D) feeding PolicyAdapter
7. **Governor CAP002** (D-D) as pure decision logic
8. **M001 spec/harness** (D-E) with multi-role selection
9. **A2A semantic bridge** (D-F) with explicit mismatch handling
10. **Threat model** (D-G) with 19 threats
11. **Formal invariants** (D-G) with 18 testable invariants
12. **56 deterministic tests** (D-H) across 14 categories
13. **Observability spec** (07) as adapter client
14. **Integration map** showing all RAIOS binding points

## Integration Instructions

### Step 1: Adapter Implementation
Implement the 12 adapter interfaces using existing RAIOS systems:
- CanonicalFingerprintProvider → RAIOS canonicalizer
- EvidenceStoreAdapter → Evidence-Trust-Lattice
- TrustLatticeAdapter → Evidence-Trust-Lattice
- WALAdapter → Existing WAL adapter
- ControlPlaneAdapter → UCP
- SemanticResolverAdapter → NeuroLingua
- PolicyAdapter → Policy Authority
- ObservabilitySinkAdapter → Existing observability
- ModelEcologyAdapter → RKG
- ModelFactoryAdapter → Model Factory
- MCPToolAdapter → MCP
- TransportAdapter → NATS

### Step 2: Conflict Resolution
- Retire C7 canonical_fingerprint
- Activate RAIOS canonicalization exclusively
- Verify I17 (no second canonicalizer)

### Step 3: Merge Execution
- Merge C7 ClaimGraph logical view with RAIOS evidence-trust-lattice
- C7 provides evaluation context
- RAIOS provides canonical storage

### Step 4: Test Execution
- Execute all 56 deterministic tests
- Verify all 18 invariants
- Confirm threat mitigations

### Step 5: Authority Binding
- Bind producer_verified fields to RAIOS identity system
- Remove free-form producer_seat="C7"

## Quality Verification

Before accepting package:
- [ ] All 12 adapters implemented
- [ ] No second canonicalizer active
- [ ] No second evidence store created
- [ ] Governor has no direct side effects
- [ ] RIF cannot directly promote canonical
- [ ] 56 tests pass
- [ ] 18 invariants verified
- [ ] A2A bridge handles mismatches correctly
- [ ] M001 output is machine-readable

## Contact
- Package created by: C7-CLOUD-SANDBOX
- Architecture direction: C3
- Authority: C1
- For questions: Reference SUPER_TASK_ID=RAIOS-RIF-DONOR-HARDENING-WAVE-02

## Classification
- **Status**: IMPLEMENTATION_READY_DONOR_PACKAGE
- **NOT**: CANONICAL, PRODUCTION_PROVEN, AG_PROVEN
- **Ready for**: C2/C6 integration work
