"""Append C1-visible convergence task and probe the existing ops plane.

Does not mutate LOCKS.json. Does not impersonate C6. Does not merge branches.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life")
sys.path.insert(0, str(REPO / "src"))
from raios.command_center.council_board import atomic, load  # noqa: E402

TASK_ID = "RAIOS-CANONICAL-CONVERGENCE-001"
TASKS = REPO / ".ai-os" / "state" / "TASKS.json"
HOME = Path.home()
OPS = HOME / ".raios" / "runtime" / "council-ops"
OUT = REPO / ".ai-os" / "reports" / "architecture" / "RAIOS-CANONICAL-CONVERGENCE-001" / "OPS-PLANE-OBSERVED.json"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def tcp(port: int, timeout: float = 0.4) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except OSError:
        return False


def http(url: str, timeout: float = 2.0) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            raw = r.read(65536).decode("utf-8-sig", errors="replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {"response_type": "NON_JSON", "len": len(raw)}
            return {"ok": True, "status": r.status, "body": body}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": str(e)}
    except Exception as e:
        return {"ok": False, "status": 0, "error": f"{type(e).__name__}:{e}"}


def append_task() -> dict:
    data = load(TASKS, {"tasks": []})
    tasks = data.setdefault("tasks", [])
    existing = next((t for t in tasks if t.get("id") == TASK_ID), None)
    now = utc()
    row = {
        "id": TASK_ID,
        "title": "التقارب التدريجي نحو الكانوني — ظاهر للمجلس",
        "objective": (
            "Gradual convergence onto canonical (option 3). Visible to all workers. "
            "Operational first: 9Router, MessageWorker, council, Command Center binding "
            "to C5/MCP/factories/resources. No wholesale merge. No clean-tree rebuild. No deletion."
        ),
        "status": "IN_PROGRESS",
        "authorized_by": "C1",
        "authority": "C1",
        "allowed_agents": ["C1", "C2", "C8"],
        "scheduler_priority": "CRITICAL",
        "dispatch_status": "SYSTEM_FIRST_ACTIVE",
        "automatic_dispatch": False,
        "self_claim_allowed": True,
        "claim_mode": "SELF_CLAIM_ALLOWED",
        "system_owner": "RAIOS_SYSTEM",
        "created_at": now if existing is None else existing.get("created_at", now),
        "started_at": now if existing is None else existing.get("started_at", now),
        "updated_at": now,
        "decision": "D-043",
        "visible_on_command_center": True,
        "board_visibility": "REQUIRED",
        "review_by": ["C1"],
        "scope": [
            ".ai-os/reports/architecture/RAIOS-CANONICAL-CONVERGENCE-001",
            "src/raios/command_center",
            "scripts/runtime/Maintain-RAIOS-Online.ps1",
        ],
        "evidence": ".ai-os/reports/architecture/RAIOS-CANONICAL-CONVERGENCE-001/C1-ACCEPTANCE.json",
        "evidence_refs": [
            ".ai-os/reports/architecture/RAIOS-CANONICAL-CONVERGENCE-001/C1-ACCEPTANCE.json",
            ".ai-os/state/DECISIONS.md",
        ],
        "validation": (
            "Board lists this task; 9Router TCP proven; Command Center health; "
            "C2/C8 live-bound or blocker reported; C6 live-bind remains required before P0 mutation."
        ),
        "blocker": (
            "C6_SIGNED_OUT; hung :8770/:8788 ACCESS_DENIED until C1 admin kill after disk clean; "
            "9Router/NATS TCP down at last probe."
        ),
        "next_step": "Restore existing 9Router/worker/council/CC plane; do not merge cursor/*; do not fake C6.",
        "hard_constraints": [
            "NO_WHOLESALE_MERGE",
            "NO_CLEAN_TREE_REBUILD",
            "NO_DELETE",
            "NO_SECOND_COMMAND_CENTER",
            "NO_SECOND_MCP",
            "LOCKS_JSON_NOT_MUTATED",
            "C6_NOT_IMPERSONATED",
        ],
        "active_workers": ["C1", "C2", "C8"],
    }
    if existing is None:
        tasks.append(row)
        action = "APPENDED"
    else:
        existing.update(row)
        action = "UPDATED"
    atomic(TASKS, data)
    verify = load(TASKS, {"tasks": []})
    found = any(t.get("id") == TASK_ID for t in verify.get("tasks") or [])
    last_id = (verify.get("tasks") or [{}])[-1].get("id")
    return {"action": action, "found": found, "last_id": last_id, "total": len(verify.get("tasks") or [])}


def lock_pid(path: Path) -> str | None:
    try:
        raw = path.read_bytes()[:32].decode("ascii", "replace").strip()
        return raw or None
    except OSError:
        return None


def main() -> int:
    observed = {
        "schema": "raios.ops-plane-observed.v1",
        "generated_at": utc(),
        "class": "OBSERVED",
        "locks_mutated": False,
        "tcp": {str(p): tcp(p) for p in (20128, 4222, 8766, 8770, 8788, 11434)},
        "http": {
            "c5_health": http("http://127.0.0.1:8766/health"),
            "cc_health": http("http://127.0.0.1:8770/health"),
            "cc_bootstrap": http("http://127.0.0.1:8770/api/bootstrap"),
            "cc_plane": http("http://127.0.0.1:8770/api/plane"),
            "mcp_health": http("http://127.0.0.1:8788/health"),
        },
        "auth": {
            "c2": (OPS / "auth" / "C2-CURSOR-AUTH.json").is_file(),
            "c8": (OPS / "auth" / "C8-DESKTOP-COMMANDER-AUTH.json").is_file(),
        },
        "consumers": {
            "c2_lock_pid": lock_pid(OPS / "consumers" / "C2.agent.lock"),
            "c8_lock_pid": lock_pid(OPS / "consumers" / "C8.agent.lock"),
            "c2_exists": (OPS / "consumers" / "C2.json").is_file(),
            "c8_exists": (OPS / "consumers" / "C8.json").is_file(),
        },
        "paths": {
            "9router_cli": str(Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "9router" / "cli.js"),
        },
    }
    observed["paths"]["9router_cli_exists"] = Path(observed["paths"]["9router_cli"]).is_file()
    try:
        observed["task"] = append_task()
    except Exception as exc:
        observed["task"] = {"action": "FAILED", "error": f"{type(exc).__name__}:{exc}"}
    OUT.write_text(json.dumps(observed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(observed, ensure_ascii=False, indent=2))
    return 0 if observed.get("task", {}).get("found") else 2


if __name__ == "__main__":
    raise SystemExit(main())
