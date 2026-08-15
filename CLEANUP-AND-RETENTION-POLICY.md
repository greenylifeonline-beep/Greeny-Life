# GREENY-LIFE Cleanup and Retention Policy

## Operating rule

Business data, canonical knowledge, source code, evidence, and approved decision records are never removed by a cleanup command. They are retained in their authoritative locations.

## Rebuildable material

The following are disposable local build material and must not be committed:

- `.next/` — Next.js build output.
- `.npm-cache/` — npm download cache.
- `node_modules/` — installed dependencies; only remove after a deliberate reinstall plan.
- `*.tsbuildinfo`, Python bytecode, temporary files, and logs.

## Generated reports

Generated reports belong under `archive/generated-reports/<run-date>/`, with an index recording their original root location. A newer verified evidence package is not replaced by an older report.

## Safety gates

1. Inspect the exact paths and sizes before a cleanup.
2. Do not recursively remove a computed or unvalidated path.
3. Never clean `archive/`, `canonical/`, `data/`, `KNOWLEDGE-BASE/`, `greenlines_brain/`, `.env`, or E3 evidence packages.
4. Rebuild and verify the application after cleanup.
