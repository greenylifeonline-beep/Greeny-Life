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

## Completion
A task is complete only when changes, validation, evidence, and handoff state are recorded.
