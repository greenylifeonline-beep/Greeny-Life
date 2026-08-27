# RIF Evidence-Claim Merge Specification v1.1

## Design Principle
Do NOT create second evidence store. ClaimGraph is:
- LOGICAL / EVALUATION VIEW
- over
- EvidenceStoreAdapter + TrustLatticeAdapter

## Relationship Types

### Core Relationships
1. **SUPPORTS**: Evidence supports claim
2. **REFUTES**: Evidence refutes claim
3. **QUALIFIES**: Evidence qualifies/limits claim scope
4. **CONTRADICTS**: Evidence contradicts other evidence
5. **DUPLICATES**: Evidence duplicates other evidence (same origin)
6. **SUPERSEDES**: Evidence supersedes older evidence
7. **DERIVED_FROM**: Evidence derived from other evidence
8. **INSUFFICIENT_FOR**: Evidence insufficient for claim

### Lineage Model

Every evidence item MUST track:
- **ORIGIN_SOURCE_ID**: Original source identifier
- **EVIDENCE_LINEAGE_ID**: Chain of derivation
- **CORRELATION_GROUP**: Grouping for correlated evidence

### Independence Rule
```
Copies derived from same origin MUST NOT count as independent evidence.
```

**INVARIANT I03**: Duplicate lineage ≠ independent source

## Evidence Evaluation Flow

1. Evidence submitted → EvidenceStoreAdapter.store()
2. TrustLatticeAdapter.evaluate_trust(source_id)
3. ClaimGraph creates logical view
4. Correlation groups identified
5. Independence verified
6. Strength assessed per relationship type
7. Contradictions flagged
8. Governor reviews

## Integration with RAIOS Evidence-Trust-Lattice

Per TREE-001 merge requirement:
- C7 provides: logical view, evaluation context, claim scope
- RAIOS provides: canonical storage, trust lattice, provenance chain
- C7 does NOT: store evidence permanently, define trust rules, own provenance
