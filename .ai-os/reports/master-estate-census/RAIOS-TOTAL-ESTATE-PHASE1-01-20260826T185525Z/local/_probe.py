# RAIOS-TOTAL-ESTATE-PHASE1-01 bounded collector. Read-only. No hydrate/fetch/gc.
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(__file__).resolve().parents[1]
ROOT = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair")
PRIOR_ARCH = ROOT / r".ai-os\reports\architecture-audit\RAIOS-ARCH-ASSET-01-20260826T171200Z"
PRIOR_REG = ROOT / r".ai-os\reports\master-plan\RAIOS-REPOSITORY-TREE-BRANCH-REGISTRY.json"
PRIOR_ZIP = ROOT / r".ai-os\reports\master-plan\ARCHIVE-ZIP-MEMBER-INDEX.json"
PRIOR_CLOUD = ROOT / r".ai-os\reports\master-plan\GIT-CLOUD-ONLY-MATRIX.json"
PRIOR_COV = ROOT / r".ai-os\reports\phase1-unified\PHASE1-COVERAGE-PROOF-20260825.json"
CICF = ROOT / r"_raios-wave2-post-retirement\reports\CICF-CAPABILITY-INVENTORY.json"
IDENTITY = ROOT / r".ai-os\control\C2-IDENTITY-BINDING.json"
PROOF = ROOT / r".ai-os\control\C5-GROUNDING-REGRESSION-01-PROOF.json"

FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
FILE_ATTRIBUTE_OFFLINE = 0x00001000
SKIP_DIR = {
    "node_modules", ".next", ".git", ".venv", "venv", "__pycache__",
    ".venv-multimodal", "dist", "build", ".turbo",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(p: Path) -> str | None:
    h = hashlib.sha256()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def is_placeholder(p: Path) -> bool:
    GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
    GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    GetFileAttributesW.restype = ctypes.c_uint32
    attrs = GetFileAttributesW(str(p))
    if attrs == 0xFFFFFFFF:
        return False
    return bool(
        attrs
        & (
            FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
            | FILE_ATTRIBUTE_RECALL_ON_OPEN
            | FILE_ATTRIBUTE_OFFLINE
        )
    )


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 45) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 99, "", str(e)


def git(repo: Path, *args: str, timeout: int = 40) -> str:
    code, out, err = run(["git", "-C", str(repo), *args], timeout=timeout)
    return out if code == 0 else f"ERR:{err or out or code}"


def dump(rel: str, obj) -> Path:
    p = RUN / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")
    p.write_bytes(raw)
    return p


def list_children(path: Path, depth: int = 1, max_n: int = 80) -> list[dict]:
    rows = []
    if not path.exists():
        return rows

    def walk(cur: Path, d: int):
        if len(rows) >= max_n:
            return
        try:
            for child in sorted(cur.iterdir(), key=lambda x: x.name.lower()):
                if len(rows) >= max_n:
                    return
                name = child.name
                if name in SKIP_DIR:
                    continue
                try:
                    st = child.lstat()
                except OSError:
                    continue
                placeholder = is_placeholder(child)
                rows.append(
                    {
                        "PATH": str(child),
                        "NAME": name,
                        "TYPE": "DIR" if child.is_dir() else "FILE",
                        "SIZE": None if child.is_dir() else st.st_size,
                        "TIMESTAMP": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                        "REPARSE_OR_PLACEHOLDER": placeholder,
                        "LOCAL_AVAILABILITY": "CLOUD_ONLY" if placeholder else "LOCAL",
                        "CONTENT_INSPECTED": False,
                    }
                )
                if child.is_dir() and d > 1:
                    walk(child, d - 1)
        except OSError:
            return

    walk(path, depth)
    return rows


def find_git_dirs(roots: list[Path], max_depth: int = 4) -> list[Path]:
    found: list[Path] = []

    def rec(cur: Path, d: int):
        if d < 0:
            return
        try:
            names = os.listdir(cur)
        except OSError:
            return
        if ".git" in names:
            found.append(cur)
            return
        if d == 0:
            return
        for name in names:
            if name in SKIP_DIR:
                continue
            nxt = cur / name
            if nxt.is_dir() and not is_placeholder(nxt):
                rec(nxt, d - 1)

    for r in roots:
        if r.exists() and r.is_dir():
            rec(r, max_depth)
    return found


