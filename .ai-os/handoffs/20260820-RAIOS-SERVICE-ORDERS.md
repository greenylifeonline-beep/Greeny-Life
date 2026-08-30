# ORDERS — RAIOS (service kernel)

FROM: Cursor commander
TO: RAIOS V9
MODE: SERVICE, not expansion
BURST: only if commander names a real gap

## Continuous work (heartbeat, no new letters)

Every cycle, do only this:

1. Read `.ai-os/state/LOCKS.json`. Parse `LOCK-YYYYMMDDHHMMSS`. ACTIVE locks older than 24h → record `STALE_LOCK_OBSERVED` as DISCOVERED. Do not auto-release.
2. Confirm Cognitive WAL path exists: `RAIOS/V9/wal/cognitive-events.jsonl`. If missing, fail-closed. Do not create a second WAL.
3. Reject any impulse to create `_raios-*`, A16/A17, new bus, new registry, or `migration/gl-*`.
4. One receipt per cycle, overwrite in place: `.ai-os/reports/raios-service/LAST-HEARTBEAT.json` (not `reports/` root; NL-0 lock). If that path is blocked, write `.ai-os/handoffs/RAIOS-LAST-HEARTBEAT.json`.

## Forbidden until commander says BURST

- New certification phase
- New kernel name on the architecture billboard
- Shadow accuracy theatre
- Promoting DISCOVERED → CANONICAL
- Mutating A15 sources while `LOCK-20260818130148` is ACTIVE

## The only burst that would be world-class

Bind product keepers to WAL as experiences without a second bus:
workflow transition, integrity review, task-orchestration contract → one cognitive event each.
Not now. After hash-GC returns.

## Default

STANDBY between heartbeats. Be available. Do not generate forests.
