from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

REPAIR = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair").resolve()

ROOT = REPAIR / "_raios-authoritative-certifier"
REPORTS = ROOT / "reports"

FINAL14 = (
    REPAIR
    / "_raios-worktree-salvage"
    / "reports"
    / "FINAL-14-FORENSIC-RESOLUTION.json"
)

TRUE_OPEN = (
    REPAIR
    / "_raios-worktree-salvage"
    / "reports"
    / "FINAL-14-TRUE-OPEN.json"
)

EXECUTION_RECEIPT = (
    REPAIR
    / "_raios-worktree-salvage"
    / "reports"
    / "TRUE-OPEN-EXECUTION-RECEIPT.json"
)

LOCAL_AGENT = (
    REPAIR
    / "scripts"
    / "ai-os"
    / "local-agent-v2.py"
)

GL003 = (
    REPAIR
    / "scripts"
    / "ai-os"
    / "gl003-synthesizer.py"
)

MODEL_CANDIDATE = (
    REPAIR
    / "_raios-worktree-salvage"
    / "learning"
    / "QWEN-LOCAL-CODER-CAPABILITY-CANDIDATE.json"
)

TASKS = REPAIR / ".ai-os" / "state" / "TASKS.json"
LOCKS = REPAIR / ".ai-os" / "state" / "LOCKS.json"
CURRENT_STATE = REPAIR / ".ai-os" / "state" / "CURRENT-STATE.json"

LEGACY_WORKTREES = [
    Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\GL-002-Main-Brain"),
    Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\GL-003-Project-Brains"),
    Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\GL-004-Runtime"),
    Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\GL-005-Convergence"),
]

EXPECTED_LOCAL_AGENT_SHA256 = (
    "5e810dda38c44aef870fde6969dde344c724288397c876c01f26649e4c7f3461"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def require(condition: bool, code: str, detail: Any = None) -> None:
    if not condition:
        if detail is None:
            raise RuntimeError(code)

        raise RuntimeError(
            f"{code}::{json.dumps(detail, ensure_ascii=False, default=str)}"
        )


def run(cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd or REPAIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )

    return {
        "command": cmd,
        "exit_code": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def git_lines(args: list[str], cwd: Path = REPAIR) -> list[str]:
    result = run(["git", *args], cwd)

    require(
        result["exit_code"] == 0,
        "GIT_COMMAND_FAILED",
        result,
    )

    return [
        x.rstrip("\r\n")
        for x in result["stdout"].splitlines()
        if x.strip()
    ]


def compile_python(path: Path) -> dict[str, Any]:
    return run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(path),
        ]
    )


