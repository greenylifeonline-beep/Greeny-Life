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
