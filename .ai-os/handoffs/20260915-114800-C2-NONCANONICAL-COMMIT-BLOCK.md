# Handoff — NONCANONICAL_BRANCH commit block (D-035)

- Agent: C2@AG (Cursor)
- packet_id: `PKT-C2-20260915-114800-NONCANONICAL-COMMIT-BLOCK`
- Task: Record the blocked UCF/C5 evidence commit in the C2 ledger and inspect ownership/locks for C1
- Status: C1 chose A. Evidence commit `775a804` on canonical. Hook not bypassed. Option B unused.
- Claim/lock: SKIPPED. TASKS.json and LOCKS.json remain ACTIVE under CHATGPT-NORMAL. Leases not released.
- Working branch: `cursor/ucf-runtime-cert-c5-recovery`
- Canonical branch: `ai-evolution-202608051809`
- Git HEAD OBSERVED: `86d0f3ed475951fa46d0e30fa250c118412a284a`

## OBSERVED

1. Pre-commit gate: `RAIOS_CHANGE_GATE=DENY reason=NONCANONICAL_BRANCH`.
2. 27 files remain staged. No unique commit on the cursor branch (same HEAD as canonical).
3. ACTIVE CHATGPT-NORMAL leases do not cover any staged path. Covered instead: `TASKS.json`, `LOCKS.json`, `Deploy-RAIOS-Command-Center.ps1`, session_agent, council_board/app, CNS.
4. Staged POLICY/EXECUTION-CHANNEL changes are `ucf_metadata` overlays only.

## C1 choice

C1 chose **A**. The 27-file set was moved onto `ai-evolution-202608051809`, inspected, approved, and committed as `775a804`. Option B was not used.

## Files

- `.ai-os/receipts/c2-executive/20260915-114800-C2-NONCANONICAL-COMMIT-BLOCK.receipt.json`
- `.ai-os/state/DECISIONS.md` (D-035)
- `.ai-os/state/EXECUTIVE-PROGRAM.json` (`noncanonical_commit_block_d035`)
- this handoff
