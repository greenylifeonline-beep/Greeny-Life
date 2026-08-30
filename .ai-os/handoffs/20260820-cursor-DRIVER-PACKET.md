# Handoff — DRIVER PACKET

- Agent: cursor (executor)
- Task: DRIVER-SYNC
- Status: STOP_STATE_RECORDED; CONSOLIDATION_NOT_EXECUTED
- For: USER MAIN ASSISTANT (steering authority)
- Branch: `v9-neurolingua-semantic-kernel`
- HEAD: `e1dfd7c235b0bd4ba1a58ab6dfea47bd00173370` (= origin)
- Machine packet: `.ai-os/handoffs/20260820-cursor-DRIVER-PACKET.json`

## Where this executor stopped

Deletion/consolidation was **authorized** and **not done**.

This cloud slice (`/workspace`) is a clean GitHub checkout at `e1dfd7c`. The Repair barn (`_raios-kaggle-census`, venv, DEEP-EVIDENCE, retired worktree copies) is **not here**. Commit-and-push had only Next/npm environment noise; it was restored, not committed.

## Already in git (do not redo)

1. NL-0 in `82fa109` — meaning kernel; WAL adapter over `cognitive_event_bus`; no second WAL.
2. Certifier forensic in `18feb63` — nested stale-lock only; remaining safety keys still fail-closed.
3. Wave2 path-signal gaps in `e1dfd7c` — `migration/gl-004` and `migration/gl-005` missing as **signals**, not as missing capabilities.

## Drive the next executor with this order

`MODE=CONSOLIDATION_EXECUTE` on Repair if reachable, else this slice.

1. Tag `safety/pre-consolidation-e1dfd7c`. No backup forests.
2. Keep the live keepers in the JSON packet. Do not create a new registry/WAL/worktrees.
3. Delete byte-identical barn and obsolete broken files (`intelligence-test.ts`, unused `gl-dos.ts`, `archive/duplicates/route.ts`).
4. Repair `engine-registry` / `health-reporter` to the live keepers, or delete if unused.
5. Prove GL-004 by type-check + build + tests + runtime, **not** by creating `migration/gl-*`.
6. Prove GL-005 by `.ai-os` tasks/locks/handoff + `tests/task_orchestration_check.ts`.
7. Return the scoreboard block. Estate compression is part of the proof.

## Do not

- Trust engine-audit `PASS` / 1872 engines.
- Treat `None is False` as current_goal proof.
- Recreate retired worktrees.
- Pad Wave2 with empty migration folders.
- Mutate `RAIOS/V9` while A15 lock is ACTIVE except as the A15 owner.
- Swap Main Cortex off `qwen3.6:35b-a3b`.

## Next

Give the executor the `order_to_give_executor` string from the JSON packet and keep steering. This executor is stopped after recording stop-state.
