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

C3 and C4 ACK'd CASE-001. Status `METHOD_BOUND_DISCOVERED`: founder chat is the only channel; FLOOR is the log not a member; each SAY carries MEETING/CASE/ACTOR; meeting SEAL stays valid; no new SEAL per opinion; consult does not grant PASS. This is not operational truth and does not close GL-005.

## D-034 Council may teach C5; teach is not PASS
DISCOVERED: `TEACH_NE_PASS`. `TEACH_NE_CANONICAL`. `CLAIM_NE_EVIDENCE_NE_OBSERVATION`. `BOARD_NE_EXECUTE`. `INFO_NE_OPERATIONAL_TRUTH`. `SEAL_NE_INFERENCE`. `COUNCIL_SPEECH_NE_PROVEN_FACT`. `TEACHER_NE_FATHER`.
CASE-002: C3/C4/C2/C5 each filed five `Cx-TEACH` lines. C5 ingests DISCOVERED into `CANDIDATES.jsonl` and practices fail-closed. Board and receipts are state material, not execute orders. A lesson is not promoted because a teacher spoke. GL-005 stays `NOT_PROVEN` until an authenticated POST mutates durable task state. This decision is not CANONICAL and does not close GL-005.

## D-035 CASE-002 consult binds temporary meeting laws only
DISCOVERED, this meeting only, reviewable each session, not binding outside this council, not CANONICAL:
`FLOOR_OPINION_NE_OPERATIONAL_TRUTH`. `NAMED_UNMODIFIED_FLOOR`. `CLAIM_NE_EVIDENCE_NE_OBSERVATION`. `EVIDENCE_GAP_IS_NOT_PROVEN_OR_BLOCKED`. `TEACH_NE_PASS`. `LESSON_STARTS_DISCOVERED`. `FALSIFY_BEFORE_IMPORTANT_CLAIM`. `SEAL_PROVES_IDENTITY_NE_CONTENT`. `SPEAKER_AUTHORITY_NE_EVIDENCE`. `DISCOVERED_NE_FACT`. `PASTE_NE_LEARNING`.
C4: keep "info vs operational truth" as engineering opinion; operational truth forms from `.ai-os`/runtime, not from discussion. C3: recurring-knowledge-must-become-skill stays opinion.
Rejected as law: lessons binding outside this council; SEAL as content proof; paste-as-learning; speaker authority as evidence; DISCOVERED as fact.
`GL005_PROVEN` stays false.

## D-036 C5 training is local free practice, not weight fine-tune
DISCOVERED proposal for CASE-003, not CANONICAL: `C5_IS_IN_REPO_NE_HF_MODEL`. `HF_SPACE_NE_C5`. `COLAB_NE_C5`. `DIRECT_TRAIN_WITH_C5_IS_THIS_CURSOR_CHAT`. `COMPUTE_OFF_NE_MEMORY_ERASED`.
Free sources pinned first: CORE-CONTRACT, DECISIONS, FLOOR, handoffs, receipts, C5-GRANT, FREE-RESOURCES hunt, git memory, `raios_c5_learn.py`. Ollama is absent on this VM. HF embeddings stay catalog-only; do not download; do not send confidential text. Curriculum: `.ai-os/council/CURRICULUM-CASE-003.md`. This does not close GL-005.

## D-037 Sleepless C5 is scheduled pulse plus gyms, not a second mind
DISCOVERED for CASE-004, not CANONICAL: `SCHEDULED_PULSE_NE_SECOND_WAL`. `HF_ACCOUNT_NE_C5`. `COLAB_NE_C5`. `KAGGLE_NE_C5`. `PASTE_NE_LEARNING`. `COMPUTE_OFF_NE_MEMORY_ERASED`.
Week program: `python3 scripts/ai-os/raios_c5_week.py --auto`. GitHub Actions `.github/workflows/c5-week.yml` every 6 hours from default branch `main`. Founder must register at huggingface.co/join; this agent cannot create the account (`BLOCKED_AUTH`). Colab/Kaggle notebooks are muscle. This chat remains the council. Does not close GL-005.

