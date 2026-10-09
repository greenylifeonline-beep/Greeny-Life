import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = r"C:\Users\Ghanam\Documents\Codex\Greeny-Life"
CONT = r"C:\Users\Ghanam\.raios\runtime\continuity"
CPDIR = os.path.join(CONT, "checkpoints", "reconnect")
CURRENT = os.path.join(CPDIR, "CURRENT.json")
BASELINE = os.path.join(CPDIR, "DISCONNECT.json")
HISTORY = os.path.join(CPDIR, "history.jsonl")
CANON = "ai-evolution-202608051809"
TASK_ID = os.environ.get("RAIOS_CONTINUITY_TASK_ID", "RAIOS-UCF-SYSTEM-LEASE-AND-COMMUNICATION-REMEDIATION-001")
TASK_RESUME_API = "http://127.0.0.1:8770/api/task-resume/"
EXCLUDES = (
    ":(exclude).ai-os/state/**",
    ":(exclude).ai-os/receipts/**",
    ":(exclude).raios/**",
)

def run_git(args, timeout=25):
    try:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        return subprocess.run(
            ["git", "-c", f"safe.directory={ROOT}", "-C", ROOT, *args],
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
    except Exception as exc:
        return None

def git_value(*args):
    p = run_git(list(args), 2)
    if p is None or p.returncode != 0:
        return None
    return p.stdout.strip()

def observe_remote_head():
    p = run_git(["ls-remote", "--heads", "origin", f"refs/heads/{CANON}"], 3)
    if p is None:
        return None, False, "LS_REMOTE_EXCEPTION_OR_TIMEOUT"
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "LS_REMOTE_FAILED").strip().replace("\r", " ").replace("\n", " ")
        return None, False, err[:400]
    line = (p.stdout or "").strip().splitlines()
    if not line:
        return None, False, "LS_REMOTE_CANONICAL_REF_MISSING"
    sha = line[0].split()[0].strip()
    if len(sha) != 40:
        return None, False, "LS_REMOTE_INVALID_SHA"
    return sha, True, None

def source_fingerprint():
    """Bounded reconnect fingerprint: never walk/stat every tracked file."""
    index_path=os.path.join(ROOT,".git","index")
    try:
        st=os.stat(index_path)
        index_meta=f"{st.st_size}:{st.st_mtime_ns}"
        fingerprint="sha256:"+hashlib.sha256(index_meta.encode("ascii")).hexdigest()
    except OSError as exc:
        return None,0,f"INDEX_STAT_ERROR:{type(exc).__name__}",None
    p=run_git(["diff-index","--quiet","HEAD","--",".",*EXCLUDES],2)
    if p is None:
        return fingerprint,1,"WORKTREE_PROBE_TIMEOUT",None
    if p.returncode==0:
        return fingerprint,1,None,True
    if p.returncode==1:
        return fingerprint,1,None,False
    err=(p.stderr or p.stdout or "DIFF_INDEX_FAILED").strip().replace("\r"," ").replace("\n"," ")
    return fingerprint,1,err[:400],None

