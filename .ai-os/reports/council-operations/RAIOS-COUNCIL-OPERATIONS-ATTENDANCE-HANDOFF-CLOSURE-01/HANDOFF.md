# Council Operations closure

The canonical council command now provides authenticated check-in/check-out, governed task claim and handoff, All-Hands coordination envelopes, idempotency enforcement, and conflict audit.

It reuses TASKS.json, LOCKS.json, A2A All-Hands, Command Fabric and the canonical receipt builder. It creates no second scheduler, task ledger, lock service, bus, WAL, authority store, or receipt system.

Operational presence is external at `~/.raios/runtime/council-ops`. No worker is marked present until its server-auth evidence validates. Check-out fails closed when the seat still owns an IN_PROGRESS task unless a handoff receipt is supplied.

CLI: `scripts/ai-os/raios_council_ops.py`. Use the Transport Python runtime and pass an auth-evidence JSON produced by the existing authenticated authority chain. Commands: `check-in`, `check-out`, `claim`, `handoff`, `message`, and `audit`.

Current rollout state: implementation and regression gates pass; attendance remains empty until C1-C7 independently check in. This is intentional truth preservation, not a fabricated all-hands presence claim.
