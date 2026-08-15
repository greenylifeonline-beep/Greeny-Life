# E3 Full Legacy Classification and Deep Lineage

Mode: read-only classification over the completed 503-file Legacy inventory.

## Coverage

- Classified assets: 503 / 503
- No asset was executed, copied, moved, merged, archived or deleted.

## Functional families

| Family | Assets | Current mirror candidates | Decisions |
|---|---:|---:|---|
| LEGACY_BRAIN_OR_INTELLIGENCE_CANDIDATE | 163 | 114 | REVIEW:163 |
| LEGACY_BUSINESS_OR_OPERATION_CANDIDATE | 153 | 152 | REVIEW:153 |
| LEGACY_PRESERVATION_ASSET | 60 | 58 | KEEP:60 |
| LEGACY_EVIDENCE_OR_COMPLIANCE_REFERENCE | 48 | 48 | REVIEW:48 |
| LEGACY_DATA_OR_CONFIGURATION_CANDIDATE | 34 | 34 | REVIEW:34 |
| EMPTY_IMPLEMENTATION_OR_PLACEHOLDER | 23 | 23 | QUARANTINE:23 |
| BINARY_OR_UNCLASSIFIED_REFERENCE | 11 | 8 | UNKNOWN:11 |
| LEGACY_REFERENCE_OR_REPORT | 11 | 11 | REVIEW:11 |

## Strict lineage rule

A same path or exact content hash is a lineage candidate only. It is not proof of ownership, System of Record, safe replacement, archive eligibility or retirement eligibility.

## Exact duplicates

- Duplicate groups: 13
- All remain REVIEW; no duplicate was removed.

## Next gate

Capability-level proof, one family at a time: callers/dependencies, unique business value, Current replacement, owner/SOR, tests and recovery.