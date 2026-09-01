# RAIOS Core Contract

## Source of truth
1. Runtime behavior
2. Executed source
3. Tests
4. Active schemas/config
5. Shared RAIOS state
6. Architecture docs
7. Reports/history

## Every agent must read
- `.ai-os/PROJECT.json`
- `.ai-os/MASTER-PLAN.md`
- `.ai-os/state/CURRENT-STATE.json`
- `.ai-os/state/TASKS.json`
- `.ai-os/state/LOCKS.json`
- `.ai-os/state/DECISIONS.md`
- latest relevant handoff

## Safety
No destructive git/database operation without explicit human approval.

## Parallelism
Parallel writes are allowed only on non-overlapping scopes.

## Existing-first law
Before proposing, implementing, or recreating any capability, component, document, workflow, integration, task, service, or artifact, every actor MUST:
1. Discover: search canonical runtime/source, tests/config, shared state, tasks/locks/handoffs, Git history/branches/worktrees, reports, and authorized local/cloud archives within scope.
2. Prove: identify candidates by path plus provenance, hash/version, and runtime/test evidence where applicable.
3. Reuse: select the authoritative existing implementation and preserve its valuable behavior and history.
4. Upgrade: improve the existing implementation in place when it is incomplete or defective.
5. Unify and link: consolidate compatible capabilities behind one canonical path and reference it instead of copying it.
6. Create only as a last resort: new construction is allowed only after recorded evidence proves the capability is absent or unusable and no safe upgrade path exists.

Mandatory order: `Discover -> Prove -> Reuse -> Upgrade -> Unify -> Link -> Create (last resort)`.

Absence of immediate evidence is not evidence of absence. A stale task status is not proof that implementation is missing. Parallel duplicate implementations and reconstruction from memory while a usable source exists are prohibited.

## Completion
A task is complete only when changes, validation, evidence, and handoff state are recorded.
