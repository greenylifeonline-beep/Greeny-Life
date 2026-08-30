# Team Relay — executive challenge (DISCOVERED, not implemented)

Verdict: **the spec as written would become a fifth OS**. Accept only actor-owned append-only **outbox**, dispatcher-only **inbox copies**, and **ACK packets**. Do not build processed-moves, git-tracked generated inboxes, Issues-as-truth, or presence-as-locks.

Mailbox ownership is the fatal hole: shared GitHub write means anyone can forge the reviewer's inbox/outbox. Git author is not identity.

GitHub private hub is allowed later, empty of Repair evidence, after C2 has actually used `.ai-os/board/NOW.md`.

Full answers: `.ai-os/handoffs/20260820-TEAM-RELAY-CHALLENGE.json`
