#!/usr/bin/env bash
# Minute exam every 60s. Failure is recorded. `|| true` is slack and forbidden.
set -euo pipefail
cd "$(dirname "$0")/../.."
while true; do
  if ! python3 scripts/ai-os/raios_c5_minute.py; then
    python3 scripts/ai-os/raios_c5_watchdog.py --note MINUTE_FAIL
    echo "MINUTE_FAIL_CLOSED $(date -u +%Y-%m-%dT%H:%M:%SZ)" >&2
  fi
  sleep 60
done
