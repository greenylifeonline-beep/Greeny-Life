# E3 Legacy Brain Recovery â€” Wave 2

Generated: 2026-08-13T13:47:16.7545845Z

| Test | Status | Detail |
|---|---|---|
| InstitutionalMemoryLifecycle | PASS | create/store/retrieve/overwrite/search preserves current source/timestamp/confidence in memory only |
| InstitutionalMemoryGovernance | PARTIAL | PARTIAL: no lifecycle/provenance fields for version, expiry, invalidated, evidence_type, audit_id |
| SemanticRuleParserExplicitRule | PASS | @{emptyKnowledgeFallback=System.Object[]; explicitRuleRelations=System.Object[]; explicitRuleConclusions=System.Object[]} |
| SemanticRuleParserConflictStaleness | PARTIAL | PARTIAL: parser includes conflicting/stale rules without status, time or authority filtering: [('honey', 'requires', 'organic'), ('honey', 'requires', 'halal'), ('honey', 'requires', 'obsolete')] |

## Invariant

TEST-FAIL-CLOSED-001 remains failed for the legacy engine because empty knowledge produces default trade relations.

## Decisions

- InstitutionalMemory: EXTRACT_FOR_HARDENING: bounded storage works but lifecycle, version, invalidation, evidence type and audit are absent.
- SemanticRuleParser: EXTRACT_DESIGN_ONLY: explicit parsing works, but fallback fabrication and lack of conflict/staleness filtering block reuse.

No legacy source/data was changed.
