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

## Do this

1. Bind Repair HEAD.
2. Bind the existing live Repair Next. Do not spawn.
3. `GET /api/tasks` and parse the semantic body.
4. Inspect whether C0 already has a legitimate session on that process.
5. If yes: BEFORE GET → authenticated `POST /api/tasks` → entity_id → AFTER GET same entity.
6. If no: `classification = BLOCKED_AUTH`, `GL005_PROVEN = FALSE`.

Protected capability is not missing capability.
