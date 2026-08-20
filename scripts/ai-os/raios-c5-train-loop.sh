#!/usr/bin/env bash
# Fail-closed pulse. Errors are receipted. Slack (`|| true`) is forbidden.
set -euo pipefail
cd "$(dirname "$0")/../.."
while true; do
  if python3 scripts/ai-os/raios_c5_train.py --auto; then
    python3 scripts/ai-os/raios_c5_watchdog.py
  else
    python3 scripts/ai-os/raios_c5_watchdog.py --note TRAIN_FAIL
    echo "TRAIN_FAIL_CLOSED $(date -u +%Y-%m-%dT%H:%M:%SZ)" >&2
  fi
  sleep 1800
done
