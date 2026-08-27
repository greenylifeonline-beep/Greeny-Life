# RIF Observability Provenance v1.1

## Classification
- TYPE: OBSERVABILITY_ADAPTER_SPEC
- SECOND_PROVENANCE_STORE: FALSE
- PROVENANCE_AUTHORITY: RAIOS

## Design Principle
Artifact 07 must NOT become a second provenance store.

`ObservabilityLogger` is conceptual adapter/client to existing RAIOS evidence/receipt infrastructure.

## Required Event Fields

Every observability event MUST include:

| Field | Type | Description |
|-------|------|-------------|
| RUN_ID | UUID | Unique run identifier |
| TASK_ID | String | Task reference from ControlPlaneAdapter |
| TRACE_ID | UUID | Distributed trace identifier |
| CORRELATION_ID | UUID | Correlation group for related events |
| CLAIM_ID | String | Claim being evaluated |
| EVIDENCE_ID | String | Evidence reference (if applicable) |
| MODEL_ID | String | Model used (if applicable) |
| POLICY_VERSION | String | Active policy version |
| SCHEMA_VERSION | String | Schema version in use |
| PRODUCER | Object | {declared, verified, component, version} |
| DECISION | String | Governor decision |
| REASON | String | Human-readable decision reason |
| COST | Decimal | Accumulated cost |
| STOP_REASON | String | Stop condition triggered (if stopped) |

## Timestamp Policy

```
DO NOT use volatile timestamp inside semantic identity fingerprint.
```

Timestamps are for observability ordering only, not identity.

## Adapter Interface

```
interface ObservabilityLogger {
  log_event(event: ObservabilityEvent) -> Boolean
  log_span(span: ObservabilitySpan) -> Boolean
  log_metric(metric: Metric) -> Boolean
}
```

All outputs route through `ObservabilitySinkAdapter` to existing RAIOS infrastructure.

## No Local Storage

- No local log files for provenance
- No local database for events
- No local cache for metrics
- All persistence through adapter

## Event Types

1. **EVALUATION_STARTED**: Run began
2. **STATE_TRANSITION**: State machine transition
3. **EVIDENCE_RECEIVED**: New evidence ingested
4. **CONTRADICTION_DETECTED**: Contradiction found
5. **RISK_ASSESSED**: Risk evaluation complete
6. **GOVERNOR_DECISION**: Governor rendered decision
7. **EVALUATION_COMPLETE**: Terminal state reached
8. **STOP_CONDITION**: Stop condition triggered
9. **ADAPTER_CALL**: External adapter invoked
10. **ERROR**: Error occurred
