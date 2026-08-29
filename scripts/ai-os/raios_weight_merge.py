"""Canonical CLI for governed V9 weight-merge plans."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "RAIOS" / "V9"))

from evolution.model_lab.merge_executor import execute
from evolution.model_lab.merge_strategy import declarations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capabilities", "plan"))
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--allow-execute", action="store_true")
    args = parser.parse_args()

    if args.action == "capabilities":
        print(json.dumps(declarations(), indent=2, sort_keys=True))
        return 0
    if args.plan is None:
        parser.error("--plan is required for plan action")
    payload = json.loads(args.plan.read_text(encoding="utf-8"))
    if args.allow_execute:
        payload["allow_execute"] = True
        payload["dry_run"] = False
    else:
        payload["dry_run"] = True
    result = execute(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
