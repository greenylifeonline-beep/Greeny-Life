"""Resource Fabric CLI. JSON is authoritative. Placement is executable; dispatch is dry-run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .census import collect_world, run_safe_probes, snapshots, status_view, write_package
from .factory import evaluate_workload, explain, place, plan_dispatch, reservoir_view, resource_request
from .c5_awareness import reason as c5_reason, resource_context
from .live import build_wave02_views, write_wave02_package
from .placement import decide, placement_request, recompose_v2
from .secrets import assert_no_secrets, mask_record

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / ".ai-os" / "reports" / "resource-fabric" / "RAIOS-RESOURCE-FABRIC-FOUNDATION-WAVE-01"


def _emit(payload: Any, *, human: bool, json_mode: bool) -> int:
    payload = mask_record(payload)
    assert_no_secrets(payload)
    if json_mode or not human:
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        return 0
    if isinstance(payload, dict):
        for key, val in payload.items():
            if isinstance(val, (dict, list)):
                sys.stdout.write(f"{key}: {json.dumps(val, ensure_ascii=False)[:240]}\n")
            else:
                sys.stdout.write(f"{key}: {val}\n")
        return 0
    sys.stdout.write(str(payload) + "\n")
    return 0


def _load_request(args: argparse.Namespace) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if args.request:
        extra.update(json.loads(Path(args.request).read_text(encoding="utf-8-sig")))
    if args.workload:
        extra["workload_class"] = args.workload
    if args.authority:
        extra["authority_context"] = args.authority
    if args.paid:
        extra["paid_allowed"] = True
    return resource_request(**extra)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="RAIOS-RESOURCE")
    parser.add_argument("command", nargs="?", default="status")
    parser.add_argument("-Human", dest="human", action="store_true")
    parser.add_argument("-Json", dest="json_mode", action="store_true", default=True)
    parser.add_argument("-Request", dest="request", default=None)
    parser.add_argument("-Workload", dest="workload", default=None)
    parser.add_argument("-Authority", dest="authority", default=None)
    parser.add_argument("-Paid", dest="paid", action="store_true")
    parser.add_argument("-DryRun", dest="dry_run", action="store_true", default=True)
    parser.add_argument("--no-probe", action="store_true")
    args = parser.parse_args(argv)
    if args.human:
        args.json_mode = False
    world = collect_world()
    if not args.no_probe:
        run_safe_probes(world)
    cmd = args.command.lower()
    snaps = snapshots(world)
    views = build_wave02_views(world) if world.get("live_state") else {}
    table = {
        "status": status_view(world),
        "providers": world["providers"],
        "accounts": world["accounts"],
        "resources": {
            "compute": world["compute"],
            "accelerators": world["accelerators"],
            "storage": world["storage"],
        },
        "compute": world["compute"],
        "gpu": world["accelerators"],
        "storage": world["storage"],
        "services": world["services"],
        "quota": world["quotas"],
        "credits": world["credits"],
        "pricing": world["pricing"],
        "recomposition": recompose_v2(world),
        "cost": snaps["COST-SAMPLES.json"],
        "models": views.get("MODEL-HOSTING-FIT.json")
        or {"warehouse": "RAIOS_MODEL_WAREHOUSE", "MODEL_WEIGHTS_LOCAL": False, "ninerouter": (world.get("gateways") or [None])[0]},
        "health": world.get("probes") or [],
        "census": snaps["RESOURCE-CENSUS.json"],
        "reservoir": reservoir_view(world),
        "failover": reservoir_view(world).get("gpu_pool"),
        "c5-awareness": resource_context(world),
        "c5-reason": None,
    }
    if cmd in {"placement", "evaluate", "plan", "explain"}:
        req = _load_request(args)
        decision = place(req, world)
        if cmd == "placement" and args.request and "workload_class" not in json.loads(Path(args.request).read_text(encoding="utf-8-sig")) and not args.workload:
            # Preserve Wave-01 decide() when a raw PlacementRequest file is supplied without workload_class.
            raw = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
            if raw.get("kind") == "PlacementRequest" or "requires_gpu" in raw:
                table["placement"] = decide(placement_request(**{k: v for k, v in raw.items() if k != "kind"}), world)
                payload = table["placement"]
                return _emit(payload, human=args.human, json_mode=args.json_mode)
        packed = evaluate_workload(req["workload_class"], world, **{k: req[k] for k in req if k not in {"schema", "kind", "placement_fit", "workload_class"}})
        table["placement"] = packed["decision"]
        table["evaluate"] = packed
        table["plan"] = packed["plan"] if args.dry_run else packed["plan"]
        table["explain"] = packed["explain"]
        table["plan"]["DRY_RUN"] = True
        table["plan"]["PROVIDER_MUTATION"] = False
        table["plan"]["GPU_SESSION_STARTED"] = False
        table["plan"]["PAID_RESOURCE_CREATED"] = False
        if cmd == "explain":
            return _emit(explain(decision), human=args.human, json_mode=args.json_mode)
        if cmd == "plan":
            return _emit(plan_dispatch(decision, req, dry_run=True), human=args.human, json_mode=args.json_mode)
        if cmd == "evaluate":
            return _emit(packed, human=args.human, json_mode=args.json_mode)
        return _emit(decision, human=args.human, json_mode=args.json_mode)
    if cmd in {"c5-reason", "c5-awareness"}:
        if cmd == "c5-awareness":
            return _emit(resource_context(world), human=args.human, json_mode=args.json_mode)
        req = _load_request(args)
        rec = c5_reason(req.get("workload_class") or "CONTROL", world, **{k: req[k] for k in req if k not in {"schema", "kind", "placement_fit", "workload_class"}})
        rec.pop("decision", None)
        rec.pop("plan", None)
        rec.pop("explain", None)
        return _emit(rec, human=args.human, json_mode=args.json_mode)
    if cmd == "write-package":
        write_package(PACKAGE, snaps)
        return _emit({"PACKAGE": str(PACKAGE), "FILES": sorted(snaps)}, human=args.human, json_mode=args.json_mode)
    if cmd in {"write-wave02", "write-package-wave02"}:
        out = write_wave02_package(world)
        return _emit(out, human=args.human, json_mode=args.json_mode)
    payload = table.get(cmd)
    if payload is None:
        return _emit({"error": "UNKNOWN_COMMAND", "command": cmd}, human=args.human, json_mode=True)
    return _emit(payload, human=args.human, json_mode=args.json_mode)


if __name__ == "__main__":
    raise SystemExit(main())
