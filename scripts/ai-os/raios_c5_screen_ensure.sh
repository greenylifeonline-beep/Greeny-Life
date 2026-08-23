#!/usr/bin/env bash
# Keep C5 screen + MCP up on the local control-plane host. Not a Cursor session.
# Not raios-service-loop.sh (that is train). No extra MCP tools. No second C5.
#
# Optional reboot keeper (on the local server, not on a Cursor VM):
#   crontab -e
#   @reboot bash /path/to/repo/scripts/ai-os/raios_c5_screen_ensure.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SCREEN_PORT=8765
MCP_PORT=8787
BIND_HOST="${RAIOS_C5_SCREEN_HOST:-127.0.0.1}"
MCP_HOST="${RAIOS_MCP_HOST:-$BIND_HOST}"

if [ -n "${RAIOS_PYTHON:-}" ]; then
  PY="$RAIOS_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "PYTHON_MISSING"
  exit 2
fi

port_up() {
  "$PY" -c 'import socket,sys
s=socket.socket(); s.settimeout(0.4)
code=1
try:
    s.connect(("127.0.0.1", int(sys.argv[1]))); code=0
except OSError:
    code=1
finally:
    s.close()
raise SystemExit(code)' "$1"
}

if [ -d /opt/cursor ] || [ "$(hostname)" = "cursor" ]; then
  SCREEN_HOME=SESSION_TEMP
  DURABLE=false
else
  SCREEN_HOME=CONTROL_PLANE
  DURABLE=true
fi

if port_up "$SCREEN_PORT"; then
  echo "SCREEN_UP :$SCREEN_PORT"
else
  nohup "$PY" scripts/ai-os/raios_c5_screen.py --serve >>/tmp/raios-c5-screen.log 2>&1 &
  echo "SCREEN_STARTED $!"
fi

if port_up "$MCP_PORT"; then
  echo "MCP_UP :$MCP_PORT"
else
  nohup "$PY" scripts/ai-os/raios_mcp/server.py --http --host "$MCP_HOST" --port "$MCP_PORT" >>/tmp/raios-mcp.log 2>&1 &
  echo "MCP_STARTED $!"
fi

echo "SCREEN_HOME=$SCREEN_HOME"
echo "DURABLE=$DURABLE"
echo "OPEN=http://127.0.0.1:8765"
echo "MCP=http://127.0.0.1:8787/mcp"
echo "CURSOR_SESSION_NE_C5=true"
echo "NEW_MCP_TOOLS=false"
echo "DUPLICATE_C5=false"
echo "GL005_PROVEN=false"
