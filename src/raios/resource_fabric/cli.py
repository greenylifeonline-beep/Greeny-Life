"""Read-only Resource Fabric CLI. JSON is authoritative."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .census import collect_world, run_safe_probes, snapshots, status_view, write_package
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="RAIOS-RESOURCE")
    parser.add_argument("command", nargs="?", default="status")
    parser.add_argument("-Human", dest="human", action="store_true")
    parser.add_argument("-Json", dest="json_mode", action="store_true", default=True)
    parser.add_argument("-Request", dest="request", default=None)
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
    }
    if cmd == "placement":
        req = placement_request()
        if args.request:
            req.update(json.loads(Path(args.request).read_text(encoding="utf-8-sig")))
        table["placement"] = decide(req, world)
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
