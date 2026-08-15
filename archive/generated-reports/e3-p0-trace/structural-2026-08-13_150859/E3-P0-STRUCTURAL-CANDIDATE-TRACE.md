# E3 P0 Structural Candidate Trace

Generated: 2026-08-13T13:09:23.2976731Z

## Scope

Read-only structural P0 candidate selection. Old/current archives, dependencies and build output excluded. A candidate is selected only from its domain path/name, not broad keywords.

| Capability | Legacy candidate | Current candidate | Entry points | Data | Tests (L/C) | Decision |
|---|---|---|---|---|---|---|
| Product | app/api/products/route.ts | app/api/products/route.ts | LEGACY:app/api/products/route.ts; CURRENT:app/api/products/route.ts | LEGACY:app/api/products/route.ts; CURRENT:app/api/products/route.ts | 0/2 | PENDING_ISOLATED_ACCEPTANCE |
| Supplier | app/api/suppliers/route.ts | app/api/suppliers/route.ts | LEGACY:app/api/suppliers/route.ts; CURRENT:app/api/suppliers/route.ts | LEGACY:app/api/suppliers/route.ts; CURRENT:app/api/suppliers/route.ts | 0/2 | PENDING_ISOLATED_ACCEPTANCE |
| Inventory | application/inventory/commands/inventory-command.ts | application/inventory/commands/inventory-command.ts | ;  | ;  | 0/0 | PENDING_ISOLATED_ACCEPTANCE |
| Customer | application/customer/commands/customer-command.ts | application/customer/commands/customer-command.ts | ;  | ;  | 0/0 | PENDING_ISOLATED_ACCEPTANCE |
| Logistics | application/logistics/commands/logistics-command.ts | application/logistics/commands/logistics-command.ts | ;  | ;  | 0/0 | PENDING_ISOLATED_ACCEPTANCE |
| Quality | application/quality/commands/quality-command.ts | tests/supplier_quality_review_check.ts | ;  | ;  | 0/0 | PENDING_ISOLATED_ACCEPTANCE |
| Orders |  | app/api/sales-orders/route.ts | ; CURRENT:app/api/sales-orders/route.ts | ; CURRENT:app/api/sales-orders/route.ts | 0/2 | PENDING_ISOLATED_ACCEPTANCE |
| Export |  | app/api/decisions/export-readiness/route.ts | ; CURRENT:app/api/decisions/export-readiness/route.ts | ;  | 0/2 | PENDING_ISOLATED_ACCEPTANCE |
| Compliance |  | app/api/decisions/official-evidence-review/route.ts | ; CURRENT:app/api/decisions/official-evidence-review/route.ts | ; CURRENT:app/api/decisions/official-evidence-review/route.ts | 0/2 | PENDING_ISOLATED_ACCEPTANCE |
| Evidence | build_evidence_layer.py | app/api/decisions/official-evidence-review/route.ts | ; CURRENT:app/api/decisions/official-evidence-review/route.ts | ; CURRENT:app/api/decisions/official-evidence-review/route.ts | 0/2 | PENDING_ISOLATED_ACCEPTANCE |
| Knowledge | greenlines_brain/graph.py | greenlines_brain/graph.py | ;  | ;  | 0/0 | PENDING_ISOLATED_ACCEPTANCE |
| Brain | brain.py | app/api/brains/greeny-life-egypt/route.ts | ; CURRENT:app/api/brains/greeny-life-egypt/route.ts | LEGACY:brain.py;  | 0/2 | PENDING_ISOLATED_ACCEPTANCE |
| Governance | app/api/workflow/route.ts | app/api/auth/login/route.ts | LEGACY:app/api/workflow/route.ts; CURRENT:app/api/auth/login/route.ts | ; CURRENT:app/api/auth/login/route.ts | 0/2 | PENDING_ISOLATED_ACCEPTANCE |

## Rule

UNKNOWN is preferred over a false candidate. No candidate is authoritative until isolated acceptance evidence is attached.

No source, database, archive, or external service was changed.
