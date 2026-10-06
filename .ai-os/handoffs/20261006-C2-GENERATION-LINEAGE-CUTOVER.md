# C2 handoff — generation lineage, then one nine-tool cutover

TASK_ID=RAIOS-NATIVE-MCP-SELFHEAL-20261002-02
AUTHORITY=C1
DONE=false
P0_EIGHT_TOOL_READ_CHANNEL_RECOVERED=true
NINE_TOOL_ACTIVE=false
AUTH_EXECUTION=false
SELF_HEAL_9_TOOL=false

## Identity fix

ROOT_CAUSE=MCP_LAUNCHER_PID_NE_SOCKET_OWNER_PID is implemented as generation lineage.
LAUNCH_PID == LISTENER_PID is not the accept rule.
Regression tests A-I plus the launch-record script tests: 11 passed.
The rollback launch below is a live example of that rule: launcher pid 16708, listener pid 5196, one owner of port 8788, health accepted.

## Controlled cutover

Request c1-generation-lineage-20261006-nine was submitted once.
Broker receipt PASS means the helper started as SYSTEM. It does not mean acceptance.
Cutover receipt status=FAIL, rolled_back=true.
First failing gate=MCP_CHILD_LAUNCHED.

That gate required a user-lane log line, MCP_PROMOTE_EXIT CODE=0. The line was never written.
At the deadline the other local predicates were already true:

SERVICE_RUNNING=true
GENERATION_BOUND=true
LISTENER_CREATED=true
LISTENER_IDENTITY_VALID=true
PORT_8788_SINGLETON=true
HEALTH_REACHED=true
TOOL_COUNT_9=true
EXECUTE_SCOPED_TASK_PRESENT=true
TUNNEL_READY=true
DCR_ONLINE=true
EXTERNAL_CHANNEL_REACHED=false

The false log-line gate rolled a local nine-tool generation back.
The gate now also accepts a listener whose launch receipt was written after the cutover start.
No second cutover was submitted.

## Restored local channel

PORT_8788_LISTENER_COUNT=1
listener pid=5196
launcher pid=16708
parent of listener=16708
LOCAL_HEALTH_OK=true
LOCAL_TOOL_COUNT=8
HEAD=9b5f1fb27e65f86daa90f821d32aee21e72d0b1b
HEAD_SOURCE=git-file
server.py sha256=889051a8cee07e3ec48a8019847904b35ef2e9fb0bae5e2add7f7aedc01b1f97
service binary sha256=0c65d5f99de4a6c91a462924cde15062ff0caac33e178d62c08687f502d858ba
DUPLICATE_MCP=false

## Still open

SOURCE_CONTRACT_9 was loaded for the attempt and restored to the eight-tool bytes by rollback.
SERVICE_CONTRACT_9 remains source-only. The running service binary is the 4 October eight-tool image.
LOCAL_9_TOOLS=false after rollback.
EXTERNAL_9_TOOLS=false
AUTH_EXECUTION=false
SELF_HEAL=false
WAL_COMMITTED=false
EVOLUTION_CONSUMED=false

Nine-tool server and gateway copies remain in the hold directory hold-9tool-20261006.
Eight-tool rollback bytes remain in hold-8tool-rollback-20261006.
