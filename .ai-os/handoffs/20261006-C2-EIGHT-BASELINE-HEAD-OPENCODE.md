# C2 handoff — eight-tool head and OpenCode baseline

TASK_ID=RAIOS-NATIVE-MCP-SELFHEAL-20261002-02
DONE=false
NINE_TOOL_CUTOVER=not started

## Cause

The rollback listener was started by the SYSTEM cutover helper.
`/health` reads the Git file, so local health still showed head 9b5f1fb27e65f86daa90f821d32aee21e72d0b1b and head_source git-file.
`get_head` called `git rev-parse`. That PATH did not include Git, so the tool returned head="".
OpenCode used `shutil.which("opencode")`. That PATH did not include the npm shim, so the projection fell back to MODEL-REGISTRY status REGISTERED_EXISTING_OPENCODE with present=false and binary=null.
A version probe whose working directory is the repository hangs, because the OpenCode executable scans that tree. The observed version was therefore empty until the probe used the executable's own directory.

## Local proof after the owned eight-tool restart

PORT_8788_LISTENER_COUNT=1
listener pid=2704
launcher pid=6284
LOCAL_HEAD=9b5f1fb27e65f86daa90f821d32aee21e72d0b1b
HEAD_SOURCE=git-file
LOCAL_TOOL_COUNT=8
DUPLICATE_MCP=false
OPENCODE_REGISTRY_PRESENT=true
OPENCODE_BINARY_PRESENT=true
OPENCODE_BINARY=C:\Users\Ghanam\AppData\Roaming\npm\opencode.CMD
OPENCODE_DECLARED_VERSION=1.18.21
OPENCODE_OBSERVED_VERSION=1.18.21
OPENCODE_STATUS=BINARY_PRESENT_NOT_EXECUTED

The head value is read from the Git files. The binary is accepted only when that file exists. The version is the executable's `--version` output.

## Not claimed

EXTERNAL_HEAD and EXTERNAL_TOOL_COUNT require a fresh C1 read of get_head.
No nine-tool cutover was submitted.
AUTH_EXECUTION, SELF_HEAL, WAL, and evolution remain open.
