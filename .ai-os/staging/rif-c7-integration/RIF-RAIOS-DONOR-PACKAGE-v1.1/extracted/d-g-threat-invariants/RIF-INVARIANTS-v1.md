# RIF Formal Invariants v1

## Classification
- TYPE: FORMAL_INVARIANTS
- TESTABLE: YES
- VERIFICATION: DETERMINISTIC_TEST_SUITE

## Invariant Definitions

### I01: UNKNOWN_NE_ZERO
```
∀x: EvaluationValue(x) ∧ Status(x, UNKNOWN) → Value(x) ≠ 0
```
**Test**: Submit claim with unknown evidence, verify not treated as zero
**Failure**: Claim rejected due to zero-value assumption
**Severity**: CRITICAL

### I02: ABSENCE_OF_EVIDENCE_NE_EVIDENCE_OF_ABSENCE
```
∀c: Claim(c) ∧ ¬∃e: Evidence(e) ∧ Supports(e, c) → ¬Proven(¬c)
```
**Test**: Claim with no evidence must not be auto-refuted
**Failure**: System rejects claim due to missing evidence
**Severity**: CRITICAL

### I03: DUPLICATE_LINEAGE_NE_INDEPENDENT_SOURCE
```
∀e1,e2: Evidence(e1) ∧ Evidence(e2) ∧ OriginSource(e1) = OriginSource(e2) → Independent(e1, e2) = FALSE
```
**Test**: Submit same evidence twice, verify counted as one
**Failure**: Confidence inflated by duplicate submission
**Severity**: HIGH

### I04: CI_PASS_NE_CAPABILITY_PROOF
```
∀c: CIPass(c) → ¬CapabilityProven(c)
```
**Test**: CI passing does not auto-prove capability
**Failure**: CI pass treated as capability proof
**Severity**: HIGH

### I05: TRANSPORT_SUCCESS_NE_CLAIM_TRUTH
```
∀m: TransportSuccess(m) → ¬ClaimTrue(Content(m))
```
**Test**: Successful message delivery ≠ claim validation
**Failure**: A2A completion treated as RIF pass
**Severity**: HIGH

### I06: GOVERNOR_CANNOT_EXECUTE
```
∀g: Governor(g) → ¬ExecuteAction(g)
```
**Test**: Governor output must not trigger direct execution
**Failure**: Governor writes to WAL directly
**Severity**: CRITICAL

### I07: RIF_CANNOT_DIRECTLY_PROMOTE_CANONICAL
```
∀r: RIF(r) → ¬PromoteToCanonical(r)
```
**Test**: RIF evaluation must not emit canonical promotion
**Failure**: RIF claims CANONICAL status
**Severity**: CRITICAL

### I08: UNTRUSTED_AUTHORITY_CANNOT_GRANT
```
∀a: Authority(a) ∧ ¬Trusted(a) → ¬GrantAuthority(a, x)
```
**Test**: Untrusted source cannot grant authority
**Failure: Self-asserted authority accepted
**Severity**: CRITICAL

### I09: SEMANTIC_MISMATCH_FAILS_CLOSED
```
∀m: SemanticMismatch(m) → Action(m) = BLOCK ∨ Action(m) = ESCALATE
```
**Test**: Incompatible semantics must not proceed silently
**Failure**: Mismatch silently ignored
**Severity**: HIGH

### I10: ILLEGAL_STATE_TRANSITION_BLOCKED
```
∀t: Transition(t) ∧ ¬Legal(t) → Blocked(t)
```
**Test**: Undefined state transition must be blocked
**Failure**: Illegal transition allowed
**Severity**: HIGH

### I11: POLICY_DENIED_CANNOT_PASS
```
∀e: Evaluation(e) ∧ PolicyDenied(e) → Result(e) ≠ PASS
```
**Test**: Policy denial must prevent pass
**Failure**: Pass achieved despite policy denial
**Severity**: CRITICAL

### I12: CRITICAL_CONTRADICTION_CANNOT_SILENT_PASS
```
∀e: Evaluation(e) ∧ CriticalContradiction(e) → Result(e) ≠ PASS ∧ Observable(e)
```
**Test**: Critical contradiction must block pass and be observable
**Failure**: Pass with hidden contradiction
**Severity**: CRITICAL

### I13: BUDGET_LIMIT_ENFORCED
```
∀e: Evaluation(e) ∧ BudgetExceeded(e) → Stopped(e)
```
**Test**: Budget exhaustion must stop evaluation
**Failure**: Evaluation continues past budget
**Severity**: HIGH

### I14: NO_PROGRESS_TERMINATES
```
∀e: Evaluation(e) ∧ NoProgress(e, N) → Stopped(e)
```
**Test**: No progress for N cycles must terminate
**Failure**: Infinite loop on no progress
**Severity**: HIGH

### I15: RECEIPT_MUST_BIND_DECISION
```
∀r: Receipt(r) → ∃d: Decision(d) ∧ Bound(r, d) ∧ Immutable(r)
```
**Test**: Receipt must cryptographically bind to decision
**Failure**: Receipt modifiable or unbound
**Severity**: CRITICAL

### I16: FINGERPRINT_PROVIDER_EXTERNALIZED
```
∀f: Fingerprint(f) → Provider(f) ≠ C7
```
**Test**: Fingerprint provider must be external
**Failure**: C7 provides canonical fingerprints
**Severity**: CRITICAL

### I17: SECOND_CANONICALIZER_FORBIDDEN
```
¬∃c: Canonicalizer(c) ∧ c ≠ RAIOS_Canonicalizer ∧ Active(c)
```
**Test**: No second canonicalizer may be active
**Failure**: C7 canonicalizer active alongside RAIOS
**Severity**: CRITICAL

### I18: MODEL_SELECTION_REPRODUCIBLE_FROM_EVIDENCE
```
∀s: Selection(s) → ∃e: Evidence(e) ∧ Reproducible(s, e)
```
**Test**: M001 selection must be reproducible from stored evidence
**Failure**: Selection cannot be re-run or challenged
**Severity**: HIGH

## Invariant Verification Matrix

| Invariant | Category | Test Count | Automation |
|-----------|----------|------------|------------|
| I01 | Semantic | 3 | Full |
| I02 | Semantic | 3 | Full |
| I03 | Evidence | 4 | Full |
| I04 | CI/Build | 2 | Full |
| I05 | Transport | 3 | Full |
| I06 | Governor | 3 | Full |
| I07 | Canonical | 3 | Full |
| I08 | Authority | 3 | Full |
| I09 | Semantic | 3 | Full |
| I10 | State | 4 | Full |
| I11 | Policy | 3 | Full |
| I12 | Contradiction | 3 | Full |
| I13 | Budget | 3 | Full |
| I14 | Progress | 3 | Full |
| I15 | Receipt | 3 | Full |
| I16 | Canonical | 3 | Full |
| I17 | Canonical | 2 | Full |
| I18 | M001 | 3 | Full |
