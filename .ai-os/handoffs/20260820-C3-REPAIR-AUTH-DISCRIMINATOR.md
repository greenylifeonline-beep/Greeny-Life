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

## Repair observation recorded

`PASSWORD_LENGTH=0`
`NEW_PASSWORD_TOO_SHORT`
`PASSWORD_VALUE_PRINTED=FALSE`
`LOGIN_EXECUTED=FALSE`
`TASK_MUTATION_EXECUTED=FALSE`
`GL005_PROVEN=FALSE`

That is `BLOCKED`, fail-closed correctly. Do **not** retry with a generated password.

## Later Repair observation: login 200, session unauthenticated

`RUNTIME_LOGIN_HTTP=200`
`RUNTIME_LOGIN_SUCCESS=True`
`SESSION_HTTP=200`
`AUTHENTICATED=False`
`SIGNED_ADMIN_SESSION` was not printed
`TASK_MUTATION_EXECUTED=FALSE`
`GL005_PROVEN=FALSE`

Printed `ATOMIC_CREDENTIAL_LOGIN_PROVEN` is **falsified**.
`LOGIN_HTTP_200_NE_SIGNED_SESSION`.

## Remaining probe only (names and flags, never values)

Do not print `gl_session`. Do not POST `/api/tasks` until `authenticated=true`.

After a login response, report only:

```text
SET_COOKIE_COUNT=
SET_COOKIE_NAME_GL_SESSION=true|false
SET_COOKIE_SECURE=true|false
SET_COOKIE_HTTPONLY=true|false
WEBSESSION_HAS_GL_SESSION=true|false
BASE_SCHEME=http|https
BOUND_NEXT_NODE_ENV=development|production|absent
SESSION_AUTHENTICATED=
GL005_PROVEN=FALSE
```

`lib/auth.ts` sets `Secure` when `NODE_ENV=production`. Observe that. Do not change it as a bypass.

