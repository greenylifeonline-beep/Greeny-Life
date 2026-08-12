# Import, Processing, Packaging, and Re-export Traceability

Each operational material movement receives a unique `traceCode` in the `TradeTraceRecord` ledger.

1. `RECEIVE_RAW_MATERIAL` registers a raw-material intake from an external supplier or one of the commercial companies.
2. `TRANSFORM_OR_PACKAGE` creates a child trace code that points to the parent source batch. It records processing or packaging without erasing origin.
3. `PLAN_REEXPORT` records the proposed next destination using the existing trace code as parent.

The permitted commercial holders are Greeny-Life Egypt, Greens Nature UAE, and Green Lines Norway/EU. MasterMind AI has no commercial ownership role.

All records begin as `REVIEW_REQUIRED`. This ledger does **not** execute shipment, customs filing, payment, legal title transfer, or issue certificates. Those actions require verified current evidence and authorized human approval.
