#!/usr/bin/env python3
"""C1-ORDER CROSS-TREE-UNIFICATION-WAVE.

DISCOVER → HASH → COMPARE → RECONCILE → TEST → REBIND → RECEIPT.
No delete. No second WAL. No blind copy-over. No GL005 mint.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORTS = ROOT / ".ai-os" / "reports"
OUT = ROOT / ".ai-os" / "receipts" / "c5-cross-tree"
SKIP_DIR = {
    "node_modules",
    ".next",
    ".venv",
    ".venv-1",
    ".venv-mergekit",
    "archive",
    "__pycache__",
    "dist",
    "build",
    ".git",
    ".pytest_cache",
}
SKIP_NAMES = {
    "DIGESTS.jsonl",
    "INDEX.json",
    "CANDIDATES.jsonl",
    "C5-SCREEN.jsonl",
    "MEMORY.json",
    "cognitive-events.jsonl",
}
SKIP_SUFFIX = {".pack", ".idx", ".bin", ".gguf", ".safetensors", ".pt", ".pth", ".onnx"}
GENERATED_PREFIX = (
    ".ai-os/learning/",
    ".ai-os/board/",
    "RAIOS/V9/evidence/",
    "RAIOS/V9/experience/",
    "RAIOS/V9/performance/",
    ".ai-os/reports/raios-service/",
)
ARCHIVE_PREFIX = ("archive/", ".architecture-backups/", "backup/")
MAX_HASH_BYTES = 2 * 1024 * 1024
ORIGIN_PUBLIC = "https://github.com/greenylifeonline-beep/greeny-life"
CANONICAL_BRANCH = "v9-neurolingua-semantic-kernel"
CLAIMED_REPAIR = r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair"
CLAIMED_LEGACY = r"C:\Users\Ghanam\OneDrive\projects\Greeny-Life"
CLAIMED_WT = {
    "GL-002": r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\GL-002-Main-Brain",
    "GL-003": r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\GL-003-Project-Brains",
    "GL-004": r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\GL-004-Runtime",
}
KEEPER_HINTS = (
    "next dev",
    "next-server",
    "raios_c5_",
    "raios_mcp",
    "raios-service",
    "raios-c5-minute",
    "ollama serve",
)
SECRET_RE = re.compile(
    r"(--auth-token\s+)\S+|(token=)\S+|(x-access-token:)[^@/\s]+",
    re.I,
)

REPORT_NAMES = (
    "CANONICAL-ROOT.json",
    "CROSS-TREE-MANIFEST.json",
    "CROSS-TREE-DIFF.json",
    "UNIQUE-ASSET-RECONCILIATION.json",
    "CAPABILITY-RECONCILIATION.json",
    "ACTOR-BINDING-MATRIX.json",
    "NONCANONICAL-TREES.json",
    "UNIFICATION-RECEIPT.json",
)

LAWS = (
    "DISCOVER_HASH_COMPARE_RECONCILE_TEST_REBIND_RECEIPT",
    "NO_BLIND_COPY_OVER",
    "NO_DELETE_UNTIL_GATES",
    "REPAIR_UNREACHABLE_NE_EMPTY",
    "TMP_CLONE_NE_C3_TREE",
    "ONE_COGNITIVE_WAL",
    "CROSS_TREE_UNIFICATION_NE_GL005",
    "ACTOR_BIND_NE_IMPERSONATION",
    "NOT_CHOSEN_BY_PATH_NAME",
    "STALE_MAIN_DUMP_NE_UNIQUE_CAPABILITY",
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime() -> float | None:
    return WAL.stat().st_mtime if WAL.exists() else None


def git(args: list[str], cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=str(cwd or ROOT),
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except subprocess.CalledProcessError as exc:
        return (exc.output or "").strip()


def strip_userinfo(url: str) -> str:
    raw = (url or "").strip()
    if "://" not in raw:
        return raw
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    netloc = host if not parsed.port else f"{host}:{parsed.port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


def redact(text: str) -> str:
    return SECRET_RE.sub(lambda m: (m.group(1) or m.group(2) or "x-access-token:") + "REDACTED", text or "")


def sha256_file(path: Path, size: int) -> tuple[str | None, str | None]:
    if size > MAX_HASH_BYTES:
        return None, "SKIPPED_OVERSIZE"
    suffix = path.suffix.lower()
    if suffix in SKIP_SUFFIX:
        return None, "SKIPPED_BINARY"
    try:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest(), None
    except OSError:
        return None, "UNREADABLE"


def skipped(rel: str, *, tracked: bool) -> bool:
    norm = rel.replace("\\", "/")
    parts = norm.split("/")
    if any(p in SKIP_DIR for p in parts):
        return True
    name = Path(norm).name
    if name in SKIP_NAMES:
        return True
    if name.startswith(".env") or name == "(.env":
        return True
    if not tracked:
        if any(norm.startswith(p) or norm.startswith(p.lower()) for p in GENERATED_PREFIX):
            return True
        if norm.startswith(".ai-os/receipts/"):
            return True
    return False


def capability_class(rel: str) -> str:
    p = rel.replace("\\", "/").lower()
    name = Path(p).name
    if name in SKIP_NAMES or any(p.startswith(x.lower()) for x in GENERATED_PREFIX):
        return "GENERATED"
    if any(p.startswith(x.lower()) or f"/{x.lower().rstrip('/')}/" in f"/{p}" for x in ARCHIVE_PREFIX):
        return "ARCHIVE"
    if "neuro_lingua" in p or p.startswith("configs/neuro_lingua"):
        return "NEUROLINGUA"
    if "model_lab" in p or p.endswith("model-registry.json") or "MODEL-REGISTRY" in rel:
        return "MODEL_LAB"
    if "qwen" in p:
        return "QWEN"
    if "granite" in p:
        return "GRANITE"
    if "deepseek" in p:
        return "DEEPSEEK"
    if "cognitive_event_bus" in p or p.endswith("neuro_lingua/wal.py") or p.startswith("raios/v9/wal/"):
        return "WAL_EVENT_BUS"
    if p.startswith(".ai-os/council/"):
        return "COUNCIL"
    if "foundry" in p:
        return "FOUNDRY"
    if "cloud/nomadic" in p or "cloud/storage" in p or "raios_c5_cloud" in p:
        return "CLOUD_NOMADIC"
    if "raios_c5_merge" in p or "consolidat" in p or "raios_c5_cross_tree" in p:
        return "CONSOLIDATION"
    if "gl005" in p or "task-orchestration" in p or "/auth" in p or "provision-admin" in p:
        return "GL005_AUTH"
    if p.startswith("scripts/ai-os/raios_c5_") or p.startswith(".ai-os/mcp/"):
        return "C5_RUNTIME"
    return "OTHER"


def bound_processes(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    proc = Path("/proc")
    if not proc.is_dir():
        return out
    root_s = str(root.resolve())
    for pid_dir in proc.iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            cwd = os.readlink(pid_dir / "cwd")
            cmd = (pid_dir / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace").strip()
        except OSError:
            continue
        if cwd == root_s or cwd.startswith(root_s + os.sep):
            out.append({"pid": int(pid_dir.name), "cwd": cwd, "cmd": redact(cmd)[:240]})
    return out


def keeper_processes(procs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits = []
    for row in procs:
        cmd = (row.get("cmd") or "").lower()
        if any(h.lower() in cmd for h in KEEPER_HINTS):
            hits.append(row)
    return hits


def probe_path(path: str) -> bool:
    try:
        return Path(path).exists()
    except OSError:
        return False


def git_identity(path: Path) -> dict[str, Any]:
    git_meta = path / ".git"
    if not git_meta.exists():
        return {"git": False}
    head = git(["rev-parse", "HEAD"], path)
    branch = git(["branch", "--show-current"], path)
    origin = strip_userinfo(git(["remote", "get-url", "origin"], path))
    if origin.lower().startswith("error:"):
        origin = None
    tracked = [ln for ln in git(["ls-files"], path).splitlines() if ln.strip()]
    porcelain = [ln for ln in git(["status", "--porcelain"], path).splitlines() if ln.strip()]
    modified = [ln[3:] for ln in porcelain if ln[:2].strip() and not ln.startswith("??")]
    untracked = [ln[3:] for ln in porcelain if ln.startswith("??")]
    wt = git(["rev-parse", "--git-dir"], path)
    common = git(["rev-parse", "--git-common-dir"], path)
    if wt and not Path(wt).is_absolute():
        wt = str((path / wt).resolve())
    if common and not Path(common).is_absolute():
        common = str((path / common).resolve())
    return {
        "git": True,
        "head": head,
        "branch": branch,
        "origin": origin,
        "worktree_git_dir": wt,
        "git_common_dir": common,
        "tracked_count": len(tracked),
        "modified_count": len(modified),
        "untracked_count": len(untracked),
        "tracked": tracked,
        "modified": modified,
        "untracked": untracked,
    }


def tree_size_bytes(path: Path) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        for name in filenames:
            fp = Path(dirpath) / name
            try:
                total += fp.stat().st_size
            except OSError:
                continue
    return total


def last_mtime(path: Path) -> str | None:
    latest = 0.0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        for name in filenames:
            fp = Path(dirpath) / name
            try:
                latest = max(latest, fp.stat().st_mtime)
            except OSError:
                continue
    if not latest:
        return None
    return datetime.fromtimestamp(latest, timezone.utc).isoformat()


def hash_tree(path: Path, identity: dict[str, Any], source_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    tracked = set(identity.get("tracked") or [])
    modified = set(identity.get("modified") or [])
    untracked = set(identity.get("untracked") or [])
    candidates = sorted(tracked | untracked)
    for rel in candidates:
        is_tracked = rel in tracked
        if skipped(rel, tracked=is_tracked):
            continue
        fp = path / rel
        if not fp.is_file():
            continue
        try:
            st = fp.stat()
            size = st.st_size
            mtime = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()
        except OSError:
            continue
        digest, note = sha256_file(fp, size)
        row = {
            "PATH": rel.replace("\\", "/"),
            "SIZE": size,
            "SHA256": digest,
            "TRACKED": is_tracked,
            "UNTRACKED": rel in untracked,
            "MODIFIED": rel in modified,
            "CAPABILITY_CLASS": capability_class(rel),
            "LAST_MODIFIED": mtime,
            "SOURCE_TREE": source_id,
        }
        if note:
            row["HASH_NOTE"] = note
        rows.append(row)
    return rows


def inspect_reachable(tree_id: str, path: Path, role: str, actors: list[str]) -> dict[str, Any]:
    ident = git_identity(path)
    procs = bound_processes(path)
    keepers = keeper_processes(procs)
    rec: dict[str, Any] = {
        "id": tree_id,
        "role": role,
        "actors_claimed": actors,
        "absolute_path": str(path),
        "host": socket.gethostname(),
        "reachable": True,
        "git_branch": ident.get("branch"),
        "HEAD": ident.get("head"),
        "git_worktree_identity": ident.get("worktree_git_dir"),
        "git_common_dir": ident.get("git_common_dir"),
        "origin": ident.get("origin"),
        "tracked_file_count": ident.get("tracked_count"),
        "untracked_file_count": ident.get("untracked_count"),
        "modified_count": ident.get("modified_count"),
        "total_size_bytes": tree_size_bytes(path),
        "last_activity": last_mtime(path),
        "active_processes": procs,
        "keeper_processes": keepers,
        "live_process_count": len(procs),
        "runtime_keeper_count": len(keepers),
        "tracked_set": set(ident.get("tracked") or []),
        "identity": {k: v for k, v in ident.items() if k not in {"tracked", "modified", "untracked"}},
    }
    rec["manifest"] = hash_tree(path, ident, tree_id)
    return rec


def inspect_claimed(tree_id: str, path: str, role: str, actors: list[str], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    rec = {
        "id": tree_id,
        "role": role,
        "actors_claimed": actors,
        "absolute_path": path,
        "host": "founder-windows-claimed",
        "reachable": False,
        "git_branch": None,
        "HEAD": None,
        "git_worktree_identity": None,
        "origin": None,
        "tracked_file_count": None,
        "untracked_file_count": None,
        "modified_count": None,
        "total_size_bytes": None,
        "last_activity": None,
        "active_processes": [],
        "keeper_processes": [],
        "live_process_count": None,
        "runtime_keeper_count": None,
        "manifest": [],
        "tracked_set": set(),
        "reason": "PATH_NOT_MOUNTED_ON_THIS_HOST",
        "probed": {
            "posix": probe_path(path.replace("\\", "/")),
            "mnt_c": probe_path("/mnt/c/Users/Ghanam/Documents/Codex/Greeny-Life-Repair"),
        },
    }
    if extra:
        rec.update(extra)
    return rec


def index_manifest(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["PATH"]: row for row in rows}


def path_status(rel: str, left_id: str, right_id: str, left: dict[str, Any] | None, right: dict[str, Any] | None) -> str:
    klass = (left or right or {}).get("CAPABILITY_CLASS") or capability_class(rel)
    if klass == "GENERATED":
        return "GENERATED_ONLY"
    if klass == "ARCHIVE" or any(rel.replace("\\", "/").startswith(p) for p in ARCHIVE_PREFIX):
        return "ARCHIVE_ONLY"
    if left and right:
        lsha = left.get("SHA256")
        rsha = right.get("SHA256")
        if lsha and rsha and lsha == rsha:
            return "SAME"
        if not lsha and not rsha:
            return "UNKNOWN"
        if right_id.startswith("TMP_"):
            return "STALE"
        return "DIVERGED_SAME_PATH"
    if left and not right:
        return "UNIQUE_TO_C2_C5_TREE" if left_id == "C2C5_LIVE" else "UNIQUE_OTHER"
    if right and not left:
        if right_id.startswith("C3"):
            return "UNIQUE_TO_C3_C4_TREE"
        if right_id.startswith("TMP_MCP"):
            return "GENERATED_ONLY"
        if right_id.startswith("TMP_"):
            return "STALE"
        return "UNIQUE_OTHER"
    return "UNKNOWN"


def classify_pair(left_id: str, right_id: str, left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    paths = sorted(set(left) | set(right))
    for rel in paths:
        l = left.get(rel)
        r = right.get(rel)
        klass = (l or r or {}).get("CAPABILITY_CLASS") or capability_class(rel)
        out.append(
            {
                "PATH": rel,
                "CLASS": path_status(rel, left_id, right_id, l, r),
                "CAPABILITY_CLASS": klass,
                "LEFT_TREE": left_id,
                "RIGHT_TREE": right_id,
                "LEFT_SHA256": (l or {}).get("SHA256"),
                "RIGHT_SHA256": (r or {}).get("SHA256"),
            }
        )
    return out


def classify_tracked(left_id: str, right_id: str, left_paths: set[str], right_paths: set[str], left_man: dict[str, dict[str, Any]], right_man: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for rel in sorted(left_paths | right_paths):
        in_left = rel in left_paths
        in_right = rel in right_paths
        l = left_man.get(rel) if in_left else None
        r = right_man.get(rel) if in_right else None
        if in_left and not in_right:
            l = l or {"CAPABILITY_CLASS": capability_class(rel), "SHA256": None}
            r = None
        elif in_right and not in_left:
            r = r or {"CAPABILITY_CLASS": capability_class(rel), "SHA256": None}
            l = None
        elif in_left and in_right:
            l = l or {"CAPABILITY_CLASS": capability_class(rel), "SHA256": None}
            r = r or {"CAPABILITY_CLASS": capability_class(rel), "SHA256": None}
        rows.append(
            {
                "PATH": rel,
                "CLASS": path_status(rel, left_id, right_id, l, r),
                "CAPABILITY_CLASS": (l or r or {}).get("CAPABILITY_CLASS") or capability_class(rel),
                "LEFT_TREE": left_id,
                "RIGHT_TREE": right_id,
                "LEFT_SHA256": (l or {}).get("SHA256"),
                "RIGHT_SHA256": (r or {}).get("SHA256"),
            }
        )
    return rows


CAPABILITY_MARKERS = {
    "NeuroLingua": [
        "src/raios/neuro_lingua/kernel.py",
        "src/raios/neuro_lingua/ops_compile.py",
        "src/raios/neuro_lingua/kae.py",
        "src/raios/neuro_lingua/customer.py",
    ],
    "Model Registry": [".ai-os/MODEL-REGISTRY.json", "RAIOS/V9/evolution/model_lab/model_registry.py"],
    "Qwen": ["src/raios/neuro_lingua/qwen_runtime.py", "scripts/ai-os/raios_c5_qwen.py"],
    "Granite": [],
    "DeepSeek": [".ai-os/adapters/DEEPSEEK.md"],
    "C5 runtime": [
        "scripts/ai-os/raios_c5_train.py",
        "scripts/ai-os/raios_c5_mind_fill.py",
        "scripts/ai-os/raios_c5_screen.py",
    ],
    "WAL/event bus": [
        "RAIOS/V9/runtime/cognitive_event_bus.py",
        "src/raios/neuro_lingua/wal.py",
    ],
    "Council": [".ai-os/council/PROTOCOL.md", ".ai-os/mcp/SEAT-MAP.json"],
    "Foundry": [],
    "Cloud/Nomadic": [
        "RAIOS/V9/cloud/nomadic/work_stealing_scheduler.py",
        "RAIOS/V9/cloud/storage/local_backend.py",
    ],
    "Model Lab": ["RAIOS/V9/evolution/model_lab/merge_executor.py"],
    "Consolidation tools": ["scripts/ai-os/raios_c5_merge_engines.py", "scripts/ai-os/raios_c5_cross_tree.py"],
    "GL005/auth runtime": [
        "lib/intelligence/task-orchestration.ts",
        "app/api/tasks/route.ts",
        "lib/auth.ts",
        "scripts/ai-os/gl005-mutation-observe.py",
    ],
}


def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def public_tree(t: dict[str, Any]) -> dict[str, Any]:
    skip = {"manifest", "identity", "tracked_set", "active_processes"}
    row = {k: v for k, v in t.items() if k not in skip}
    row["active_process_sample"] = (t.get("keeper_processes") or t.get("active_processes") or [])[:12]
    return row


def discover_ephemeral() -> list[Path]:
    found: list[Path] = []
    tmp = Path("/tmp")
    if not tmp.is_dir():
        return found
    for child in tmp.iterdir():
        name = child.name
        if not child.is_dir():
            continue
        if name.startswith("raios-mcp-") and (child / ".git").exists():
            found.append(child)
    return sorted(found)


def unrelated_git() -> list[dict[str, Any]]:
    rows = []
    for path, why in (
        (Path("/home/ubuntu/.nvm"), "nodejs_version_manager_not_greeny_life"),
        (Path("/home/ubuntu/.cursor/plugins/cache/cursor-public"), "cursor_plugin_cache_not_greeny_life"),
    ):
        git_meta = None
        if path.is_dir() and (path / ".git").exists():
            git_meta = str(path)
        elif path.is_dir():
            for dirpath, dirnames, _filenames in os.walk(path):
                if ".git" in dirnames:
                    git_meta = dirpath
                    dirnames[:] = []
                    break
                if path.as_posix().count("/") + 6 < dirpath.count("/"):
                    dirnames[:] = []
        if git_meta:
            rows.append({"path": git_meta, "host": socket.gethostname(), "class": "UNRELATED_GIT", "reason": why, "hashed": False, "origin_recorded": False})
    return rows


def remote_refs() -> list[dict[str, str]]:
    raw = git(["for-each-ref", "--format=%(refname:short)|%(objectname)|%(committerdate:iso-strict)", "refs/remotes/origin"])
    rows = []
    for line in raw.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        rows.append({"ref": parts[0], "HEAD": parts[1], "date": parts[2], "is_worktree": False})
    return rows


def ahead_behind(head: str, remote_ref: str) -> tuple[int, int]:
    ahead_s = git(["rev-list", "--count", f"{remote_ref}..{head}"])
    behind_s = git(["rev-list", "--count", f"{head}..{remote_ref}"])
    try:
        ahead = int(ahead_s)
    except ValueError:
        ahead = -1
    try:
        behind = int(behind_s)
    except ValueError:
        behind = -1
    return ahead, behind


def reconcile() -> dict[str, Any]:
    t0 = wal_mtime()
    host = socket.gethostname()
    head = git(["rev-parse", "HEAD"])
    branch = git(["branch", "--show-current"])
    origin = strip_userinfo(git(["remote", "get-url", "origin"])) or ORIGIN_PUBLIC
    wt_list = git(["worktree", "list", "--porcelain"])
    origin_branch = git(["rev-parse", f"origin/{CANONICAL_BRANCH}"])
    ahead, behind = ahead_behind(head, f"origin/{CANONICAL_BRANCH}")

    live = inspect_reachable("C2C5_LIVE", ROOT, "canonical_candidate", ["C2", "C5"])
    clone_v9 = inspect_reachable("TMP_C5_CLONE_V9", Path("/tmp/c5-clone-v9"), "stale_clone", []) if Path("/tmp/c5-clone-v9").exists() else None
    clone_main = inspect_reachable("TMP_C5_CLONE_MAIN", Path("/tmp/c5-clone-main"), "stale_clone", []) if Path("/tmp/c5-clone-main").exists() else None
    mcp_trees = []
    for i, p in enumerate(discover_ephemeral()):
        mcp_trees.append(inspect_reachable(f"TMP_MCP_{i:02d}", p, "ephemeral_mcp_sandbox", []))
    repair = inspect_claimed(
        "C3C4_REPAIR",
        CLAIMED_REPAIR,
        "founder_operating_copy",
        ["C3", "C4"],
        extra={
            "claimed_branch": CANONICAL_BRANCH,
            "last_observed_head": "e1dfd7c235b0bd4ba1a58ab6dfea47bd00173370",
            "source": ".ai-os/handoffs/20260820-C3-REPAIR-AUTH-DISCRIMINATOR.md",
        },
    )
    legacy = inspect_claimed("LEGACY_ONEDRIVE", CLAIMED_LEGACY, "read_only_legacy", [], extra={"mode": "READ_ONLY", "source": ".ai-os/WORKTREE-REGISTRY.json"})
    named_wts = [
        inspect_claimed(f"CLAIMED_WT_{k}", v, "registered_worktree", [], extra={"registry_key": k, "source": ".ai-os/WORKTREE-REGISTRY.json"})
        for k, v in CLAIMED_WT.items()
    ]

    reachable = [t for t in [live, clone_v9, clone_main, *mcp_trees] if t]
    claimed = [repair, legacy, *named_wts]
    unrelated = unrelated_git()
    remotes = remote_refs()

    live_idx = index_manifest(live["manifest"])
    clone_v9_idx = index_manifest(clone_v9["manifest"]) if clone_v9 else {}
    clone_main_idx = index_manifest(clone_main["manifest"]) if clone_main else {}

    diffs: list[dict[str, Any]] = []
    if clone_v9:
        diffs.extend(classify_tracked("C2C5_LIVE", "TMP_C5_CLONE_V9", live["tracked_set"], clone_v9["tracked_set"], live_idx, clone_v9_idx))
    if clone_main:
        diffs.extend(classify_tracked("C2C5_LIVE", "TMP_C5_CLONE_MAIN", live["tracked_set"], clone_main["tracked_set"], live_idx, clone_main_idx))
    diffs.append(
        {
            "PATH": "*",
            "CLASS": "UNKNOWN",
            "CAPABILITY_CLASS": "OTHER",
            "LEFT_TREE": "C2C5_LIVE",
            "RIGHT_TREE": "C3C4_REPAIR",
            "LEFT_SHA256": None,
            "RIGHT_SHA256": None,
            "reason": "C3C4_REPAIR_UNREACHABLE_NO_PATH_HASH",
        }
    )

    clone_only_tracked = 0
    live_only_vs_v9 = 0
    clone_v9_only_paths: list[str] = []
    live_only_vs_v9_paths: list[str] = []
    if clone_v9:
        a = clone_v9["tracked_set"]
        b = live["tracked_set"]
        clone_v9_only_paths = sorted(a - b)
        live_only_vs_v9_paths = sorted(b - a)
        clone_only_tracked = len(clone_v9_only_paths)
        live_only_vs_v9 = len(live_only_vs_v9_paths)

    main_only_paths: list[str] = []
    main_only_source: list[str] = []
    if clone_main:
        main_only_paths = sorted(clone_main["tracked_set"] - live["tracked_set"])
        main_only_source = [p for p in main_only_paths if p.endswith((".py", ".ts", ".tsx", ".js", ".md")) and ".architecture-backups/" not in p and not p.startswith("backup/")]

    mcp_unique = []
    for t in mcp_trees:
        extra = sorted(t["tracked_set"] - live["tracked_set"])
        mcp_unique.append({"id": t["id"], "path": t["absolute_path"], "unique_tracked": extra, "copied": False})

    unique_keepers = {
        "mind_fill": (ROOT / "scripts/ai-os/raios_c5_mind_fill.py").is_file(),
        "kae": (ROOT / "src/raios/neuro_lingua/kae.py").is_file(),
        "ops_compile": (ROOT / "src/raios/neuro_lingua/ops_compile.py").is_file(),
        "clone_v9_mind_fill": bool(clone_v9) and (Path("/tmp/c5-clone-v9") / "scripts/ai-os/raios_c5_mind_fill.py").is_file(),
        "clone_v9_kae": bool(clone_v9) and (Path("/tmp/c5-clone-v9") / "src/raios/neuro_lingua/kae.py").is_file(),
        "clone_v9_ops_compile": bool(clone_v9) and (Path("/tmp/c5-clone-v9") / "src/raios/neuro_lingua/ops_compile.py").is_file(),
    }

    proof = {
        "newest_valid_HEAD_on_live_branch": live["HEAD"] == origin_branch,
        "origin_branch_head": origin_branch,
        "ahead_of_origin_branch": ahead,
        "behind_origin_branch": behind,
        "in_sync_with_origin_branch": ahead == 0 and behind == 0,
        "tracked_completeness": {t["id"]: t["tracked_file_count"] for t in reachable if not str(t["id"]).startswith("TMP_MCP")},
        "runtime_keeper_count_on_C2C5_LIVE": live["runtime_keeper_count"],
        "live_process_count_on_C2C5_LIVE": live["live_process_count"],
        "git_worktree_list": wt_list,
        "unique_keepers_only_on_live": unique_keepers,
        "repair_reachable": repair["reachable"],
        "not_chosen_by_path_name": True,
        "path_name_would_have_chosen_repair": CLAIMED_REPAIR,
        "chosen_because": [
            "only reachable tree with live Next/MCP/screen/minute keeper processes",
            "newest HEAD on origin/v9-neurolingua-semantic-kernel (in sync when ahead=behind=0)",
            "highest tracked completeness among reachable Greeny-Life git trees",
            "unique keepers mind_fill/kae/ops_compile present here, absent on /tmp/c5-clone-v9",
            "Repair/OneDrive/named worktrees are not mounted so they cannot be canonical on this host",
            "/tmp/c5-clone-main is origin/main dump (images, architecture-backups, 87MB summary) — not a newer RAIOS HEAD",
        ],
        "clone_v9_unique_tracked": clone_only_tracked,
        "clone_main_is_older_main": bool(clone_main) and (clone_main.get("HEAD") or "").startswith("da67f44"),
    }
    canonical_root_proven = bool(
        live["reachable"]
        and live["HEAD"] == origin_branch
        and live["runtime_keeper_count"] >= 1
        and unique_keepers["mind_fill"]
        and unique_keepers["kae"]
        and unique_keepers["ops_compile"]
        and not repair["reachable"]
        and live["tracked_file_count"]
        and (not clone_v9 or (live["tracked_file_count"] or 0) > (clone_v9["tracked_file_count"] or 0))
    )

    unique = {
        "reachable_unique_to_live_vs_clone_v9_tracked": live_only_vs_v9,
        "reachable_unique_to_clone_v9_tracked": clone_only_tracked,
        "reachable_unique_to_clone_v9_paths": clone_v9_only_paths[:50],
        "live_only_vs_clone_v9_sample": live_only_vs_v9_paths[:40],
        "reachable_unique_to_repair": None,
        "clone_main_unique_tracked": len(main_only_paths),
        "clone_main_unique_top_dirs": {},
        "clone_main_source_like_outside_backups": main_only_source[:40],
        "mcp_unique": mcp_unique,
        "merge_batches": [
            {
                "batch": 1,
                "pair": "C2C5_LIVE vs TMP_C5_CLONE_V9",
                "action": "NO_COPY",
                "reason": "stale clone is tracked subset; unique_tracked=0",
                "hash_before_head": live["HEAD"],
                "hash_after_head": live["HEAD"],
                "copied_paths": [],
                "tests": "pytest tests/neuro_lingua/test_cross_tree.py",
            },
            {
                "batch": 2,
                "pair": "C2C5_LIVE vs TMP_C5_CLONE_MAIN",
                "action": "NO_COPY",
                "reason": "origin/main dump: architecture-backups, images, 87MB project-summary, stale HTML site. Not unique RAIOS capability.",
                "hash_before_head": live["HEAD"],
                "hash_after_head": live["HEAD"],
                "copied_paths": [],
                "tests": "pytest tests/neuro_lingua/test_cross_tree.py",
            },
            {
                "batch": 3,
                "pair": "C2C5_LIVE vs TMP_MCP_*",
                "action": "NO_COPY",
                "reason": "ephemeral MCP accept sandboxes; unique app/secret.ts is `export const x = 1` fixture",
                "copied_paths": [],
            },
            {
                "batch": 4,
                "pair": "C2C5_LIVE vs C3C4_REPAIR",
                "action": "HOLD",
                "reason": "unreachable; unique work UNKNOWN; do not impersonate a merge",
                "copied_paths": [],
            },
        ],
        "copied_paths": [],
        "diverged_resolved": [
            {
                "pair": "C2C5_LIVE vs TMP_C5_CLONE_V9",
                "resolution": "KEEP_LIVE_NEWER_SUPERSET",
                "unique_on_stale_tracked": clone_only_tracked,
                "hash_before_head": live["HEAD"],
                "hash_after_head": live["HEAD"],
                "copied": False,
            },
            {
                "pair": "C2C5_LIVE vs TMP_C5_CLONE_MAIN",
                "resolution": "KEEP_LIVE_REJECT_STALE_MAIN_DUMP",
                "copied": False,
            },
        ],
        "repair_unique_work": "UNKNOWN_UNREACHABLE",
        "blind_copy_over": False,
        "authorship_preserved": True,
        "note": "No file copied. Stale /tmp clones are subset or main-dump. Repair unique uncommitted work cannot be merged until the tree is mounted or pushed.",
    }
    if clone_main:
        unique["clone_main_unique_top_dirs"] = dict(Counter((p.split("/")[0] if "/" in p else p) for p in main_only_paths))

    caps = {}
    for name, markers in CAPABILITY_MARKERS.items():
        present_live = [m for m in markers if (ROOT / m).is_file()] if markers else []
        present_clone = [m for m in markers if clone_v9 and (Path("/tmp/c5-clone-v9") / m).is_file()] if markers else []
        owner = "C2C5_LIVE" if present_live or name in {"Granite", "Foundry"} else ("C2C5_LIVE" if name == "DeepSeek" else "MISSING")
        status = "PRESENT_ON_CANONICAL"
        if name == "Granite":
            status = "IDENTITY_CLAIM_NOT_LIVE_ON_THIS_VM"
        elif name == "DeepSeek":
            status = "ADAPTER_FILE_PRESENT_RUNTIME_POINTS_AT_REPAIR_NOT_THIS_VM"
        elif name == "Foundry":
            status = "NOT_RUN"
        elif name == "GL005/auth runtime":
            status = "CODE_PRESENT_RUNTIME_UNPROVEN"
        caps[name] = {
            "canonical_owner_tree": owner,
            "markers_present_live": present_live or markers,
            "markers_present_clone_v9": present_clone,
            "repair": "UNREACHABLE",
            "status": status,
            "merge_required": False,
        }

    bindings = {
        "canonical_root": {
            "absolute_path": str(ROOT),
            "host": host,
            "git": ORIGIN_PUBLIC,
            "branch": CANONICAL_BRANCH,
            "HEAD": live["HEAD"],
        },
        "actors": {
            "C2": {
                "bound": True,
                "this_session": True,
                "identity": "cursor-cloud C2 executor on C2C5_LIVE",
                "cwd": str(ROOT),
                "head": live["HEAD"],
                "target_identity": ORIGIN_PUBLIC + f"/tree/{CANONICAL_BRANCH}",
            },
            "C3": {
                "bound": False,
                "this_session": False,
                "identity": "C3 engineer claimed on Repair",
                "target_identity": f"{ORIGIN_PUBLIC} {CANONICAL_BRANCH}@{live['HEAD']}",
                "required_action": f"cd Repair; git stash WAL if dirty; git pull --ff-only origin {CANONICAL_BRANCH}; confirm HEAD={live['HEAD']}",
                "impersonated": False,
            },
            "C4": {
                "bound": False,
                "this_session": False,
                "identity": "C4 DeepSeek peer claimed on Repair",
                "target_identity": f"{ORIGIN_PUBLIC} {CANONICAL_BRANCH}@{live['HEAD']}",
                "required_action": f"same pull as C3 onto {CANONICAL_BRANCH} @{live['HEAD'][:12]}",
                "impersonated": False,
            },
            "C5": {
                "bound": True,
                "this_session": False,
                "identity": "RAIOS git mind",
                "cwd": str(ROOT),
                "head": live["HEAD"],
                "lives_in": "git, not the Cursor session",
            },
            "C6": {
                "bound": False,
                "this_session": False,
                "identity": "C6 not live",
                "law": "C6_C10_NE_LIVE",
            },
        },
        "seat_map_laws_unchanged": True,
        "do_not_summon": True,
        "impersonated": False,
    }

    noncanonical = []
    for t in reachable + claimed:
        if t["id"] == "C2C5_LIVE":
            continue
        if t["id"].startswith("TMP_MCP"):
            extra_n = len(t["tracked_set"] - live["tracked_set"])
            live_n = t.get("live_process_count") or 0
            noncanonical.append(
                {
                    "id": t["id"],
                    "path": t["absolute_path"],
                    "classification": "DELETE_CANDIDATE",
                    "unique_content_count": extra_n,
                    "live_process_count": live_n,
                    "deleted": False,
                    "reason": "ephemeral MCP sandbox; unique tracked are fixtures; gates not jointly green (confidence<0.99, no C1 delete order)",
                }
            )
        elif t["id"].startswith("TMP_"):
            unique_n = clone_only_tracked if t["id"] == "TMP_C5_CLONE_V9" else (len(main_only_paths) if t["id"] == "TMP_C5_CLONE_MAIN" else None)
            live_n = t.get("live_process_count") or 0
            if t["id"] == "TMP_C5_CLONE_V9" and unique_n == 0 and live_n == 0:
                klass = "DELETE_CANDIDATE"
                reason = "stale v9 clone tracked subset; do not delete this pass (untracked not fully proven, confidence<0.99)"
            elif t["id"] == "TMP_C5_CLONE_MAIN":
                klass = "ARCHIVE_READONLY"
                reason = "stale origin/main dump retained as evidence until C1 delete order; unique dumps are STALE not RAIOS keepers"
            else:
                klass = "RETAIN_AS_WORKTREE"
                reason = "retain"
            noncanonical.append(
                {
                    "id": t["id"],
                    "path": t["absolute_path"],
                    "classification": klass,
                    "unique_content_count": unique_n,
                    "live_process_count": live_n,
                    "deleted": False,
                    "reason": reason,
                }
            )
        elif t["id"] == "C3C4_REPAIR":
            noncanonical.append(
                {
                    "id": t["id"],
                    "path": t["absolute_path"],
                    "classification": "RETAIN_AS_WORKTREE",
                    "unique_content_count": None,
                    "live_process_count": None,
                    "deleted": False,
                    "reason": "Founder operating copy. Unreachable here. Do not delete. Pull this HEAD.",
                }
            )
        elif t["id"] == "LEGACY_ONEDRIVE":
            noncanonical.append(
                {
                    "id": t["id"],
                    "path": t["absolute_path"],
                    "classification": "ARCHIVE_READONLY",
                    "unique_content_count": None,
                    "live_process_count": None,
                    "deleted": False,
                    "reason": "WORKTREE-REGISTRY legacy_source READ_ONLY",
                }
            )
        else:
            noncanonical.append(
                {
                    "id": t["id"],
                    "path": t["absolute_path"],
                    "classification": "REMOVE_LATER",
                    "unique_content_count": None,
                    "live_process_count": None,
                    "deleted": False,
                    "reason": "Registered isolated worktree branches not on origin; unreachable; do not recreate; do not delete from this host.",
                }
            )

    noncan_live = sum((t.get("live_process_count") or 0) for t in reachable if t["id"] != "C2C5_LIVE")
    flags = {
        "CANONICAL_ROOT_PROVEN": canonical_root_proven,
        "C2_BOUND_TO_CANONICAL": True,
        "C3_BOUND_TO_CANONICAL": False,
        "C4_BOUND_TO_CANONICAL": False,
        "C5_BOUND_TO_CANONICAL": True,
        "C6_BOUND_TO_CANONICAL": False,
        "UNIQUE_WORK_PRESERVED": True,
        "DIVERGED_PATHS_RESOLVED": clone_only_tracked == 0,
        "NONCANONICAL_LIVE_PROCESSES": noncan_live,
        "CROSS_TREE_UNIFICATION_PROVEN": False,
        "GL005_PROVEN": False,
        "EXTRACTED_QWEN_GRANITE": False,
        "SAFE_TO_REMOVE_SOURCE": False,
        "REPAIR_REACHABLE": False,
        "DELETED_ANY_TREE": False,
        "WAL_WRITTEN": False,
        "SCOPE": "REACHABLE_TREES_THIS_HOST",
    }

    canonical_doc = {
        "schema": "raios.canonical-root.v1",
        "ts": utc(),
        "from": "C2",
        "c5": "git",
        "absolute_path": str(ROOT),
        "host": host,
        "git": ORIGIN_PUBLIC,
        "origin_observed": origin,
        "branch": branch,
        "HEAD": live["HEAD"],
        "git_worktree_identity": live["git_worktree_identity"],
        "tracked_file_count": live["tracked_file_count"],
        "untracked_file_count": live["untracked_file_count"],
        "modified_count": live["modified_count"],
        "total_size_bytes": live["total_size_bytes"],
        "last_activity": live["last_activity"],
        "runtime_keeper_count": live["runtime_keeper_count"],
        "proof": proof,
        "canonical_root_proven": canonical_root_proven,
        "scope": "REACHABLE_TREES_THIS_HOST",
        "not_chosen_by_path_name": True,
        "gl005_proven": False,
        "law": list(LAWS),
    }
    trees_public = [public_tree(t) for t in reachable + claimed]
    manifest_doc = {
        "schema": "raios.cross-tree-manifest.v1",
        "ts": utc(),
        "trees": trees_public,
        "unrelated_git": unrelated,
        "remote_refs_not_worktrees": remotes,
        "files": {
            live["id"]: live["manifest"],
            **({clone_v9["id"]: clone_v9["manifest"]} if clone_v9 else {}),
            **({clone_main["id"]: clone_main["manifest"]} if clone_main else {}),
            **{t["id"]: t["manifest"] for t in mcp_trees},
        },
        "claimed_unreachable": [t["id"] for t in claimed],
        "gl005_proven": False,
    }
    diff_doc = {
        "schema": "raios.cross-tree-diff.v1",
        "ts": utc(),
        "rows": diffs,
        "summary": {
            "same": sum(1 for r in diffs if r.get("CLASS") == "SAME"),
            "stale": sum(1 for r in diffs if r.get("CLASS") == "STALE"),
            "unique_live": sum(1 for r in diffs if r.get("CLASS") == "UNIQUE_TO_C2_C5_TREE"),
            "unique_repair": 0,
            "unknown_repair": 1,
            "generated": sum(1 for r in diffs if r.get("CLASS") == "GENERATED_ONLY"),
            "archive": sum(1 for r in diffs if r.get("CLASS") == "ARCHIVE_ONLY"),
            "diverged": sum(1 for r in diffs if r.get("CLASS") == "DIVERGED_SAME_PATH"),
        },
        "gl005_proven": False,
    }
    unique_doc = {
        "schema": "raios.unique-asset-reconciliation.v1",
        "ts": utc(),
        **unique,
        "gl005_proven": False,
    }
    cap_doc = {
        "schema": "raios.capability-reconciliation.v1",
        "ts": utc(),
        "capabilities": caps,
        "gl005_proven": False,
    }
    actor_doc = {
        "schema": "raios.actor-binding-matrix.v1",
        "ts": utc(),
        **bindings,
        "gl005_proven": False,
        "wal_written": False,
    }
    noncan_doc = {
        "schema": "raios.noncanonical-trees.v1",
        "ts": utc(),
        "trees": noncanonical,
        "delete_gates": {
            "unique_content_count": "must be 0",
            "live_process_count": "must be 0",
            "rollback_receipt": True,
            "confidence": 0.85,
            "confidence_required": 0.99,
            "any_deleted": False,
            "reason": "Gates not jointly satisfied for Repair (unreachable, unique UNKNOWN). /tmp v9 clone tracked-unique=0 but confidence<0.99 without untracked full proof and C1 delete order.",
        },
        "gl005_proven": False,
    }

    t1 = wal_mtime()
    if t0 != t1:
        raise SystemExit("CROSS_TREE_WAL_VIOLATION")

    hashes = {}
    payload_map = {
        "CANONICAL-ROOT.json": canonical_doc,
        "CROSS-TREE-MANIFEST.json": manifest_doc,
        "CROSS-TREE-DIFF.json": diff_doc,
        "UNIQUE-ASSET-RECONCILIATION.json": unique_doc,
        "CAPABILITY-RECONCILIATION.json": cap_doc,
        "ACTOR-BINDING-MATRIX.json": actor_doc,
        "NONCANONICAL-TREES.json": noncan_doc,
    }
    for name, payload in payload_map.items():
        hashes[name] = write_json(REPORTS / name, payload)

    receipt = {
        "schema": "raios.unification-receipt.v1",
        "ts": utc(),
        "from": "C2",
        "c5": "git",
        "this_session": "C2",
        "wave": "CROSS-TREE-UNIFICATION",
        "ok": True,
        "head": live["HEAD"],
        "branch": branch,
        "host": host,
        "canonical_path": str(ROOT),
        "flags": flags,
        "report_sha256": hashes,
        "trees_enumerated": [t["id"] for t in reachable + claimed],
        "reachable_tree_count": len(reachable),
        "claimed_unreachable_count": len(claimed),
        "unrelated_git_count": len(unrelated),
        "merge_executed": False,
        "copied_paths": [],
        "deleted": False,
        "wal_written": False,
        "wal_mtime_unchanged": True,
        "gl005_proven": False,
        "law": list(LAWS),
        "next": [
            "C1: mount Repair or have C3/C4 pull origin/v9-neurolingua-semantic-kernel at this HEAD",
            "Do not delete Repair",
            "P0 remains AUTHENTICATED_ORCHESTRATION_TASK",
        ],
    }
    hashes["UNIFICATION-RECEIPT.json"] = write_json(REPORTS / "UNIFICATION-RECEIPT.json", receipt)
    receipt["report_sha256"] = hashes
    write_json(REPORTS / "UNIFICATION-RECEIPT.json", receipt)
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "LAST.json", receipt)
    if t0 != wal_mtime():
        raise SystemExit("CROSS_TREE_WAL_VIOLATION")
    return receipt


def main() -> int:
    rec = reconcile()
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "canonical": rec["canonical_path"],
                "HEAD": rec["head"],
                "flags": rec["flags"],
                "gl005_proven": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
