# Handoff
- Agent: cursor
- Seat: C2-KAGGLE-CONTROL
- Task: RAIOS-A2A-AUTH-EVIDENCE-CONSISTENCY-01B
- Status: CONSISTENCY_DONE / NOT_PRODUCTION
- Reviewer: C6 (read-only). Do not duplicate implementation.
- NOT_FOR: C6-AG-REMOTE-RECON, C7-CLOUD-SANDBOX

## TASK_ID
RAIOS-A2A-AUTH-EVIDENCE-CONSISTENCY-01B

## REPORT_ROOT
C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\.ai-os\reports\a2a-federated-interop\RAIOS-A2A-AUTH-EVIDENCE-CONSISTENCY-01B

## PRIOR PACKAGES PRESERVED
Foundation: `.ai-os/reports/a2a-federated-interop/RAIOS-A2A-FEDERATED-INTEROP-01`  
01A: `.ai-os/reports/a2a-federated-interop/RAIOS-A2A-SECURITY-REMEDIATION-01A`

## BLOCKER_CLASSIFICATION
REPORTING_ONLY_BUG

Authorization already required trusted issuer + bound principal + server-side `raios.a2a.high_risk` + C1 `high_risk_principals`. Caller claims were not grants.

## FIRST_DIVERGENCE_COMPONENT
`src/raios/a2a/gateway.py:handle` serialized `AUTH_RESULT.SCOPE_AUTHORIZED` from `trust.SCOPE_AUTHORIZED`, which used hardcoded `required_scope=raios.a2a.task`. A principal scoped only for `raios.a2a.high_risk` therefore reported `SCOPE_AUTHORIZED=false` while `CAPABILITY_AUTHORIZED=true` and `EFFECTIVE_AUTHORITY=true`.

## FIX
One `AuthorityDecision.as_auth_result()` feeds policy evidence, handle `auth_result`, and receipt `AUTH_RESULT` (same object). `SCOPE_AUTHORIZED` is derived from server-side capability coverage. Protected `EFFECTIVE_AUTHORITY=true` requires `SCOPE_AUTHORIZED` and `CAPABILITY_AUTHORIZED`. C1 high-risk grant is labeled `AUTHORITY_SOURCE=EXPLICIT_C1_TASK_GATE` with server-side provenance. Caller `granted_scopes`/`admin`/`C1` remain request data only.

## TESTS
OLD_TESTS_PASS=35 OLD_TESTS_FAIL=0  
NEW_TESTS_PASS=5 NEW_TESTS_FAIL=0  
TOTAL_TESTS=40 TOTAL_PASS=40 TOTAL_FAIL=0  
LLM_CALLS=0 GPU_USED=false PAID_API_CALLS=0

## PRESERVED
A2A_PRODUCTION_ACTIVATED=false  
A2A_PUBLIC_LISTENER_ENABLED=false  
A2A_EXTERNAL_MUTATION_ALLOWED=false  
HTTP_PRIMARY=true NATS_PRIMARY=false  
AP2_IMPLEMENTED=false AP2_ACTIVATED=false  
GL005_PROVEN=false D-059=BLOCKED WAL_WRITTEN=false

## FILES_CREATED
- `tests/a2a/test_auth_evidence_consistency.py`
- this report package
- `.ai-os/handoffs/20260827-094500-cursor-RAIOS-A2A-AUTH-EVIDENCE-CONSISTENCY-01B.md`

## FILES_CHANGED
- `src/raios/a2a/authority.py`
- `src/raios/a2a/gateway.py`

## FILES_DELETED
none

## QUEUED NEXT
RAIOS-TOTAL-TREE-COPY-REPO-RECON-01B  
Not started. No new estate scan from this task. Existing 01B recon package remains for C6 if already produced.

## FINAL_VERDICT
A2A_AUTH_EVIDENCE_CONSISTENCY_PASS
