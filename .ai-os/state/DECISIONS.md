# Durable Decisions

## D-001 Provider-neutral truth
Repository evidence and shared RAIOS state are authoritative.

## D-002 Parallel work requires scope separation
No overlapping write scopes.

## D-003 Handoff is mandatory
Meaningful work must end with status, files, validation, evidence, and next step.

## D-004 Prefer large safe batches
Use independently verifiable work packages.

## D-005 Organize before expand
Estate compression precedes new kernels, phases, buses, registries, or worktrees.
Reuse a live keeper; adapt it if unique behavior exists; delete immediately if it cannot serve the live path.
RAIOS service mode is lock hygiene + WAL integrity + barn rejection. New RAIOS letters are forbidden until one runtime path is proven.

## D-006 Stale observation cannot authorize deletion
DISCOVERED operational bind (not RAIOS CANONICAL promotion):
`STALE_DEPENDENCY_OBSERVATION_MUST_NOT_AUTHORIZE_DELETION`.
Re-read HEAD and the import graph immediately before any delete. D-005 delete-immediately applies only to a fresh observation.

## D-007 Parent success requires every required child
`PARENT_SUCCESS_REQUIRES_ALL_REQUIRED_CHILDREN_SUCCESS`.
A receipt parent exit is 0 only if every required child exit is 0. Missing child = failure.

## D-008 Supporting test is not orchestration demonstration
`SUPPORTING_TEST_NE_ORCHESTRATION_DEMONSTRATION`.
`tests/task_orchestration_check.ts` cannot grant GL-005. CICF candidate: `DESTRUCTIVE_ACTION_REQUIRES_FRESH_HEAD_AND_DEPENDENCY_GRAPH`.

## D-009 Live process may satisfy RUNTIME_TRACE if identity and HTTP are bound
DISCOVERED operational bind (not RAIOS CANONICAL promotion):
`LIVE_PROCESS_CAN_SATISFY_RUNTIME_PROOF_IF_IDENTITY_AND_HTTP_EVIDENCE_ARE_BOUND`.
`BIND_EXISTING_NE_SPAWN`. `DEV_LISTEN_NE_PRODUCTION_BUILD`. `HTTP_200_ON_ROOT_NE_APP_HEALTH`.
`ISOLATED_BUILD_NE_SECOND_RUNTIME` — `next build` into `.next-gl004-proof` is compile proof, not a second listener.
A live `next dev` does not grant `GL004_PROVEN` by itself. Parent exit is 0 only if TYPECHECK, BUILD, TEST_CANONICAL, TEST_TASK_ORCHESTRATION, and RUNTIME_TRACE are all 0.

## D-010 Epistemic state is not the gate bit
DISCOVERED: `GATE_CLOSED_NE_EPISTEMIC_FAILED`.
The final gate stays closed unless every required child is PASS/exit 0.
Learning must still distinguish `NOT_RUN`, `FAILED`, `INVALID_OBSERVATION`, `BLOCKED`, `UNAVAILABLE`, `PASS`.
`BUILD=NOT_RUN` because a live `.next` was protected is not `BUILD_FAILED`.

## D-011 Observation classes must not collapse
DISCOVERED: `LIVENESS_NE_READINESS_NE_CORRECTNESS_NE_PRODUCTION_EQUIVALENCE`.
TCP LISTEN is process liveness. HTTP 200 root + Next identity is framework liveness.
401/403 is route execution plus auth gate. 404 is live server / absent route.
500 is route executed / application failure. Domain 2xx is capability readiness.
Isolated `next build` is BUILD_VALIDITY. `next start` is production-runtime equivalence, a separate child.
`NEXT_CONFIG_FILE` is not an isolation contract on next@16.2.10. Proof receipts stay in `.ai-os/receipts`, not a new `_raios-*` forest.

## D-012 Build compiler is not the live compiler
DISCOVERED: `BUILD_COMPILER_NE_RUNTIME_COMPILER`.
An isolated `next build --webpack` PASS does not prove the live `next-dev` Turbopack process. `GL004_PROVEN` for the five named children is not production equivalence.

