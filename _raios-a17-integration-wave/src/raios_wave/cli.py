"""Callable CLI for mastery, retirement, normalization, and loop operations."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .identity import WAVE_PACKAGE, canonical_json, repo_root_from
from .runtime import WaveRuntime


def default_runtime_root() -> Path:
    return repo_root_from() / WAVE_PACKAGE / "runtime"


def build_runtime(root: str | None) -> WaveRuntime:
    return WaveRuntime(root or default_runtime_root())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="raios-wave")
    parser.add_argument("--root", default=None, help="Isolated wave runtime directory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_norm = sub.add_parser("normalize")
    p_norm.add_argument("artifact")

    p_diff = sub.add_parser("differential")
    p_diff.add_argument("student")
    p_diff.add_argument("teacher")

    p_m = sub.add_parser("mastery-evaluate")
    p_m.add_argument("capability")
    p_m.add_argument("--metrics", default="{}")

    sub.add_parser("competency-status").add_argument("capability")
    sub.add_parser("teacher-dependency").add_argument("capability")
    sub.add_parser("capability-gap").add_argument("capability")

    p_ret = sub.add_parser("retirement-evaluate")
    p_ret.add_argument("teacher_id")
    p_ret.add_argument("capability")

    p_loop = sub.add_parser("loop-run")
    p_loop.add_argument("task_json")

    sub.add_parser("reuse-status")
    sub.add_parser("identity")
    sub.add_parser("a17-4-status")

    args = parser.parse_args(argv)
    rt = build_runtime(args.root)
    try:
        if args.cmd == "normalize":
            artifact = args.artifact
            path = Path(artifact)
            payload = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" and path.is_file() else artifact
            result = rt.normalizer.normalize_artifact(payload if isinstance(payload, dict) else path)
        elif args.cmd == "differential":
            student = json.loads(Path(args.student).read_text(encoding="utf-8"))
            teacher = json.loads(Path(args.teacher).read_text(encoding="utf-8"))
            result = rt.differential.compare(student, teacher)
        elif args.cmd == "mastery-evaluate":
            metrics = json.loads(args.metrics)
            if metrics:
                result = rt.mastery.record_evaluation(args.capability, metrics)
            else:
                result = rt.mastery.evaluate(args.capability)
        elif args.cmd == "competency-status":
            result = rt.mastery.competency_status(args.capability)
        elif args.cmd == "teacher-dependency":
            result = rt.mastery.teacher_dependency(args.capability)
        elif args.cmd == "capability-gap":
            result = rt.mastery.capability_gap(args.capability)
        elif args.cmd == "retirement-evaluate":
            result = rt.retirement.evaluate(args.teacher_id, args.capability)
        elif args.cmd == "loop-run":
            task = json.loads(Path(args.task_json).read_text(encoding="utf-8"))
            result = rt.loop.run(task, authorize_tools=False)
        elif args.cmd == "reuse-status":
            result = rt.reuse_status()
        elif args.cmd == "identity":
            result = rt.store.identity()
        elif args.cmd == "a17-4-status":
            result = rt.a174.status()
        else:
            raise SystemExit(2)
        print(canonical_json(result))
        return 0
    finally:
        rt.close()


if __name__ == "__main__":
    sys.exit(main())
