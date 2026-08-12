# Intelligence Execution Truth

## Active in the final runtime

- `canonical/intelligence/runtime/controlled-runtime-orchestrator.ts`: governance orchestration.
- `canonical/intelligence/adapters/gl-dos-governance-gate.ts`: authorization rules.
- `lib/intelligence/export-decision.ts`: evidence-first export decision package.
- `/api/decisions/export-readiness`: read-only decision endpoint; it never executes an export.
- `/api/commercial-changes`: time-bound commercial-change registry with governance.

## Historical or inactive

- `brain.py`: source-management, audit, reporting, and generation tool; it is not connected to the web runtime.
- `canonical/intelligence/intelligence/intelligence-test.ts`: inactive; it imports missing files.
- Historical `eos-core` engine paths: stale; the referenced implementation is absent.
- Root npm intelligence commands: stale because declared target files are missing.

## Safety rule

No report, historical map, self-declared supplier capability, or LLM output becomes official truth. A decision remains `NOT_READY` until missing official and commercial evidence is supplied.
