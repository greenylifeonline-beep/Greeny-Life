#!/usr/bin/env bash
# C2 helper: start the existing C5 HTTP screen from a v9 git worktree.
# Does not copy trees into the C2 checkout. Does not write WAL. Does not train C5.
set -euo pipefail

WORKTREE="${C5_V9_WORKTREE:-/home/ubuntu/raios-c5-v9}"
SESSION_NAME="${C5_TMUX_SESSION:-c5-http-screen}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REF="${C5_V9_REF:-origin/v9-neurolingua-semantic-kernel}"
TMUX_CONF="${TMUX_CONF:-/exec-daemon/tmux.portal.conf}"
SCREEN_PY="scripts/ai-os/raios_c5_screen.py"

if [[ -f "$TMUX_CONF" ]]; then
  TMUX=(tmux -f "$TMUX_CONF")
else
  TMUX=(tmux)
fi

if [[ ! -f "$WORKTREE/$SCREEN_PY" ]]; then
  mkdir -p "$(dirname "$WORKTREE")"
  git -C "$REPO_ROOT" worktree add --detach "$WORKTREE" "$REF"
fi

if python3 -c 'import socket; raise SystemExit(0 if socket.socket().connect_ex(("127.0.0.1", 8765))==0 else 1)'; then
  echo "C5_HTTP_ALREADY_LISTENING http://127.0.0.1:8765"
  curl -sS http://127.0.0.1:8765/api/status
  echo
  exit 0
fi

"${TMUX[@]}" has-session -t "=$SESSION_NAME" 2>/dev/null || \
  "${TMUX[@]}" new-session -d -s "$SESSION_NAME" -c "$WORKTREE" -- "${SHELL:-bash}" -l
"${TMUX[@]}" send-keys -t "$SESSION_NAME:0.0" "python3 $SCREEN_PY --serve" C-m

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if python3 -c 'import socket; raise SystemExit(0 if socket.socket().connect_ex(("127.0.0.1", 8765))==0 else 1)'; then
    echo "C5_HTTP_STARTED http://127.0.0.1:8765"
    curl -sS http://127.0.0.1:8765/api/status
    echo
    echo "FORWARD_PORT_8765 SAME_LOOPBACK_OR_PORT_FORWARD"
    echo "LAPTOP_LOCALHOST_IS_A_DIFFERENT_LOOP unless Repair also runs the screen."
    exit 0
  fi
  sleep 0.3
done

echo "C5_HTTP_START_FAILED port 8765 still closed"
exit 2
