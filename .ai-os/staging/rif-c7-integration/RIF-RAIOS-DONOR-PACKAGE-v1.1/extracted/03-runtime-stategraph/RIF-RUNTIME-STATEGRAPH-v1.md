# RIF Runtime StateGraph v1

## Purpose
Track evaluation state transitions during a single RIF evaluation run.

## Historical Design (v1.0)
- Nodes: evaluation states
- Edges: transitions triggered by events
- State ownership: assumed global (INCORRECT)
- Could initiate canonical promotion (FORBIDDEN in v1.1)

## Historical States
- INITIALIZED
- EVIDENCE_COLLECTING
- EVALUATING
- RISK_ASSESSING
- GOVERNOR_REVIEW
- COMPLETED
- FAILED

## Historical Transitions
- Event-driven, some LLM-mediated (FORBIDDEN in v1.1)
- No explicit preconditions/guards on all transitions
- No risk_effect annotation on transitions

## v1.0 Limitations
- Claimed authority over runtime state beyond evaluation scope
- Could emit canonical promotion signals
- Hidden LLM state transitions
- No illegal transition blocking

## v1.1 Adaptation Notes
- Renamed to RIF_EVALUATION_STATE_MACHINE
- Owns ONLY evaluation-local state
- All transitions have explicit FROM/TO/TRIGGER/PRECONDITIONS/GUARDS/EVIDENCE_REQUIRED/RISK_EFFECT/OBSERVABILITY_EVENT/FAILURE_PATH
- Illegal transitions BLOCKED (fail closed)
- No hidden LLM transitions
- Terminal outcomes limited to: PASS, FAIL, ABSTAIN, ESCALATE, NEEDS_MORE_EVIDENCE, BLOCKED
- Promotion advisory only: DISCOVERED, VALIDATED, CANONICAL_CANDIDATE (never CANONICAL directly)
