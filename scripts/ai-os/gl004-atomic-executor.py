#!/usr/bin/env python3
"""Fail-closed Wave2 isolated proof. Does not spawn or kill a Next server.

GL-004 required children: TYPECHECK, BUILD, TEST_CANONICAL, TEST_TASK_ORCHESTRATION, RUNTIME_TRACE.
GL-005 required children: AIOS_STATUS, GL005_CONTROL_PLANE, TEST_TASK_ORCHESTRATION, GL005_ORCHESTRATION_DEMO.

Verdicts are independent. Combined PARENT_EXIT is the worst of both gates.
Epistemic states are recorded so NOT_RUN is not collapsed into FAILED.
NEXT_CONFIG_FILE is not an isolation contract. Isolated distDir injection is.
Proof receipts live in .ai-os/receipts, not a new _raios-* forest.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gl004_lib import (  # noqa: E402
    GL005_CHILDREN,
    ISOLATED_DIST,
    PRELOAD,
    REQUIRED_CHILDREN,
    ROOT,
    BindError,
    bind_live,
    classify_http,
    epistemic_state,
    fingerprint_dist,
    git,
    gl004_proven,
    http_probe,
    parent_exit,
    utc,
    write_json,
)

RECEIPT = ROOT / ".ai-os" / "receipts" / "GL004-ATOMIC.json"
BIND_RECEIPT = ROOT / ".ai-os" / "receipts" / "GL004-RUNTIME-BIND.json"
API_BODY = ROOT / ".ai-os" / "receipts" / "api-tasks-body.txt"


def annotate(child: dict, **flags) -> dict:
    child["epistemic"] = epistemic_state(child.get("exit"), **flags)
    child["gate_open"] = child.get("exit") == 0 and child["epistemic"] == "PASS"
    return child


def run_child(name: str, argv: list[str], env: dict[str, str] | None = None, cwd: Path = ROOT, timeout: int = 600) -> dict:
    t0 = time.time()
    merged = os.environ.copy()
    if env:
        merged.update(env)
    try:
        proc = subprocess.run(argv, cwd=cwd, env=merged, text=True, capture_output=True, timeout=timeout)
        return annotate(
            {
                "name": name,
                "argv": argv,
                "exit": int(proc.returncode),
                "seconds": round(time.time() - t0, 3),
                "stdout_tail": (proc.stdout or "")[-4000:],
                "stderr_tail": (proc.stderr or "")[-4000:],
            }
        )
    except subprocess.TimeoutExpired as err:
        return annotate(
            {
                "name": name,
                "argv": argv,
                "exit": 124,
                "seconds": round(time.time() - t0, 3),
                "stdout_tail": (str(err.stdout or ""))[-4000:],
                "stderr_tail": "TIMEOUT",
            }
        )
    except FileNotFoundError:
        return annotate({"name": name, "argv": argv, "exit": 127, "seconds": round(time.time() - t0, 3)}, unavailable=True)


def child_runtime_trace() -> dict:
    t0 = time.time()
    try:
        rec = bind_live()
        rec["ok"] = True
        digest = write_json(BIND_RECEIPT, rec)
        Path(str(BIND_RECEIPT) + ".sha256").write_text(digest + "\n", encoding="utf-8")
        return annotate(
            {
                "name": "RUNTIME_TRACE",
                "argv": ["python3", "scripts/ai-os/gl004-runtime-bind.py"],
                "exit": 0,
                "seconds": round(time.time() - t0, 3),
                "pid": rec["pid"],
                "ppid": rec["ppid"],
                "port": rec["listen_port"],
                "mode": rec["mode"],
                "start": rec.get("start"),
                "http_root": rec["http"][0].get("status") if rec.get("http") else None,
                "http_observations": [
                    {"url": p.get("url"), "status": p.get("status"), "observation": p.get("observation")}
                    for p in rec.get("http") or []
                ],
                "classification": "FRAMEWORK_LIVENESS" if rec["mode"] == "dev" else "PRODUCTION_RUNTIME_EQUIVALENCE",
                "proven_as": "BINDABLE/PROVEN_AS_DEV_LIVENESS" if rec["mode"] == "dev" else "BINDABLE/PROVEN_AS_START",
                "log": rec.get("log", {}).get("path"),
                "receipt": str(BIND_RECEIPT),
                "receipt_sha256": digest,
                "spawned": False,
            }
        )
    except BindError as err:
        write_json(BIND_RECEIPT, {"ok": False, "exit": err.code, "reason": err.reason, **err.extra})
        unavailable = err.code in (2, 8)
        invalid = err.code in (3, 4, 6)
        return annotate(
            {
                "name": "RUNTIME_TRACE",
                "argv": ["python3", "scripts/ai-os/gl004-runtime-bind.py"],
                "exit": int(err.code),
                "seconds": round(time.time() - t0, 3),
                "reason": err.reason,
                "spawned": False,
            },
            unavailable=unavailable,
            invalid=invalid,
        )


def child_build() -> dict:
    before = fingerprint_dist()
    if before["dot_next_has_production_build_id"]:
        return annotate(
            {
                "name": "BUILD",
                "exit": 2,
                "reason": "LIVE_DOT_NEXT_ALREADY_HAS_PRODUCTION_BUILD_ID",
                "fingerprint_before": before,
                "listened": False,
            },
            invalid=True,
        )
    env = {"GL004_ISOLATED_DIST": ISOLATED_DIST, "NODE_ENV": "production"}
    child = run_child("BUILD", ["node", str(PRELOAD.parent / "gl004-isolated-build.cjs")], env=env, timeout=900)
    after = fingerprint_dist()
    child["isolated_dist"] = ISOLATED_DIST
    child["listened"] = False
    child["law"] = "ISOLATED_BUILD_NE_SECOND_RUNTIME"
    child["rejected_isolation"] = "NEXT_CONFIG_FILE is not a Next.js contract on this version"
    child["fingerprint_before"] = before
    child["fingerprint_after"] = after
    isolation_failed = after["dot_next_has_production_build_id"] and not before["dot_next_has_production_build_id"]
    if isolation_failed:
        child["exit"] = 2
        child["reason"] = "ISOLATION_FAILED_WROTE_LIVE_DOT_NEXT"
        return annotate(child, invalid=True)
    if child["exit"] == 0 and not after["isolated_exists"]:
        child["exit"] = 2
        child["reason"] = "ISOLATED_DIST_MISSING_PRELOAD_FAILED"
        return annotate(child, invalid=True)
    if child["exit"] == 0:
        child["classification"] = "BUILD_VALIDITY"
    return annotate(child)


def child_aios() -> dict:
    r = subprocess.run(["python3", "scripts/ai-os/aios.py", "status"], cwd=ROOT, text=True, capture_output=True)
    return annotate(
        {
            "name": "AIOS_STATUS",
            "argv": ["python3", "scripts/ai-os/aios.py", "status"],
            "exit": int(r.returncode),
            "stdout_tail": (r.stdout or "")[-2000:],
        }
    )


def child_control_plane() -> dict:
    ok = all((ROOT / p).exists() for p in [".ai-os/state/TASKS.json", ".ai-os/state/LOCKS.json", ".ai-os/handoffs"])
    return annotate(
        {
            "name": "GL005_CONTROL_PLANE",
            "exit": 0 if ok else 97,
            "paths": {
                "TASKS": (ROOT / ".ai-os/state/TASKS.json").exists(),
                "LOCKS": (ROOT / ".ai-os/state/LOCKS.json").exists(),
                "handoffs": (ROOT / ".ai-os/handoffs").exists(),
            },
        },
        unavailable=not ok,
    )


def child_orchestration_demo(port: int | None) -> dict:
    """Capture real /api/tasks body. 2xx is CAPABILITY_READINESS. 500 is not PASS."""
    if port is None:
        return annotate({"name": "GL005_ORCHESTRATION_DEMO", "exit": 100, "reason": "NO_BOUND_PORT"}, unavailable=True)
    probe = http_probe(f"http://127.0.0.1:{port}/api/tasks")
    body = str(probe.get("body_prefix") or "")
    if probe.get("error") and not body:
        body = str(probe.get("error"))
    API_BODY.parent.mkdir(parents=True, exist_ok=True)
    # Re-fetch full body for the receipt (prefix may be truncated).
    full = body
    try:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/tasks", headers={"User-Agent": "gl005-demo"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                full = resp.read().decode("utf-8", "replace")
                probe["status"] = int(resp.status)
        except urllib.error.HTTPError as err:
            full = err.read().decode("utf-8", "replace")
            probe["status"] = int(err.code)
    except Exception as err:
        full = full or str(err)
    API_BODY.write_text(full, encoding="utf-8")
    digest = hashlib.sha256(full.encode("utf-8")).hexdigest()
    status = probe.get("status")
    observation = classify_http(status)
    details = None
    try:
        parsed = json.loads(full)
        details = parsed.get("details") or parsed.get("error")
    except Exception:
        parsed = None
    ok = isinstance(status, int) and 200 <= status < 300
    child = {
        "name": "GL005_ORCHESTRATION_DEMO",
        "exit": 0 if ok else 99 if status else 99,
        "status": status,
        "observation": observation,
        "body_path": str(API_BODY),
        "body_sha256": digest,
        "body": full[:4000],
        "details": details,
        "discriminating_evidence": details,
        "law": "HTTP_200_ON_ROOT_NE_APP_HEALTH; LIVENESS_NE_READINESS_NE_CORRECTNESS",
    }
    if ok:
        return annotate(child)
    return annotate(child)


def live_pid_alive(pid: int | None) -> bool:
    return bool(pid) and Path(f"/proc/{int(pid)}").exists()


def main() -> int:
    safety = f"safety/pre-gl004-bind-{git('rev-parse', '--short', 'HEAD')}"
    if not git("tag", "--list", safety):
        subprocess.run(["git", "tag", safety], cwd=ROOT, check=False)

    from gl004_lib import discover_next_pids

    before_pids = discover_next_pids()
    fp_before = fingerprint_dist()

    runtime = child_runtime_trace()
    typecheck = run_child("TYPECHECK", ["npm", "run", "type-check"], timeout=300)
    canon = run_child("TEST_CANONICAL", ["npx", "--no-install", "tsx", "tests/canonical_intelligence_check.ts"], timeout=120)
    orch = run_child("TEST_TASK_ORCHESTRATION", ["npx", "--no-install", "tsx", "tests/task_orchestration_check.ts"], timeout=120)
    build = child_build()
    aios = child_aios()
    control = child_control_plane()
    demo = child_orchestration_demo(runtime.get("port"))

    after_pids = discover_next_pids()
    fp_after = fingerprint_dist()
    pid = runtime.get("pid")
    still = live_pid_alive(pid)

    gl004_children = [typecheck, build, canon, orch, runtime]
    gl005_children = [aios, control, orch, demo]
    all_children = [runtime, typecheck, canon, orch, build, aios, control, demo]

    gl004_parent = parent_exit(gl004_children, REQUIRED_CHILDREN)
    gl005_parent = parent_exit(gl005_children, GL005_CHILDREN)
    combined = parent_exit(all_children, REQUIRED_CHILDREN + ("AIOS_STATUS", "GL005_CONTROL_PLANE", "GL005_ORCHESTRATION_DEMO"))
    proven4 = gl004_proven(gl004_children, gl004_parent)
    proven5 = gl005_parent == 0

    payload = {
        "schema": "raios.wave2.isolated-proof.v1",
        "knowledge_state": "DISCOVERED",
        "HEAD": git("rev-parse", "HEAD"),
        "BRANCH": git("branch", "--show-current"),
        "SAFETY_TAG": safety,
        "bound_at": utc(),
        "children": all_children,
        "GL004_PARENT_EXIT": gl004_parent,
        "GL005_PARENT_EXIT": gl005_parent,
        "PARENT_EXIT": combined,
        "RECEIPT": str(RECEIPT),
        "GL004_PROVEN": proven4,
        "GL004_PRODUCTION_RUNTIME_PROVEN": runtime.get("mode") == "start" and proven4,
        "GL005_PROVEN": proven5,
        "RUNTIME_TRACE": runtime.get("proven_as"),
        "spawned_second_runtime": False,
        "killed_live_process": False,
        "live_pid_still_alive": still,
        "next_pids_before": before_pids,
        "next_pids_after": after_pids,
        "second_runtime_detected": sorted(set(after_pids) - set(before_pids)) != [],
        "fingerprint_before": fp_before,
        "fingerprint_after": fp_after,
        "rejected": {
            "NEXT_CONFIG_FILE": "not present in next@16.2.10; writing next.config.* would HMR the live server",
            "_raios-wave2-proof-isolated": "proof forest rejected; receipts stay in .ai-os/receipts",
        },
        "c1_contract_attack": {
            "historical_gl004": "type-check + build + tests + runtime execution truth",
            "does_not_say": "next start / production-runtime equivalence",
            "ruling": "REJECT silent strengthening. Production equivalence is a new named child, not RUNTIME_TRACE.",
            "dev_bind_may_satisfy_runtime_trace": True,
            "isolated_build_may_satisfy_build": True,
            "api_tasks_500": "ROUTE_EXECUTED/APPLICATION_FAILURE — orchestration path present, capability not ready",
        },
        "laws": [
            "LIVE_PROCESS_CAN_SATISFY_RUNTIME_PROOF_IF_IDENTITY_AND_HTTP_EVIDENCE_ARE_BOUND",
            "BIND_EXISTING_NE_SPAWN",
            "DEV_LISTEN_NE_PRODUCTION_BUILD",
            "HTTP_200_ON_ROOT_NE_APP_HEALTH",
            "ISOLATED_BUILD_NE_SECOND_RUNTIME",
            "NEXT_CONFIG_FILE_NE_ISOLATION_CONTRACT",
            "LIVENESS_NE_READINESS_NE_CORRECTNESS_NE_PRODUCTION_EQUIVALENCE",
            "GATE_CLOSED_NE_EPISTEMIC_FAILED",
            "PARENT_SUCCESS_REQUIRES_ALL_REQUIRED_CHILDREN_SUCCESS",
            "PROOF_FOREST_NE_RECEIPT",
        ],
    }
    digest = write_json(RECEIPT, payload)
    (ROOT / ".ai-os" / "receipts" / "GL004-ATOMIC.sha256").write_text(digest + "\n", encoding="utf-8")

    block = {
        "HEAD": payload["HEAD"],
        "SAFETY_TAG": safety,
        "children": [{"name": c["name"], "exit": c["exit"], "epistemic": c.get("epistemic")} for c in all_children],
        "GL004_PARENT_EXIT": gl004_parent,
        "GL005_PARENT_EXIT": gl005_parent,
        "PARENT_EXIT": combined,
        "RECEIPT": str(RECEIPT),
        "RECEIPT_SHA256": digest,
        "GL004_PROVEN": proven4,
        "GL005_PROVEN": proven5,
        "live_pid_still_alive": still,
    }
    print(json.dumps(block, indent=2, ensure_ascii=False))
    print(f"RECEIPT_SHA256={digest}")
    return combined


if __name__ == "__main__":
    raise SystemExit(main())
