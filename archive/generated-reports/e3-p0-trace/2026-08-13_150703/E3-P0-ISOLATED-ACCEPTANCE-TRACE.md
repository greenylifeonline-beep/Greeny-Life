# E3 P0 Isolated Acceptance Trace

Generated: 2026-08-13T13:07:14.3702767Z

## Scope

P0 candidates only. Read-only source tracing; archived/historical paths, dependencies and build output excluded. No legacy or current source was executed or changed.

| Capability | Legacy candidate | Current candidate | Entry point | Data | Legacy tests | Current tests | Runtime | System of Record |
|---|---|---|---|---|---:|---:|---|---|
| Product | app/api/products/route.ts | app/api/products/route.ts | LEGACY:app/api/products/route.ts; CURRENT:app/api/products/route.ts | LEGACY:app/api/products/route.ts; CURRENT:app/api/products/route.ts | 0 | 3 | CURRENT_BUILD/SMOKE_PARTIAL | PENDING_ACCEPTANCE_TRACE |
| Supplier | app/api/suppliers/route.ts | app/api/suppliers/route.ts | LEGACY:app/api/suppliers/route.ts; CURRENT:app/api/suppliers/route.ts | LEGACY:app/api/suppliers/route.ts; CURRENT:app/api/suppliers/route.ts | 0 | 3 | CURRENT_BUILD/SMOKE_PARTIAL | PENDING_ACCEPTANCE_TRACE |
| Inventory | canonical/lib/workflowEngine.ts | app/api/tasks/route.ts | CURRENT:app/api/tasks/route.ts | LEGACY:canonical/lib/workflowEngine.ts; CURRENT:app/api/tasks/route.ts | 0 | 2 | UNPROVEN | PENDING_ACCEPTANCE_TRACE |
| Customer | app/api/sales-orders/route.ts | app/api/sales-orders/route.ts | LEGACY:app/api/sales-orders/route.ts; CURRENT:app/api/sales-orders/route.ts | LEGACY:app/api/sales-orders/route.ts; CURRENT:app/api/sales-orders/route.ts | 0 | 2 | CURRENT_BUILD/SMOKE_PARTIAL | PENDING_ACCEPTANCE_TRACE |
| Logistics | app/api/workflow/route.ts | app/api/traceability/route.ts | LEGACY:app/api/workflow/route.ts; CURRENT:app/api/traceability/route.ts | CURRENT:app/api/traceability/route.ts | 0 | 4 | UNPROVEN | PENDING_ACCEPTANCE_TRACE |
| Quality | brain.py | app/api/auth/login/route.ts | CURRENT:app/api/auth/login/route.ts | LEGACY:brain.py; CURRENT:app/api/auth/login/route.ts | 0 | 4 | UNPROVEN | PENDING_ACCEPTANCE_TRACE |
| Orders | app/api/sales-orders/route.ts | app/api/sales-orders/route.ts | LEGACY:app/api/sales-orders/route.ts; CURRENT:app/api/sales-orders/route.ts | LEGACY:app/api/sales-orders/route.ts; CURRENT:app/api/sales-orders/route.ts | 0 | 2 | CURRENT_BUILD/SMOKE_PARTIAL | PENDING_ACCEPTANCE_TRACE |
| Export | app/api/products/route.ts | app/api/tasks/route.ts | LEGACY:app/api/products/route.ts; CURRENT:app/api/tasks/route.ts | LEGACY:app/api/products/route.ts; CURRENT:app/api/tasks/route.ts | 0 | 2 | UNPROVEN | PENDING_ACCEPTANCE_TRACE |
| Compliance | app/api/products/route.ts | app/api/products/route.ts | LEGACY:app/api/products/route.ts; CURRENT:app/api/products/route.ts | LEGACY:app/api/products/route.ts; CURRENT:app/api/products/route.ts | 0 | 4 | CURRENT_BUILD/SMOKE_PARTIAL | PENDING_ACCEPTANCE_TRACE |
| Evidence | brain.py | app/api/evidence/official/route.ts | CURRENT:app/api/evidence/official/route.ts | LEGACY:brain.py; CURRENT:app/api/evidence/official/route.ts | 0 | 6 | CURRENT_BUILD/SMOKE_PARTIAL | PENDING_ACCEPTANCE_TRACE |
| Knowledge | brain.py | brain.py | NO_SELECTED_API_ENTRYPOINT | LEGACY:brain.py; CURRENT:brain.py | 0 | 6 | UNPROVEN | PENDING_ACCEPTANCE_TRACE |
| Brain | brain.py | app/api/tasks/route.ts | CURRENT:app/api/tasks/route.ts | LEGACY:brain.py; CURRENT:app/api/tasks/route.ts | 0 | 7 | UNPROVEN | PENDING_ACCEPTANCE_TRACE |
| Governance | canonical/lib/workflowEngine.ts | app/api/auth/login/route.ts | CURRENT:app/api/auth/login/route.ts | LEGACY:canonical/lib/workflowEngine.ts; CURRENT:app/api/auth/login/route.ts | 0 | 7 | UNPROVEN | PENDING_ACCEPTANCE_TRACE |

## Next gate

For each P0 capability, run only the selected CURRENT candidate through an acceptance test; run the selected LEGACY candidate only in a disposable isolated environment after reviewing side effects. Then assign owner, authority, System of Record, and reuse decision.

No source, database, archive, or external service was changed.
