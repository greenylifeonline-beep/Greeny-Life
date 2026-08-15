# E3 System of Record â€” P0 Map

Generated: 2026-08-13T13:02:20.0001961Z

## Scope

Read-only static map. Legacy and current sources are compared but are not merged. No source, database, archive, or external service was changed.

| Capability | Legacy | Current | API | Data | Events | Tests | Status | Decision |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Product | 52 | 108 | 13 | 21 | 0 | 16 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Supplier | 28 | 57 | 6 | 13 | 0 | 6 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Inventory | 19 | 50 | 4 | 9 | 0 | 11 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Customer | 18 | 28 | 2 | 5 | 0 | 2 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Logistics | 20 | 51 | 6 | 12 | 0 | 7 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Quality | 21 | 51 | 4 | 10 | 0 | 6 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Orders | 4 | 8 | 1 | 7 | 0 | 2 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Export | 63 | 162 | 27 | 30 | 1 | 32 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Compliance | 20 | 44 | 2 | 9 | 0 | 3 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Evidence | 20 | 70 | 8 | 15 | 0 | 15 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Knowledge | 21 | 27 | 0 | 2 | 1 | 2 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Brain | 52 | 92 | 8 | 9 | 1 | 11 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |
| Governance | 15 | 77 | 18 | 25 | 0 | 15 | BOTH_PRESENT_STATIC_ONLY | PENDING_OWNER_AND_RUNTIME_TRACE |

## Rules

- Static evidence is not runtime proof.
- CURRENT is not automatically authoritative merely because it is newer.
- LEGACY is not automatically reusable merely because it exists.
- No REUSE/HARDEN/CONSOLIDATE/RETIRE decision is authorized until owner and runtime trace are completed.

## Next gate

For P0 decisions: Evidence, Governance, Product, Supplier, Inventory, Orders, Logistics, Export, Compliance, Knowledge, Brain. Assign an owner and execute isolated acceptance traces only for the candidate selected as potential system of record.