def atomic_json_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        obj,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")

    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_name, path)

    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def main() -> int:
    run_id = (
        "RAIOS-CERT-"
        + time.strftime("%Y%m%d-%H%M%S")
        + "-"
        + uuid.uuid4().hex[:12]
    )

    started = time.time()

    evidence: dict[str, Any] = {
        "run_id": run_id,
        "started_at_epoch": started,
    }

    try:
        require(REPAIR.exists(), "REPAIR_NOT_FOUND")

        real_root = Path(
            git_lines(
                ["rev-parse", "--show-toplevel"]
            )[0]
        ).resolve()

        require(
            real_root == REPAIR,
            "WRONG_REPOSITORY",
            {
                "expected": str(REPAIR),
                "actual": str(real_root),
            },
        )

        branch = git_lines(
            ["branch", "--show-current"]
        )[0]

        head = git_lines(
            ["rev-parse", "HEAD"]
        )[0]

        evidence["repository"] = {
            "root": str(real_root),
            "branch": branch,
            "head": head,
        }

        required = [
            FINAL14,
            TRUE_OPEN,
            EXECUTION_RECEIPT,
            LOCAL_AGENT,
            GL003,
            MODEL_CANDIDATE,
            TASKS,
            LOCKS,
            CURRENT_STATE,
        ]

        missing = [
            str(p)
            for p in required
            if not p.exists()
        ]

        require(
            not missing,
            "REQUIRED_EVIDENCE_MISSING",
            missing,
        )

        final14 = load_json(FINAL14)
        true_open = load_json(TRUE_OPEN)
        exec_receipt = load_json(EXECUTION_RECEIPT)

        tasks = load_json(TASKS)
        locks = load_json(LOCKS)
        current_state = load_json(CURRENT_STATE)
        model_candidate = load_json(MODEL_CANDIDATE)

        require(
            int(final14.get("cases", -1)) == 14,
            "FINAL14_CASE_COUNT_INVALID",
            final14.get("cases"),
        )

        require(
            int(final14.get("true_open_count", -1)) == 8,
            "FINAL14_TRUE_OPEN_ORIGINAL_INVALID",
            final14.get("true_open_count"),
        )

        require(
            isinstance(true_open, list),
            "TRUE_OPEN_NOT_ARRAY",
        )

        require(
            len(true_open) == 8,
            "TRUE_OPEN_PHYSICAL_COUNT_INVALID",
            len(true_open),
        )

        require(
            exec_receipt.get("unresolved_logical_cases") == 0,
            "EXECUTION_RECEIPT_NOT_ZERO_GAP",
            exec_receipt,
        )

        require(
            exec_receipt.get("safety", {}).get("stale_locks_reactivated") is False,
            "STALE_LOCK_REACTIVATION_DETECTED",
        )

        require(
            exec_receipt.get("current_goal_overwritten") is False,
            "CURRENT_GOAL_OVERWRITE_DETECTED",
        )

        require(
            exec_receipt.get("active_wave_overwritten") is False,
            "ACTIVE_WAVE_OVERWRITE_DETECTED",
        )

        require(
            exec_receipt.get("legacy_provider_binding_restored") is False,
            "LEGACY_PROVIDER_BINDING_RESTORED",
        )

        local_agent_hash = sha256(LOCAL_AGENT)

        require(
            local_agent_hash == EXPECTED_LOCAL_AGENT_SHA256,
            "LOCAL_AGENT_HASH_INVALID",
            local_agent_hash,
        )

        compile_local = compile_python(LOCAL_AGENT)
        compile_gl003 = compile_python(GL003)

        require(
            compile_local["exit_code"] == 0,
            "LOCAL_AGENT_COMPILE_FAILED",
            compile_local,
        )

        require(
            compile_gl003["exit_code"] == 0,
            "GL003_COMPILE_FAILED",
            compile_gl003,
        )

        require(
            isinstance(tasks, dict),
            "TASKS_JSON_NOT_OBJECT",
        )

        require(
            isinstance(locks, dict),
            "LOCKS_JSON_NOT_OBJECT",
        )

        require(
            isinstance(current_state, dict),
            "CURRENT_STATE_JSON_NOT_OBJECT",
        )

        require(
            isinstance(model_candidate, dict),
            "MODEL_CANDIDATE_JSON_NOT_OBJECT",
        )

        worktree_rows = []

        for wt in LEGACY_WORKTREES:
            exists = wt.exists()

            row: dict[str, Any] = {
                "path": str(wt),
                "exists": exists,
            }

            if exists:
                status = run(
                    [
                        "git",
                        "-C",
                        str(wt),
                        "status",
                        "--porcelain=v1",
                    ]
                )

                require(
                    status["exit_code"] == 0,
                    "WORKTREE_GIT_STATUS_FAILED",
                    status,
                )

                dirty = [
                    x
                    for x in status["stdout"].splitlines()
                    if x.strip()
                ]

                row["dirty_count"] = len(dirty)
                row["dirty_entries"] = dirty

            worktree_rows.append(row)

        evidence["legacy_worktrees"] = worktree_rows

        repair_status = git_lines(
            ["status", "--porcelain=v1"]
        )

        evidence["repair_dirty_count"] = len(
            repair_status
        )

        evidence["hashes"] = {
            "final14": sha256(FINAL14),
            "true_open_original": sha256(TRUE_OPEN),
            "execution_receipt": sha256(EXECUTION_RECEIPT),
            "local_agent": local_agent_hash,
            "gl003": sha256(GL003),
            "model_candidate": sha256(MODEL_CANDIDATE),
            "tasks": sha256(TASKS),
            "locks": sha256(LOCKS),
            "current_state": sha256(CURRENT_STATE),
        }

        evidence["compile"] = {
            "local_agent": compile_local,
            "gl003": compile_gl003,
        }

        checks = {
            "repository_identity": True,
            "final14_original_cases": 14,
            "final14_original_true_open": 8,
            "true_open_physical_cases": 8,
            "reconciliation_receipt_unresolved_logical_cases": 0,
            "local_agent_hash_verified": True,
            "local_agent_compile": True,
            "gl003_compile": True,
            "state_json_readback": True,
            "legacy_provider_binding_restored": False,
            "stale_lock_reactivated": False,
            "current_goal_overwritten": False,
            "active_wave_overwritten": False,
        }

        receipt = {
            "schema": "raios.authoritative-certification.v1",
            "run_id": run_id,
            "status": "CERTIFIED",
            "certified": True,
            "exit_code": 0,
            "checks": checks,
            "evidence": evidence,
            "duration_seconds": round(
                time.time() - started,
                6,
            ),
        }

        receipt_path = (
            REPORTS
            / f"{run_id}.receipt.json"
        )

        atomic_json_write(
            receipt_path,
            receipt,
        )

        readback = load_json(receipt_path)

        require(
            readback.get("run_id") == run_id,
            "RECEIPT_RUN_ID_MISMATCH",
        )

        require(
            readback.get("certified") is True,
            "RECEIPT_NOT_CERTIFIED",
        )

        require(
            readback.get("exit_code") == 0,
            "RECEIPT_EXIT_INVALID",
        )

        receipt_hash = sha256(receipt_path)

        pointer = {
            "run_id": run_id,
            "receipt": str(receipt_path),
            "receipt_sha256": receipt_hash,
            "certified": True,
        }

        atomic_json_write(
            REPORTS / "LATEST.json",
            pointer,
        )

        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "certified": True,
                    "receipt": str(receipt_path),
                    "receipt_sha256": receipt_hash,
                },
                ensure_ascii=False,
            )
        )

        return 0

    except Exception as exc:
        failure = {
            "schema": "raios.authoritative-certification.v1",
            "run_id": run_id,
            "status": "FAILED",
            "certified": False,
            "exit_code": 1,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "evidence": evidence,
            "duration_seconds": round(
                time.time() - started,
                6,
            ),
        }

        failure_path = (
            REPORTS
            / f"{run_id}.failure.json"
        )

        atomic_json_write(
            failure_path,
            failure,
        )

        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "certified": False,
                    "failure": str(failure_path),
                    "error": str(exc),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())