from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CANONICAL_BRANCH = "ai-evolution-202608051809"
POLICY_PATH = Path(".ai-os/mcp/CANONICAL-CHANGE-AUTHORITY.json")


def run(*args: str) -> str:
    cp = subprocess.run(args, check=True, text=True, capture_output=True)
    return cp.stdout.strip()


def repo_root() -> Path:
    return Path(run("git", "rev-parse", "--show-toplevel")).resolve()


def branch() -> str:
    return run("git", "rev-parse", "--abbrev-ref", "HEAD")


def head() -> str:
    return run("git", "rev-parse", "HEAD")


def staged_diff_hash() -> str:
    cp = subprocess.run(
        ["git", "diff", "--cached", "--binary", "--no-ext-diff"],
        check=True, stdout=subprocess.PIPE,
    )
    return hashlib.sha256(cp.stdout).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def approval_root() -> Path:
    value = os.getenv("RAIOS_CHANGE_AUTHORITY_ROOT")
    if value:
        return Path(value).expanduser().resolve()
    cp = subprocess.run(["git", "config", "--get", "raios.home"], text=True, capture_output=True)
    home = Path(cp.stdout.strip()).resolve() if cp.returncode == 0 and cp.stdout.strip() else Path.home()
    return (home / ".raios" / "runtime" / "change-authority").resolve()


def current_approval_path() -> Path:
    value = os.getenv("RAIOS_CHANGE_APPROVAL")
    return Path(value).resolve() if value else approval_root() / "current-approval.json"


def active_lease_path() -> Path:
    return approval_root() / "active-change.json"


