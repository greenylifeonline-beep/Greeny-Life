# C6 Handoff — RAIOS-C1-C5-TASK-DISPATCH-01A

- Agent: cursor
- Seat: C2-PRIMARY-EXECUTOR (compatibility TO_SEAT=C2-KAGGLE-CONTROL)
- Status: REMEDIATED_PENDING_C6_REREVIEW
- Does not overwrite RAIOS-C1-C5-TASK-DISPATCH-01.

## C6 FAIL accepted

`raios.identity.C1.ACTIVE_CANONICAL` and a matching `session_id` string were bearer grants. That permitted C1 impersonation.

## Fix

Static identity token removed from the trust set. Non-channel `dispatch()` requires HMAC `founder_binding` over `session_id`, `task_id`, `idempotency_key`, `correlation_id` using server-side `founder_secret`. CHANNEL attests the live process session and ignores envelope `authority_context_reference`. `actor=C1` remains request data.

## Negative tests

T11 static identity string rejected. T12 session id without HMAC rejected. T13 wrong HMAC rejected. T15 HMAC not reusable on another task_id.

## Live proof (HMAC, READ_ONLY)

GET `/health` → HTTP 200 `ONLINE`. Envelope `RAIOS-C1-C5-TASK-DISPATCH-01A-LIVE-03` / `idem-c1c5-live-health-03` / `COR-UCP-PROOF-01A`: first COMPLETED, `AUTHORITY_SOURCE=HMAC_FOUNDER_SESSION`, capability invoked, bound receipt `415717063d4bdd51caba7583.receipt.json` SHA256 `a289ce8e…`. Second ALREADY_APPLIED, capability not invoked again.

Prior LIVE-02 receipts remain bearer-session artifacts and are not this proof.

## Preserved

HTTP_PRIMARY=true NATS_PRIMARY=false COMMAND_FABRIC_E2E_PROVEN=false WAL_WRITTEN=false GL005_PROVEN=false D-059=BLOCKED
