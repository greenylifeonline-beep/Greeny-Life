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

    print(json.dumps({"pid": rec["pid"], "port": rec["listen_port"], "mode": rec["mode"], "head": rec["head"][:12]}))
    print("gl004_runtime_bind_check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
