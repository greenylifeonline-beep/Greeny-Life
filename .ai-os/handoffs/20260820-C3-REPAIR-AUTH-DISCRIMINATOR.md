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

## Later Repair observation: Secure cookie on HTTP

`SESSION_HTTP=200`
`AUTHENTICATED=False`
Secure session cookie count >= 1
`DIAGNOSIS=SECURE_SESSION_COOKIE_NOT_USABLE_OVER_CURRENT_HTTP_RUNTIME`
`DB_BINDING_MISMATCH=FALSIFIED`
`CREDENTIAL_FAILURE=FALSIFIED`
`COOKIE_TRANSPORT_MISMATCH=PROVEN_CANDIDATE`
`PASSWORD_RETAINED=FALSE`
`EVIDENCE_MUTATION_EXECUTED=FALSE`
`TASK_MUTATION_EXECUTED=FALSE`
`GL005_PROVEN=FALSE`

That is a transport candidate, not GL-005. C0 ordered `صلح`. Product fix: `lib/auth.ts` `Secure` follows request scheme and `X-Forwarded-Proto`. HTTPS keeps Secure. HTTP production does not emit Secure. This is not a global Secure-off bypass.

## After this HEAD (Repair only)

1. Pull `v9-neurolingua-semantic-kernel`.
2. Restart the **same** bound Repair Next. Do not spawn a second process.
3. Login over the current HTTP runtime. Do not print the cookie value.
4. Report flags only:

```text
BOUND_HEAD=
SET_COOKIE_COUNT=
SET_COOKIE_NAME_GL_SESSION=true|false
SET_COOKIE_SECURE=true|false
SET_COOKIE_HTTPONLY=true|false
WEBSESSION_HAS_GL_SESSION=true|false
BASE_SCHEME=http|https
BOUND_NEXT_NODE_ENV=development|production|absent
SESSION_AUTHENTICATED=
SESSION_ROLE=
GL005_PROVEN=FALSE
```

On HTTP after this fix, `SET_COOKIE_SECURE` should be false. If `SESSION_AUTHENTICATED=true` and `SESSION_ROLE` is ADMIN|WAREHOUSE|EXPORT, run the 11-step mutation chain. Else stay FAILED at session bind. Do not POST `/api/tasks` until authenticated=true.

## Later Repair observation: pull blocked, stale HEAD built

`GIT_PULL_FAILED` because `RAIOS/V9/wal/cognitive-events.jsonl` was dirty.
`BOUND_HEAD=e1dfd7c235b0bd4ba1a58ab6dfea47bd00173370` (not `9758765`).
Old Next PID 18312 stopped. Stale HEAD built. New Next PID 19720 on 3107.
`LIVE_RUNTIME_HTTP=200` `LIVE_RUNTIME_SEMANTIC_SUCCESS=TRUE`
Cookie header probe failed (`GetValues` missing). Printed `SET_COOKIE_*=False` are **unmeasured**.
`WEBSESSION_HAS_GL_SESSION=False` (measured)
`BASE_SCHEME=http`
`BOUND_NEXT_NODE_ENV=production`
`SESSION_AUTHENTICATED=False`
`C3_SESSION_BINDING` was not printed (`else` ran as a new command)
`PASSWORD_RETAINED=FALSE`
`GL005_PROVEN=FALSE`

`STALE_HEAD_NE_PRODUCT_FIX_OBSERVATION`. Do **not** commit WAL. This did **not** observe the cookie-scheme fix.

## Next on Repair (one script, not line-by-line)

Paste the whole block as one unit. Do not print header values. Do not print the password.

