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
