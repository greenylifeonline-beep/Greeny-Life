"""Read-only C5 capabilities. No public agent publication."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

CAPABILITY_HEALTH = "c5.self_inspect.health"
CAPABILITY_HANGING = "raios.system.hanging_work"
CAPABILITY_ECOLOGY = "raios.system.model_ecology"
CAPABILITY_FILE_INTELLIGENCE = "raios.system.file_intelligence"

_READ_ONLY = {
    "RISK_CLASS": "LOW",
    "SIDE_EFFECTS": False,
    "PUBLIC_SAFE_SUBSET": False,
    "MODE": "READ_ONLY",
    "REVERSIBLE": True,
}

CONTRACTS: dict[str, dict[str, Any]] = {
    CAPABILITY_HEALTH: {"CAPABILITY_ID": CAPABILITY_HEALTH, **_READ_ONLY},
    CAPABILITY_HANGING: {"CAPABILITY_ID": CAPABILITY_HANGING, **_READ_ONLY},
    CAPABILITY_ECOLOGY: {"CAPABILITY_ID": CAPABILITY_ECOLOGY, **_READ_ONLY},
    CAPABILITY_FILE_INTELLIGENCE: {"CAPABILITY_ID": CAPABILITY_FILE_INTELLIGENCE, **_READ_ONLY},
}

UNKNOWN_CAPABILITY = "UNKNOWN_CAPABILITY"
CAPABILITY_NOT_AUTHORIZED = "CAPABILITY_NOT_AUTHORIZED"

HealthFn = Callable[[], dict[str, Any]]


def get_contract(capability_id: str) -> dict[str, Any]:
    if capability_id not in CONTRACTS:
        raise ValueError(UNKNOWN_CAPABILITY)
    return dict(CONTRACTS[capability_id])


def default_health() -> dict[str, Any]:
    request = urllib.request.Request("http://127.0.0.1:8766/health")
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            body = json.loads(response.read().decode("utf-8-sig"))
            return {"LIVE": response.status == 200, "http_status": response.status, "body": body}
    except urllib.error.URLError as exc:
        return {"LIVE": False, "http_status": 0, "error": str(exc)}
    except Exception as exc:
        return {"LIVE": False, "http_status": 0, "error": f"{type(exc).__name__}:{exc}"}


def _hanging_work() -> dict[str, Any]:
    from pathlib import Path

    from raios.command_center.board_now import hanging_work

    root = Path(__file__).resolve().parents[3]
    path = root / ".ai-os" / "state" / "TASKS.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"LIVE": False, "error": f"{type(exc).__name__}:{exc}"}
    tasks = doc.get("tasks") if isinstance(doc, dict) else []
    out = hanging_work(tasks if isinstance(tasks, list) else [])
    out["LIVE"] = True
    return out


def _model_ecology() -> dict[str, Any]:
    from raios.factory_fabric.orchestrator import model_ecology_probe

    out = model_ecology_probe()
    out["LIVE"] = str(out.get("status") or "").upper() == "PASS"
    return out


def _file_intelligence() -> dict[str, Any]:
    from raios.file_intelligence import tool_health

    out = tool_health()
    out["LIVE"] = True
    return out


def invoke(capability_id: str, *, health: HealthFn | None = None) -> dict[str, Any]:
    contract = get_contract(capability_id)
    if capability_id == CAPABILITY_HEALTH:
        fn = health or default_health
        out = fn()
        return {"INVOKED": True, "contract": contract, "result": out}
    if capability_id == CAPABILITY_HANGING:
        return {"INVOKED": True, "contract": contract, "result": _hanging_work()}
    if capability_id == CAPABILITY_ECOLOGY:
        return {"INVOKED": True, "contract": contract, "result": _model_ecology()}
    if capability_id == CAPABILITY_FILE_INTELLIGENCE:
        return {"INVOKED": True, "contract": contract, "result": _file_intelligence()}
    raise ValueError(CAPABILITY_NOT_AUTHORIZED)

# RAIOS_ENGINEERING_SCOPED_REPO_TASK_V1
# Governed repository execution capability. No raw shell.
from pathlib import Path as _RaiosPath
import base64 as _raios_base64
import hashlib as _raios_hashlib
import os as _raios_os
import re
import subprocess as _raios_subprocess

_RAIOS_SCOPED_REPO_CAPABILITY = "engineering.scoped_repo_task"
_RAIOS_ORIGINAL_INVOKE = invoke

def _raios_sha256_bytes(data: bytes) -> str:
    return _raios_hashlib.sha256(data).hexdigest()

def _raios_repo_root(payload: dict) -> _RaiosPath:
    root = _RaiosPath(str(payload.get("repository_root") or r"C:\Users\Ghanam\Documents\Codex\Greeny-Life")).resolve()
    expected = _RaiosPath(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life").resolve()
    if root != expected:
        raise ValueError("REPOSITORY_ROOT_DENIED")
    return root

def _raios_rel(root: _RaiosPath, raw: str) -> tuple[str, _RaiosPath]:
    rel = str(raw or "").replace("\\", "/").strip().lstrip("/")
    if not rel or rel.startswith(".git/") or rel == ".git":
        raise ValueError("PATH_DENIED")
    p = (root / rel).resolve()
    if root not in p.parents and p != root:
        raise ValueError("PATH_TRAVERSAL")
    low = rel.casefold()
    forbidden = (
        ".ai-os/mcp/tokens.local.json",
        ".env",
        "credentials",
        "secrets",
        "private_key",
        "id_rsa",
    )
    if any(x in low for x in forbidden):
        raise ValueError("SECRET_PATH_DENIED")
    return rel, p


def _raios_git_identity(root: _RaiosPath) -> tuple[str, str]:
    """Read canonical branch + HEAD from Git metadata without spawning Git."""
    git_dir = root / ".git"

    if git_dir.is_file():
        meta = git_dir.read_text(encoding="utf-8").strip()
        if not meta.lower().startswith("gitdir:"):
            raise RuntimeError("GIT_METADATA_INVALID")
        target = meta.split(":", 1)[1].strip()
        git_dir = (root / target).resolve()

    raw = (git_dir / "HEAD").read_text(
        encoding="utf-8"
    ).strip()

    if not raw.startswith("ref:"):
        if re.fullmatch(r"[0-9a-fA-F]{40}", raw):
            return "", raw.lower()
        raise RuntimeError("GIT_HEAD_INVALID")

    ref = raw.split(":", 1)[1].strip()

    if (
        not ref.startswith("refs/heads/")
        or ".." in ref
    ):
        raise RuntimeError("GIT_REF_INVALID")

    branch = ref[len("refs/heads/"):]

    ref_path = git_dir.joinpath(*ref.split("/"))

    if ref_path.is_file():
        head = ref_path.read_text(
            encoding="utf-8"
        ).strip()
    else:
        head = ""

        packed = git_dir / "packed-refs"

        if packed.is_file():
            for line in packed.read_text(
                encoding="utf-8"
            ).splitlines():
                if not line or line.startswith(("#", "^")):
                    continue
                parts = line.split(" ", 1)
                if len(parts) == 2 and parts[1].strip() == ref:
                    head = parts[0].strip()
                    break

    if not re.fullmatch(r"[0-9a-fA-F]{40}", head):
        raise RuntimeError("GIT_HEAD_INVALID")

    return branch, head.lower()

def _raios_git(root: _RaiosPath, args: list[str], timeout: int = 60) -> str:
    cp = _raios_subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=getattr(_raios_subprocess, "CREATE_NO_WINDOW", 0),
    )
    if cp.returncode != 0:
        raise RuntimeError("GIT_FAILED::" + " ".join(args) + "::" + (cp.stderr or cp.stdout)[-2000:])
    return (cp.stdout or "").strip()

def _raios_scoped_repo_task(payload: dict | None = None) -> dict:
    p = dict(payload or {})
    root = _raios_repo_root(p)
    branch, head_before = _raios_git_identity(root)
    if branch != "ai-evolution-202608051809":
        raise RuntimeError("WRONG_BRANCH::" + branch)
    expected_head = str(p.get("expected_head") or "").strip()
    if expected_head and expected_head != head_before:
        raise RuntimeError("STALE_HEAD")

    allowed = [str(x).replace("\\", "/").strip().lstrip("/") for x in (p.get("allowed_paths") or [])]
    if not allowed:
        raise ValueError("ALLOWED_PATHS_REQUIRED")

    def assert_allowed(rel: str) -> None:
        ok = any(rel == a or rel.startswith(a.rstrip("/") + "/") for a in allowed)
        if not ok:
            raise PermissionError("PATH_OUTSIDE_SCOPE::" + rel)

    operation = str(p.get("operation") or "").strip().upper()
    result: dict = {
        "INVOKED": True,
        "CAPABILITY": _RAIOS_SCOPED_REPO_CAPABILITY,
        "OPERATION": operation,
        "BRANCH": branch,
        "HEAD_BEFORE": head_before,
        "SHELL": False,
    }

    if operation == "READ_FILE":
        rel, path = _raios_rel(root, str(p.get("path") or ""))
        assert_allowed(rel)
        if not path.is_file():
            raise FileNotFoundError(rel)
        data = path.read_bytes()
        if len(data) > 262144:
            raise ValueError("FILE_TOO_LARGE")
        result.update({
            "PATH": rel,
            "SHA256": _raios_sha256_bytes(data),
            "SIZE": len(data),
            "TEXT": data.decode("utf-8", errors="replace"),
        })
        return result

    if operation not in {"REPLACE_TEXT", "WRITE_FILE"}:
        raise ValueError("OPERATION_DENIED")

    rel, path = _raios_rel(root, str(p.get("path") or ""))
    assert_allowed(rel)

    before = path.read_bytes() if path.exists() else b""
    expected_sha = str(p.get("expected_sha256") or "").lower().strip()
    if expected_sha and _raios_sha256_bytes(before) != expected_sha:
        raise RuntimeError("EXPECTED_SHA256_MISMATCH")

    if operation == "REPLACE_TEXT":
        if not path.is_file():
            raise FileNotFoundError(rel)
        old = str(p.get("old") or "")
        new = str(p.get("new") or "")
        if not old:
            raise ValueError("OLD_TEXT_REQUIRED")
        text = before.decode("utf-8")
        count = text.count(old)
        expected_count = int(p.get("expected_count") or 1)
        if count != expected_count:
            raise RuntimeError(f"REPLACE_COUNT_MISMATCH::{count}::{expected_count}")
        after = text.replace(old, new, expected_count).encode("utf-8")
    else:
        if p.get("content_b64") is not None:
            after = _raios_base64.b64decode(str(p["content_b64"]), validate=True)
        else:
            after = str(p.get("content") or "").encode("utf-8")

    if len(after) > 4 * 1024 * 1024:
        raise ValueError("WRITE_TOO_LARGE")

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".raios-tmp-" + _raios_os.urandom(6).hex())
    tmp.write_bytes(after)
    _raios_os.replace(tmp, path)

    result.update({
        "PATH": rel,
        "SHA256_BEFORE": _raios_sha256_bytes(before),
        "SHA256_AFTER": _raios_sha256_bytes(after),
        "STATE_CHANGED": before != after,
    })

    commit = bool(p.get("commit_and_push"))
    if commit:
        # Only stage declared scope, never the whole worktree.
        _raios_git(root, ["add", "--", *allowed])
        staged = _raios_git(root, ["diff", "--cached", "--name-only", "--", *allowed])
        staged_paths = [x.strip().replace("\\", "/") for x in staged.splitlines() if x.strip()]
        if not staged_paths:
            result["COMMIT_CREATED"] = False
            result["HEAD_AFTER"] = head_before
            return result
        for staged_rel in staged_paths:
            assert_allowed(staged_rel)
        msg = str(p.get("commit_message") or "RAIOS governed scoped execution").strip()
        if not msg:
            raise ValueError("COMMIT_MESSAGE_REQUIRED")
        _raios_git(root, ["commit", "-m", msg, "--", *allowed], timeout=120)
        _, head_after = _raios_git_identity(root)
        _raios_git(root, ["push", "origin", "ai-evolution-202608051809"], timeout=180)
        remote = _raios_git(root, ["ls-remote", "origin", "refs/heads/ai-evolution-202608051809"], timeout=60)
        remote_sha = remote.split()[0] if remote else ""
        if remote_sha != head_after:
            raise RuntimeError("PUSH_PROOF_MISMATCH")
        result.update({
            "COMMIT_CREATED": True,
            "HEAD_AFTER": head_after,
            "REMOTE_HEAD": remote_sha,
            "PUSH_PROVEN": True,
            "STAGED_PATHS": staged_paths,
        })
    else:
        result["HEAD_AFTER"] = _raios_git_identity(root)[1]

    return result

try:
    CONTRACTS[_RAIOS_SCOPED_REPO_CAPABILITY] = _raios_scoped_repo_task
except Exception as _raios_contract_error:
    raise RuntimeError("RAIOS_SCOPED_CAPABILITY_REGISTRATION_FAILED") from _raios_contract_error

def invoke(capability, payload=None):
    if capability == _RAIOS_SCOPED_REPO_CAPABILITY:
        return _raios_scoped_repo_task(payload)
    return _RAIOS_ORIGINAL_INVOKE(capability)