def lease_valid_for_approval(row: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    lease = load_json(active_lease_path())
    if not lease:
        return False, "CHANGE_LEASE_MISSING", lease
    if lease.get("authority") != "C1":
        return False, "CHANGE_LEASE_AUTHORITY_INVALID", lease
    if lease.get("task_id") != row.get("task_id") or lease.get("base_head") != row.get("base_head"):
        return False, "CHANGE_LEASE_SCOPE_MISMATCH", lease
    if lease.get("staged_diff_sha256") != row.get("staged_diff_sha256"):
        return False, "CHANGE_LEASE_DIFF_MISMATCH", lease
    if row.get("approval_id") and lease.get("approval_id") != row.get("approval_id"):
        return False, "CHANGE_LEASE_APPROVAL_MISMATCH", lease
    try:
        expiry = datetime.fromisoformat(str(lease["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return False, "CHANGE_LEASE_EXPIRY_INVALID", lease
    if expiry <= datetime.now(timezone.utc):
        return False, "CHANGE_LEASE_EXPIRED", lease
    return True, "PASS", lease


def approval_valid(path: Path) -> tuple[bool, str, dict[str, Any]]:
    row = load_json(path)
    required = ("authority", "decision", "canonical_branch", "base_head",
                "staged_diff_sha256", "task_id", "expires_at")
    if any(not row.get(k) for k in required):
        return False, "APPROVAL_FIELDS_MISSING", row
    if row.get("authority") != "C1" or row.get("decision") != "APPROVED":
        return False, "APPROVAL_AUTHORITY_INVALID", row
    if row.get("canonical_branch") != CANONICAL_BRANCH:
        return False, "APPROVAL_BRANCH_MISMATCH", row
    if row.get("base_head") != head():
        return False, "APPROVAL_BASE_HEAD_MISMATCH", row
    if row.get("staged_diff_sha256") != staged_diff_hash():
        return False, "APPROVAL_SCOPE_HASH_MISMATCH", row
    lease_ok, lease_reason, _ = lease_valid_for_approval(row)
    if not lease_ok:
        return False, lease_reason, row
    try:
        expiry = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
    except ValueError:
        return False, "APPROVAL_EXPIRY_INVALID", row
    if expiry <= datetime.now(timezone.utc):
        return False, "APPROVAL_EXPIRED", row
    return True, "PASS", row


def verify_pre_commit() -> int:
    if branch() != CANONICAL_BRANCH:
        print("RAIOS_CHANGE_GATE=DENY reason=NONCANONICAL_BRANCH", file=sys.stderr)
        return 31
    path = current_approval_path()
    ok, reason, row = approval_valid(path)
    if not ok:
        print(f"RAIOS_CHANGE_GATE=DENY reason={reason} approval={path}", file=sys.stderr)
        return 32
    print(f"RAIOS_CHANGE_GATE=PASS task_id={row['task_id']}")
    return 0


def record_post_commit() -> int:
    path = current_approval_path()
    row = load_json(path)
    commit = head()
    parent = run("git", "rev-parse", f"{commit}^")
    valid = bool(
        row.get("authority") == "C1"
        and row.get("decision") == "APPROVED"
        and row.get("canonical_branch") == CANONICAL_BRANCH
        and row.get("base_head") == parent
        and row.get("task_id")
        and row.get("staged_diff_sha256")
    )
    if not valid:
        print("RAIOS_POST_COMMIT=NO_VALID_APPROVAL", file=sys.stderr)
        return 33
    out = dict(row)
    out["commit"] = commit
    out["parent"] = parent
    out["recorded_at"] = datetime.now(timezone.utc).isoformat()
    dest = approval_root() / "approved-commits" / f"{commit}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        path.unlink()
    except OSError:
        pass
    lease_path = active_lease_path()
    lease = load_json(lease_path)
    if lease.get("task_id") == row.get("task_id") and lease.get("base_head") == row.get("base_head"):
        try:
            lease_path.unlink()
        except OSError:
            pass
    print(f"RAIOS_POST_COMMIT=RECORDED commit={commit} task_id={row['task_id']}")
    return 0


def approved_commit(commit: str) -> bool:
    path = approval_root() / "approved-commits" / f"{commit}.json"
    row = load_json(path)
    return bool(row.get("authority") == "C1" and row.get("decision") == "APPROVED" and row.get("commit") == commit)


def verify_pre_push() -> int:
    payload = sys.stdin.read().splitlines()
    for line in payload:
        parts = line.split()
        if len(parts) != 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if remote_ref != f"refs/heads/{CANONICAL_BRANCH}":
            print(f"RAIOS_PUSH_GATE=DENY reason=NONCANONICAL_REMOTE_REF ref={remote_ref}", file=sys.stderr)
            return 41
        if local_sha == "0" * 40:
            print("RAIOS_PUSH_GATE=DENY reason=BRANCH_DELETE_FORBIDDEN", file=sys.stderr)
            return 42
        if remote_sha != "0" * 40:
            merge = subprocess.run(["git", "merge-base", "--is-ancestor", remote_sha, local_sha])
            if merge.returncode != 0:
                print("RAIOS_PUSH_GATE=DENY reason=NON_FAST_FORWARD", file=sys.stderr)
                return 43
            revs = run("git", "rev-list", f"{remote_sha}..{local_sha}").splitlines()
        else:
            revs = [local_sha]
        missing = [sha for sha in revs if sha and not approved_commit(sha)]
        if missing:
            print(f"RAIOS_PUSH_GATE=DENY reason=UNAPPROVED_COMMITS commits={','.join(missing)}", file=sys.stderr)
            return 44
    print("RAIOS_PUSH_GATE=PASS")
    return 0


def status() -> int:
    root = repo_root()
    worktrees = run("git", "worktree", "list", "--porcelain").splitlines()
    count = sum(1 for line in worktrees if line.startswith("worktree "))
    rows = {
        "schema": "raios.change-authority.status.v1",
        "canonical_branch": CANONICAL_BRANCH,
        "current_branch": branch(),
        "head": head(),
        "worktree_count": count,
        "single_worktree": count == 1,
        "approval_present": current_approval_path().exists(),
        "change_lease_present": active_lease_path().exists(),
        "hooks_path": run("git", "config", "--get", "core.hooksPath") if subprocess.run(["git","config","--get","core.hooksPath"],capture_output=True).returncode == 0 else None,
        "repo": str(root),
    }
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0 if rows["current_branch"] == CANONICAL_BRANCH and rows["single_worktree"] else 51


def main() -> int:
    p = argparse.ArgumentParser(prog="raios-change-gate")
    p.add_argument("mode", choices=("pre-commit", "post-commit", "pre-push", "status", "hash"))
    args = p.parse_args()
    if args.mode == "pre-commit":
        return verify_pre_commit()
    if args.mode == "post-commit":
        return record_post_commit()
    if args.mode == "pre-push":
        return verify_pre_push()
    if args.mode == "hash":
        print(staged_diff_hash())
        return 0
    return status()


if __name__ == "__main__":
    raise SystemExit(main())