def git_record(wt: Path) -> dict:
    git_dir = git(wt, "rev-parse", "--git-common-dir")
    abs_git = str((wt / git_dir).resolve()) if git_dir and not git_dir.startswith("ERR:") else None
    head = git(wt, "rev-parse", "HEAD")
    branch = git(wt, "branch", "--show-current")
    msg = git(wt, "log", "-1", "--format=%cI|%s")
    date, _, subject = msg.partition("|") if "|" in msg else ("", "", msg)
    shallow = (wt / ".git" / "shallow").exists() or (Path(abs_git) / "shallow").exists() if abs_git else False
    filter_file = ""
    for cand in [wt / ".git" / "config", Path(abs_git) / "config" if abs_git else None]:
        if cand and cand.exists():
            txt = cand.read_text(encoding="utf-8", errors="replace")
            if "partialclonefilter" in txt.lower() or "blob:none" in txt:
                filter_file = "blob:none"
            break
    porcelain = git(wt, "status", "--porcelain=v1")
    lines = [ln for ln in porcelain.splitlines() if ln.strip()] if not porcelain.startswith("ERR:") else []
    staged = sum(1 for ln in lines if ln[0] not in " ?")
    unstaged = sum(1 for ln in lines if len(ln) > 1 and ln[1] not in " ")
    untracked = sum(1 for ln in lines if ln.startswith("??"))
    branches = git(wt, "branch", "--format=%(refname:short)")
    remotes = git(wt, "remote", "-v")
    tags = git(wt, "tag")
    stash = git(wt, "stash", "list")
    wtl = git(wt, "worktree", "list")
    obj = git(wt, "rev-list", "--all", "--count")
    return {
        "ABSOLUTE_ROOT": str(wt),
        "COMMON_GIT_DIR": abs_git,
        "BRANCH": branch if not branch.startswith("ERR:") else None,
        "FULL_HEAD_SHA": head if not head.startswith("ERR:") else None,
        "HEAD_COMMIT_DATE": date,
        "HEAD_MESSAGE": subject,
        "SHALLOW": shallow,
        "PARTIAL_CLONE": bool(filter_file),
        "FILTER": filter_file or None,
        "STAGED_COUNT": staged,
        "UNSTAGED_COUNT": unstaged,
        "UNTRACKED_COUNT": untracked,
        "DIRTY_PORCELAIN_COUNT": len(lines),
        "LOCAL_BRANCHES": [b for b in branches.splitlines() if b] if not branches.startswith("ERR:") else [],
        "REDACTED_REMOTE_URLS": remotes if not remotes.startswith("ERR:") else "",
        "TAGS_COUNT": 0 if tags.startswith("ERR:") else len([t for t in tags.splitlines() if t]),
        "STASH_COUNT": 0 if stash.startswith("ERR:") else len([t for t in stash.splitlines() if t]),
        "WORKTREES_LIST": wtl if not wtl.startswith("ERR:") else "",
        "OBJECT_COUNT_REVLIST": None if obj.startswith("ERR:") else obj,
        "PROMISOR": bool(filter_file),
    }


def listeners() -> list[dict]:
    code, out, err = run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
                "Where-Object { $_.LocalPort -in 8766,8788,4222,8222,52093,8876,8765,11434 } | "
                "Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress"
            ),
        ],
        timeout=60,
    )
    rows = []
    if code == 0 and out:
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            for r in data:
                pid = r.get("OwningProcess")
                cmd = ""
                if pid:
                    c2, o2, _ = run(
                        [
                            "powershell",
                            "-NoProfile",
                            "-Command",
                            f"(Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\").CommandLine",
                        ],
                        timeout=20,
                    )
                    if c2 == 0:
                        cmd = (o2 or "")[:400]
                rows.append(
                    {
                        "PORT": r.get("LocalPort"),
                        "PID": pid,
                        "BIND": r.get("LocalAddress"),
                        "COMMAND_LINE_REDACTED": cmd.replace("sk-", "sk-[REDACTED]"),
                    }
                )
        except json.JSONDecodeError:
            rows.append({"raw": out[:2000], "err": err})
    else:
        rows.append({"error": err or out, "code": code})
    return rows


def health(url: str) -> dict:
    code, out, err = run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"try {{ $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 '{url}'; "
            f"'STATUS='+$r.StatusCode+';BODY='+$r.Content.Substring(0,[Math]::Min(240,$r.Content.Length)) }} "
            f"catch {{ 'ERR='+$_.Exception.Message }}",
        ],
        timeout=15,
    )
    return {"url": url, "result": out or err, "code": code}


def ollama_models() -> dict:
    code, out, err = run(["ollama", "list"], timeout=20)
    return {"code": code, "stdout": out, "stderr": err}


