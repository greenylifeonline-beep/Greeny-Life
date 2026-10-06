# Native channel contract, not complete

Date: 2026-10-06
Seat: C2
Task: RAIOS-NATIVE-MCP-SELFHEAL-20261002-02
Status: NOT DONE

Adopted contract in source: eight tools. Delegated execution stays on send_packet. execute_scoped_task is not a registered tool. compiled_service_marker was removed because it hid a tool_count mismatch.

Live listener PID 21944 still serves the previous nine-tool process. It was not reloaded. PID 26880 is absent (open error 87) and is not named in the C5 WAL, state, generation, or DCR child record. DCR owned_local_mcp_pids is 10176 while its supervisor parent is service 20672. The listener parent is python 14404 and the next parent 6628 is gone. Stop-Process was not used.

Loopback get_head returned HEAD dfc08e62a6392af53c9995e74278a5ba6d153a84 as LOOPBACK_READ. A non-grant bearer returned UNAUTHENTICATED and did not become C1. No token was disclosed. No delegated execution receipt was produced.

Evolution consumed WAL events 1c0a9e7f-278b-4614-b09e-fefa88ff0023 (FAILURE) and 7dec703d-8131-44c6-b6e6-b6ae1d3b93ba (DECISION).