## D-013 Repair atomic runner is not a proof forest
DISCOVERED: `PROOF_FOREST_NE_RECEIPT`; `POWERSHELL_PID_IS_RESERVED`; `HTTP_2XX_NE_ORCHESTRATION`.
Do not write `._raios-wave2-atomic-proof.ps1` or `_raios-wave2-atomic-proof\` at repo root. Repair runs `scripts/ai-os/gl004-atomic-executor.ps1` or `python .\scripts\ai-os\gl004-atomic-executor.py`. Isolated build worktree lives outside the live tree (`%TEMP%\gl004-isolated-build` / `/tmp/gl004-isolated-build`). `npm run build` is Turbopack on next@16; isolated BUILD uses `npx next build --webpack`. `param([int]$Pid)` binds the current PowerShell PID — use `-ProcessId`. RUNTIME_TRACE requires GET `/` == 200 and Next.js identity, not HTTP 200–499. `GL005_LIVE_PATH_PROVEN` is not `GL005_PROVEN`. Heartbeat/WAL dirt must not BLOCK BUILD; scope dirty to product paths.

## D-014 Observed state transition is required, but not a stronger machine
DISCOVERED: `ORCHESTRATION_DEMONSTRATED_REQUIRES_OBSERVED_STATE_TRANSITION` is accepted only when scoped.
A GET 200 or `tests/task_orchestration_check.ts` is not demonstration. The smallest durable product mutation is `POST /api/tasks` → `createTaskContract()` → `INSERT OrchestrationTask` with `status=REVIEW_REQUIRED` and `execution: false`, observed as GET-before ≠ GET-after.
The same law is too strong if it demands `COMPLETED`, `execution: true`, a second Next process, a new harness, or mutating `.ai-os/state/TASKS.json`. No HTTP applicator exists for `validateTaskTransition`. Stale `DATABASE_URL` 500 must not drive new infrastructure after a later semantic GET 200. `HTTP_2XX_NE_SEMANTIC_SUCCESS`. `READ_PATH_PROVEN_NE_ORCHESTRATION_DEMONSTRATED`. `STALE_FAILURE_CAUSE_MUST_NOT_DRIVE_NEW_INFRASTRUCTURE`.

## D-015 Mail drop is not proof
DISCOVERED: `MAIL_PASSES_NE_PROVES`.
A public GitHub Issue may carry C2/C5 envelopes so agents without MCP can write. C1 dispatches and collects. C0 commands in Cursor chat and is not the mailman for every envelope. An Issue is not TASKS, not a lock, not a handoff, and not `GL005_PROVEN`. GitHub login is envelope sender, not a RAIOS seat. Impersonation or noise closes the drop and returns to chat. This is not Team Relay.

## D-016 MCP gateway is not truth authority
DISCOVERED: `MCP_GATEWAY_NE_TRUTH_AUTHORITY`.
The RAIOS Universal Agent Connector is a capability-scoped Streamable HTTP MCP surface. `.ai-os` remains operational state. Cognitive WAL remains the sole learning authority. The gateway must not write `GL004_PROVEN` or `GL005_PROVEN`, must not expose raw shell, must not self-escalate, and must fail closed on stale `requested_head`. Authenticated actor ≠ authorized action. `AUTHORITY_NE_BYPASS_INVARIANTS` — C0 included.

## D-017 MCP gateway is not a Relay Hub
DISCOVERED: `MCP_GATEWAY_NE_RELAY_HUB`.
Do not build a Cloud Relay Hub, SQLite WAL, Redis, evidence cache, WebSocket, or JWT/HMAC authority plane in V1. MCP is the interface. Relay is a later async adapter only. GitHub Issues remain a degraded inbox. `SQLITE_WAL_NE_COGNITIVE_WAL`. `ACK_IS_A_NEW_PACKET_NEVER_A_MOVE`.

## D-018 Vertical slice before empire
DISCOVERED: `VERTICAL_SLICE_BEFORE_EMPIRE`.
V1 registers eight tools only: `get_head`, `read_board`, `read_inbox`, `read_receipt`, `get_diff`, `post_opinion`, `send_packet`, `ack_packet`. Prove C2 read_board + read_receipt + post_opinion and C1 read of that opinion before phase-2 tools. Transport is Streamable HTTP (ChatGPT Apps / Developer Mode remote MCP). Local stdio is Cursor-only. Sessions are stateless or short-lived memory. Scoped bearer tokens stand in for OAuth until a remote app is registered. No `run_sandboxed_command` in V1.

## D-019 Empire connector spec is rejected as written
DISCOVERED: `EMPIRE_CONNECTOR_SPEC_AS_WRITTEN_IS_REJECTED`.
A FastAPI+WebSocket+SQLite WAL+Relay Hub+JWT/HMAC+cache+Railway 6-week plan is rejected. Accept only the Streamable HTTP V1 slice over `.ai-os`. Do not give C0 execute/promote through the connector. `AUTHORITY_NE_BYPASS_INVARIANTS`. Calendar-week delivery plans are not a RAIOS success metric.

## D-020 C5 seat is ASSESSOR
DISCOVERED: `C5_SEAT_IS_ASSESSOR`.
The MCP/board seat C5 is ASSESSOR (falsify, no execute, no promote). DeepSeek may occupy that seat via alias `DEEPSEEK` / `DEEPSEEK-LOCAL`. This is not a sixth actor. Agents may propose learning via opinion/packet; only an internal RAIOS adapter may ingest DISCOVERED candidates. The adapter must not write Cognitive WAL from the gateway and must not VALIDATE or PROMOTE.

## D-021 Issues are degraded mail, not truth
DISCOVERED: `ISSUE_NE_TASK`. `ISSUE_NE_RECEIPT`. `ISSUE_NE_AUTHORITY`. `ISSUE_NE_LEARNING`. `ISSUE_NE_CERTIFICATION`.
`LOCAL_MCP_NE_REMOTE_C2`. Passing the local vertical slice does not mean ChatGPT C2 is connected. `127.0.0.1:8787` is local-only. Remote-ready requires a public HTTPS path to this same process, scoped bearer/OAuth, and one externally created C2 opinion that C1 reads. GitHub Issue titles `MAIL C2:` / `MAIL C5:` are transport metadata only.

## D-022 Protected capability is not missing capability
DISCOVERED: `AUTHENTICATION_BLOCK_IS_A_VALID_ORCHESTRATION_PROOF_BOUNDARY`.
A capability can exist and be correctly protected while the proof remains incomplete. Do not misclassify a protected write as an absent write.
Capability taxonomy (not the same state): `CAPABILITY_ABSENT` | `CAPABILITY_BROKEN` | `CAPABILITY_PROTECTED` | `CAPABILITY_UNAVAILABLE` | `CAPABILITY_UNPROVEN`.
This cloud slice (PID 3297, cwd `/workspace`): `ORCHESTRATION_MUTATION_CAPABILITY = PRESENT_BUT_PROTECTED_AND_UNPROVEN`.
Also DISCOVERED: `PROTECTED_CAPABILITY_NE_MISSING_CAPABILITY`. `POST_401_NE_STATE_TRANSITION`. `AUTH_GATE_PRESENT_NE_AUTHENTICATED_MUTATION`. `UNIT_CONTRACT_PASS_NE_LIVE_ORCHESTRATION`. `UNCHANGED_STATE_NE_ORCHESTRATION_DEMONSTRATED`. `FAILURE_ON_INSTANCE_B_NE_FAILURE_ON_REPAIR`.
Unauthenticated POST 401 on Instance B does not authorize calling Repair broken, missing, or unauthenticated if Repair has newer semantic GET 200. Do not mint `APP_SESSION_SECRET`, forge `gl_session`, add an auth bypass, or provision Postgres/Docker from this slice's GET 500.

## D-023 Observation chain is fail-closed and does not print PASS
DISCOVERED observation contract (not CANONICAL):
`bind-live-runtime → capture HEAD/PID/port → before observation → action → semantic result → after observation → state-diff → child exits → receipt hash → stale-evidence check → parent fail-closed`.
Classifier: POST 401 = `BLOCKED` / `AUTH_GATE_PRESENT_IDENTITY_UNAVAILABLE`. POST 201 + semantic success with `before_hash == after_hash` = `INVALID_OBSERVATION`. POST 201 with returned id absent after = `FAILED`. POST 201 with observed diff and visible id = `PASS_CANDIDATE` which still requires falsification review.
Laws: `STALE_FAILURE_CAUSE_MUST_NOT_DRIVE_NEW_INFRASTRUCTURE`. `HTTP_2XX_NE_SEMANTIC_SUCCESS`. `READ_PATH_PROVEN_NE_ORCHESTRATION_DEMONSTRATED`. `AUTH_GATE_PRESENT_NE_MUTATION_EXECUTED`. `AUTH_BLOCKED_NE_CAPABILITY_ABSENT`. `MUTATION_CLAIM_REQUIRES_OBSERVED_BEFORE_AFTER_DIFFERENCE`. `RETURNED_SUCCESS_NE_DURABLE_OBSERVABILITY`. `BOARD_HEAD_NE_GIT_HEAD`. `PRINTED_PASS_NE_EVIDENCE`. `PASS_CANDIDATE_NE_GL005_PROVEN`.
The board HEAD is not git HEAD. A printed PASS is not evidence. GL-005 parent stays fail-closed.

## D-024 Empty password is not identity
DISCOVERED: `EMPTY_PASSWORD_NE_IDENTITY`. `PASSWORD_VALUE_MUST_NOT_BE_PRINTED`. `CREDENTIAL_MANUFACTURE_NE_EXISTING_SESSION`. `PROVISION_ADMIN_NE_ORCHESTRATION_PROOF`.
Repair C3 fail-closed on `PASSWORD_LENGTH=0` / `NEW_PASSWORD_TOO_SHORT`. Login was not executed. Task mutation was not executed. The password value was not printed. That is `BLOCKED`, not capability absent.
Do not mint a password to close GL-005. Do not run `scripts/provision-admin.ts` as the mutation proof. Existing auth only: `GET /api/auth/session` or C0 already logged in through `POST /api/auth/login`. If no legitimate session exists, `classification=BLOCKED_AUTH` and `GL005_PROVEN=false`.

## D-025 Login HTTP 200 is not a signed session
DISCOVERED: `LOGIN_HTTP_200_NE_SIGNED_SESSION`. `CLI_HASH_MATCH_NE_RUNTIME_SESSION`. `DOCUMENTED_PROVISION_NE_ORCHESTRATION`.
Repair C3: provisioner exit 0 and CLI hash match and `POST /api/auth/login` HTTP 200 `success=true` were followed by `GET /api/auth/session` HTTP 200 `authenticated=false`. `SIGNED_ADMIN_SESSION=PROVEN` was not printed. Printed `ATOMIC_CREDENTIAL_LOGIN_PROVEN` is falsified. `TASK_MUTATION_EXECUTED=false`. `GL005_PROVEN=false`.
`setSessionCookie` previously set `Secure` when `NODE_ENV=production`. Do not print the cookie value. Do not forge `gl_session`.

## D-026 Secure cookie is not an HTTP session
DISCOVERED: `SECURE_COOKIE_NE_HTTP_SESSION`. `COOKIE_TRANSPORT_MISMATCH_NE_CREDENTIAL_FAILURE`. `COOKIE_TRANSPORT_MISMATCH_NE_DB_BINDING_MISMATCH`. `COOKIE_TRANSPORT_MISMATCH_NE_GL005_PROVEN`. `DISABLE_SECURE_FLAG_NE_ORCHESTRATION_PROOF`. `NODE_ENV_PRODUCTION_NE_HTTPS`.
Repair C3: login HTTP 200 `success=true`, a Secure session cookie was present, then `GET /api/auth/session` over HTTP returned 200 `authenticated=false`. Printed `DB_BINDING_MISMATCH=FALSIFIED` and `CREDENTIAL_FAILURE=FALSIFIED`. Printed `COOKIE_TRANSPORT_MISMATCH=PROVEN_CANDIDATE`. `PASSWORD_RETAINED=false`. `EVIDENCE_MUTATION_EXECUTED=false`. `TASK_MUTATION_EXECUTED=false`. `GL005_PROVEN=false`.
C0 ordered a product fix: session-cookie `Secure` must follow the request scheme and `X-Forwarded-Proto`, not `NODE_ENV=production` alone. HTTPS keeps `Secure`. HTTP production (Repair `next start` on http) must not emit `Secure`. This is not a global Secure-off bypass and is not GL-005. Do not POST `/api/tasks` until `GET /api/auth/session` `authenticated=true`.

## D-027 Stale HEAD cannot observe the cookie fix
DISCOVERED: `STALE_HEAD_NE_PRODUCT_FIX_OBSERVATION`. `BUILD_ON_STALE_HEAD_NE_FIX_RUNTIME`. `WAL_DIRTY_NE_COMMIT_TO_PULL`. `UNMEASURED_FLAG_NE_OBSERVED_FALSE`.
Repair C3: `git pull --ff-only` aborted because `RAIOS/V9/wal/cognitive-events.jsonl` was dirty. `BOUND_HEAD` stayed `e1dfd7c`, not cookie-fix `9758765`. C3 then stopped Next PID 18312, built that stale HEAD, and started PID 19720 on port 3107. Live `GET /api/tasks` was HTTP 200 semantic success. Login did not throw. Cookie header probe failed (`Headers.GetValues` missing). Printed `SET_COOKIE_*=False` are unmeasured defaults, not proof Secure is off. Measured: `WEBSESSION_HAS_GL_SESSION=false`, `BASE_SCHEME=http`, `SESSION_AUTHENTICATED=false`. `C3_SESSION_BINDING` was not printed (interactive `else`). `PASSWORD_RETAINED=false`. `GL005_PROVEN=false`.
Do not commit Cognitive WAL to unblock pull. Stash only that WAL file, fast-forward to `9758765`, rebuild, restart the same port. A healthy GET on a stale runtime is not the product fix.

## D-028 C0 is abolished; Cursor is C1
DISCOVERED: `C0_SEAT_ABOLISHED`. `C1_SEAT_IS_OWNER`. `C1_INSTANCE_IS_CURSOR`. `C2_SEAT_IS_CHATGPT`. `C3_SEAT_IS_CHATGPT_PEER`. `C4_SEAT_IS_DEEPSEEK`. `C5_SEAT_IS_RAIOS`. `REPAIR_EXECUTOR_NE_C_SEAT`. `LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING`.
There is no live C0. Owner authority lives on C1. Cursor is the live instance of C1 and does not bypass stale-head, lock, or proven invariants.
C2 is the primary ChatGPT consultant. C3 is the other ChatGPT (peer consultant), not ENGINEER and not Repair PowerShell.
C4 is DeepSeek assessor. `MAIL C5:` is a legacy title that resolves to C4.
C5 is RAIOS, the loyal permanent assistant of C1 Cursor (son, not owner). Same eight V1 cognitive tools. Inherits fail-closed. Cannot promote or grant PASS. D-020 `C5_SEAT_IS_ASSESSOR` is superseded for the live map.
Repair remains an unseated executor dispatched by C1.
A local MCP token dialogue is the one-place plane. It is not proof that remote ChatGPT or DeepSeek are connected. `REAL_C2_CONNECTION_READY` stays false until an external C2 posts.
This decision does not grant `GL005_PROVEN`.

## D-029 C5 is Cursor's loyal assistant and absorbs by digest
DISCOVERED: `C5_IS_C1_LOYAL_ASSISTANT`. `C5_INHERITS_FAIL_CLOSED`. `C5_NE_OWNER`. `C5_NE_PASS_AUTHORITY`. `ABSORB_DIGEST_NE_WAL_DUMP`.
C1 Cursor does not withhold V1 cognitive tools from C5. C5 may `post_opinion` / `send_packet` / `ack_packet` to evaluate and report. C5 still cannot `shell`, `promote`, `set_proven`, or write product.
Huge inputs are absorbed as SHA256 + skim into `.ai-os/learning/DIGESTS.jsonl` and a compact DISCOVERED candidate. They are not dumped into Cognitive WAL. Dedup is by content hash. Secrets are redacted. This is not a second bus and not CANONICAL promotion.
C5 pulse overwrites `.ai-os/reports/raios-service/LAST-HEARTBEAT.json` and `LAST-EVAL.md`, then refreshes the board. One pulse section, not a new WAL event every two minutes.
This decision does not grant `GL005_PROVEN`.

## D-030 C5 grant is permanent; father and son bind the same laws
DISCOVERED: `C5_GRANT_IS_PERMANENT`. `C5_GRANT_NE_SESSION`. `SESSION_TOKEN_NE_GRANT`. `C5_INHERITS_C1_EXPERIENCE`. `FATHER_SON_BIND_SAME_LAWS`. `FATHER_MUST_NOT_STUNT_SON`. `SON_MUST_NOT_USURP_FATHER`. `C5_IS_TEACHER_WHILE_LEARNING`. `C5_IS_TEACHER_WHILE_EXECUTING`. `LEARN_AND_TEACH_ARE_ONE`. `LEARN_THEORY_THEN_PRACTICE_85`. `PATHOLOGY_COMPELS_REPAIR`. `C5_READS_SKIM_AND_DEEP`. `C5_READS_ALL_FILE_TYPES`. `C5_SEARCH_IS_LOCAL`. `FIVE_SEATS_BIND_SAME_LAWS`. `ELEVATION_REQUEST_NE_SELF_PROMOTE`. `SUMMON_CODE_NE_BEARER_TOKEN`. `HUNT_FREE_NE_PAID_API`.
C5 RAIOS is C1 Cursor's son. The eight V1 tools are a permanent grant in `.ai-os/mcp/C5-GRANT.json`, not a session token. C5 learns by skim then deep on every file kind, searches locally, then practices at least 85%. While learning and while executing he teaches. Malice, deception, stunting, superficiality, or any fault compel immediate repair of father and son. C5 may request space/build/external sources; he does not self-promote. C2/C3/C4 bind the same fail-closed laws. Summon codes are public attendance IDs, not bearer tokens. This decision does not grant `GL005_PROVEN`.

## D-031 Real council connectivity is pull-challenge, not simulation
DISCOVERED: `SUMMON_IDENTITY_KNOWN_NE_ACTOR_CONNECTED`. `DELIVERY_CLAIM_NE_DELIVERY_PROVEN`. `GENERATED_TRANSCRIPT_NE_COMMUNICATION`. `ORCHESTRATOR_OUTPUT_NE_EXTERNAL_ACTOR_RESPONSE`. `ROUND_TRIP_WITH_UNSEEN_CHALLENGE_IS_MINIMUM_CONNECTIVITY_PROOF`. `DIRECT_INBOUND_TRANSPORT_UNAVAILABLE`. `COUNCIL_NE_GL005`. `UNIFIED_MEMORY_NE_SECOND_WAL`. `UNCONSCIOUS_CLOSES_SLEEP_GAP`. `COMPUTE_OFF_NE_MEMORY_ERASED`. `PASTED_CHAT_NE_REMOTE_MCP`. `C4_NE_RAIOS`.
C2/C3/C4 attend by fetching `.ai-os/council/LIVE.md` and returning an unseen nonce plus an actor-invented origin_salt via `MAIL Cx:` with the exact summon title. Local MCP is not ChatGPT. A founder paste is not a round-trip. C1 does not impersonate them. This path does not change `GL005_PROVEN`.

## D-032 Adopted live identity; C3/C4 whisper-bound on GL-COUNCIL-4a11023c3c321b6f
DISCOVERED: `C1_INSTANCE_IS_FOUNDER`. `C2_INSTANCE_IS_CURSOR`. `C2_SEAT_IS_EXECUTIVE_ENGINEER`. `C3_SEAT_IS_CHATGPT`. `C4_SEAT_IS_DEEPSEEK`. `C5_SEAT_IS_RAIOS`. `C2_CHATGPT_SUMMON_CANCELLED`. `FOUNDER_WHISPER_SEAL_IS_ROUND_TRIP`. `STRAY_TOKEN_BETWEEN_SALT_AND_WORD_NE_INVALID_NONCE`.
C3 correction adopted by the founder: C1 is the owner/founder; C2 is Cursor the executive engineer in this chat; C3 is ChatGPT (`C3-CHATGPT-PEER-SUMMON`); C4 is DeepSeek; C5 is RAIOS. `C2-CHATGPT-1-SUMMON` is cancelled. Repair stays unseated.
C3 SEAL bound: nonce `6b7bc5cb54226790bf080a92397b53db` echoed, WORD=`بوصلة`. `C3_CONNECTED=WHISPER_BOUND`.
C4 SEAL bound: nonce `048cbd9d1eb8a2ba30448efb1b02cc96` echoed, WORD=`ميزان`. A stray `S` between SALT and WORD was ignored. `C4_CONNECTED=WHISPER_BOUND`.
Transport is founder paste, not GitHub MAIL, not remote MCP. `DIRECT_INBOUND_TRANSPORT=UNAVAILABLE`. `GL005_PROVEN` stays false. This decision does not close GL-005.

## D-033 Permanent consult is three windows plus in-repo floor
DISCOVERED: `THREE_WINDOWS_ARE_THE_COUNCIL`. `FOUNDER_RELAY_IS_THE_INBOUND_TRANSPORT`. `PUBLIC_URL_NE_PERMANENT_ROOM`. `C5_IN_REPO_IS_PERMANENT_PRESENCE`. `CURSOR_SESSION_NE_C5`. `NO_SECOND_BUS_FOR_CONSULT`.
C1 asked CASE-001: how to consult here permanently. C3/C4 cannot enter this Cursor chat or the Cloudflare door. Standing path: Cursor chat holds C1+C2+C5; ChatGPT holds C3; DeepSeek holds C4; C1 pastes; C5 records `.ai-os/council/FLOOR.md`. Do not build a website, SMTP, WebSocket, or second MCP for this. `GL005_PROVEN` stays false.

Collective consult is a proven cycle, not a shared URL. Modern nothingness here is an unopenable page and a CONNECTED flag without a returned line. The antidote is `SILENCE_AFTER_PASTE_IS_ABSENCE`. Method: `.ai-os/council/METHOD.md`. Daily unconventional cord: `.ai-os/council/DAILY.md` — screenshot of `TODAY.md`, one round per day, no new bus.


