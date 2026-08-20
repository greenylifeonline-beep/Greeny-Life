#!/usr/bin/env python3
"""Fail-closed GL-004 atomic executor. Does not spawn or kill a Next server.

Required children: TYPECHECK, BUILD, TEST_CANONICAL, TEST_TASK_ORCHESTRATION, RUNTIME_TRACE.
Parent exit is 0 only if every required child exit is 0.
GL004_PROVEN is true only then. GL005_PROVEN is never granted here.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gl004_lib import (  # noqa: E402
    ISOLATED_DIST,
    PRELOAD,
    REQUIRED_CHILDREN,
    ROOT,
    BindError,
    bind_live,
    git,
    gl004_proven,
    parent_exit,
    sha256_file,
    utc,
    write_json,
)

RECEIPT = ROOT / ".ai-os" / "receipts" / "GL004-ATOMIC.json"
BIND_RECEIPT = ROOT / ".ai-os" / "receipts" / "GL004-RUNTIME-BIND.json"


def run_child(name: str, argv: list[str], env: dict[str, str] | None = None, cwd: Path = ROOT, timeout: int = 600) -> dict:
    t0 = time.time()
    merged = os.environ.copy()
    if env:
        merged.update(env)
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=merged,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "name": name,
            "argv": argv,
            "exit": int(proc.returncode),
            "seconds": round(time.time() - t0, 3),
            "stdout_tail": (proc.stdout or "")[-4000:],
            "stderr_tail": (proc.stderr or "")[-4000:],
        }
    except subprocess.TimeoutExpired as err:
        return {
            "name": name,
            "argv": argv,
            "exit": 124,
            "seconds": round(time.time() - t0, 3),
            "stdout_tail": ((err.stdout or b"") if isinstance(err.stdout, (bytes, bytearray)) else (err.stdout or ""))[-4000:]
            if err.stdout
            else "",
            "stderr_tail": "TIMEOUT",
        }


def child_runtime_trace() -> dict:
    t0 = time.time()
    try:
        rec = bind_live()
        rec["ok"] = True
        digest = write_json(BIND_RECEIPT, rec)
        Path(str(BIND_RECEIPT) + ".sha256").write_text(digest + "\n", encoding="utf-8")
        return {
            "name": "RUNTIME_TRACE",
            "argv": ["python3", "scripts/ai-os/gl004-runtime-bind.py"],
            "exit": 0,
            "seconds": round(time.time() - t0, 3),
            "pid": rec["pid"],
            "ppid": rec["ppid"],
            "port": rec["listen_port"],
            "mode": rec["mode"],
            "http_root": rec["http"][0].get("status") if rec.get("http") else None,
            "log": rec.get("log", {}).get("path"),
            "receipt": str(BIND_RECEIPT),
            "receipt_sha256": digest,
            "spawned": False,
        }
    except BindError as err:
        payload = {"ok": False, "exit": err.code, "reason": err.reason, **err.extra}
        write_json(BIND_RECEIPT, payload)
        return {
            "name": "RUNTIME_TRACE",
            "argv": ["python3", "scripts/ai-os/gl004-runtime-bind.py"],
            "exit": int(err.code),
            "seconds": round(time.time() - t0, 3),
            "reason": err.reason,
            "spawned": False,
        }


def child_build() -> dict:
    """Compile into an isolated distDir. Does not listen. Does not touch live `.next`."""
    env = {
        "GL004_ISOLATED_DIST": ISOLATED_DIST,
        "NODE_ENV": "production",
    }
    child = run_child(
        "BUILD",
        ["node", str(PRELOAD.parent / "gl004-isolated-build.cjs")],
        env=env,
        timeout=900,
    )
    child["isolated_dist"] = ISOLATED_DIST
    child["listened"] = False
    child["law"] = "ISOLATED_BUILD_NE_SECOND_RUNTIME"
    dist = ROOT / ISOLATED_DIST
    child["dist_exists"] = dist.exists()
    if child["exit"] == 0 and not dist.exists():
        child["exit"] = 2
        child["reason"] = "ISOLATED_DIST_MISSING_PRELOAD_FAILED"
    return child


def aios_status_blob() -> str:
    r = subprocess.run(["python3", "scripts/ai-os/aios.py", "status"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "") + (r.stderr or "")


def main() -> int:
    safety = f"safety/pre-gl004-bind-{git('rev-parse', '--short', 'HEAD')}"
    existing = git("tag", "--list", safety)
    if not existing:
        subprocess.run(["git", "tag", safety], cwd=ROOT, check=False)

    before_pids = []
    try:
        from gl004_lib import discover_next_pids

        before_pids = discover_next_pids()
    except Exception:
        pass

    children = [
        child_runtime_trace(),
        run_child("TYPECHECK", ["npm", "run", "type-check"], timeout=300),
        child_build(),
        run_child("TEST_CANONICAL", ["npx", "--no-install", "tsx", "tests/canonical_intelligence_check.ts"], timeout=120),
        run_child("TEST_TASK_ORCHESTRATION", ["npx", "--no-install", "tsx", "tests/task_orchestration_check.ts"], timeout=120),
    ]

    after_pids = before_pids
    try:
        from gl004_lib import discover_next_pids

        after_pids = discover_next_pids()
    except Exception:
        pass

    parent = parent_exit(children)
    proven = gl004_proven(children, parent)
    runtime = next((c for c in children if c["name"] == "RUNTIME_TRACE"), {})
    payload = {
        "schema": "raios.gl004-atomic.v1",
        "knowledge_state": "DISCOVERED",
        "HEAD": git("rev-parse", "HEAD"),
        "BRANCH": git("branch", "--show-current"),
        "SAFETY_TAG": safety,
        "bound_at": utc(),
        "children": children,
        "PARENT_EXIT": parent,
        "RECEIPT": str(RECEIPT),
        "GL004_PROVEN": proven,
        "GL004_PRODUCTION_RUNTIME_PROVEN": runtime.get("mode") == "start" and proven,
        "GL005_PROVEN": False,
        "GL005_reason": "SUPPORTING_TEST_NE_ORCHESTRATION_DEMONSTRATION; GL-005 depends on GL-002/003/004",
        "spawned_second_runtime": False,
        "killed_live_process": False,
        "next_pids_before": before_pids,
        "next_pids_after": after_pids,
        "second_runtime_detected": sorted(set(after_pids) - set(before_pids)) != [],
        "aios_status": aios_status_blob().strip(),
        "laws": [
            "LIVE_PROCESS_CAN_SATISFY_RUNTIME_PROOF_IF_IDENTITY_AND_HTTP_EVIDENCE_ARE_BOUND",
            "BIND_EXISTING_NE_SPAWN",
            "DEV_LISTEN_NE_PRODUCTION_BUILD",
            "HTTP_200_ON_ROOT_NE_APP_HEALTH",
            "ISOLATED_BUILD_NE_SECOND_RUNTIME",
            "PARENT_SUCCESS_REQUIRES_ALL_REQUIRED_CHILDREN_SUCCESS",
        ],
    }
    digest = write_json(RECEIPT, payload)
    # Hash is of file bytes. Re-write including hash would invalidate it; sidecar + print.
    (ROOT / ".ai-os" / "receipts" / "GL004-ATOMIC.sha256").write_text(digest + "\n", encoding="utf-8")

    block = {
        "HEAD": payload["HEAD"],
        "SAFETY_TAG": safety,
        "children": [{"name": c["name"], "exit": c["exit"]} for c in children],
        "PARENT_EXIT": parent,
        "RECEIPT": str(RECEIPT),
        "RECEIPT_SHA256": digest,
        "GL004_PROVEN": proven,
        "GL005_PROVEN": False,
    }
    print(json.dumps(block, indent=2, ensure_ascii=False))
    print(f"RECEIPT_SHA256={digest}")
    missing = [n for n in REQUIRED_CHILDREN if n not in {c["name"] for c in children}]
    if missing:
        print("MISSING_REQUIRED:" + ",".join(missing), file=sys.stderr)
        return 2
    return parent


if __name__ == "__main__":
    raise SystemExit(main())
