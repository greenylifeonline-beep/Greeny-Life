#!/usr/bin/env bash
# Service pulse uses the training mesh, not five-seat consult.
# Failure is recorded. `|| true` is slack and forbidden.
set -euo pipefail
cd "$(dirname "$0")/../.."
while true; do
  if python3 scripts/ai-os/raios_c5_train.py --auto; then
    python3 scripts/ai-os/raios_c5_watchdog.py
  else
    python3 scripts/ai-os/raios_c5_watchdog.py --note SERVICE_TRAIN_FAIL
    echo "SERVICE_TRAIN_FAIL_CLOSED $(date -u +%Y-%m-%dT%H:%M:%SZ)" >&2
  fi
  sleep 120
done
