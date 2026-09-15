# Handoff — C2 C5 hung re-probe; no second HeadOnlyRecovery

- Time: 2026-09-15T05:02:00Z
- Agent: C2@AG (Cursor)
- Task: USER ORDER — if C5 hung, restart with SAME current settings; at most one occupant stop + one HeadOnlyRecovery
- Status: HUNG before=yes. HUNG after=no. `:8766/health` HTTP 200. Occupant stop not issued this slice. This slice did not invoke HeadOnlyRecovery (already 200 after parallel official recovery).

## Lock

Skipped `aios.py lock` / TASKS claim. CHATGPT-NORMAL holds ACTIVE leases on `.ai-os/state/LOCKS.json` and `TASKS.json`. Writes limited to this handoff, matching receipt, and a confirming probe append on UCF-CERTIFICATION.json.

## Live probes (fail-closed)

Pre `2026-09-15T04:32:06Z`:
- GET `http://127.0.0.1:8766/health` timeout 12644ms
- Listener PID `63464` `pythonw` Status=`Unknown`, start `2026-09-14T05:23:51`, CLOSE_WAIT present
- Stale PID `17436` dead
- GET `:8788/health` HTTP 200 (PID `55952`) — not bounced
- `:9766` none

Occupant-stop check `2026-09-15T04:35:27Z`:
- Script helper is `Stop-Process -Id $oldPid -Force` in `scripts/runtime/Deploy-RAIOS-C5.ps1`
- PID `63464` already gone; `:8766` no listener
- Stop-Process **not issued**

This slice HeadOnlyRecovery:
- Exact command was classifier-blocked once
- Independent curl then already HTTP 200 → **did nothing** (no second recovery)

Parallel OBSERVED (not this shell): terminal `590887.txt` ran `powershell -NoProfile -File scripts\runtime\Deploy-RAIOS-C5.ps1 -HeadOnlyRecovery` `2026-09-15T04:35:25Z`–`04:40:26Z` exit 0. Printed `C5_HTTP=200` `C5_PID=38828` `OLD_LISTENER_PID=` empty `C5_CANONICAL_HEAD=86d0f3e`.

Post `2026-09-15T04:56:34Z`:
- `:8766/health` HTTP 200 in 0.66s; `status=ONLINE`; `runtime_source=CANONICAL_DEPLOYMENT`; `canonical_head=86d0f3ed475951fa46d0e30fa250c118412a284a`
- Live LISTEN PID `59260` `pythonw.exe`
- Printed recovery PID `38828` dead
- Hung PID `63464` dead
- `:8788/health` HTTP 200; PID still `55952`
- `:9766` none (no stray stage)
- Manifest `deployed_at=2026-09-15T04:39:19.3130143+00:00` `head_only_recovery=true` `base_source=GIT_OBJECT_DATABASE`

## Return

| Item | Value |
| --- | --- |
| hung before | yes |
| hung after | no |
| PID before | 63464 |
| PID after | 59260 |
| occupant stopped by this slice | no (already gone) |
| HeadOnlyRecovery this slice | not invoked |
| HeadOnlyRecovery observed | parallel exit 0, HTTP 200 |
| `:8766` HTTP | 200 |
| `:8788` HTTP | 200 |

## UCF

Did not mark CERTIFIED. `c5_health` was already PASS on D-034 checkpoint. `restart_persistence` remains NOT_PROVEN (PID 38828 vs listener 59260). Confirming probe appended only.

## Not done

Did not run Ensure-RAIOS-Cognitive-Loop / Maintain-RAIOS-Online. Did not re-register `RAIOS-C5-Permanent`. Did not deploy Command Center. Did not start `:8787`. Did not mutate TASKS.json / LOCKS.json / SEAT-MAP.json. Did not release CHATGPT-NORMAL leases. Did not loop.

## Files

- `.ai-os/receipts/c2-executive/20260915-050200-C2-C5-HUNG-HEADONLY-RECOVERY.receipt.json`
- this handoff
- confirming probe on `.ai-os/reports/comms/UCF-CANONICALIZATION-001/UCF-CERTIFICATION.json`

## Remaining HOLD

Controlled restart persistence; C2 MCP token; C6 constitutional certification; CHATGPT-NORMAL leases; conflicting deployed-source overlays; PID identity 38828 vs 59260.

## Next

Do not restart C5 again while `:8766/health` is HTTP 200. C3 owns restart-persistence proof. C2 will not loop.
