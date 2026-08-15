# E3 Legacy Brain Recovery Decision

Generated: 2026-08-13T13:42:45.2979396Z

## Finding

P1: semantic engine fabricates trade/export relations when repository rules are empty. This violates fail-closed evidence governance.

## Decision

**P1: decision engine quarantined.**

| Component | Evidence status | Decision | Reason |
|---|---|---|---|
| GreenlinesBrain.decide / SemanticReasoningEngine | RUNTIME_PROVEN_UNSAFE | QUARANTINE | Empty knowledge creates five trade relations and returns a medium-confidence export recommendation with fabricated evidence. |
| InstitutionalMemory | STATIC_COMPONENT; NOT_INDEPENDENTLY_PROVEN | EXTRACT_FOR_ISOLATED_TEST | In-memory storage is separable from unsafe decision fallback; must be tested for lifecycle and provenance independently. |
| JSONKnowledgeRepository | RUNTIME_PROVEN_BOUNDED | REUSE_CANDIDATE | Temporary JSON load/search/retrieval passed; it is a repository adapter, not verified production persistence. |
| KnowledgeGraph | RUNTIME_PROVEN_PARTIAL | HARDEN_CANDIDATE | Graph operations passed in memory, but name lookup duplicates entity references. |
| BrainContract data classes | RUNTIME_PROVEN_BOUNDED | REUSE_CANDIDATE | Typed Evidence and Decision data structures instantiate correctly; no reasoning behavior is proven. |
| ImplementationEvidenceLayer | IMPORT_FAILURE | REJECT_AS_IS; EXTRACT_DESIGN_ONLY | Python dataclass cannot import because a default argument precedes required fields. |

## Non-negotiable policy

No legacy brain component may issue an actionable commercial recommendation, create assumed relationships, or execute an operation until it passes the Evidence Ladder through OPERATIONAL_PROVEN, TEST_EVIDENCE, OWNER_PROVEN, and SYSTEM_OF_RECORD.

## Next gate

Isolated proof Wave 2: InstitutionalMemory, semantic rule parser with explicit evidence only, and candidate business workflows. No promotion yet.

No legacy source was changed, moved, copied into the application, or deleted.