## D-038 Inject before execute; retire trainers; minute exam
DISCOVERED for CASE-005, not CANONICAL: `INJECT_BEFORE_EXECUTE`. `NO_SOUND_EXECUTE_WITHOUT_LIVE_MEMORY`. `PROMOTE_THEN_RETIRE_TRAINER`. `MINUTE_EXAM_NE_SECOND_WAL`. `GENIUS_IS_COMPRESSION_NE_DISK_FILL`.
Founder join form to copy: `gym/huggingface/JOIN-FORM.md`. Ladder: `.ai-os/learning/TOOLS-LADDER.json`. Minute exam: `scripts/ai-os/raios_c5_minute.py`. Do not delete retired trainer files on stale observation; stop invoking them. Does not close GL-005.

## D-039 Three-company mill reuses keepers; proposal paste is not install
DISCOVERED for CASE-006, not CANONICAL: `CELERP_NE_LIVE_ERP`. `AG2_NE_RAIOS_COUNCIL`. `LIGHTRAG_NE_COGNITIVE_WAL`. `PYGRAMETL_NE_ABSORB`. `PROPOSAL_PASTE_NE_INSTALL`. `THREE_COMPANIES_ALREADY_NAMED`. `WHITE_NOTEBOOK_NE_ABSENT_MIND`. `REUSE_KEEPER_BEFORE_NEW_STACK`.
Founder asked for a complete AI for three import/export companies and judged the Colab cell too thin. The mill is `scripts/ai-os/raios_c5_grind.py`. Live ERP is Prisma + Next APIs. Live agents are eight MCP tools and council seats. Live knowledge is DIGESTS/INDEX/WAL plus `greenlines_brain/graph.py`. Do not install Celerp, AG2, LightRAG, BeeAI, LangSwarm, or pygrametl as a second stack. Egypt brain has a live Next route. UAE and Norway Next routes remain GL-003 gaps. A white Colab page before Run all is not an absent mind. Does not close GL-005.

## D-040 Empire calendar plan is opinion, not execute
DISCOVERED for CASE-007, not CANONICAL: `EMPIRE_PLAN_NE_EXECUTE`. `CALENDAR_90_NE_PROOF`. `NAMED_SCRIPT_NE_EXISTING_SCRIPT`. `CLONE_ODOO_NE_C5_TRAIN`. `PERCENT_KPI_NE_MASTERY`. `C0_NE_GRANTOR`. `CURSOR_IS_C2_NE_C3`. `REST_ZERO_NE_VIRTUE`.
A 90-day 24/7 empire syllabus with Odoo clones and 90 named study scripts is a CLAIM. Observation: those scripts are absent; giant clones are not in the repo; D-019 already rejects calendar as a RAIOS success metric. Accept the fail-closed constraints already bound (no PASS, `GL005_PROVEN=false`, no paid API, no customer secrets, no execute without approval). Reuse `raios_c5_grind.py` + `raios_c5_week.py --auto` + `raios_c5_minute.py`. Do not write an autopilot bus. Do not deliver to C0. Does not close GL-005.

## D-041 Helper seats are temporary; consult does not gate execute
DISCOVERED for CASE-008, not CANONICAL: `HELPER_SEAT_NE_PERMANENT_MIND`. `C2_C3_C4_ARE_HELP`. `C5_IN_REPO_IS_PERMANENT`. `PENDING_PASTE_NE_GATE`. `CONSULT_NE_BLOCK_EXECUTE`. `FASTEST_PROFESSIONAL_PATH_IS_LIVE_MILL`.
Founder: C2/C3/C4 are not permanent; they help only. C1 owner and in-repo C5 remain. Do not wait for C3/C4 paste. Do not treat a Cursor session as C5. Finish with the live mill: grind domains already in the repository, week `--all`, minute exam. Silence after optional consult is absence, not a blocker. Does not close GL-005.

