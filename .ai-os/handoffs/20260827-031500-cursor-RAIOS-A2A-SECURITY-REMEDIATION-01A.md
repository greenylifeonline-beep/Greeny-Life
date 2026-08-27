# Handoff
- Agent: cursor
- Seat: C2-KAGGLE-CONTROL
- Task: RAIOS-A2A-SECURITY-REMEDIATION-01A
- Status: SECURITY_REMEDIATION_DONE / NOT_PRODUCTION
- Reviewer: C6 (read-only independent review from AG). Do not duplicate implementation.
- NOT_FOR: C6-AG-REMOTE-RECON, C7-CLOUD-SANDBOX

## TASK_ID
RAIOS-A2A-SECURITY-REMEDIATION-01A

## SOURCE_TASK
RAIOS-A2A-FEDERATED-INTEROP-01 (C6_REVIEW=PARTIAL). Foundation evidence was not overwritten.

## REPORT_ROOT
C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\.ai-os\reports\a2a-federated-interop\RAIOS-A2A-SECURITY-REMEDIATION-01A

## FOUNDATION_PACKAGE_PRESERVED
`.ai-os/reports/a2a-federated-interop/RAIOS-A2A-FEDERATED-INTEROP-01`  
FOUNDATION_MANIFEST_SHA256=`82a4d656f52ba454e4ffb3bc8630166775e1a43d1746e7f61d842bb74f631d27`  
FOUNDATION_RECEIPT_SHA256=`ecf862e58b61ea99d7db6ee85921f7ff5a84c9dd3b21e4db4377ba3bdc6b8018`

## BLOCKERS REMEDIATED
1. AUTHORITY_GATE_ACCEPTS_UNTRUSTED_SCOPELESS_SIGNATURE_WITH_CALLER_ASSERTED_AUTHORITY
2. C7_CLOUD_SANDBOX_MISSING_FROM_OPERATIONAL_SEAT_DENY_GUARD

## WHAT CHANGED
- Added `src/raios/a2a/authority.py`. Effective authority is derived only from trusted issuer registry, authenticated principal mapping, server-side scope mapping, capability-scope map, high-risk principal set, and NeuroLingua/policy_bridge risk. Caller `authority` / `role` / `admin` / `granted_scopes` / `trusted` fields are request data only.
- `policy_bridge.evaluate()` now takes `effective_authority` (not caller `authority_present`) and merges AUTH_INPUT / TRUST_RESULT / SCOPE_RESULT / CAPABILITY_RESULT / RISK_RESULT / AUTHORITY_RESULT / DENIAL_REASON.
- `trust.verify()` accepts server-side `authorized_scopes` only. Signature validity does not imply issuer trust, scope, or authority.
- Operational seat deny set now includes C1, C2-KAGGLE-CONTROL, C2-PRIMARY-EXECUTOR, C2-ESTATE-RECON, C6-AG-REMOTE-RECON, C7-CLOUD-SANDBOX, plus legacy C2A/C2B.
- Tests T28-T35 in `tests/a2a/test_security_remediation.py`. Previous 27 foundation tests still pass.

## REUSED AUTHORITY SOURCE
No parallel A2A authority database.
- `src/raios/a2a/trust.py:trusted_issuers`
- `src/raios/a2a/authority.py:principal_by_issuer+scopes_by_principal+high_risk_principals`
- `src/raios/neuro_lingua/schema.py:RiskLevel`
- `src/raios/a2a/policy_bridge.py`
- `.ai-os/control/RAIOS-CONTROL-PLANE-V1.py` via DryRunUCP (no live acquire)

## FILES_CREATED
- `src/raios/a2a/authority.py`
- `tests/a2a/test_security_remediation.py`
- this report package under REPORT_ROOT
- `.ai-os/handoffs/20260827-031500-cursor-RAIOS-A2A-SECURITY-REMEDIATION-01A.md`

## FILES_CHANGED
- `src/raios/a2a/gateway.py`
- `src/raios/a2a/trust.py`
- `src/raios/a2a/cards.py`
- `src/raios/a2a/failclosed.py`
- `src/raios/a2a/policy_bridge.py`

LOCKS.json, TASKS.json, NeuroLingua, RAIOS/V9, census dir, architecture-audit, docs/v9, and root reports/ were not mutated for this task.

## FILES_DELETED
none

## CARD CHECKS
AGENT_CARD_VERIFIED=true  
Public identity: RAIOS Foundation Agent  
Allowed public skill: raios.foundation.noop_intent  
Operational seat strings are not published identities.

EXTENDED_CARD_VERIFIED=true  
Unauthenticated GetExtendedAgentCard → AUTH_FAILED.  
Authenticated extended card remains gated and does not publish operational seats.

OPERATIONAL_SEAT_DENY_GUARD_PROVEN=true  
C7-CLOUD-SANDBOX rejected (T34). Complete deny set rejected (T35).

## POLICY BRIDGE
POLICY_BRIDGE_VERIFIED=true  
Fail-closed for untrusted / scopeless / self-asserted / capability-mismatch / high-risk without server grant.  
Evidence keys present on allow path (T32). Secrets/tokens not logged.

## TEST_RESULTS
PYTHONPATH=src NO_LLM_CALLS=true  
`.venv/Scripts/python.exe -m unittest tests.a2a.test_foundation tests.a2a.test_security_remediation`  
OLD_TESTS_TOTAL=27 OLD_TESTS_PASS=27 OLD_TESTS_FAIL=0  
NEW_SECURITY_TESTS_TOTAL=8 NEW_SECURITY_TESTS_PASS=8 NEW_SECURITY_TESTS_FAIL=0  
TOTAL_TESTS=35 TOTAL_PASS=35 TOTAL_FAIL=0  
LLM_CALLS=0 GPU_USED=false PAID_API_CALLS=0

## PRESERVED FLAGS
HTTP_PRIMARY=true  
NATS_PRIMARY=false  
A2A_PRODUCTION_ACTIVATED=false  
A2A_PUBLIC_LISTENER_ENABLED=false  
A2A_EXTERNAL_MUTATION_ALLOWED=false  
AP2_IMPLEMENTED=false  
AP2_ACTIVATED=false  
GL005_PROVEN=false  
D-059=BLOCKED  
WAL_WRITTEN=false  
PUBLIC_LISTENER_CREATED=false  
EXTERNAL_MUTATION_EXECUTED=false

## FINAL_VERDICT
A2A_SECURITY_REMEDIATION_PASS

## Next
C6 independent review of 01A only. Do not activate production A2A, public listeners, AP2, or live UCP mutation from this package.
