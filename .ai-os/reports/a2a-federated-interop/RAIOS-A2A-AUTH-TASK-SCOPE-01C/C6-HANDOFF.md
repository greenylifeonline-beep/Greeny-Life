# C6 Handoff — RAIOS-A2A-AUTH-TASK-SCOPE-01C

- Agent: cursor
- Seat: C2-PRIMARY-EXECUTOR (compatibility TO_SEAT=C2-KAGGLE-CONTROL)
- Task: RAIOS-A2A-AUTH-TASK-SCOPE-01C
- Status: REMEDIATED_PENDING_C6_REREVIEW
- Reviewer: C6 (read-only). Do not duplicate implementation.
- NOT_FOR: C6-AG-REMOTE-RECON, C7-CLOUD-SANDBOX
- Does not overwrite 01 / 01A / 01B packages.

## C6 finding accepted

`EXPLICIT_C1_TASK_GATE` was a principal membership check. `a2a_task_id` was recorded, not used as a grant predicate.

## Fix

`Gateway.high_risk_task_grants` is a server-side map `principal -> allowed a2a_task_id`. Principal in `high_risk_principals` is eligibility only. Missing task grant is `AUTHORITY_REQUIRED`. The label `EXPLICIT_C1_TASK_GATE` is emitted only when `(principal, task_id)` matched.

## Tests

T01–T40 still pass. T41–T42 added. Combined A2A suite 42/42.

## Re-verify

Same principal, granted task_id → allow dry-run, `task_scoped=true`, `granted_task_id` matches. Same principal, other task_id → deny. Caller `granted_scopes` still ignored.
