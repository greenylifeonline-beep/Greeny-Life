#!/usr/bin/env python3
"""Fail-closed checks for the GL-004 live-process binder. Not a GL-004 named child."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gl004_lib import (  # noqa: E402
    EXIT_SPAWN_REFUSED,
    REQUIRED_CHILDREN,
    ROOT,
    BindError,
    bind_live,
    classify_http,
    epistemic_state,
    parent_exit,
    refuse_spawn,
)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok:", msg)


def main() -> int:
    rec = bind_live()
    check(rec["pid"] > 1, "pid bound")
    check(rec["ppid"] > 1, "ppid bound")
    check(Path(rec["cwd"]).resolve() == ROOT.resolve(), "cwd is repo")
    check(int(rec["listen_port"]) > 0, "listen port")
    check(rec["http_root_ok"] is True, "HTTP root identity")
    check(rec["http"][0]["status"] == 200, "GET / is 200")
    check(rec["spawned"] is False, "did not spawn")
    check(rec["killed"] is False, "did not kill")
    check("next-server" in rec["cmdline"] or "next-server" in rec["comm"], "next-server identity")
    check(rec["head"] == subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "HEAD matches git")
    check(Path(rec["log"]["path"]).exists() if rec["log"].get("path") else True, "runtime log path exists")

    still = Path(f"/proc/{rec['pid']}").exists()
    check(still, "live pid still exists after bind")

    try:
        refuse_spawn()
        raise SystemExit("FAIL: spawn was not refused")
    except BindError as err:
        check(err.code == EXIT_SPAWN_REFUSED, "spawn refused")

    spawn = subprocess.run(
        [sys.executable, str(ROOT / "scripts/ai-os/gl004-runtime-bind.py"), "--spawn"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    check(spawn.returncode == EXIT_SPAWN_REFUSED, "--spawn CLI refused")

    missing = parent_exit([])
    check(missing != 0, "missing children fail parent")
    zeros = parent_exit([{"name": n, "exit": 0} for n in REQUIRED_CHILDREN])
    check(zeros == 0, "all-zero children yield parent 0")
    mixed = parent_exit(
        [{"name": n, "exit": 0} for n in REQUIRED_CHILDREN[:-1]] + [{"name": REQUIRED_CHILDREN[-1], "exit": 2}]
    )
    check(mixed == 2, "nonzero child becomes parent")
    check(classify_http(200, is_root=True, next_identity=True) == "FRAMEWORK_LIVENESS", "200 root class")
    check(classify_http(401) == "ROUTE_EXECUTION+AUTH_GATE_PRESENT", "401 class")
    check(classify_http(404) == "SERVER_LIVE/ROUTE_ABSENT", "404 class")
    check(classify_http(500) == "ROUTE_EXECUTED/APPLICATION_FAILURE", "500 class")
    check(epistemic_state(0) == "PASS", "exit0 PASS")
    check(epistemic_state(1) == "FAILED", "exit1 FAILED")
    check(epistemic_state(2, not_run=True) == "NOT_RUN", "NOT_RUN distinct from FAILED")
    check(epistemic_state(2, invalid=True) == "INVALID_OBSERVATION", "isolation invalid")

    from gl004_lib import fingerprint_dist, gl005_verdict, product_scoped_dirty

    fp = fingerprint_dist()
    check(isinstance(fp.get("dot_next_top"), list), "fingerprint_dist restored")
    scoped = product_scoped_dirty()
    check(all("LAST-HEARTBEAT" not in n for n in scoped["files"]), "heartbeat not product-dirty")
    check(all("experience/pending" not in n for n in scoped["files"]), "WAL pending not product-dirty")
    scripts_diff = subprocess.check_output(
        ["git", "diff", "--name-only", "--", "scripts/ai-os"],
        cwd=ROOT,
        text=True,
    ).strip()
    if scripts_diff:
        check(scoped["dirty"] is True, "uncommitted scripts/ai-os blocks BUILD")
        check(any(n.startswith("scripts/ai-os/") for n in scoped["files"]), "dirty scripts listed")
    all_ready = gl005_verdict(aios_ok=True, control_ok=True, orch_ok=True, api_ok=True)
    check(all_ready["gl005_live_path_proven"] is True, "live path can open")
    check(all_ready["gl005_proven"] is False, "GL005_PROVEN stays false when live path is true")

    print(json.dumps({"pid": rec["pid"], "port": rec["listen_port"], "mode": rec["mode"], "head": rec["head"][:12]}))
    print("gl004_runtime_bind_check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
