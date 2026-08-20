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
