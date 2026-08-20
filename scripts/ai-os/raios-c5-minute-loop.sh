#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
while true; do
  python3 scripts/ai-os/raios_c5_minute.py || true
  sleep 60
done
