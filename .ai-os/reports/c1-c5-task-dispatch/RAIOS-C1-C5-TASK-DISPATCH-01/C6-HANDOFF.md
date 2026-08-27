# C6 Handoff — RAIOS-C1-C5-TASK-DISPATCH-01

- Agent: cursor
- Seat: C2-KAGGLE-CONTROL
- Status: PASS
- Reviewer: C6 read-only. Do not duplicate implementation.
- NOT_FOR: C6-AG-REMOTE-RECON, C7-CLOUD-SANDBOX

## Distinction proven

MESSAGE_TRANSPORT != TASK_DISPATCH != TOOL_EXECUTION != BOUND_RECEIPT

C1↔C5 HTTP chat remains PROVEN_E2E as message transport. Plain chat is not a task.

## Path

Founder channel `RAIOS-C1-C5-CHANNEL.py` now branches on schema `raios.c1c5.task-envelope.v1` before LLM bind.

Authority is server-side founder session (`C1-C5-SESSION.json`). `actor=C1` is request data only.

Policy reuses `src/raios/a2a/policy_bridge.py`. UCP reuses `DryRunUCP`. Receipts reuse `.ai-os/receipts/command-fabric/c1c5-task/`.

## Live proof (READ_ONLY)

Capability `c5.self_inspect.health` GET 127.0.0.1:8766/health.

First envelope: TASK_BOUND=true, POLICY_CHECKED=true, UCP ACCEPTED_DRY_RUN, capability invoked, BOUND_RECEIPT=true, PROVEN=true.

Same idempotency key: ALREADY_APPLIED, capability not invoked again, original COMPLETED receipt preserved.

## Tests

11/11 PASS. LLM_CALLS=0 GPU_USED=false PAID_API_CALLS=0

## Preserved

HTTP_PRIMARY=true NATS_PRIMARY=false
COMMAND_FABRIC_E2E_PROVEN=false
GL005_PROVEN=false D-059=BLOCKED WAL_WRITTEN=false
A2A_PRODUCTION_ACTIVATED=false C5 not published

## C5 A2A fit (no publication)

C5_STABLE_SERVICE_IDENTITY_SUITABLE=false
C5_PUBLIC_AGENT_CARD_RECOMMENDED=false
C5_AUTHENTICATED_AGENT_CARD_RECOMMENDED=true (recommendation only)
