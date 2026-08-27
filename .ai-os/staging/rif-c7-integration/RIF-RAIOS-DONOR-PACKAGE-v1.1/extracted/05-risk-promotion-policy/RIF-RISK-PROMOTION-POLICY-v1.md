# RIF Risk Promotion Policy v1

## Purpose
Assess risk of claims and advise on promotion decisions.

## Historical Design (v1.0)
- Risk dimensions: limited set
- Risk classes: LOW, MEDIUM, HIGH, CRITICAL
- Could self-authorize promotion (FORBIDDEN in v1.1)
- Output fed to governor directly without adapter

## Historical Limitations
- Insufficient risk dimensions
- No explicit UNKNOWN handling (defaulted to MEDIUM)
- Self-authorization on HIGH/CRITICAL
- No blast radius analysis
- No reversibility assessment

## v1.1 Adaptation Notes
- Renamed to RIF_RISK_ASSESSMENT_DONOR
- NOT policy authority — feeds existing PolicyAdapter/UCP
- Expanded dimensions: reversibility, blast_radius, external_side_effect, canonical_impact, financial_impact, security_impact, privacy_impact, evidence_sufficiency, uncertainty, contradiction, novelty, resource_cost_exposure
- Classes: LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN
- UNKNOWN: fail closed / escalate
- HIGH/CRITICAL: never self-authorize
