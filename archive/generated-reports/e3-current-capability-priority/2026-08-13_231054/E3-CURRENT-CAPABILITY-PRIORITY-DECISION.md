# E3 Current Capability Priority Decision

## Selected P0 capability

**Greeny-Life Egypt export-readiness decision package**.

It uses existing Current components only. The current behavior is fail-closed: missing official evidence or commercial terms returns NOT_READY and never executes trade.

## Existing components to reuse

- `app/api/decisions/export-readiness/route.ts` â€” existing entry point.
- `lib/intelligence/export-decision.ts` â€” extend, do not replace.
- Egypt Brain, supplier-quality review, official-evidence gate, official-evidence registry and commercial-change registry â€” reuse.

## Proven tests

- Greeny-Life Egypt Brain: PASS
- Supplier quality: PASS
- Trade traceability: PASS
- Official evidence gate: PASS

## Controlled improvement

Extend the existing export-decision contract to consume persisted official evidence and approved in-date commercial facts. It must remain review-only, fail closed and free of schema change, Legacy execution and automatic execution.

## Decision

`APPROVED_FOR_CONTROLLED_IMPROVEMENT_PLANNING_ONLY` â€” implementation requires the listed targeted tests and isolated runtime proof.