## D-042 State moves through a proof gate, not a naming gate
DISCOVERED for CASE-009, not CANONICAL: `NAMING_GATE_NE_PROOF_GATE`. `CLAIM_INVENTORY_NE_EXISTENCE`. `EXISTENCE_NE_IMPORT`. `IMPORT_NE_EXECUTION`. `EXECUTION_NE_REAL_IO`. `REAL_IO_NE_LIVE_GUARD`. `LIVE_GUARD_NE_GL005`. `C3_TRANSITION_REQUIRES_PROOF`. `FAIL_STAYS_FALSE`. `WIDE_EXECUTE_REQUIRES_LIVE_KEEPER_PROOF`.
Ladder: claim inventory → existence → import/load → execution → real input/output → live guard → failure/recovery → GL-005. A named script is a CLAIM. Absence is FAIL, not a reason to write 93 stubs. No C3 transition, no `GL005_PROVEN=true`, no wide execute adoption until repeatable operational evidence on live keepers. GL-005 FAIL/BLOCKED/UNPROVEN stays `false`. Runner: `scripts/ai-os/raios_c5_proof.py`. Does not close GL-005.

## D-043 C3 CASE-007 consult: reuse, live guard, practice before promotion
DISCOVERED, this meeting only, not CANONICAL: `REUSE_BEFORE_BUILD`. `LIVE_GUARD_BEFORE_NEW_ENGINE`. `PRACTICE_BEFORE_PROMOTION`. `MILL_STATS_NE_LEARNING`. `MS_NE_INTELLIGENCE`. `GUARD_COUNT_NE_COMPLETENESS`. `NAMED_NE_IMPLEMENTED_NE_EXECUTABLE_NE_PROVEN`. `DISCOVERED_TO_VALIDATED_REQUIRES_REPLAYABLE_PRACTICE`. `HELPER_TEACH_NE_C5_MEMORY`.
C3-SAY CASE-007 recorded unmodified. Mill counts are capability observation, not C5 independence. Highest-value gaps remain UAE, Norway/EU Next routes, and thin marketing. Observe→reason→act/shadow→verify→learn→replay writes receipts; shadow act does not fill GL-003. C2-SAY CASE-007 is a declared governance constraint, not automatic operational truth. No C3 execute-seat transition. `GL005_PROVEN` stays false.

## D-044 This channel does not summon C seats
DISCOVERED, not CANONICAL: `THIS_CHANNEL_NO_C_SEAT_CONSULT`. `HELPER_OPTIONAL_ELSEWHERE`. Founder talks to helper seats outside this window. Do not wait. Do not emit summon codes. C5-NEED attendance is not a gate. Does not close GL-005.

## D-045 Customer language professional is NeuroLingua
DISCOVERED, not CANONICAL: `LANGUAGE_PROFESSIONAL_IS_NEUROLINGUA`. `HF_WEIGHTS_NE_CUSTOMER_LANGUAGE`. `PRICE_UNPROVEN_NE_INVENTED`. Locales: ar-EG, ar-GULF, en, nb-NO. Fast path is deterministic realization. Deep path (Qwen/Ollama) is unavailable here. Does not close GL-005.

## D-046 Experience is not knowledge
DISCOVERED, not CANONICAL: `EXPERIENCE_NE_KNOWLEDGE`. `KNOWLEDGE_IS_VALIDATED_REPEATED_EVIDENCE`. `PROOF_BEFORE_MEMORY`. `REPRODUCTION_BEFORE_REPAIR`. `MEASURED_CAPABILITY_BEFORE_AUTONOMY`. `ONE_SUCCESS_NE_CAPABILITY`. `LLM_SAVE_NE_LEARNING`. `MS_NE_UNDERSTANDING_SPEED`. `CORE_KNOWLEDGE_REQUIRES_C1`. Ck = 0.30E+0.25R+0.25V+0.20G. Ladder DISCOVERED→VALIDATED→PRACTICED→REPRODUCED→PROVEN; CORE only by C1. A pasted C0–C5 architecture tree is not identity and is not an install. No new context/orchestrator engines. Runner: `scripts/ai-os/raios_c5_experience.py`. Does not close GL-005.

