# E3 Legacy Engine Deep Trace

Generated: 2026-08-13T13:00:09.2494871Z

## Scope

Actual old project only. Static/read-only call and dependency trace. No legacy code was executed; replacement runtime and database excluded.

| Candidate | Kind | Consumers | Persistence | Event impl. | Risk | Verdict |
|---|---|---:|---|---|---|---|
| application/customer/workflows/customer-workflow.ts | APPLICATION_WORKFLOW | 1 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | EXTRACT_OR_REUSE_CANDIDATE_AFTER_TEST |
| application/inventory/workflows/inventory-workflow.ts | APPLICATION_WORKFLOW | 1 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | EXTRACT_OR_REUSE_CANDIDATE_AFTER_TEST |
| application/logistics/workflows/logistics-workflow.ts | APPLICATION_WORKFLOW | 1 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | EXTRACT_OR_REUSE_CANDIDATE_AFTER_TEST |
| application/product/workflows/product-workflow.ts | APPLICATION_WORKFLOW | 1 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | EXTRACT_OR_REUSE_CANDIDATE_AFTER_TEST |
| application/quality/workflows/quality-workflow.ts | APPLICATION_WORKFLOW | 0 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | EXTRACT_OR_REUSE_CANDIDATE_AFTER_TEST |
| application/supplier/workflows/supplier-workflow.ts | APPLICATION_WORKFLOW | 1 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | EXTRACT_OR_REUSE_CANDIDATE_AFTER_TEST |
| canonical/intelligence/intelligence/engines/audit-engine.ts | AUDIT_ENGINE | 11 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | EXTRACT_OR_REUSE_CANDIDATE_AFTER_TEST |
| canonical/intelligence/intelligence/engines/data-integrity-engine.ts | DATA_INTEGRITY_ENGINE | 1 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | EXTRACT_OR_REUSE_CANDIDATE_AFTER_TEST |
| canonical/intelligence/intelligence/health/health-reporter.ts | HEALTH_REPORTER | 0 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | TRACE_AND_TEST_BEFORE_DECISION |
| canonical/intelligence/runtime/controlled-runtime-orchestrator.ts | RUNTIME_ORCHESTRATOR | 0 | False | False | NO_HIGH_RISK_STATIC_SIGNAL | TRACE_AND_TEST_BEFORE_DECISION |
| canonical/lib/workflowEngine.ts | PERSISTED_WORKFLOW_ENGINE | 4 | True | False | NO_HIGH_RISK_STATIC_SIGNAL | RECONNECT_CANDIDATE_AFTER_ISOLATED_TEST |

## Next gate

Isolated tests for selected P0 candidates only: persisted workflow engine, controlled runtime orchestrator, data integrity engine, audit engine, then the six application workflows.

No source was executed, changed, moved, merged, renamed, or deleted.
