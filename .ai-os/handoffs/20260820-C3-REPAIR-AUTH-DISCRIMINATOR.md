# C3 Repair — cheapest auth discriminator

FROM: C1 COMMANDER (via C2 CONSULTANT FALSIFICATION ACCEPTED)
TO: C3 ENGINEER on Repair
REPO: `C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair`
BRANCH: `v9-neurolingua-semantic-kernel`

`GL005_PROVEN` stays false until an authenticated POST creates a real `OrchestrationTask` and AFTER GET shows the same id.

PID 3297 `/workspace` is **not** Repair. Do not copy Instance B GET 500 or BLOCKED_AUTH onto Repair if Repair has newer semantic GET 200.

## Forbidden

- Do not manufacture `APP_SESSION_SECRET`
- Do not forge `gl_session`
- Do not add an auth bypass
- Do not spawn a second Next
- Do not create PostgreSQL/Docker unless a **fresh Repair** observation proves the dependency is absent

## Existing auth only

- Gate: `lib/authz.ts` `authorizeRequest()`; `writeRolePolicy.task` = ADMIN | WAREHOUSE | EXPORT
- Cookie: `lib/auth.ts` `gl_session`
- Login: `POST /api/auth/login`
- Probe: `GET /api/auth/session`

## Do this (fail-closed chain)

1. bind-live-runtime
2. capture HEAD/PID/port
3. before observation (`GET /api/tasks` semantic body)
4. action (existing auth only)
5. semantic result
6. after observation
7. state-diff
8. child exits
9. receipt hash
10. stale-evidence check
11. parent fail-closed

Classifier: 401 = `BLOCKED`. 201 with unchanged hash = `INVALID_OBSERVATION`. 201 with missing id after = `FAILED`. 201 with diff + visible id = `PASS_CANDIDATE` (still not `GL005_PROVEN`).

Protected capability is not missing capability.
