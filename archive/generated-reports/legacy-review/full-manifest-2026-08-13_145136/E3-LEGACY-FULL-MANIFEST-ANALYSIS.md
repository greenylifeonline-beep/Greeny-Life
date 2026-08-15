# E3 Legacy Full Manifest Analysis

Generated: 2026-08-13T12:53:28.8394996Z

## Scope

OLD PROJECT AS REPRESENTED BY E3-REPOSITORY-MANIFEST.json. Read-only source inspection. Replacement runtime/database excluded from all measurements.

## Counts

| Metric | Count |
|---|---:|
| Count | 6 |
| IsReadOnly | False |
| Keys | apiRoutes engineCandidates eventImplementationCandidates persistenceCandidates quarantineRisks exactDuplicateGroups |
| Values | 4 13 23 8 1 4 |
| IsFixedSize | False |
| SyncRoot | System.Object |
| IsSynchronized | False |
| manifestEntries | 50007 |
| eligibleLegacySourceFiles | 13592 |

## Safety interpretation

- A candidate is not proof of runtime behavior.
- Event implementation candidate is not proof of an event architecture.
- Exact duplicate is not deletion authority.
- The report distinguishes old-project files from dependency/build noise before any decision.

## Required next gate

Trace only the P0 groups first: evidence/decision, workflow, trade-logistics, data persistence, security and event candidates. Then assign owner, consumers, canonical version, isolated test, and KEEP/REUSE/RECONNECT/CONSOLIDATE/ARCHIVE/RETIRE decision.

No source was executed, changed, moved, renamed, merged, or deleted. No database or external service was accessed.
