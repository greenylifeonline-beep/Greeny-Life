# RAIOS Canonical Convergence 001 — Design

Status: P0_MUTATION_BLOCKED_C6_ABSENT. C1_EXECUTE_ORDERED=true. C1_MUTATION_AUTHORIZED=true. mutation_allowed=false. IMPLEMENTATION=NOT_STARTED.

The defect is not “too many copies.” Four kinds share one space: legal source, volatile runtime state, evidence/governance, and historical legacy. Direct cleanup now can destroy unique value or freeze a temporary runtime stamp as permanent truth.

Selected option: gradual convergence onto the canonical tree. Rejected: wholesale merge; clean-tree rebuild.

Official programs 00–12 are not rewritten. This campaign is an overlay through P00, P03, P11, and P12.

## Phase 0 — Authority gate

No mutation until: canonical branch `ai-evolution-202608051809`, proven HEAD, C6 live-bound consumer, active task lease, LOCK_OWNER=RAIOS_SYSTEM, SCOPE_CONFLICTS=0, and C1 acceptance of this design.

Rebind C6. Issue scoped expiring leases. C1 remains sole promotion authority. No merge/push/delete/restart outside the task contract. Checkpoint before each wave. No extra worktree/branch.

D-038 emitted the Phase 0 gate files and fail-closed tests only. C6 rebind and leases were not performed in that slice.

Fail-closed: ownership/canonical/governance conflict → READY + checkpoint.

## Phase 1 — Separate source from runtime

Highest engineering priority. Classify: Source (Git), Governance (Git after authority), Durable evidence (Git or evidence store), Runtime state (out of source tracking), Volatile telemetry (out of Git), WAL (bounded store), Temporary (isolate then delete after proof), Recovery artifacts (hash-archive then value-assess).

Do not treat `.gitignore` alone as the fix. Do not stop services outside a C1 quiescence window.

D-039 emitted the Phase 1 classification contract and fail-closed tests only. No file was moved. P1 mutation stays blocked until P0 `mutation_allowed` is true. `WORKER-REGISTRY.json` remains an observed RUNTIME_STATE example in the tree.

## Phase 2 — HEAD truth model

Distinguish repository_head, evidence_commit, deployed_source_head, runtime_reported_head, state_projection_head, upstream_head. Each stamp needs observed_at, source, proof_hash, class. EXECUTIVE-PROGRAM.json is a projection, not an independent authority. Do not cut over C5 off `86d0f3e` without deployment-delta and rollback tests. Treat `2efd081` and `96a1e7e` as historical unless a live runtime proves it still uses them.

D-040 emitted the Phase 2 named-stamp snapshot and fail-closed tests only. Conflicts remain recorded: repository `c527cd7` vs worker/projection `2efd081` vs EXECUTION-CHANNEL `96a1e7e`. Live deployed C5 head is UNPROVEN (HTTP timeout). The projection `head` field was not rewritten as current. C5 was not cut over.

## Phases 3–5 — Census and extraction

Global census across AG tree, Git history/remotes, `cursor/*`, GitHub, proven Kaggle copies, authorized local/archive surfaces, Factory/Resource/Knowledge/Cognitive/WAL, and `brain.py`. Classify CANONICAL_CURRENT through RETAIN_FOR_PROVENANCE. No parallel registry.

Cursor branches are historical value sources, not merge branches. Extract hunks; re-prove on current canonical HEAD. No `git merge origin/cursor/*`, whole-branch rebase/squash, or deletion before unresolved unique value = 0.

Kaggle: inventory without leaking secrets; no weight/sensitive-data move without C1.

## Phases 6–9 — Capabilities, integration, runtime, providers

One Capability Contract, one canonical owner, one primary implementation; others become providers/adapters. Capabilities are Core; Providers are replaceable; MCP remains the client gateway; no duplicate runtime/scheduler/memory/knowledge/control plane.

Integration is capability-by-capability: discover → prove → failing test → extract → implement on canonical → tests → governance gate → runtime probe → receipt → C1 promotion.

Runtime order: MCP → Command Center → Fabric consumer/binding → C5 → 9Router → adapters → P00 dashboard. UCF must prove REQUEST through ACTOR_ACK, plus reconnect, lease reclaim, crash/restart/reboot, no duplicate delivery, no fabricated ACK.

No provider promotion without Adapter Profile and security/recovery certificates.

## Phases 10–12 — Archive, delete, certify

Archive before delete. Exact-redundancy delete only after C8 certification, recovery proof, and C1 approval. Final flags (FOUNDATION_BOOTSTRAP_CERTIFIED, READY_FOR_ASSIMILATION, RAIOS_CANONICAL_RUNTIME_CERTIFIED) only after the phase-12 gate vector is true.

C2 emitted Phase 0–2 files (D-038–D-040). D-041 attempted P0 mutation via the existing council-ops status path. C6 is SIGNED_OUT. C2 did not impersonate C6. P1 relocation and C5 cutover remain blocked.
