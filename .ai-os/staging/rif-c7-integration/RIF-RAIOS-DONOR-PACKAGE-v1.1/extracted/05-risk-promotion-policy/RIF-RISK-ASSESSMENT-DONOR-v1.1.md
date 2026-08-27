# RIF Risk Assessment Donor v1.1

## Classification
- TYPE: RISK_ASSESSMENT_DONOR
- POLICY_AUTHORITY: FALSE
- OUTPUT_DESTINATION: PolicyAdapter / UCP

## Design Principle
C7 risk policy is NOT policy authority. It is:
- `RIF_RISK_ASSESSMENT_DONOR`
- Output feeds existing PolicyAdapter/UCP

## Risk Dimensions

1. **reversibility**: Can the decision be undone?
2. **blast_radius**: Scope of impact if wrong
3. **external_side_effect**: Effects outside the system
4. **canonical_impact**: Impact on canonical state
5. **financial_impact**: Cost if wrong
6. **security_impact**: Security implications
7. **privacy_impact**: Privacy implications
8. **evidence_sufficiency**: Adequacy of evidence
9. **uncertainty**: Level of unknowns
10. **contradiction**: Presence of conflicting evidence
11. **novelty**: How new/untested is the claim
12. **resource_cost_exposure**: Resource cost of being wrong

## Risk Classes

- **LOW**: Minimal impact, easily reversible
- **MEDIUM**: Moderate impact, reversible with effort
- **HIGH**: Significant impact, difficult to reverse
- **CRITICAL**: Severe impact, irreversible or catastrophic
- **UNKNOWN**: Insufficient information to assess

## Handling Rules

### UNKNOWN
- **Action**: Fail closed / escalate
- **Reason**: Cannot assess what we don't know
- **INVARIANT**: Unknown must not default to medium or low

### HIGH / CRITICAL
- **Action**: Never self-authorize
- **Reason**: Requires higher authority
- **Output**: ESCALATE to PolicyAdapter/UCP

### LOW / MEDIUM
- **Action**: Can proceed with standard evaluation
- **Output**: CONTINUE with risk annotation

## Confidence Separation

Do NOT collapse into one scalar. Provide separate fields:

1. **source_trust**: From TrustLatticeAdapter
2. **evidence_strength**: Aggregated from evidence quality
3. **claim_confidence**: Confidence in the claim itself
4. **model_confidence**: Confidence from model evaluation
5. **uncertainty**: Explicit uncertainty measure
6. **contradiction_severity**: Severity of any contradictions

### Combination Policy
- Interface: `ConfidenceCombinationPolicy`
- Method: `combine(fields: ConfidenceFields) -> CombinedAssessment`
- C7 provides default policy, RAIOS can override
- No single scalar unless explicitly combined
