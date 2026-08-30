# Resumable execution contract

The RAIOS Worker is infrastructure, not a council seat and not an authority.

Canonical lifecycle:

1. C1-authorized work enters the single TASKS ledger.
2. The Worker selects a present, idle, capability-eligible seat.
3. The target must explicitly accept the dispatch.
4. Every progress transition saves a resumable checkpoint in the task record.
5. The checkpoint records completed steps, changed files, validation, evidence, blocker, and next step.
6. If presence expires, the task returns to READY without losing its checkpoint.
7. Reassignment includes the latest checkpoint and begins from its next step.
8. Completion requires existing execution evidence.
9. Reports and checkpoint receipts preserve the audit trail.
10. NATS remains an optional transport beneath the same fabric.

C7-C12 remain reserved until C1 approves their canonical identities and functions.
