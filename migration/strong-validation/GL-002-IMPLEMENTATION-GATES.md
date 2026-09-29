# GL-002 IMPLEMENTATION GATES

Scope reminder: GL-002 owns `intelligence/`, `governance/`, `canonical/` — not `app/` (GL-004) and not project-brain bridges (GL-003), except where authority docs/adapters live in canonical.

## SAFE_TO_IMPLEMENT

1. **Record durable decision:** Main Brain runtime authority = MasterMind TS path (`lib/intelligence/mastermind-agents.ts` + `app/api/mastermind/**`), with `brain.py` classified LEGACY.
   - Gate owner after human confirmation: GL-002 agent writing only governance/decision docs under allowed scope.
2. **Inventory-only labeling** of top-level `intelligence/*.json` and empty `intelligence/intelligence/**` stubs as NON_RUNTIME / ARCHIVE_CANDIDATE without deleting or moving files yet.
3. **Document** that `ControlledRuntimeOrchestrator` + `GLDOSGovernanceGate` are write-governance, not Main Brain decision authority.
4. **Do not treat** scout “52 duplicate basenames” as 52 duplicate implementations; only evidence-backed duplicates (below) matter.

## NEEDS_RUNTIME_PROOF

1. Any change that alters MasterMind package shape or agent composition.
2. Any change to `GLDOSGovernanceGate` risk outcomes (currently all non-CRITICAL → `REVIEW_REQUIRED`).
3. Wiring MasterMind to call project-brain HTTP endpoints (depends on GL-003 bridges existing).

## NEEDS_TEST_PROOF

1. Expanding MasterMind agents beyond current read-only set.
2. Changes to `three-operating-brains.ts` escalation/approval contracts (covered today by `tests/three_operating_brains_check.ts`).
3. Changes to tool-registry dispositions (`tests/tool_registry_check.ts`).

## NEEDS_DB_PROOF

1. MasterMind evidence agent paths that call `prisma.officialEvidenceRegistry.findMany` (`tests/mastermind_agents_check.ts` fails without DB).
2. Any governance change that depends on `SecurityAuditEvent` persistence (`lib/authz.ts`).

## NEEDS_HUMAN_DECISION

1. Whether the product term **“Main Brain”** is formally aliased to **MasterMind AI** in RAIOS decisions.
2. Disposition of multi-megabyte `intelligence/ast_*.json` reports (retain archive vs relocate outside runtime tree).
3. Which `governance/eos-canonical-truth-registry-v*.json` version is authoritative if any must bind to runtime.
4. Whether EOS/GELS remain specialized modules under MasterMind (current evidence) or become separate peer authorities (not supported by runtime imports today).

## DO_NOT_IMPLEMENT

1. **Do not** make `brain.py` an application runtime entry point.
2. **Do not** import/execute `brain.py` from Next routes or MasterMind agents.
3. **Do not** delete `brain.py` or `greenlines_brain/` without a separate archive/migration decision.
4. **Do not** implement UAE/Norway REST bridges under GL-002 scope (belongs to GL-003 / runtime worktrees).
5. **Do not** create a second decision-package assembler parallel to `buildMasterMindDecisionPackage`.
6. **Do not** promote archive `controlled-runtime-orchestrator.ts` into active imports.
7. **Do not** trust deepseek scout narratives as authority maps without re-verification.

## UNPROVEN

1. Claim that EOS “enterprise blueprint” JSONs under `intelligence/` govern live execution.
2. Claim that all 526 “main brain candidates” are meaningful authorities (inventory artifact).
3. Claim that legacy `brain.py` Arabic/ops content is fully superseded by MasterMind (partial supersession verified for decision path only).

## Evidence-backed duplicate resolution (not 52)

| Signal | Verdict |
|---|---|
| 29× `route.ts` | Normal Next.js App Router basenames — **not** duplicate authorities |
| 3× `page.tsx` | Normal pages — **not** duplicate authorities |
| `canonical/.../controlled-runtime-orchestrator.ts` vs `archive/old_folders/.../controlled-runtime-orchestrator.ts` | **Duplicate residue**; only canonical is imported by `app/` |
| `brain.py` vs MasterMind | **Competing historical identity**; runtime winner = MasterMind |
| Empty `intelligence/intelligence/*/index.ts` vs `lib/intelligence/*` | Empty stubs **non-runtime**; lib is active |
