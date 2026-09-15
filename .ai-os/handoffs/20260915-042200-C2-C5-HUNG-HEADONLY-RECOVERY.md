# Handoff — C2 C5 hung check + one HeadOnlyRecovery

- Time: 2026-09-15T04:22:00Z
- Agent: C2@AG (Cursor)
- Task: USER ORDER — check current C5 session; restart only if hung, same settings
- Status: HUNG=yes. One certified restart ran. Cutover/rollback FAILED. C5 still hung. No second restart.

## User-supplied vs live

User paste said `cognitive.runtime.health=DEGRADED` / `waiting_for_c1_authorization` and HTTP `:8766=200`. Treated as USER-SUPPLIED. Live probe did **not** confirm HTTP 200.

DEGRADED + `waiting_for_c1_authorization` + `:8766` HTTP 200 is not a restart trigger. That case was not OBSERVED live.

## Live probes (fail-closed)

Pre-restart `2026-09-15T04:09:33Z`:
- GET `http://127.0.0.1:8766/health` timeout 8101ms, 0 body
- Listener PID `63464` `pythonw` alive, start `2026-09-14T05:23:51+03:00`
- Stale PID `17436` not alive
- GET `:8788/health` HTTP 200 (916ms) — not bounced

Post-restart `2026-09-15T04:16:39Z`:
- `curl.exe -m 8` `:8766/health` exit 28, timeout, 0 bytes
- `:8788/health` HTTP 200
- `netstat`: `:8766` still LISTENING PID `63464`; many CLOSE_WAIT; `:9766` none
- `tasklist` PID `63464` Status=`Unknown`

## Restart

Command (exact, one time): `powershell -File scripts\runtime\Deploy-RAIOS-C5.ps1 -HeadOnlyRecovery`

- Exit 1 after 159199ms
- Dirty canonical sources excluded (HeadOnlyRecovery)
- Stage on `:9766` OBSERVED healthy (`GET /health` 200)
- Live cutover failed: bind `:8766` WinError 10048 — PID `63464` not released
- Rollback process `39084` failed the same bind
- Throw: `C5_CUTOVER_AND_ROLLBACK_FAILED`
- No new flags/env/ports/config
- `C5_LIVE_APP_MUTATION=false` not printed (success path not reached)

## Post-state

- Hung: yes
- PID: `63464` (unchanged)
- HTTP `:8766/health`: timeout
- HTTP `:8788`: 200
- Existing runtime manifest still `deployed_at=2026-09-15T01:45:19Z` `head_only_recovery=true` `canonical_head=2efd08184614749dee999be7a2456c6bf1387c2e`

## Not done

No second restart. Did not run Ensure-RAIOS-Cognitive-Loop / Maintain-RAIOS-Online. Did not re-register `RAIOS-C5-Permanent`. Did not deploy Command Center. Did not start `:8787`. Did not mutate TASKS.json / LOCKS.json / SEAT-MAP.json. Did not release CHATGPT-NORMAL leases.

## Files

- `.ai-os/receipts/c2-executive/20260915-042200-C2-C5-HUNG-HEADONLY-RECOVERY.receipt.json`
- this handoff

## Next

C3/C1: PID `63464` still owns `:8766` and does not answer `/health`. Official HeadOnlyRecovery cannot cut over while that listener remains. C2 will not loop.
