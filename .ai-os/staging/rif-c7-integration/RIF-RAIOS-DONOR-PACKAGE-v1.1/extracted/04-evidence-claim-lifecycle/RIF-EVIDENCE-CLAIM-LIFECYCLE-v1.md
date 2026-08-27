# RIF Evidence/Claim Lifecycle v1

## Purpose
Model the relationship between evidence and claims during evaluation.

## Historical Design (v1.0)
- ClaimGraph: local graph of claims and evidence
- Evidence nodes linked to claim nodes
- Relationships: SUPPORTS, REFUTES, QUALIFIES
- Local evidence storage (FORBIDDEN in v1.1)

## Historical Limitations
- Second evidence store (violation of TREE-001)
- No lineage tracking
- No correlation grouping
- Duplicate evidence counted as independent
- No trust lattice integration

## v1.1 Adaptation Notes
- ClaimGraph becomes LOGICAL/EVALUATION VIEW over EvidenceStoreAdapter + TrustLatticeAdapter
- Required relationships expanded: SUPPORTS, REFUTES, QUALIFIES, CONTRADICTS, DUPLICATES, SUPERSEDES, DERIVED_FROM, INSUFFICIENT_FOR
- Explicit modeling: ORIGIN_SOURCE_ID, EVIDENCE_LINEAGE_ID, CORRELATION_GROUP
- Copies from same origin do NOT count as independent evidence
- Integrates with existing RAIOS evidence-trust-lattice (merge candidate per TREE-001)
