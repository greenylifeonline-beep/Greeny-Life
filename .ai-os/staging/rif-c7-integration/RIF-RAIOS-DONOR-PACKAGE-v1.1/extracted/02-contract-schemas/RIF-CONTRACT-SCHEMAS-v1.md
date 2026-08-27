# RIF Contract Schemas v1

## Purpose
Define the evaluation contract between RIF evaluator and claim submitter.

## Historical Design (v1.0)
- contract_id
- claim_scope: what is being evaluated
- evidence_requirements: minimum evidence types and quantities
- acceptance_criteria: pass/fail thresholds
- canonical_fingerprint: of the contract itself (RETIRED in v1.1)
- producer_seat: "C7" (RETIRED in v1.1)

## Schema Types
1. EVIDENCE_CONTRACT: binds evidence types to claims
2. EVALUATION_CONTRACT: binds evaluation procedure to claims
3. RISK_CONTRACT: binds risk thresholds to claims
4. GOVERNOR_CONTRACT: binds governor stop conditions to evaluation

## v1.0 Limitations
- No schema_version field
- No unknown-field policy
- No provenance reference chain
- Monolithic producer identity
- Assumed ownership of canonicalization

## v1.1 Adaptation Notes
- Added schema_version, producer, provenance_reference, extensions, unknown_field_policy
- Canonicalization externalized
- Identity decomposed per D-C