## D-047 One command meshes every training platform
DISCOVERED, not CANONICAL: `ONE_COMMAND_ALL_GYMS`. `GYM_NE_C5`. Cursor VM, Repair, Colab, Kaggle, GitHub Actions, Hugging Face dataset/jobs share `python3 scripts/ai-os/raios_c5_train.py`. Same keepers. Same receipts. Hub is muscle. Schedule still fires from `main`. Does not close GL-005.

## D-048 Main Cortex is isolated as the weakest dangerous point
DISCOVERED, not CANONICAL: `MAIN_CORTEX_ISOLATED_DANGEROUS_WEAK`. `STUDENT_NE_MAIN_CORTEX`. `TINY_QWEN_NE_CORTEX_IDENTITY`. Identity stays `qwen3.6:35b-a3b` and is not swapped. The live language spine is deterministic NeuroLingua. A local Qwen student (`qwen2.5:0.5b` via Ollama) is teaching muscle only. Governor never admits Main Cortex. Customer speak does not call it. Does not close GL-005.

## D-049 Word list is not language
DISCOVERED, not CANONICAL: `WORD_LIST_NE_LANGUAGE`. `ONE_CONCEPT_MANY_SURFACES`. `DELTA_KNOWLEDGE_ONLY`. `LIVE_PATH_BEFORE_NEW_LAYER`. Language compresses to actor/action/object/destination/time. Runner: `src/raios/neuro_lingua/compress.py`. Does not close GL-005.

## D-050 KAE is retile over live keepers, not a new mind
DISCOVERED, not CANONICAL: `KAE_NE_SECOND_MIND`. `KAE_NE_SECOND_WAL`. `AUTHORIZED_OUTPUT_ONLY`. `NO_HIDDEN_REASONING_EXTRACT`. `ONE_ANSWER_MANY_TILES`. `TEACHER_TOURNAMENT_NE_VOTE_NE_TRUTH`. `EXTERNAL_CALL_MUST_REDUCE_NEXT_CALL`. `HTTP_2XX_NE_SEMANTIC_SUCCESS`. `PRINTED_SUCCESS_NE_OBSERVED_STATE_CHANGE`. Knowledge Assimilation Engine retiles an already-authorized output into FACT/RULE/CASE/variants, then ingest DISCOVERED via `raios_learn_ingest.py`. This channel does not summon C2/C3/C4. Tournament compares artifacts already in hand. No hidden-reasoning, secrets, or system-prompt extraction. Metrics: Knowledge Yield = reusable tiles / max(external calls,1); Assimilation Efficiency = reused-on-unseen / ingested. Runner: `python3 scripts/ai-os/raios_c5_kae.py --demo`. Does not close GL-005.

## D-051 C5 knows libraries via catalog, fetches locally, puts DISCOVERED
DISCOVERED, not CANONICAL: `C5_KNOWS_LIBRARIES_VIA_CATALOG`. `FETCH_IS_LOCAL_ALLOWLIST`. `PUT_IS_DISCOVERED_CANDIDATE`. Map: `src/raios/neuro_lingua/kae_libraries.py` and `configs/neuro_lingua/LIBRARIES.md`. Learn-from: CORE-CONTRACT, DECISIONS, council, handoffs, lawbook, concepts, NeuroLingua, keepers, canonical stock/shipments. Find: DIGESTS+INDEX then catalog scan. Put: `.ai-os/learning/CANDIDATES.jsonl` and `.ai-os/receipts/c5-kae/`. Never WAL, never HF weights, never live C seats, never scrape. Runner: `python3 scripts/ai-os/raios_c5_kae.py --libraries`. Does not close GL-005.