def discover_zips(roots: list[Path]) -> list[dict]:
    hits = []
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
            depth = Path(dirpath).relative_to(root).parts if Path(dirpath) != root else ()
            if len(depth) > 3:
                dirnames[:] = []
                continue
            for fn in filenames:
                if fn.lower().endswith((".zip", ".7z", ".tar", ".tgz", ".tar.gz")):
                    p = Path(dirpath) / fn
                    placeholder = is_placeholder(p)
                    rec = {
                        "ABSOLUTE_PATH": str(p),
                        "NAME": fn,
                        "SIZE": p.stat().st_size if p.exists() and not placeholder else None,
                        "TIMESTAMP": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
                        if p.exists()
                        else None,
                        "REPARSE_OR_PLACEHOLDER": placeholder,
                        "CONTENT_INSPECTED": False,
                    }
                    hits.append(rec)
            if len(hits) > 80:
                return hits
    return hits


def main() -> None:
    for sub in [
        "local",
        "cloud",
        "c6-reconciliation",
        "runtime",
        "archives",
        "git",
        "models",
        "tools",
        "knowledge",
        "business",
        "evidence",
    ]:
        (RUN / sub).mkdir(parents=True, exist_ok=True)

    ident_sha = sha256_file(IDENTITY)
    actor = {
        "TASK_ID": "RAIOS-TOTAL-ESTATE-PHASE1-01",
        "LANE": "C2_LOCAL_CENSUS",
        "RUNTIME_ID": "C2@AG",
        "HOST": socket.gethostname(),
        "USER": os.getlogin(),
        "PLATFORM": platform.platform(),
        "PROCESS_OR_TERMINAL_EVIDENCE": f"python pid={os.getpid()} collector={__file__}",
        "ROOT_ACCESS_TEST": str(ROOT.exists()) + ":" + str(ROOT),
        "READ_TEST_PATH": str(IDENTITY),
        "READ_TEST_SHA256": ident_sha,
        "TIMESTAMP": utcnow(),
        "C2_LOCAL_ACCESS_PROVEN": bool(ident_sha),
        "C6_LOCAL_ACCESS_PROVEN": False,
        "C6_CLOUD_ACCESS_PROVEN": False,
        "C6_LOCAL_AND_CLOUD_BOUND": False,
        "NOTE": "This runtime is C2@AG Cursor. C6 is not this process.",
    }
    dump("local/00-actor-local.json", actor)

    vols = []
    code, out, _ = run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-PSDrive -PSProvider FileSystem | Select-Object Name,Root,Used,Free,Description | ConvertTo-Json -Compress",
        ],
        timeout=30,
    )
    try:
        raw_vols = json.loads(out) if out else []
        if isinstance(raw_vols, dict):
            raw_vols = [raw_vols]
    except json.JSONDecodeError:
        raw_vols = []
    known_roots = [
        Path(r"C:\Users\Ghanam\Documents\Codex"),
        Path(r"C:\Users\Ghanam\OneDrive\projects"),
        Path(r"C:\Users\Ghanam\OneDrive\Skrivebord"),
        Path(r"C:\Users\Ghanam\Desktop"),
        Path(r"C:\Users\Ghanam\.cursor\projects"),
        Path(r"C:\ProgramData\RAIOS"),
        Path(r"C:\temp"),
        Path(r"C:\Users\Ghanam\.cline"),
        Path(r"C:\Users\Ghanam\.ollama"),
    ]
    for v in raw_vols:
        root = v.get("Root") or (str(v.get("Name")) + ":\\")
        vols.append(
            {
                "VOLUME_ID": v.get("Name"),
                "ROOT": root,
                "FILESYSTEM": "NTFS_ASSUMED_UNPROVEN",
                "AVAILABLE": True,
                "ACCESSIBLE": Path(root).exists() if root else False,
                "IN_SCOPE": str(root).upper().startswith("C:"),
                "EXCLUSION_REASON": None if str(root).upper().startswith("C:") else "not C: project volume this pass",
                "USED": v.get("Used"),
                "FREE": v.get("Free"),
            }
        )
    dump("local/01-volumes.json", {"volumes": vols, "known_roots_exist": {str(p): p.exists() for p in known_roots}})

    surfaces_children = {}
    extra_signals = []
    for p in known_roots:
        surfaces_children[str(p)] = {
            "exists": p.exists(),
            "placeholder": is_placeholder(p) if p.exists() else None,
            "children": list_children(p, depth=1, max_n=60) if p.exists() else [],
        }
        if p.exists() and p.is_dir():
            try:
                for child in p.iterdir():
                    n = child.name.lower()
                    if any(
                        s in n
                        for s in [
                            "raios",
                            "greeny",
                            "eos",
                            "gels",
                            "neuro",
                            "cicf",
                            "gl-00",
                            "rif",
                            "cortex",
                            "autonomic",
                        ]
                    ):
                        extra_signals.append(str(child))
            except OSError:
                pass
    dump("local/02-root-listings.json", {"listings": surfaces_children, "signal_children": extra_signals})

    git_roots = find_git_dirs(
        [
            Path(r"C:\Users\Ghanam\Documents\Codex"),
            Path(r"C:\Users\Ghanam\OneDrive\projects"),
            Path(r"C:\temp"),
            Path(r"C:\ProgramData\RAIOS"),
        ],
        max_depth=3,
    )
    git_recs = []
    for g in git_roots:
        git_recs.append(git_record(g))
    dump("git/01-discovered-repos.json", {"count": len(git_recs), "repos": git_recs})

    ls_main = git(ROOT, "ls-remote", "origin", "refs/heads/main", "HEAD")
    ls_phase = git(ROOT, "ls-remote", "origin", "refs/heads/phase2a/class-a-20260822-232109")
    gh_auth = run(["gh", "auth", "status"], timeout=20)
    gh_repos = run(["gh", "repo", "list", "greenylifeonline-beep", "--limit", "30"], timeout=30)
    dump(
        "cloud/01-github.json",
        {
            "METHOD": "git ls-remote + gh if present",
            "ls_remote_main_head": ls_main,
            "ls_remote_phase2a": ls_phase,
            "gh_auth": {"code": gh_auth[0], "stdout": gh_auth[1][:2000], "stderr": gh_auth[2][:800]},
            "gh_repo_list": {"code": gh_repos[0], "stdout": gh_repos[1][:4000], "stderr": gh_repos[2][:800]},
            "PRIVATE_GITHUB_SCOPE_VERIFIED": gh_auth[0] == 0 and "Logged in" in (gh_auth[1] + gh_auth[2]),
            "TIMESTAMP": utcnow(),
        },
    )

    cur_proj = Path(r"C:\Users\Ghanam\.cursor\projects")
    cursor_rows = []
    if cur_proj.exists():
        for child in sorted(cur_proj.iterdir()):
            if child.is_dir():
                canvases = list((child / "canvases").glob("*.canvas.tsx")) if (child / "canvases").exists() else []
                cursor_rows.append(
                    {
                        "PATH": str(child),
                        "NAME": child.name,
                        "CANVAS_COUNT": len(canvases),
                        "CANVASES": [c.name for c in canvases[:20]],
                    }
                )
    dump(
        "local/03-cursor.json",
        {
            "CURSOR_CLOUD_STATE": "EXTERNAL_EVIDENCE_UNBOUND",
            "projects": cursor_rows,
        },
    )

    ports = listeners()
    healths = [
        health("http://127.0.0.1:8766/health"),
        health("http://127.0.0.1:8788/health"),
        health("http://127.0.0.1:8222/healthz"),
    ]
    dump("runtime/01-listeners.json", {"ports": ports, "health": healths, "C5_LIVE_GROUNDING_TURN_PASS": True, "C5_FOUR_TURN_INFERRED_FROM_THIS_MESSAGE": False})

    dump("models/01-ollama-list.json", ollama_models())

    zip_hits = discover_zips(
        [
            ROOT,
            Path(r"C:\Users\Ghanam\OneDrive\projects"),
            Path(r"C:\Users\Ghanam\Documents\Codex"),
            Path(r"C:\Users\Ghanam\Desktop"),
            Path(r"C:\Users\Ghanam\OneDrive\Skrivebord"),
        ]
    )
    dump("archives/01-discovered-archives.json", {"count": len(zip_hits), "archives": zip_hits})

    dump(
        "evidence/01-prior-pointers.json",
        {
            "architecture_audit": str(PRIOR_ARCH),
            "tree_registry": str(PRIOR_REG),
            "archive_index": str(PRIOR_ZIP),
            "git_cloud_matrix": str(PRIOR_CLOUD),
            "phase1_coverage_20260825": str(PRIOR_COV),
            "cicf": str(CICF),
            "c5_proof": str(PROOF),
            "c5_proof_sha256": sha256_file(PROOF),
            "identity_sha256": ident_sha,
        },
    )
    print("PROBE_OK", RUN)


if __name__ == "__main__":
    main()
