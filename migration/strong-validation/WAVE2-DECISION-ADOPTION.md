# Wave 2 Decision Adoption

## Status

ADOPTED

## Governing policy

EVIDENCE-FIRST / NO FABRICATION

## Adopted decisions

### Main Brain

Runtime authority is:

- `lib/intelligence/mastermind-agents.ts`
- `app/api/mastermind/**`

MasterMind TypeScript is the current authoritative Main Brain runtime path.

This decision does not authorize refactoring or widening MasterMind authority.

### Legacy brain.py

Classification:

`LEGACY / NON_ENTRY`

This does NOT mean:

- deleted
- deprecated
- safe to archive
- safe to migrate blindly

No cleanup is authorized by this decision.

### UAE project brain

Operational source status:

`MISSING`

No verified operational/runtime source has been adopted.

Policy:

Do not fabricate distributors, operational state, commercial facts, or bridge behavior from historical `brain.py` content.

Full UAE project-brain implementation is deferred.

### Norway project brain

Operational source / runtime bridge status:

`MISSING`

No fabricated operational state is permitted.

Full Norway project-brain implementation is deferred until verified evidence exists.

### Bridge strategy

Current strategy:

`DEFER`

No UAE/Norway bridge will be created until a verified runtime/canonical source justifies one.

When evidence exists, allowed candidates may include:

1. native TypeScript implementation,
2. controlled bridge to an existing verified runtime,
3. continued explicit `MISSING` state.

### Egypt project brain

Egypt remains the only verified current project-brain REST implementation.

It may be used as an architectural pattern, but its data ownership must not automatically be copied to UAE or Norway.

### Duplicate signals

The scout result of 52 duplicate basenames is informational only.

It must NOT be treated as evidence of 52 duplicate runtime authorities.

Only independently verified duplicate authorities may trigger consolidation.

### GL-004

Real database integration proof remains:

`PENDING`

Placeholder Prisma validation is not equivalent to real DB integration.

### GL-005

Current convergence status:

`NOT_READY`

No GL-005 implementation/convergence is authorized by this decision.

## Next critical path

GL-004 Real DB Proof.