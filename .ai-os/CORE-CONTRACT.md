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

## Deep legacy forensic pre-delete law
Old versions, archives, duplicate-looking trees, retired projects, historical branches, donor packages, and legacy cognitive assets are evidence-bearing assets until proven otherwise.

No actor may delete, remove, retire, prune, or destroy an old copy/source merely because it is older, duplicated by name, superseded by architecture, or apparently redundant.

Before any destructive retirement, the system MUST complete the canonical deep legacy forensic gate:
1. Census every authorized evidence surface: current canonical tree, current runtime-derived state, canonical Git history/refs, canonical estate reports, Factory Fabric/assimilation manifests, Cognitive WAL/learning evidence, and authorized archives/manifests already inside the canonical estate or explicitly authorized by C1.
2. Hash and lineage: identify every candidate by path/reference, content hash, provenance, version/commit, date, and known runtime role.
3. Semantic capability extraction: identify executable behavior, algorithms, prompts, policies, data schemas, business/commercial intelligence, domain brains, tests, tools, workflows, configuration, knowledge, and operational tricks that filename equality can miss.
4. Current-vs-legacy comparison: produce exact and semantic overlap, current coverage, contradictions, and unique-value deltas.
5. Unique-value closure: every unique item must be REUSED, MERGED, COMPILED, MIGRATED, or explicitly RETAINED before deletion can be considered.
6. Behavior proof: where executable behavior exists, prove equivalence or superior replacement using tests/runtime evidence, not text similarity alone.
7. Data/schema proof: verify that historical data, schemas, mappings, customer/supplier/commercial knowledge, and business intelligence are preserved or migrated.
8. Recovery proof: preserve provenance and a durable recovery path or canonical Git/object recovery where applicable.
9. Zero unresolved rule: unknown, unclassified, unreviewed, or unresolved unique value MUST equal zero.
10. Final gate: SAFE_TO_REMOVE_SOURCE=true may be asserted only after all prior gates pass with machine-verifiable evidence.

Standing duplicate-deletion authority applies only to TRUE EXACT REDUNDANCY after the deep gate passes. Any non-exact retirement, destructive history rewrite, or asset with semantic differences still requires explicit C1 approval.

Mandatory order: Discover -> Hash/Lineage -> Extract Capability/Data/Knowledge -> Compare -> Prove -> Reuse/Merge/Migrate/Retain -> Verify Coverage -> Recovery Proof -> Zero Unresolved -> Delete/Retire (last).

Historical absolute paths that point to retired/noncanonical trees are provenance only. They do not authorize reopening or reading a retired tree unless C1 explicitly reauthorizes that source.

## Completion
A task is complete only when changes, validation, evidence, and handoff state are recorded.
