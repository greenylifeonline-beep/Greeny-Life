# FINAL NEXT ACTION

## Current authoritative state

GL-002:
PARTIAL — authority/validation phase closed.

GL-003:
PARTIAL — Egypt verified; UAE/Norway deferred as MISSING.

GL-004:
NEXT CRITICAL PATH.

GL-005:
NOT_READY.

---

## Next exact action

Perform GL-004 REAL DATABASE PROOF in:

`raios/gl-004-runtime`

The objective is NOT new feature development.

The objective is to replace placeholder-only database confidence with real integration evidence.

Required proof should establish, as applicable:

1. real `DATABASE_URL`,
2. successful Prisma connection against the intended database,
3. schema compatibility,
4. required migrations/state,
5. relevant DB-dependent test execution,
6. runtime behavior required by Wave 2,
7. evidence sufficient to classify the DB gate PASS / PARTIAL / BLOCKED.

---

## Explicitly deferred

Do not implement UAE/Norway brains.

Do not create fake bridges.

Do not alter MasterMind authority.

Do not converge GL-005.

Do not archive or delete `brain.py`.

---

## Re-entry condition for GL-003

Return to UAE/Norway implementation only when verified source/runtime evidence exists or when the human operator explicitly changes the current MISSING policy.

---

## GL-005 convergence condition

GL-005 remains blocked until:

- GL-004 real DB proof is resolved,
- required runtime/test gates are satisfied,
- any convergence-critical UNPROVEN claims are closed or explicitly accepted.