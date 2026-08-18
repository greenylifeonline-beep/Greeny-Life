"""CLI for mastery, retirement, reality-audit, and live learning."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .identity import PACKAGE, canonical_json, repo_root_from
from .runtime import ParallelRuntime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="raios-parallel")
    parser.add_argument("--root", default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reality-audit")
    sub.add_parser("shared-state")
    p_g = sub.add_parser("graph")
    p_g.add_argument("--out", default=None)
    p_ev = sub.add_parser("mastery")
    p_ev.add_argument("action", choices=["evaluate", "status", "teacher-dependency", "capability-gap", "retention-status", "transfer-status"])
    p_ev.add_argument("capability")
    p_ev.add_argument("--metrics", default="{}")
    p_r = sub.add_parser("retirement")
    p_r.add_argument("action", choices=["evaluate", "status", "report"])
    p_r.add_argument("teacher_id")
    p_r.add_argument("capability", nargs="?")
    args = parser.parse_args(argv)
    root = Path(args.root) if args.root else repo_root_from() / PACKAGE / "runtime"
    rt = ParallelRuntime(root)
    try:
        if args.cmd == "reality-audit":
            result = rt.auditor.audit()
        elif args.cmd == "shared-state":
            result = rt.shared_state()
        elif args.cmd == "graph":
            out = Path(args.out) if args.out else root / "TEACHER-CAPABILITY-TRANSFER-GRAPH.json"
            result = rt.graph.write(out)
        elif args.cmd == "mastery":
            if args.action == "evaluate":
                metrics = json.loads(args.metrics)
                result = rt.mastery.record(args.capability, metrics) if metrics else rt.mastery.evaluate(args.capability)
            elif args.action == "status":
                result = rt.mastery.status(args.capability)
            elif args.action == "teacher-dependency":
                result = rt.mastery.teacher_dependency(args.capability)
            elif args.action == "capability-gap":
                result = rt.mastery.capability_gap(args.capability)
            elif args.action == "retention-status":
                result = rt.mastery.retention_status(args.capability)
            else:
                result = rt.mastery.transfer_status(args.capability)
        elif args.cmd == "retirement":
            if args.action == "evaluate":
                if not args.capability:
                    raise SystemExit("capability required")
                result = rt.retirement.evaluate(args.teacher_id, args.capability)
            elif args.action == "status":
                result = rt.retirement.status(args.teacher_id)
            else:
                result = rt.retirement.report(args.teacher_id)
        else:
            raise SystemExit(2)
        print(canonical_json(result))
        return 0
    finally:
        rt.close()


if __name__ == "__main__":
    raise SystemExit(main())
