# RIF-A2A Semantic Bridge v1

## Classification
- TYPE: SEMANTIC_BRIDGE_SPECIFICATION
- A2A_PROTOCOL_MODIFICATION: FALSE
- RIF_PROTOCOL_MODIFICATION: FALSE

## Design Principle
Do NOT modify A2A protocol. Map incoming A2A governed semantic context to RIF evaluation context.

## A2A to RIF Mapping

### A2A Semantic Fields → RIF Evaluation Context

| A2A Field | RIF Mapping | Notes |
|-----------|-------------|-------|
| semantic_contract_id | EvaluationContext.contract_reference | Contract binding |
| semantic_version | EvaluationContext.schema_version | Version validation |
| concept_set_hash | SemanticResolverAdapter.get_concept_set_hash() | Concept resolution |
| schema_hash | EvaluationContext.schema_reference | Schema binding |
| provenance_policy | EvidenceStoreAdapter.provenance_policy | Provenance rules |
| authority_domain | GovernorInput.authority_status | Authority context |
| tenant | EvaluationContext.tenant_id | Multi-tenancy |
| context_fingerprint | CanonicalFingerprintProvider.fingerprint() | Context identity |

### Semantic Mismatch Handling

When A2A and RIF semantics differ:

```
MUST NOT silently downgrade.
```

Return explicit compatibility assessment:

```json
{
  "transport_compatible": true,
  "semantically_compatible": false,
  "mismatches": [
    {
      "a2a_field": "provenance_policy",
      "rif_expectation": "EVIDENCE_LINEAGE_REQUIRED",
      "a2a_provided": "BASIC_PROVENANCE",
      "severity": "HIGH",
      "resolution": "ESCALATE_TO_AUTHORITY"
    }
  ],
  "recommended_action": "ESCALATE"
}
```

### Compatibility Matrix

| Transport | Semantic | Action |
|-----------|----------|--------|
| true | true | PROCEED |
| true | false | ESCALATE |
| false | true | BLOCK |
| false | false | BLOCK |

## A2A Task Result vs RIF Verdict

### Critical Separation

```
A2A TASK COMPLETED ≠ RIF CLAIM PASSED
```

These are SEPARATE dimensions:

| Dimension | A2A | RIF |
|-----------|-----|-----|
| Type | Transport status | Epistemic verdict |
| Values | COMPLETED, FAILED, TIMEOUT | PASS, FAIL, ABSTAIN, ESCALATE |
| Authority | Transport layer | Evaluation logic |
| Meaning | Message delivered | Claim validated |

### Machine-Readable Mapping

```json
{
  "a2a_task_status": "COMPLETED",
  "rif_verdict": "ABSTAIN",
  "mapping": {
    "transport_success": true,
    "semantic_validation": "PARTIAL",
    "evidence_sufficiency": "INSUFFICIENT",
    "risk_assessment": "UNKNOWN",
    "governor_decision": "REQUEST_EVIDENCE"
  },
  "decision": "DO_NOT_PROMOTE"
}
```

### Rules
1. A2A task completion does NOT imply RIF pass
2. RIF pass requires independent evaluation
3. A2A failure does NOT imply RIF fail (could be transport issue)
4. Both dimensions must be reported separately
