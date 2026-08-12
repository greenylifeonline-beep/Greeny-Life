# Import, Processing, Packaging, and Re-export Traceability

Each operational material movement receives a unique `traceCode` in the `TradeTraceRecord` ledger.

## Consolidated legacy batch register

The historical `batch-traceability-v1` registers are not discarded or duplicated. The traceability API exposes them through a read-only adapter:

- `GET /api/traceability?legacy=true` — consolidated register and any detected inconsistency.
- `GET /api/traceability?traceCode=BATCH-H001-001` — resolves an existing historical batch when no current ledger record exists.

The export-operations snapshot is the preferred source because it includes product IDs; the ERP snapshot enriches missing origin information. Both are labeled historical reference, never current compliance evidence.

1. `RECEIVE_RAW_MATERIAL` registers a raw-material intake from an external supplier or one of the commercial companies.
2. `TRANSFORM_OR_PACKAGE` creates a child trace code that points to the parent source batch. It records processing or packaging without erasing origin.
3. `PLAN_REEXPORT` records the proposed next destination using the existing trace code as parent.

The permitted commercial holders are Greeny-Life Egypt, Greens Nature UAE, and Green Lines Norway/EU. MasterMind AI has no commercial ownership role.

All records begin as `REVIEW_REQUIRED`. This ledger does **not** execute shipment, customs filing, payment, legal title transfer, or issue certificates. Those actions require verified current evidence and authorized human approval.