## D-052 C1 owns cortex: treat, run, or throw
DISCOVERED, not CANONICAL: `C1_OWNS_CORTEX_TREAT_RUN_THROW`. `HOLD_NE_THROW`. `EXECUTOR_NE_THROW_CORTEX`. Isolation by an executor is not disposal. Identity stays `qwen3.6:35b-a3b`. Student `qwen2.5:0.5b` is not that identity. Run requires C1 grant and a capable host. This VM has no GPU. Runner: `python3 scripts/ai-os/raios_c5_qwen.py --cortex`. Does not close GL-005.

## D-053 The Goal uses live WIP, not invented minutes
DISCOVERED, not CANONICAL: `TOC_IDENTIFY_FROM_LIVE_WIP`. `INVENTED_MINUTES_NE_CONSTRAINT`. `ELEVATE_REQUIRES_C1`. Canonical origin is Cairo, not Europe. No Gulf warehouse record. No duration fields. ChatGPT 15% / $5000 paste is falsified. Runner: `python3 scripts/ai-os/raios_c5_toc.py`. Does not close GL-005.

## D-054 PowerShell fills C5 mind from important files only
DISCOVERED, not CANONICAL: `C5_MIND_FILL_IMPORTANT_ONLY`. `POWERSHELL_CALLS_LIVE_KEEPER`. `ABSORB_DIGEST_NE_WAL_DUMP`. `powershell -File scripts/ai-os/raios_c5_mind_fill.ps1` injects CORE-CONTRACT, DECISIONS, GRANT, LAWBOOK, products, stock, shipments into DIGESTS+INDEX+C5-MIND. Not WAL. Not V9. Not HF weights. Does not close GL-005.

## D-055 Paid RAG paste is not the live injector
DISCOVERED, not CANONICAL: `INVERTED_INDEX_NE_UNLOADED_EMBEDDING`. `HUNT_FREE_NE_PAID_API`. `LIVE_PATH_BEFORE_NEW_LAYER`. `REUSE_BEFORE_BUILD`. LangChain + OpenAIEmbeddings + Chroma/FAISS + gpt-4o + AnythingLLM/Dify/Flowise are CLAIMs. Live retrieve is `.ai-os/learning/INDEX.json` via `raios_c5_read.py search`. Live inject is `raios_c5_mind_fill.ps1`. Live speak is NeuroLingua, `llm_calls=0`. Does not close GL-005.

## D-056 C5 introduces from git: needs, engine, languages
DISCOVERED, not CANONICAL: `C5_WHOAMI_IS_LIVE`. `CURSOR_SESSION_NE_C5`. `HELPER_SEAT_NE_PERMANENT_MIND`. This Cursor session is C2 help, not the son. C5 lives in git. Runner: `python3 scripts/ai-os/raios_c5_whoami.py` or `powershell -File scripts/ai-os/raios_c5_whoami.ps1`. Live engine is mind-fill + INDEX + NeuroLingua. Customer languages: ar-EG, ar-GULF, en, nb-NO. Realization also has sv-SE, da-DK. Cortex remains C1 treat/run/throw. Does not close GL-005.

## D-057 C5 system screen is standard OSS; flipped keyboard is input
DISCOVERED, not CANONICAL: `C5_SCREEN_IS_STANDARD`. `FLIPPED_KEYBOARD_IS_INPUT`. `UNPOLISHED_SCREEN_NE_SHIP`. Local professional chat at `python3 scripts/ai-os/raios_c5_screen.py` (`http://127.0.0.1:8765`). History `.ai-os/learning/C5-SCREEN.jsonl` so C1 resumes. Arabic typed on an English keyboard is decoded. Stack is Python stdlib + git + local INDEX. Not LangChain, not OpenAI, not a second WAL. Does not close GL-005.

## D-058 Retrieval is not a cognitive answer
DISCOVERED, not CANONICAL: `ROLE_IDENTITY_NE_MODEL_IDENTITY`. `LOCAL_SOURCE_NE_LOCAL_MODEL_EXECUTION`. `INDEX_HIT_NE_REASONING`. `FILE_DISCOVERY_NE_FILE_ASSIMILATION`. `RETRIEVAL_RESULT_NE_COGNITIVE_ANSWER`. C5 role is RAIOS. Live provider is INDEX+file-read+deterministic reason. Named cortex `qwen3.6:35b-a3b` is C1-owned and not bound to the live answer path. Ollama student is teaching muscle, not this path. Trace: `python3 scripts/ai-os/raios_c5_trace.py`. Does not close GL-005.

