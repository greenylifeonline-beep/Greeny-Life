# E3 Full Legacy Project Inventory and Coverage Gate

Mode: read-only. No Legacy or Current asset was executed, moved, archived, deleted, staged or changed.

## Coverage

- Legacy root: `C:\Users\Ghanam\OneDrive\projects\Greeny-Life`
- Files inventoried: 503
- Directories inventoried: 206
- Unreadable entries retained explicitly: 0
- Coverage claim: every enumerable entry is listed; skipped text analysis is declared per file, never omitted.

## Classification

| Classification | Count |
|---|---:|
| DATA_OR_CONFIG_CANDIDATE | 245 |
| SOURCE_CODE_CANDIDATE | 60 |
| ARCHIVE_OR_BACKUP | 60 |
| DOCUMENTATION_OR_REPORT | 60 |
| BINARY_OR_UNCLASSIFIED | 55 |
| EMPTY_FILE_REVIEW | 23 |

## Exact hash duplicate groups

- Groups: 13
- All remain REVIEW. No canonical replacement, archive, merge or retirement decision was inferred.

## Decision boundary

- `KEEP` is used only for dependency/VCS/preservation assets in this inventory.
- Empty files are `QUARANTINE`, not deletion candidates.
- All other Legacy assets remain `UNKNOWN` or `REVIEW` until capability, owner, SOR, caller, business-value and replacement proof exist.