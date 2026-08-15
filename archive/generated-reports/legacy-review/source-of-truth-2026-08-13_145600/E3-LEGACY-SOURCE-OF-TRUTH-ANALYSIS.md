# E3 Legacy Source-of-Truth Analysis

Generated: 2026-08-13T12:56:13.7236604Z

## Scope

READ-ONLY ANALYSIS OF THE ACTUAL OLD PROJECT at C:\Users\Ghanam\OneDrive\projects\Greeny-Life. The replacement source, application runtime, and database are excluded.

## Counts

| Metric | Count |
|---|---:|
| Count | 8 |
| IsReadOnly | False |
| Keys | legacySourceFiles apiRoutes engineCandidates eventImplementationCandidates persistenceCandidates quarantineRisks exactDuplicateGroups readFailures |
| Values | 149 4 11 1 8 1 2 0 |
| IsFixedSize | False |
| SyncRoot | System.Object |
| IsSynchronized | False |

## Classification

| Classification | Files |
|---|---:|
| API_ROUTE | 4 |
| BRAIN_EVIDENCE_KNOWLEDGE | 25 |
| COMPONENT_OR_TOOL_CANDIDATE | 88 |
| ENGINE_OR_SERVICE_CANDIDATE | 11 |
| HISTORICAL_OR_ARCHIVED | 18 |
| MIXED_LEGACY_TOOLBOX | 1 |
| TEST_OR_FIXTURE | 2 |

## Verdict

DISCOVERY_AND_CLASSIFICATION_ONLY. No candidate is an approved runtime engine. No deletion, merge, rename, or execution is authorized.

## Next gate

Create the System of Record map for P0 capabilities, then isolated trace each selected old runtime path before reuse or retirement.

No source was executed, modified, moved, merged, renamed, or deleted. No database or external service was accessed.
