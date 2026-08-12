# E3 Engine Decision Ledger — First Classification

Date: 2026-08-12  
Scope: 112 entries from `E3-RECON-OUTPUT/E3-ENGINE-CANDIDATES-DEEP.json` in the original E3 snapshot.  
Method: read-only static classification. This is not evidence that a candidate runs in the final repaired runtime.

## Result

| Classification | Count | Decision |
|---|---:|---|
| Current runtime candidate | 4 | Keep; prove execution and consumer path individually. |
| Reusable evidence brain | 18 | Extract only verified evidence, knowledge, graph, and provenance capabilities through adapters. |
| Reusable source review | 16 | Review one by one; reconnect only after a focused test. |
| Offline tool or script | 7 | Keep as controlled/offline tooling; never make it an automatic runtime dependency. |
| Legacy orchestrator | 1 | `brain.py`: extract useful functions only; do not run broad build/cleanup/evolution modes. |
| Historical or archived | 21 | Preserve as history; do not execute or merge directly. |
| Placeholder | 45 | Do not treat as capability or runtime. Preserve until an explicit consolidation decision. |

Total: 112.

## Current-runtime candidates found in the E3 engine list

- `app/api/workflow/route.ts`
- `canonical/intelligence/adapters/gl-dos-governance-gate.ts`
- `canonical/intelligence/runtime/controlled-runtime-orchestrator.ts`
- `canonical/lib/workflowEngine.ts`

The separate E3 runtime-candidate list also includes the original product, supplier, sales-order, and workflow APIs. That list contains archived copies too, so it cannot be treated as an active-runtime inventory without execution proof.

## High-value reusable capability groups

### Evidence and decision safety

- `greenlines_brain/evidence/models.py`
- `greenlines_brain/contract.py`
- `greenlines_brain/kernel.py`
- `greenlines_brain/graph.py`
- `greenlines_brain/repository/json_repo.py`

Disposition: adapt only the fail-closed evidence, provenance, graph, and reasoning contracts. Do not promote `greenlines_brain` to MasterMind or let it infer unsupported trade relationships.

### Integrity and canonical-data review

- `canonical/intelligence/intelligence/engines/data-integrity-engine.ts`
- `canonical/intelligence/intelligence/engines/audit-engine.ts`
- `canonical/intelligence/intelligence/core/report-writer.ts`

Disposition: controlled offline adapters. They need path, output-retention, and test hardening before adoption.

### Governance and workflow

- `canonical/intelligence/adapters/gl-dos-governance-gate.ts`
- `canonical/intelligence/runtime/controlled-runtime-orchestrator.ts`
- `canonical/lib/workflowEngine.ts`

Disposition: retain as the shared authorization and controlled execution boundary. Prove each entry point independently.

## Explicit non-runtime items

The 45 zero/one-line Domain and Application files are architectural placeholders, not implemented Domain/Application behavior. They must not be cited as an operating product, inventory, quality, supplier, logistics, or customer engine.

The 21 archived and duplicated entries must remain archival until compared against their canonical counterpart. No automatic merging or deletion is authorized by this classification.

`brain.py` is a 6,609-line legacy orchestrator. Its analysis, classification, and knowledge-extraction ideas may be extracted into controlled adapters. Its cleanup, construction, reporting, continuous-evolution, scheduler, and self-modifying modes must remain blocked from direct execution.

## Next proof gate for Greeny-Life Egypt Brain

For each capability the Egypt brain requests, record:

1. Candidate path and canonical owner.
2. Exact exported function or endpoint.
3. Inputs, outputs, data source, and side effects.
4. A repeatable safe test.
5. Current consumer in the repaired runtime.
6. Final disposition: `KEEP`, `RECONNECT`, `CONSOLIDATE`, `HARDEN`, or `DO_NOT_RUN`.

The first candidates to prove are the governance gate, controlled runtime orchestrator, workflow engine, evidence gate, canonical integrity engine, and the safe read-only parts of the legacy brain.

## Execution proof recorded on 2026-08-12

The following tests were run successfully in the repaired project. They are execution proof for the named behavior only; they do not prove complete end-to-end commercial readiness.

| Component | Proof | Result |
|---|---|---|
| Domain order-workflow rules | `npm run test:domain` | Passed transition blocking and landed-cost validation. |
| Canonical audit engine | `npm run test:canonical-intelligence` | Passed: 15 products checked, zero audit errors. |
| Canonical integrity engine | `npm run test:canonical-intelligence` | Passed: 15 canonical and unique products, health `HEALTHY`. |
| Three operating-brain authority model | `npm run test:operating-brains` | Passed: correct local-brain mapping and explicit approval rule. |
| Evidence gate | Python unit suite | Passed: missing evidence blocks export twice. |
| Evidence registry | Python unit suite | Passed: official evidence supports; missing/stale/unverified evidence requires review; prohibition is `NO_GO`. |

This establishes a minimal reusable core for Greeny-Life Egypt Brain: canonical data integrity, workflow validation, fail-closed evidence, and approval governance. It does not establish live ERP, production, supplier, QC, customs, pricing, or logistics integration.

## Workflow hardening decision

- `calculateLogisticsCost` is retained as a calculation only; every input is explicit and labelled unverified.
- `transitionOrderState` is retained as a controlled write only. The public API now submits a high-risk governance review and does not mutate an order while no durable approval record exists.

Disposition: `HARDEN`. The engine is not an autonomous execution engine.
## GL-DOS governance hardening decision

The legacy gate automatically authorized low- and medium-risk operations.
That behavior conflicts with the required approval model.

The repaired gate returns `REVIEW_REQUIRED` for LOW, MEDIUM, and HIGH
operations, and `DENIED` for CRITICAL operations. It does not issue an
execution authorization; a separate durable user-approval mechanism is required.

## `greenlines_brain` evidence-brain proof

The extracted knowledge runtime was tested against `Egypt / honey / Norway` and `Egypt / spices / EU`. Both scenarios returned `NEEDS_VERIFICATION` with `UNKNOWN` confidence, zero supporting evidence, and no `GO` decision.

Disposition: `KEEP_AS_EVIDENCE_AND_KNOWLEDGE_COMPONENT`. It is not MasterMind AI and not the Greeny-Life Egypt operational brain. It may supply evidence, provenance, knowledge-graph, and fail-closed reasoning capabilities through a controlled adapter only. Its identity mutation and any unscoped knowledge must not be used as trade authorization.

## Canonical integrity adapter proof

The canonical audit and data-integrity engines are read-only: they read `canonical/data/master_products.json` and return findings without writing, deleting, or altering source data. A unified adapter now supplies their health, source, timestamp, and boundaries to Greeny-Life Egypt Brain.

Disposition: `KEEP_AND_RECONNECT`. It validates the internal product reference only; it is not proof of live inventory, supplier approval, certificates, price, customs, or export eligibility.

## Operational-data freshness boundary

The Egypt stock, supplier, and shipment files currently contain reference timestamps dated 2026-08-07. A freshness adapter now exposes their age and marks records older than 24 hours as `STALE_REFERENCE`. These records can inform a review but cannot support automatic production, purchase, allocation, shipment, or export decisions.

Disposition: `HARDEN_BEFORE_LIVE_USE`. A connected, authenticated source with independently verified retrieval time is required before a record can be called `LIVE_CONFIRMED`.