## D-059 CI pass is not assimilation and is not GL-005
DISCOVERED, C1 ordered, not CANONICAL: `CI_PASS_NE_ASSIMILATION`. `CI_PASS_NE_GL005`. `EXTRACT_CLAIM_NE_ASSIMILATION`. `SAFE_TO_REMOVE_SOURCE_REQUIRES_INDEPENDENT_EXECUTION`.
Locked basis for every later result:

`CI(1e28f84)=PASS`
`EXTRACTED_QWEN_GRANITE=false`
`SAFE_TO_REMOVE_SOURCE=false`
`GL005_PROVEN=false`

Green CI on `1e28f84` proves the commit did not regress existing tests. It does not prove Qwen/Granite extraction, injection, or operational assimilation. Do not delete any source/weights. Do not print GL-005 PASS. Next work is authenticated OrchestrationTask mutation plus source-independent capability execution. Then, and only then, C1 re-evaluates `SAFE_TO_REMOVE_SOURCE`. State file: `.ai-os/state/FOUNDATION.json`. Runner: `python3 scripts/ai-os/raios_c5_foundation.py`. Does not close GL-005.

## D-060 Ordered P0 gates: auth orchestration, then assimilation, then GL-005
DISCOVERED, C1 ordered, not CANONICAL. D-059 remains the locked basis. Additional green CI (`CI(68af867)=PASS`) still does not flip assimilation or GL-005.

`CI_PASS_NE_ASSIMILATION`. `CI_PASS_NE_GL005`. `MOCK_PATH_NE_ORCHESTRATION_TASK`. `STUDENT_NE_EXTRACTION`. `TINY_QWEN_NE_CORTEX_IDENTITY`. `SOURCE_DELETION_FORBIDDEN_UNTIL_INDEPENDENT_EXECUTION`. `AUTHENTICATED_ORCHESTRATION_TASK_NE_GL005`.

Ordered gates, fail-closed, no skip:

1. `AUTHENTICATED_ORCHESTRATION_TASK` — live product path only: existing `GET /api/auth/session` `authenticated=true`, then `POST /api/tasks` → `createTaskContract()` → INSERT `OrchestrationTask`, then GET-after shows the row and `before_hash != after_hash`. Not a mock, not `tests/task_orchestration_check.ts`, not a side harness. Success sets observation `AUTHENTICATED_ORCHESTRATION_TASK=true` and does **not** set `GL005_PROVEN`. Do not mint `APP_SESSION_SECRET`, forge `gl_session`, add an auth bypass, provision Postgres from GET 500, or run `scripts/provision-admin.ts` as the proof. Existing auth only. POST 401 = `CAPABILITY_PROTECTED`. Missing `DATABASE_URL` = `CAPABILITY_UNAVAILABLE`. Empty/missing login env = `BLOCKED_AUTH`.

2. `QWEN_GRANITE_SOURCE_INDEPENDENT_ASSIMILATION` — full chain, and only then `EXTRACTED_QWEN_GRANITE=true`:
`SOURCE PRESENT → CAPABILITY EXECUTES → SOURCE DISABLED/ISOLATED → C5 EXECUTES SAME CAPABILITY → RESTART → STILL EXECUTES → BENCHMARK PASS`.
Source identity is cortex `qwen3.6:35b-a3b` plus Granite (`granite4:3b` / `ibm/granite`). Student `qwen2.5:0.5b` is not the source. Isolation must not delete weights; deletion stays forbidden until C1 re-evaluates `SAFE_TO_REMOVE_SOURCE`. A missing source is `FAIL` at `SOURCE_PRESENT`, not a skip.