```powershell
$ErrorActionPreference = "Stop"
$RequiredHead = "9758765602ba1fc04645a0327e1a0f33a07fc0d1"
$Port = 3107
git stash push -m "repair-runtime-wal" -- "RAIOS/V9/wal/cognitive-events.jsonl"
if ($LASTEXITCODE -ne 0) { throw "WAL_STASH_FAILED" }
git pull --ff-only origin v9-neurolingua-semantic-kernel
if ($LASTEXITCODE -ne 0) { throw "GIT_PULL_FAILED" }
$BoundHead = (git rev-parse HEAD).Trim()
Write-Host "BOUND_HEAD=$BoundHead"
if (-not $BoundHead.StartsWith($RequiredHead.Substring(0,12))) { throw "STALE_HEAD::$BoundHead" }
npm run build
if ($LASTEXITCODE -ne 0) { throw "BUILD_FAILED" }
$Listener = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($Listener.Count -eq 1) { Stop-Process -Id $Listener[0].OwningProcess -Force; Start-Sleep -Seconds 2 }
$StartProcess = Start-Process -FilePath "npm.cmd" -ArgumentList @("run","start","--","-p","$Port") -WorkingDirectory (Get-Location).Path -PassThru -WindowStyle Hidden
$NewListener = $null
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 1
  $Candidate = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
  if ($Candidate.Count -eq 1) { $NewListener = $Candidate[0]; break }
}
if ($null -eq $NewListener) { throw "REPAIR_RUNTIME_DID_NOT_BIND" }
Write-Host "BOUND_RUNTIME_PID=$($NewListener.OwningProcess)"
$Base = ("http" + "://" + "localhost:$Port")
$Health = Invoke-WebRequest -Uri ($Base + "/api/tasks") -Method GET -UseBasicParsing
$HealthJson = $Health.Content | ConvertFrom-Json
if ($Health.StatusCode -ne 200 -or $HealthJson.success -ne $true) { throw "LIVE_RUNTIME_HEALTH_FAILED" }
Write-Host "LIVE_RUNTIME_HTTP=200"
$Bytes = New-Object byte[] 24
$Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $Rng.GetBytes($Bytes) } finally { $Rng.Dispose() }
$Password = [Convert]::ToBase64String($Bytes)
try {
  $env:INIT_ADMIN_PASSWORD = $Password
  & ".\node_modules\.bin\tsx.cmd" ".\scripts\provision-admin.ts" "admin@greeny-life.local" "GL005 Runtime Admin" "ADMIN"
  if ($LASTEXITCODE -ne 0) { throw "DOCUMENTED_ADMIN_PROVISION_FAILED" }
} finally { Remove-Item Env:INIT_ADMIN_PASSWORD -ErrorAction SilentlyContinue }
$Jar = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$LoginBody = @{ email = "admin@greeny-life.local"; password = $Password } | ConvertTo-Json
$Login = Invoke-WebRequest -Uri ($Base + "/api/auth/login") -Method POST -ContentType "application/json" -Body $LoginBody -WebSession $Jar -UseBasicParsing
$LoginJson = $Login.Content | ConvertFrom-Json
if ($Login.StatusCode -ne 200 -or $LoginJson.success -ne $true) { throw "LIVE_LOGIN_FAILED" }
$Raw = [string]$Login.Headers["Set-Cookie"]
$Measured = -not [string]::IsNullOrWhiteSpace($Raw)
Write-Host "SET_COOKIE_HEADER_MEASURED=$Measured"
Write-Host "SET_COOKIE_COUNT=$(if ($Measured) { 1 } else { 0 })"
Write-Host "SET_COOKIE_NAME_GL_SESSION=$($Measured -and ($Raw -match '(?i)(^|,|\s)gl_session='))"
Write-Host "SET_COOKIE_SECURE=$($Measured -and ($Raw -match '(?i)(^|;|\s)Secure(;|$)'))"
Write-Host "SET_COOKIE_HTTPONLY=$($Measured -and ($Raw -match '(?i)HttpOnly'))"
$Stored = @($Jar.Cookies.GetCookies([Uri]::new($Base)) | Where-Object { $_.Name -eq "gl_session" })
Write-Host "WEBSESSION_HAS_GL_SESSION=$($Stored.Count -ge 1)"
Write-Host "BASE_SCHEME=$(([Uri]::new($Base)).Scheme)"
Write-Host "BOUND_NEXT_NODE_ENV=production"
$SessionResponse = Invoke-WebRequest -Uri ($Base + "/api/auth/session") -Method GET -WebSession $Jar -UseBasicParsing
$SessionJson = $SessionResponse.Content | ConvertFrom-Json
Write-Host "SESSION_AUTHENTICATED=$($SessionJson.authenticated)"
if ($SessionJson.authenticated -eq $true) { Write-Host "SESSION_ROLE=$($SessionJson.session.role)" } else { Write-Host "SESSION_ROLE=" }
$Allowed = @("ADMIN","WAREHOUSE","EXPORT") -contains ([string]$SessionJson.session.role)
$BindPass = $Measured -and ($Raw -match '(?i)(^|,|\s)gl_session=') -and -not ($Raw -match '(?i)(^|;|\s)Secure(;|$)') -and ($Raw -match '(?i)HttpOnly') -and ($Stored.Count -ge 1) -and ($SessionJson.authenticated -eq $true) -and $Allowed
if ($BindPass) { Write-Host "C3_SESSION_BINDING=PASS"; Write-Host "NEXT_GATE=AUTHORIZED_TASK_MUTATION" } else { Write-Host "C3_SESSION_BINDING=BLOCKED"; Write-Host "NEXT_GATE=STOP" }
$LoginBody = $null; $Password = $null; $Raw = $null; [Array]::Clear($Bytes, 0, $Bytes.Length)
Write-Host "PASSWORD_RETAINED=FALSE"
Write-Host "GL005_PROVEN=FALSE"
```

`PROVISION_ADMIN_NE_ORCHESTRATION_PROOF` still holds. Do not POST `/api/tasks` unless `C3_SESSION_BINDING=PASS` and `SESSION_AUTHENTICATED=true`.

