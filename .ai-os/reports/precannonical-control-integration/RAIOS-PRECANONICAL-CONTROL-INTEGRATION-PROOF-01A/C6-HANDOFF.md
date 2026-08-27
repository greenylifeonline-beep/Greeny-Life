# C6 Handoff — RAIOS-PRECANONICAL-CONTROL-INTEGRATION-PROOF-01A

Does not overwrite PROOF-01. UCP was not rebuilt. No acquire. No WAL. NATS_PRIMARY remains false. COMMAND_FABRIC_E2E_PROVEN remains false.

Live existing control plane `send`/`ack` for kind `TASK_DRY_RUN`, target `C2-OBS`, correlation `COR-UCP-PROOF-01A`, message `MSG-1787844821137190-c621b602`. Per-target ack receipt and send receipt hashed in `CONTROL-INTEGRATION-PROOF-01A.json`.

Same correlation_id used for HMAC C5 health task `RAIOS-C1-C5-TASK-DISPATCH-01A-LIVE-03` (COMPLETED, bound receipt).

In-process DryRunUCP T11 still passes. T16 covers send/ack without lease.
