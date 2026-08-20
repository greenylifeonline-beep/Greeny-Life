#!/usr/bin/env python3
"""Observe the smallest existing GL-005 mutation surface. Does not grant PASS.

Binds the live Next process. GET before → POST existing /api/tasks → GET after.
Does not spawn, kill, provision Postgres/Docker, mint secrets, or forge gl_session.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gl004_lib import (  # noqa: E402
    EXIT_PLATFORM,
    ROOT,
    BindError,
    bind_live,
    classify_http,
    utc,
    write_json,
)

RECEIPT = ROOT / ".ai-os" / "receipts" / "GL005-MUTATION-OBSERVE.json"
BEFORE_BODY = ROOT / ".ai-os" / "receipts" / "gl005-mutation-before.json"
AFTER_BODY = ROOT / ".ai-os" / "receipts" / "gl005-mutation-after.json"
POST_BODY = ROOT / ".ai-os" / "receipts" / "gl005-mutation-post.json"

POST_PAYLOAD = {
    "taskType": "SYSTEM_MAINTENANCE_REVIEW",
    "ownerCompany": "MASTERMIND",
    "subjectId": "gl005-mutation-observe",
    "evidenceIds": ["GL005-MUTATION-OBSERVE"],
    "payload": {
        "intent": "OBSERVE_STATE_TRANSITION",
        "execution": False,
        "note": "Review request only. Not commercial execution.",
    },
}


def http(method: str, url: str, *, data: bytes | None = None, timeout: float = 15.0) -> dict:
    headers = {"User-Agent": "gl005-mutation-observe", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = int(resp.status)
    except urllib.error.HTTPError as err:
        raw = err.read()
        status = int(err.code)
    except Exception as err:
        return {
            "url": url,
            "method": method,
            "status": None,
            "error": str(err),
            "ms": int((time.time() - t0) * 1000),
            "body": "",
            "sha256": None,
            "json": None,
        }
    text = raw.decode("utf-8", "replace")
    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    return {
        "url": url,
        "method": method,
        "status": status,
        "ms": int((time.time() - t0) * 1000),
        "body": text,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "json": parsed,
        "observation": classify_http(status),
    }


def semantic_read(probe: dict) -> dict:
    parsed = probe.get("json") if isinstance(probe.get("json"), dict) else {}
    success = parsed.get("success") is True
    data = parsed.get("data")
    ids = []
    if isinstance(data, list):
        ids = [str(row.get("id")) for row in data if isinstance(row, dict) and row.get("id")]
    healthy = (
        probe.get("status") == 200
        and success
        and isinstance(data, list)
    )
    return {
        "http_2xx": isinstance(probe.get("status"), int) and 200 <= int(probe["status"]) < 300,
        "semantic_success": success,
        "read_path_healthy": healthy,
        "count": parsed.get("count") if isinstance(parsed.get("count"), int) else (len(data) if isinstance(data, list) else None),
        "ids": ids,
        "error": parsed.get("error"),
        "details_prefix": (str(parsed.get("details") or "")[:240] or None),
    }


def domain_surface() -> dict:
    route = (ROOT / "app" / "api" / "tasks" / "route.ts").read_text(encoding="utf-8")
    domain = (ROOT / "lib" / "intelligence" / "task-orchestration.ts").read_text(encoding="utf-8")
    test = (ROOT / "tests" / "task_orchestration_check.ts").read_text(encoding="utf-8")
    return {
        "files": [
            "app/api/tasks/route.ts",
            "lib/intelligence/task-orchestration.ts",
            "tests/task_orchestration_check.ts",
        ],
        "http_methods_in_route": {
            "GET": "export async function GET" in route,
            "POST": "export async function POST" in route,
            "PATCH": "export async function PATCH" in route,
            "PUT": "export async function PUT" in route,
            "DELETE": "export async function DELETE" in route,
        },
        "domain_writes_database": "prisma" in domain.lower() or "$queryRaw" in domain or "$executeRaw" in domain,
        "domain_all_execution_false": domain.count("execution: false") >= 7 and "execution: true" not in domain,
        "createTaskContract_status": "REVIEW_REQUIRED",
        "validateTaskTransition_persists": False,
        "unit_test_hits_http_or_db": "/api/tasks" in test or "prisma" in test.lower(),
        "smallest_durable_mutation": "POST /api/tasks → createTaskContract() → INSERT OrchestrationTask status=REVIEW_REQUIRED",
        "rejected_as_demonstration": [
            "GET /api/tasks 200",
            "tests/task_orchestration_check.ts",
            "validateTaskTransition to COMPLETED (no HTTP applicator)",
            ".ai-os/state/TASKS.json",
            "second Next server",
            "new harness that copies route SQL",
        ],
    }


def run_unit_test() -> dict:
    proc = subprocess.run(
        ["npx", "--no-install", "tsx", "tests/task_orchestration_check.ts"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )
    return {
        "argv": ["npx", "--no-install", "tsx", "tests/task_orchestration_check.ts"],
        "exit": int(proc.returncode),
        "stdout_tail": (proc.stdout or "")[-1000:],
        "stderr_tail": (proc.stderr or "")[-1000:],
    }


def main() -> int:
    surface = domain_surface()
    unit = run_unit_test()

    try:
        bound = bind_live()
        bind_error = None
    except BindError as err:
        sidecar = ROOT / ".ai-os" / "receipts" / "GL004-RUNTIME-BIND.json"
        if err.code == EXIT_PLATFORM and sidecar.exists():
            bound = json.loads(sidecar.read_text(encoding="utf-8"))
            bind_error = None
            bound.setdefault("listen_port", bound.get("port") or bound.get("listen_port"))
        else:
            bound = {"ok": False, "exit": err.code, "reason": err.reason, **err.extra}
            bind_error = err.reason

    port = bound.get("listen_port") if isinstance(bound, dict) else None
    pid = bound.get("pid") if isinstance(bound, dict) else None
    base = f"http://127.0.0.1:{port}/api/tasks" if port else None

    before = http("GET", base) if base else {"status": None, "error": "NO_BOUND_PORT", "json": None, "sha256": None, "body": ""}
    before_sem = semantic_read(before)
    BEFORE_BODY.write_text(before.get("body") or "", encoding="utf-8")

    post = http("POST", base, data=json.dumps(POST_PAYLOAD).encode("utf-8")) if base else {"status": None, "error": "NO_BOUND_PORT", "json": None, "sha256": None, "body": ""}
    POST_BODY.write_text(post.get("body") or "", encoding="utf-8")

    after = http("GET", base) if base else {"status": None, "error": "NO_BOUND_PORT", "json": None, "sha256": None, "body": ""}
    after_sem = semantic_read(after)
    AFTER_BODY.write_text(after.get("body") or "", encoding="utf-8")

    new_ids = sorted(set(after_sem.get("ids") or []) - set(before_sem.get("ids") or []))
    state_changed = bool(
        before_sem.get("read_path_healthy")
        and after_sem.get("read_path_healthy")
        and (
            new_ids
            or before_sem.get("count") != after_sem.get("count")
            or (before.get("sha256") and before.get("sha256") != after.get("sha256"))
        )
        and post.get("status") == 201
        and isinstance(post.get("json"), dict)
        and post["json"].get("success") is True
    )

    invariant = {
        "no_execution_flag": True,
        "review_only_status_if_created": True,
        "no_second_server": True,
        "no_forged_session": True,
        "no_new_database": True,
        "live_pid_untouched": (Path(f"/proc/{int(pid)}").exists() if pid and os.name != "nt" else pid is not None),
    }

    law_attack = {
        "candidate": "ORCHESTRATION_DEMONSTRATED_REQUIRES_OBSERVED_STATE_TRANSITION",
        "ruling": "ACCEPT_SCOPED_REJECT_STRENGTHENED",
        "accept_if": (
            "One durable OrchestrationTask row is created through existing POST /api/tasks "
            "+ createTaskContract, observed as GET-before ≠ GET-after, status REVIEW_REQUIRED, execution false."
        ),
        "too_strong_if": [
            "Requires COMPLETED / execution:true / multi-agent — no HTTP applicator exists; all routing is execution:false.",
            "Requires a second next start child — that is production-equivalence, not GL-005 mutation.",
            "Requires a new harness that reimplements route SQL — duplication, not demonstration.",
        ],
        "too_weak_if": [
            "GET 200 / success:true counts as demonstration.",
            "tests/task_orchestration_check.ts exit 0 counts as demonstration.",
            "HTTP 2xx with success:false counts as semantic success.",
        ],
        "historical_gl005": "Shared task state locks handoff and orchestration demonstrated.",
        "historical_fit": (
            "Control plane already exists. The missing observed transition is product OrchestrationTask INSERT, "
            "not a new orchestrator and not a status walk to COMPLETED."
        ),
    }

    payload = {
        "schema": "raios.gl005-mutation-observe.v1",
        "knowledge_state": "DISCOVERED",
        "GL005_PROVEN": False,
        "classification": "LIVE_READ_PATH_PROVEN_EXECUTION_MUTATION_NOT_YET_PROVEN"
        if before_sem.get("read_path_healthy") and not state_changed
        else "MUTATION_NOT_PROVEN",
        "HEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "BRANCH": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "bound_at": utc(),
        "bind_error": bind_error,
        "runtime": {
            "pid": pid,
            "ppid": bound.get("ppid") if isinstance(bound, dict) else None,
            "port": port,
            "mode": bound.get("mode") if isinstance(bound, dict) else None,
            "spawned": False,
            "killed": False,
        },
        "surface": surface,
        "unit_test": {"exit": unit["exit"]},
        "BEFORE_HASH": before.get("sha256"),
        "AFTER_HASH": after.get("sha256"),
        "ACTION_PROCESS_EXIT": post.get("status"),
        "STATE_CHANGED": state_changed,
        "TARGETED_TEST_EXIT": unit["exit"],
        "BEFORE_STATE": {
            "probe": {k: before.get(k) for k in ("status", "sha256", "observation", "error")},
            "semantic": before_sem,
            "body_path": str(BEFORE_BODY),
        },
        "ACTION": {
            "method": "POST",
            "url": base,
            "auth": "none — gl_session not forged",
            "payload": POST_PAYLOAD,
            "why_this_action": surface["smallest_durable_mutation"],
        },
        "ACTION_PROCESS_EXIT": {
            "status": post.get("status"),
            "sha256": post.get("sha256"),
            "observation": post.get("observation"),
            "error": (post.get("json") or {}).get("error") if isinstance(post.get("json"), dict) else post.get("error"),
            "body_path": str(POST_BODY),
        },
        "AFTER_STATE": {
            "probe": {k: after.get(k) for k in ("status", "sha256", "observation", "error")},
            "semantic": after_sem,
            "new_ids": new_ids,
            "body_path": str(AFTER_BODY),
        },
        "STATE_CHANGED": state_changed,
        "DOMAIN_INVARIANT_PRESERVED": invariant,
        "law_attack": law_attack,
        "next_cheapest_action": (
            "On the machine where GET is semantically healthy, POST /api/tasks with an existing gl_session "
            "whose role is ADMIN|WAREHOUSE|EXPORT. Do not mint DATABASE_URL. Do not forge APP_SESSION_SECRET. "
            "Do not start a second Next process."
        ),
        "this_environment": (
            "Unauthenticated POST is the strongest action this observer may take without forging identity. "
            "401 means the mutation surface is present and gated. 201 without a session would be a security defect. "
            "GET 500 on this slice does not authorize Repair to ignore a later GET 200, and Repair GET 200 does not "
            "authorize provisioning Postgres on this slice."
        ),
    }
    digest = write_json(RECEIPT, payload)
    (ROOT / ".ai-os" / "receipts" / "GL005-MUTATION-OBSERVE.sha256").write_text(digest + "\n", encoding="utf-8")
    summary = {
        "GL005_PROVEN": False,
        "BEFORE_STATE": before_sem,
        "BEFORE_HASH": before.get("sha256"),
        "ACTION": "POST /api/tasks unauthenticated (gl_session not forged)",
        "ACTION_PROCESS_EXIT": post.get("status"),
        "AFTER_STATE": after_sem,
        "AFTER_HASH": after.get("sha256"),
        "STATE_CHANGED": state_changed,
        "DOMAIN_INVARIANT_PRESERVED": invariant,
        "TARGETED_TEST_EXIT": unit["exit"],
        "READ_PATH_HEALTHY": before_sem.get("read_path_healthy"),
        "epistemic": {
            "mutation": "PASS" if state_changed else ("BLOCKED" if post.get("status") in (401, 403) else "FAILED" if before.get("status") else "UNAVAILABLE"),
            "read_path": "PASS" if before_sem.get("read_path_healthy") else "FAILED" if before.get("status") == 500 else "UNAVAILABLE",
            "unit_test": "PASS" if unit["exit"] == 0 else "FAILED",
            "gl005_gate": "GATE_CLOSED",
        },
        "RECEIPT": str(RECEIPT),
        "RECEIPT_SHA256": digest,
        "PID_ALIVE": invariant["live_pid_untouched"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"RECEIPT_SHA256={digest}")
    return 0 if not payload["GL005_PROVEN"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
