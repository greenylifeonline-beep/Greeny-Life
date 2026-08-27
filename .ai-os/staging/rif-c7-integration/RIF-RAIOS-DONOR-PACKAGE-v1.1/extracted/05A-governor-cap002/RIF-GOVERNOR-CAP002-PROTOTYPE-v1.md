# RIF Governor CAP002 Prototype v1

## Purpose
Decision logic for when to continue, stop, or escalate evaluation.

## Historical Design (v1.0)
- Stop conditions: MAX_ITERATIONS, MAX_COST, MAX_TIME
- Could write to filesystem directly (FORBIDDEN in v1.1)
- Could write to WAL directly (FORBIDDEN in v1.1)
- Could publish to NATS directly (FORBIDDEN in v1.1)
- Could invoke models directly (FORBIDDEN in v1.1)

## Historical Limitations
- Insufficient stop conditions
- No precedence rules for multiple stop conditions
- Direct side effects instead of pure decision logic
- No adapter-based persistence

## v1.1 Adaptation Notes
- Governor must be PURE DECISION LOGIC
- Interface: GovernorInput → GovernorDecision
- Output: CONTINUE, REQUEST_EVIDENCE, ABSTAIN, PASS, FAIL, ESCALATE, STOP_BUDGET, STOP_NO_PROGRESS, STOP_POLICY, STOP_AUTHORITY_REQUIRED, STOP_CRITICAL_CONTRADICTION
- Persistence through adapters supplied by RAIOS
- Expanded stop conditions per D-D
- Precedence rules defined
