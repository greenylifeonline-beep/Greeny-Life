# RAIOS 12-seat council and worker separation

The canonical council contains exactly C1 through C12.

RAIOS-WORKER is an external system worker with no C code, vote, opinion, ownership, or permanent lock. C7 remains a council member and is not the worker.

Broadcast ALL expands to C1-C12 only. Direct routing aliases remain transport addresses, not council members.

Task dispatch requires PRESENT state and a valid unexpired presence lease. A pending, unclaimed assignment is returned automatically when its target becomes absent or expires.

The same canonical TASKS.json and Command Fabric are reused. No second task ledger, bus, registry, Command Center, or worktree was created.

NATS remains optional because nats-server is absent. The reliable local fabric remains the active fallback.

Validation: Python compile PASS; Command Center/council map tests 8/8 PASS; application import PASS. Legacy A2A/Council tests are blocked at collection because a2a.utils is absent from the available Python environment; no dependency was downloaded.