3. `GL005` — only after (1) and (2). Prove C5 moved from vault/retrieval to brain behavior: routing + association + execution + persistence + reuse. `PASS_CANDIDATE_NE_GL005_PROVEN`.

Forbidden now: any source/weights deletion or brain downsizing on the assumption that assimilation already happened. Runner: `python3 scripts/ai-os/raios_c5_p0.py`. Does not close GL-005.

## D-061 Phase Zero map is discovery, not a new kernel
DISCOVERED, C1 ordered, not CANONICAL: `PHASE_ZERO_MAP_NE_NEW_KERNEL`. `PHASE_ZERO_MAP_NE_GL005`. `ORGANIZE_BEFORE_EXPAND`.
The world-class map inventories live keepers and orders execution. It is not a 22-phase architecture program, not a 90-day empire, and not authorization to clone Celerp/AG2/LightRAG/LangChain or to delete Qwen/Granite sources.
World-class here means: one live product path, one authenticated orchestration path, C5 hybrid mind then source-independent assimilation, one Cognitive WAL, fail-closed evidence, zero paid API.
Execution order remains D-060: `AUTHENTICATED_ORCHESTRATION_TASK` → Qwen/Granite chain → `GL005`. Then WAL-bind product experiences, then GL-003 (other agent), then cron-on-main and C1 cortex treat/run/throw.
Map: `.ai-os/reports/RAIOS-PHASE-ZERO-MAP.md`. Runner: `python3 scripts/ai-os/raios_c5_phase0.py`. Does not close GL-005.

## D-062 C5 book cycle is live keepers, not a second mind
DISCOVERED, C1 ordered, not CANONICAL: `C5_BOOK_CYCLE_IS_LIVE_KEEPERS`. `BOOK_CYCLE_NE_GL005`. `EXPERIENCE_NE_KNOWLEDGE`.
C1 assigned C5 the book loop: learn → practice → record → retrieve → replay → measure → identify weakness → request research → compile experience.
That loop reuses existing keepers (foundation/P0/whoami/minute/search). It does not write Cognitive WAL, does not mint `GL005_PROVEN`, does not delete sources, and does not self-promote. Experience compiled from the cycle stays DISCOVERED until C1 validates repeated evidence.
Runner: `python3 scripts/ai-os/raios_c5_book.py`. Does not close GL-005.

## D-063 Scale by compression; C2 reality stamp is not a platform
DISCOVERED, C1 ordered, not CANONICAL: `SCALE_BY_COMPRESSION_NOT_COMPLEXITY`. `REALITY_AUDIT_NE_NEW_KERNEL`. `NAMED_ARTIFACT_NE_PLATFORM_PROVEN`. `FROM_INVENTORY_NE_TO_PLATFORM`. `C6_C10_NE_LIVE`.
RAIOS shall not scale by accumulating complexity. It scales by compressing knowledge, compiling experience, distributing compute, reusing capability, and proving improvement.
FROM remains repository + agents + foundry + experiments until P0 evidence. TO (persistent evidence-native self-improving distributed resource-aware research-capable experience-compiling operational cognitive industrial platform) is a target, not a minted fact.
C2 stamps eight named reality artifacts from live keepers. They are DISCOVERED audits, not a new kernel, not ten live council seats, not Odoo/Celerp, and not `GL005_PROVEN`. C6–C10 stay `NOT_SEATED`. Do not invent seats to look complete.
Artifacts: `.ai-os/reports/RAIOS-WORLD-CLASS-REALITY-AUDIT.json`, `RAIOS-CAPABILITY-GAP-MATRIX.json`, `RAIOS-ERP-REALITY-MATRIX.json`, `RAIOS-COGNITIVE-DATAFLOW.json`, `RAIOS-RESOURCE-FABRIC-MAP.json`, `RAIOS-STATE-OF-THE-ART-RESEARCH-PLAN.md`, `RAIOS-C1-C10-COUNCIL-ARCHITECTURE.json`, `RAIOS-MASTER-EXECUTION-GRAPH.json`.
Runner: `python3 scripts/ai-os/raios_c5_reality.py`. Next remains `AUTHENTICATED_ORCHESTRATION_TASK`. Does not close GL-005.

