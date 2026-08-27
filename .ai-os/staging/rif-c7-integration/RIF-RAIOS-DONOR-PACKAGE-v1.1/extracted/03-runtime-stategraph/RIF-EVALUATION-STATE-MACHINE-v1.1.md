# RIF Evaluation State Machine v1.1

## Classification
- TYPE: RUNTIME_ADAPTATION
- AUTHORITY: EVALUATION_LOCAL_ONLY
- GLOBAL_STATE_OWNERSHIP: FALSE

## Design Principle
C7 StateGraph is NOT authoritative runtime state. It is:
- `RIF_EVALUATION_STATE_MACHINE`
- Wraps/contributes decisions to existing UCP/lifecycle
- Owns ONLY evaluation-local state of one RIF run

## States

### Non-Terminal States
1. **RECEIVED**: Evaluation request received, not yet processed
2. **NORMALIZED**: Input normalized to canonical form
3. **VALIDATING**: Schema and contract validation in progress
4. **EVIDENCE_REQUIRED**: Insufficient evidence, gathering needed
5. **EVIDENCE_GATHERED**: Evidence collection complete
6. **CONTRADICTION_CHECK**: Checking for contradictions in evidence
7. **EVALUATING**: Core evaluation logic executing
8. **UNCERTAINTY_CHECK**: Assessing uncertainty levels
9. **RISK_CHECK**: Risk assessment in progress
10. **GOVERNOR_DECISION**: Governor reviewing evaluation

### Terminal/Local Outcomes
- **PASS**: Evaluation passed all criteria
- **FAIL**: Evaluation failed criteria
- **ABSTAIN**: Cannot reach definitive conclusion
- **ESCALATE**: Requires higher authority
- **NEEDS_MORE_EVIDENCE**: Insufficient evidence, return to EVIDENCE_REQUIRED
- **BLOCKED**: Illegal state or policy violation, fail closed

### Promotion Advisory (NOT Canonical)
- **DISCOVERED**: Claim identified for potential promotion
- **VALIDATED**: Claim validated against criteria
- **CANONICAL_CANDIDATE**: Ready for canonical review by RAIOS authority
- **NEVER CANONICAL DIRECTLY** — RIF cannot promote to canonical

## Transition Contract

Every transition MUST specify:
- **FROM**: Source state
- **TO**: Target state
- **TRIGGER**: Event causing transition
- **PRECONDITIONS**: Required conditions for transition
- **GUARDS**: Boolean checks (all must pass)
- **EVIDENCE_REQUIRED**: Evidence needed for this transition
- **RISK_EFFECT**: Risk impact of this transition
- **OBSERVABILITY_EVENT**: Event emitted on transition
- **FAILURE_PATH**: State to enter if transition fails

### Illegal Transition Handling
- Any transition not explicitly defined: **BLOCKED**
- Fail closed — no silent allowance
- No hidden LLM-driven state transitions

### Example: VALIDATING → EVIDENCE_REQUIRED
```
FROM: VALIDATING
TO: EVIDENCE_REQUIRED
TRIGGER: validation.evidence_insufficient
PRECONDITIONS: [contract.evidence_minimum_defined]
GUARDS: [evidence.count < contract.evidence_minimum]
EVIDENCE_REQUIRED: false (this IS the evidence request)
RISK_EFFECT: delay_risk + uncertainty_increase
OBSERVABILITY_EVENT: EVIDENCE_SHORTFALL
FAILURE_PATH: BLOCKED
```

### Example: EVALUATING → GOVERNOR_DECISION
```
FROM: EVALUATING
TO: GOVERNOR_DECISION
TRIGGER: evaluation.complete
PRECONDITIONS: [evaluation.result_ready, contradiction.check_passed]
GUARDS: [uncertainty < threshold, risk.assessed]
EVIDENCE_REQUIRED: true (all evidence must be bound)
RISK_EFFECT: evaluation_risk_committed
OBSERVABILITY_EVENT: EVALUATION_COMPLETE
FAILURE_PATH: ABSTAIN
```

## State Ownership Boundaries

| Aspect | C7 Owns | RAIOS Owns |
|--------|---------|------------|
| Evaluation-local state | ✓ | |
| Global task authority | | ✓ |
| Canonical repository state | | ✓ |
| System-wide execution authority | | ✓ |
| Evidence storage | | ✓ |
| Policy enforcement | | ✓ |
| Canonical promotion | | ✓ |