def canonical_task_resume():
    """Read CouncilBoard checkpoint state; never write a second ledger."""
    url=TASK_RESUME_API+urllib.parse.quote(TASK_ID,safe="")
    try:
        req=urllib.request.Request(url,headers={"Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=2.0) as response:
            body=json.loads(response.read().decode("utf-8-sig")); code=response.status
        return {"available":code==200,"task_id":TASK_ID,"engine":"CouncilBoard.resume_checkpoint","api":"/api/task-resume/{task_id}","single_task_ledger":bool(body.get("single_task_ledger")),"status":body.get("status"),"claimed_by":body.get("claimed_by"),"dispatch_status":body.get("dispatch_status"),"resume_checkpoint":body.get("resume_checkpoint")}
    except Exception as exc:
        return {"available":False,"task_id":TASK_ID,"engine":"CouncilBoard.resume_checkpoint","api":"/api/task-resume/{task_id}","single_task_ledger":True,"error":f"{type(exc).__name__}:{exc}"[:400],"fail_soft":True}

def snapshot(reason, probe_remote=False):
    remote_observed = None
    probe_ok = None
    probe_error = None
    if probe_remote:
        remote_observed, probe_ok, probe_error = observe_remote_head()
    branch = git_value("branch", "--show-current")
    head = git_value("rev-parse", "HEAD")
    remote_tracking = git_value("rev-parse", "origin/" + CANON)
    dirty_hash, dirty_lines, status_error, working_tree_clean = source_fingerprint()
    remote_for_compare = remote_observed or remote_tracking
    comparable = (
        branch == CANON
        and bool(head)
        and bool(remote_for_compare)
        and bool(dirty_hash)
        and (probe_ok is not False)
        and status_error is None
    )
    obj = {
        "schema": "raios.reconnect-checkpoint.v2",
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reason": reason,
        "canonical_branch": CANON,
        "branch": branch,
        "local_head": head,
        "remote_tracking_head": remote_tracking,
        "remote_observed_head": remote_observed,
        "dirty_tracked_sha256": dirty_hash,
        "dirty_tracked_lines": dirty_lines,
        "source_fingerprint_scope": "GIT_INDEX_METADATA_PLUS_BOUNDED_DIFF_INDEX",
        "working_tree_clean": working_tree_clean,
        "remote_probe_attempted": bool(probe_remote),
        "remote_probe_ok": probe_ok,
        "remote_probe_error": probe_error,
        "status_error": status_error,
        "comparable": bool(comparable),
        "source": "RAIOS_CONTINUITY",
        "authority": "RAIOS_SYSTEM",
        "checkpoint_state_engine": "CouncilBoard.resume_checkpoint",
        "canonical_task_resume": canonical_task_resume(),
        "second_task_ledger": False,
        "checkpoint_policy": "FAIL_SOFT_RUNTIME_FAIL_CLOSED_MUTATION",
    }
    return obj

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None

def seal(obj):
    body = {k: v for k, v in obj.items() if k != "proof_hash"}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
    obj["proof_hash"] = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return obj

def atomic(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def append_history(obj):
    os.makedirs(CPDIR, exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n")
        f.flush()
        os.fsync(f.fileno())

def compare(base, new):
    """Return only proven source drift.

    Probe failures, timeouts, or incomplete snapshots are verification
    uncertainty, not drift. They fail closed for source mutation elsewhere but
    must never block transport/runtime continuation.
    """
    drift = {}
    for key in (
        "canonical_branch",
        "branch",
        "local_head",
    ):
        before = base.get(key)
        after = new.get(key)
        if before is None or after is None:
            continue
        if before != after:
            drift[key] = {"before": before, "after": after}

    base_remote = base.get("remote_observed_head") or base.get("remote_tracking_head")
    new_remote = new.get("remote_observed_head") or new.get("remote_tracking_head")
    if base_remote is not None and new_remote is not None and base_remote != new_remote:
        drift["remote_canonical_head"] = {"before": base_remote, "after": new_remote}

    # Git index metadata is only a bounded probe aid, never semantic source
    # identity. Treat only a proven clean/dirty state transition as workspace
    # drift; dirty-to-dirty remains fail-closed for mutation without blocking
    # runtime continuation.
    base_clean = base.get("working_tree_clean")
    new_clean = new.get("working_tree_clean")
    if isinstance(base_clean, bool) and isinstance(new_clean, bool) and base_clean != new_clean:
        drift["working_tree_clean"] = {"before": base_clean, "after": new_clean}
    return drift

def verification_pending(base, new):
    """Uncertainty is advisory for runtime and fail-closed only for mutation."""
    required = (
        "canonical_branch",
        "branch",
        "local_head",
    )
    missing = [
        key for key in required
        if not base.get(key) or not new.get(key)
    ]
    reasons = {}
    if missing:
        reasons["missing_comparable_fields"] = missing
    if new.get("remote_probe_ok") is False:
        reasons["remote_probe"] = new.get("remote_probe_error") or "FAILED"
    if new.get("status_error"):
        reasons["working_tree_probe"] = new.get("status_error")
    if not new.get("comparable"):
        reasons["snapshot_comparable"] = False
    return reasons

def main():
    reason = (sys.argv[1] if len(sys.argv) > 1 else "CHECKPOINT").strip().upper()
    is_disconnect = reason.startswith("DISCONNECT")
    is_reconnect = reason.startswith("RECONNECT")
    is_baseline_refresh = reason == "BASELINE_REFRESH"
    old_current = load_json(CURRENT)

    if is_disconnect or is_baseline_refresh:
        new = snapshot(reason, probe_remote=is_baseline_refresh)
        new["event"] = "BASELINE_REFRESH" if is_baseline_refresh else "DISCONNECT_CHECKPOINT"
        new["previous_proof_hash"] = old_current.get("proof_hash") if old_current else None
        new["comparison_against"] = None
        new["drift"] = {}
        new["reconciliation_required"] = False
        new["continuation_allowed"] = True
        new["resume_allowed"] = True
        new["mutation_allowed"] = False
        seal(new)
        atomic(BASELINE, new)
        atomic(CURRENT, new)
        append_history(new)
        print(json.dumps(new, separators=(",", ":")))
        return 0

    if is_reconnect:
        base = load_json(BASELINE)
        drift = {}
        pending = {}
        new = snapshot(reason, probe_remote=True)
        if base:
            drift = compare(base, new)
            pending = verification_pending(base, new)
        else:
            pending = {"disconnect_baseline": "MISSING"}
        if drift:
            new["event"] = "RECONNECT_CONTINUE_RECONCILIATION_REQUIRED"
        elif pending:
            new["event"] = "RECONNECT_CONTINUE_VERIFICATION_PENDING"
        else:
            new["event"] = "NO_DRIFT_RESUME"
        new["previous_proof_hash"] = old_current.get("proof_hash") if old_current else None
        new["comparison_against"] = base.get("proof_hash") if base else None
        new["drift"] = drift
        new["verification_pending"] = pending
        new["reconciliation_required"] = bool(drift)
        new["continuation_allowed"] = True
        new["resume_allowed"] = True
        new["mutation_allowed"] = bool(
            new.get("comparable")
            and not drift
            and not pending
            and new.get("working_tree_clean") is True
        )
        seal(new)
        atomic(CURRENT, new)
        append_history(new)
        print(json.dumps(new, separators=(",", ":")))
        return 0

    new = snapshot(reason, probe_remote=False)
    new["event"] = "CHECKPOINT_ONLY"
    new["previous_proof_hash"] = old_current.get("proof_hash") if old_current else None
    new["comparison_against"] = None
    new["drift"] = {}
    new["reconciliation_required"] = False
    new["continuation_allowed"] = True
    new["resume_allowed"] = True
    new["mutation_allowed"] = bool(new.get("comparable") and new.get("working_tree_clean") is True)
    seal(new)
    atomic(CURRENT, new)
    append_history(new)
    print(json.dumps(new, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
