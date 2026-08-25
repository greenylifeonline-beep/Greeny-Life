# Authoritative certifier

Fail-closed certification for the true-open worktree reconciliation receipt.

## Safety schema (PR3b)

The execution receipt (`raios.worktree.true-open-execution.v1`) stores
overwrite / restore flags **only** under `safety`:

- `safety.stale_locks_reactivated`
- `safety.authoritative_current_goal_overwritten`
- `safety.authoritative_active_wave_overwritten`
- `safety.legacy_provider_binding_restored`

A missing top-level `current_goal_overwritten` is **not** an overwrite.
That lookup (`None is False`) was the `CURRENT_GOAL_OVERWRITE_DETECTED`
false-positive. Missing nested keys fail as `SAFETY_SCHEMA_PATH_MISSING`.

## Root resolution

`RAIOS_REPAIR_ROOT` overrides the tree. Otherwise the Windows Repair path
is used when it exists; otherwise the git toplevel (cloud clones).

## Tests

```bash
python3 -m pytest tests/authoritative_certifier -q
```

This package does not set `GL005_PROVEN`.