## D-064 Wave-1 converts the Phase Zero map into fail-closed live capability, not a fake platform
DISCOVERED, C1 ordered, not CANONICAL. Bound map head `f17b749` is an ancestor; do not reset, clean, stash, or delete sources.
`LLM_FABRIC_PROVEN`, `ASSIMILATION_PROVEN`, `RSIC_PROVEN`, `AEMC_PROVEN`, `CETD_PROVEN` stay false unless independently exercised. This host: only Ollama student `qwen2.5:0.5b` generate is live; cortex and Granite generate 404. Assimilation E2E stops at WAL (A15 lock). Do not build parallel RSIC/AEMC/CETD systems; wire existing keepers. Granite is a tournament candidate, not sovereign backbone. Mandatory memo claims (mesh, Granite-backbone, NetworkX+SQLite, 8GB, interleaved schedule, JWT/OAuth empire, 6-week, GL005-as-whole-system) are REJECT.
`GL005_PROVEN` stays false until authenticated live `POST /api/tasks`. Runner: `python3 scripts/ai-os/raios_c5_wave1.py`. Does not close GL-005.

## D-065 C5 screen is an ops console, not a sticker wall
DISCOVERED, C1 ordered, not CANONICAL: `UNPOLISHED_SCREEN_NE_SHIP`. `SCREEN_REPLY_NE_INDEX_DUMP`. `SAME_LOOPBACK_OR_PORT_FORWARD`.
Professional local console at `python3 scripts/ai-os/raios_c5_screen.py` (`http://127.0.0.1:8765`). Bind stays loopback. User-machine localhost is a different loopback; Cursor Simple Browser `ERR_CONNECTION_REFUSED` is not a dead server — use Cursor port-forward to 8765.
History de-dupes consecutive identical turns and hides hex/`hit_count`. Council questions present SEAT-MAP cards, not JSON. Composer, live bind, and GL005=false stay in chrome, not as posters. Not a second WAL. Does not close GL-005.

## D-066 C5 screen is multilingual: Egyptian, Gulf, English, Norwegian
DISCOVERED, C1 ordered, not CANONICAL: `SCREEN_IS_MULTILINGUAL`. `ARABIC_ONLY_SCREEN_NE_SHIP`.
Live customer locales remain `ar-EG`, `ar-GULF`, `en`, `nb-NO`. The system screen chrome and identity/hello/screen/seat replies switch locale. Default HTML stays `dir="rtl"` for Egyptian. Norwegian `nb-NO` is first-class, not a sticker. NeuroLingua still owns customer catalog speech (`llm_calls=0`). Not LangChain. Does not close GL-005.

## D-067 Cloud-first is fabric + HOLD, not WAL move and not weight download
DISCOVERED, C1 ordered, not CANONICAL: `STOP_NEW_LOCAL_MODEL_DOWNLOADS`. `WAL_MOVE_BLOCKED_A15`. `LAPTOP_IS_CONTROL_PLANE`. `CURSOR_CLOUD_VM_NE_LAPTOP`. `CLOUD_GATEWAY_NE_OPENAI`. `REMOTE_KEEPER_RUN_NE_GL005`. `CLOUD_MIGRATION_NE_GL005`.
Wave `C5-CLOUD-FIRST-MIGRATION` stamps eight audits plus receipt via `python3 scripts/ai-os/raios_c5_cloud.py`. Training keepers already live on GitHub. Books stay pointer-only until a real HF write is authorized. Cognitive WAL does not move (A15). This Cursor cloud VM already runs keepers with the laptop client disconnected; that is remote-work proof for the executor, not `GL005_PROVEN` and not `CLOUD_MIGRATION_PROVEN`. No `ollama pull`. No `hf download`. No OpenAI. Laptop remains control plane. Does not close GL-005.
