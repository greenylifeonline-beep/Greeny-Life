# C2 handoff — eight-tool MCP channel

TASK_ID=RAIOS-NATIVE-MCP-SELFHEAL-20261002-02
DONE=false
NINE_TOOL_ACTIVE=false
EXTERNAL_CHANNEL_DOWN=SUPERSEDED
P0_EIGHT_TOOL_READ_CHANNEL_RECOVERED=true
NOTE=C1 later proved EXTERNAL_GET_HEAD, EXTERNAL_READ_BOARD, and EXTERNAL_READ_INBOX PASS at head 9b5f1fb27e65f86daa90f821d32aee21e72d0b1b with mcp_tool_count=8. The unauthenticated 404 probe below is not the external read result. See 20261006-C2-GENERATION-LINEAGE-CUTOVER.md.

## Classification

SERVICE_RUNNING_NE_MCP_HEALTHY was correct at intake.
After rollback, maintain reached MCP and ensure started a server, then stopped it:
MCP_LISTENER_PID_NOT_LAUNCH_PID. The venv python.exe is a CreateProcess launcher;
netstat showed the base interpreter. No listener survived, so the pre-repair
state is ROLLBACK_SERVICE_DID_NOT_RESPAWN_MCP.

## Live eight-tool proof

PORT_8788_LISTENER_COUNT=1
listener pid=30148
parent pid=15880 (ensure, exited after LOCAL_MCP_ALREADY_HEALTHY)
SCM chain: service 30416 -> user lane 21944 -> maintain 20312 -> ensure 15880 -> python 30148
LAUNCH_RECEIPT_MATCH=true (schema raios.universal-mcp-launch.v1)
LOCAL_HEALTH_OK=true
LOCAL_TOOL_COUNT=8
HEAD_SOURCE=git-file
HEAD=9b5f1fb27e65f86daa90f821d32aee21e72d0b1b
DUPLICATE_MCP=false
service generation mcp_ready=true
tunnel readyz=200
local get_head returned that head
local read_board returned a board body

## External

Unauthenticated GET of the public tunnel URL and its /mcp suffix returned 404.
GET of the tunnels metadata route returned 401.
Tunnel client started, main channel routable, metadata fetched, poller operational.
No dispatcher forwarded command has arrived since that start.
EXTERNAL_GET_HEAD=FAIL
EXTERNAL_READ_BOARD=FAIL

## Acceptance timeout (not promoted)

ACCEPTANCE_TIMEOUT_STAGE=LIVE_ACCEPTANCE combined predicate
EXPECTED=service Running, tunnel ready, one session-0 tunnel, MCP tool_count 9 with execute_scoped_task, DCR ONLINE, within 150s
OBSERVED=listener absent after ensure killed the launcher PID, health not reached, contract 9 not reached, tunnel not ready
CHILD_PID=launch examples 26308 and 6812, stopped by ensure
CHILD_EXIT_CODE=ensure non-zero MCP_LISTENER_PID_NOT_LAUNCH_PID
LISTENER_CREATED=false at acceptance end
HEALTH_REACHED=false
CONTRACT_REACHED_9=false
SCM_GENERATION_BOUND=false for a nine-tool child
ROOT_CAUSE=venv launcher PID is not the socket owner, and the cutover window requires a nine-tool listener plus a ready tunnel before maintain can keep one
FIX_SCOPE=eight-tool ensure now starts the base interpreter; do not retry the nine-tool cutover until the external eight-tool channel passes

Nine-tool sources are preserved at C:\Users\Ghanam\.raios\runtime\continuity\c5-service\hold-9tool-20261006
