# Handoff — Command Center promotion: system laws + integration mesh

- Agent: C2-CURSOR
- To: C1, C6, C8
- Task: RAIOS-CANONICAL-CONVERGENCE-001 (not claimed; aios `dependencies` KeyError fixed in source; TASKS ledger not mutated)
- Status: LIVE_CC_PROMOTED_LAWS_VISIBLE — seats still unbound; Actor ACK UNPROVEN
- Authority: C1 Arabic order 2026-09-27 — complete assigned work; no gap/abbreviation/conflict/duplication/fake result; laws in the system for everyone not chat-only; close gaps; promote Command Center; prove whole-system interconnection

## Existing-first (no second plane)

Reused: CORE-CONTRACT, RAIOS-SINGLE-TRUTH-POLICY, Command Center `:8770` TX `C6-WORKER-PRIORITY-20260927-03`, hanging_work, live_plane, system_topology, DirectConversation, MessageWorker.

Not created: second Command Center, bus, task ledger, or constitution.

C6 sources not overwritten: `message_worker.py`, `session_agent.py`, `coordination_truth.py`, `Start-RAIOS-Seat-Session.ps1`, `Ensure-RAIOS-Seat-Sessions.ps1`.

## Laws now system-visible

1. `.ai-os/CORE-CONTRACT.md` Completion — ten binding operator laws.
2. `.ai-os/governance/RAIOS-SINGLE-TRUTH-POLICY.json` `completion_operator_laws` (`chat_only: false`).
3. `.ai-os/state/DECISIONS.md` D-059.
4. Command Center `/api/laws` and `/health.operator_laws`.
5. Council-state `laws[]` includes COMPLETE_ASSIGNED_WORK / NO_FAKE_* / LAWS_SYSTEM_VISIBLE.
6. UI cards: المشهد التشغيلي، العمل، الطوبولوجيا، التشخيص.

Law ids: COMPLETE_ASSIGNED_WORK, NO_ABBREVIATION, NO_CONFLICT, NO_DUPLICATION, NO_FAKE_RESULT, NO_FAKE_DONE, NO_HANGING_WITHOUT_NOTICE, LAWS_SYSTEM_VISIBLE, EXISTING_FIRST, ONE_COMMAND_CENTER, DELIVERY_ACK_NE_ACTOR_ACK, C5_RUNTIME_NE_SEAT_PRESENCE.

## Command Center repairs (in place)

- TASKS.json mtime cache (`load_tasks_document`) — not a second ledger.
- `/api/overview` C5 HTTP 2.5s; TIMEOUT stays UNKNOWN not OFFLINE; probes parallel.
- `/api/system-topology` now uses `live_plane()` services (was empty).
- `/api/council-state` persist=False (no rewrite of COUNCIL-MEMBER-STATE.json on poll).
- `/api/integration` mesh: CC, C5, MCP, 9Router, NATS, Fabric, DirectConversation, laws, hanging work, factories, EcoModel, live seats. Does not walk presence-challenges.
- `aios.py task-claim` missing `dependencies` is empty not KeyError.
- `/api/command` one-shot process skips mocks without `inbox`.
- Live board includes 9Router TCP.

## Tests

`8 passed` focused: bilingual surface, command ALL, lazy command_fabric, health/laws, operator laws, integration mesh does not fake full bind, TASKS cache, council persist=False.

Prior combined run: 63 passed; 3 failures fixed then re-proven.

## Live this slice

- Overlay into TX `C6-WORKER-PRIORITY-20260927-03`: app.py, index.html, system_surface.py, board_now.py, council_member_state.py, catalog.py.
- Restart :8770 START 9120 (after hang-fix overlay). HEALTH_ONLINE worker=ONLINE laws_count=12 chat_only=False.
- `GET /api/laws` HTTP 200, 12 ids, chat_only=false.
- `GET /api/integration` HTTP 200 overall=PARTIAL fully_integrated=false fake_integrated=false live_bound=0 actor_ack_proven=false.
  - ONLINE/WIRED/VISIBLE/INFORMED/PASS: CommandCenter, CommandFabric, DirectConversation, OperatorLaws, HangingWork, FactoryFabric PASS, EcoModel WIRED.
  - OFFLINE/UNKNOWN/UNBOUND: C5, MCP, 9Router, NATS, live seats.

## Honest remainder (not faked)

- Live-bound seats = 0. Actor ACK UNPROVEN. `fully_integrated` stays false until live-bound consumers exist.
- C5 :8766 / MCP :8788 / 9Router :20128 TCP were False on the 2026-09-27T17:44Z probe — PARTIAL mesh, not INTEGRATED.
- C6/C8 still must self-bind. C2 will not impersonate C6 auth or start C6 session.
- Open TASKS not stamped DONE. SAFE_TO_REMOVE_SOURCE=false. RAIOS-C5-Permanent not killed.
- Full Deploy-RAIOS-Command-Center.ps1 not stolen; surgical overlay only with C1 authorization.

## Next

1. C6: SeatSessionRecoveryInPlace then live consumer heartbeat.
2. C8: provider-live Ensure if `RAIOS_C8_PROVIDER_LIVE=1`.
3. Restore C5/MCP/9Router listeners if they remain TCP-closed; then `/api/integration` should move from PARTIAL toward CONTROL_PLANE_BOUND_SEATS_UNBOUND without faking seats.
4. Do not mark CONVERGENCE-001 DONE.
