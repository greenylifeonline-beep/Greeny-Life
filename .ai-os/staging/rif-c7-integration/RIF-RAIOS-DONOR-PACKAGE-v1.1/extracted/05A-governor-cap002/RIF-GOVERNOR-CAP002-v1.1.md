# RIF Governor CAP002 v1.1

## Classification
- TYPE: PURE_DECISION_LOGIC
- SIDE_EFFECTS: NONE_DIRECT
- PERSISTENCE: THROUGH_ADAPTERS_ONLY

## Design Principle
Governor must be PURE DECISION LOGIC.

### Forbidden Direct Actions
- ❌ Direct filesystem writes
- ❌ Direct WAL writes
- ❌ Direct NATS publish
- ❌ Direct model invocation
- ❌ Direct evidence store mutation
- ❌ Direct policy enforcement

### Required Interface
```
interface Governor {
  decide(input: GovernorInput) -> GovernorDecision
}
```

## Governor Input

```
struct GovernorInput {
  evaluation_state: EvaluationState
  evidence_status: EvidenceStatus
  risk_assessment: RiskAssessment
  iteration_count: Integer
  cost_accumulated: Decimal
  time_elapsed: Duration
  last_evidence_timestamp: Timestamp
  last_confidence_value: Decimal
  last_information_gain: Decimal
  state_history: StateHistory
  tool_call_history: ToolCallHistory
  contradiction_status: ContradictionStatus
  authority_status: AuthorityStatus
  policy_status: PolicyStatus
  resource_status: ResourceStatus
  goal_status: GoalStatus
}
```

## Governor Decision Output

1. **CONTINUE**: Proceed with evaluation
2. **REQUEST_EVIDENCE**: Need more evidence
3. **ABSTAIN**: Cannot reach conclusion
4. **PASS**: Evaluation passed
5. **FAIL**: Evaluation failed
6. **ESCALATE**: Requires higher authority
7. **STOP_BUDGET**: Budget limit reached
8. **STOP_NO_PROGRESS**: No progress detected
9. **STOP_POLICY**: Policy violation detected
10. **STOP_AUTHORITY_REQUIRED**: Authority needed
11. **STOP_CRITICAL_CONTRADICTION**: Unresolvable contradiction

## Stop Conditions (Expanded)

### Budget Limits
- **MAX_ITERATIONS**: Maximum evaluation iterations
- **MAX_COST**: Maximum cost threshold
- **MAX_TIME**: Maximum time allowed

### Progress Conditions
- **NO_NEW_EVIDENCE**: No new evidence in N cycles
- **NO_CONFIDENCE_GAIN**: Confidence not improving
- **NO_INFORMATION_GAIN**: No new information
- **REPEATED_STATE**: Cycling through same states
- **REPEATED_TOOL_CALL**: Same tool called with same params

### Quality Conditions
- **CYCLIC_EVIDENCE_REQUEST**: Evidence requests cycling
- **UNRESOLVED_CRITICAL_CONTRADICTION**: Cannot resolve contradiction
- **AUTHORITY_REQUIRED**: Needs authority not available
- **POLICY_DENIED**: Active policy denies continuation

### Resource Conditions
- **RESOURCE_EXHAUSTION**: Required resources unavailable
- **DEPENDENCY_UNAVAILABLE**: Required adapter/system down

### Success Conditions
- **GOAL_ACHIEVED**: Evaluation goal met

## Precedence Rules

When multiple stop conditions apply:

1. **STOP_CRITICAL_CONTRADICTION** (highest)
2. **STOP_POLICY**
3. **STOP_AUTHORITY_REQUIRED**
4. **STOP_BUDGET**
5. **STOP_NO_PROGRESS**
6. **RESOURCE_EXHAUSTION**
7. **DEPENDENCY_UNAVAILABLE**
8. **GOAL_ACHIEVED**
9. **FAIL**
10. **PASS**
11. **ABSTAIN**
12. **ESCALATE**
13. **REQUEST_EVIDENCE**
14. **CONTINUE** (lowest)

## Persistence

All governor decisions persisted through:
- WALAdapter.append()
- ObservabilitySinkAdapter.emit_event()
- ControlPlaneAdapter.update_status()

Never direct writes.
