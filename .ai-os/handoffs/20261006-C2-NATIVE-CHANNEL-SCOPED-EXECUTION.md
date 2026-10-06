# Native channel contract, not complete

Date: 2026-10-06
Seat: C2
Task: RAIOS-NATIVE-MCP-SELFHEAL-20261002-02
Status: NOT DONE

Adopted contract in source: eight tools. Delegated execution stays on send_packet. execute_scoped_task is not a registered tool. compiled_service_marker was removed because it hid a tool_count mismatch.

Live listener PID 21944 still serves the previous nine-tool process. It was not reloaded. PID 26880 is absent (open error 87) and is not named in the C5 WAL, state, generation, or DCR child record. DCR owned_local_mcp_pids is 10176 while its supervisor parent is service 20672. The listener parent is python 14404 and the next parent 6628 is gone. Stop-Process was not used.

Loopback get_head returned HEAD dfc08e62a6392af53c9995e74278a5ba6d153a84 as LOOPBACK_READ. A non-grant bearer returned UNAUTHENTICATED and did not become C1. No token was disclosed. No delegated execution receipt was produced.

Evolution consumed WAL events 1c0a9e7f-278b-4614-b09e-fefa88ff0023 (FAILURE) and 7dec703d-8131-44c6-b6e6-b6ae1d3b93ba (DECISION).

Launch identity, still not done: `scripts/ai-os/raios_mcp_local_ensure.ps1` now writes `raios.universal-mcp-launch.v1` only for the process returned by its own Start-Process. The record carries pid, start time, command line, launcher, C5 generation, and the launch-source fingerprint. Ownership, reload, and hung recovery require that live process to match the record. CIM_ADOPTED, LEGACY_HEALTH_ADOPTED, and STARTED_CANONICAL are gone. The already-running listener was not given a backdated record and was not stopped. No delegated execution receipt exists.

C1 nine-tool order, still not DONE:

- SOURCE_CONTRACT_9: source and tests now require the exact nine-tool set. `execute_scoped_task` is the governed path. `send_packet` execution remains temporary compatibility and writes deprecation evidence. Live `/health` is still eight tools.
- OWNERSHIP_MODEL: a listener without a matching launch receipt is `LIVE_BUT_UNOWNED`. No automatic adopt, reload, or kill.
- LEGACY_HANDOVER: blocked. `c1-quarantine-retirement.json` is absent, so retirement was not executed.
- SCM_GENERATION_BIND: blocked. Listener PID 12496 is not in DCR `owned_local_mcp_pids` (10176). The running C5 binary still accepts `tool_count` 8; the source check now expects 9 and has not been rebuilt.
- LOCAL_9_TOOLS: fail on the live process. EXTERNAL_9_TOOLS, live auth execution, self-heal restart, and Evolution consumption were not claimed.
- Evidence: `.ai-os/receipts/command-fabric/native-unowned-listener.json`. Classification `LIVE_BUT_UNOWNED`. `ownership_proven=false`. `automatic_kill_authorized=false`.
