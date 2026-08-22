#!/usr/bin/env python3
"""C2 evidence-reuse preparation.

READ_ONLY against canonical trees. Writes only c2-evidence-preparation/*.json.
Does not census every file (that is C3). Hashes each unique blob once.
Does not treat old report claims as current disk truth.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("/workspace")
OUT_DIR = ROOT / "c2-evidence-preparation"
PEEK_BYTES = 8192
FULL_JSON_PEEK_MAX = 256 * 1024
TODAY = datetime(2026, 8, 22, tzinfo=timezone.utc)
SESSION = {
    "order": "C2-EVIDENCE-REUSE-PREPARATION",
    "bc_id": "bc-45b80213-d5e4-47bc-9ce4-e63550834247",
    "checkout_head": None,
    "checkout_branch": None,
}

BRANCHES = [
    "HEAD",
    "origin/main",
    "origin/v9-neurolingua-semantic-kernel",
    "origin/raios/gl-005-convergence",
    "origin/pr/authoritative-certifier-forensic",
    "origin/pr/cairo-shipment-origin-salvage",
    "origin/pr/nl0-semantic-kernel",
    "origin/cursor/neurolingua-semantic-kernel-4f9d",
    "origin/cursor/raios-false-pass-training-147d",
    "origin/cursor/raios-live-assimilation-147d",
    "origin/cursor/raios-repair-boot-41f5",
    "origin/cursor/file-intelligence-authority-f3c7",
    "origin/cursor/file-intelligence-fabric-f3c7",
    "origin/cursor/file-intelligence-parallel-f3c7",
    "origin/cursor/a18-ccee-foundation-f3c7",
    "origin/cursor/a17-cursor-parallel-f3c7",
    "origin/cursor/a17-integration-wave-f3c7",
    "origin/cursor/setup-dev-environment-ee89",
    "origin/codex-clean",
]

GIT_PREFIXES = [
    ".ai-os/reports",
    ".ai-os/receipts",
    ".ai-os/handoffs",
    ".ai-os/learning",
    ".ai-os/council",
    ".ai-os/mcp",
    "RAIOS/V9/evidence",
    "RAIOS/V9/evaluation/a9/reports",
    "RAIOS/V9/evaluation/a9/splits",
    "RAIOS/V9/agents/a13/reports",
    "RAIOS/V9/agents/a13/registry",
    "RAIOS/V9/agents/a14/reports",
    "RAIOS/V9/agents/a14/journal",
    "RAIOS/V9/agents/a14/registry",
    "RAIOS/V9/agents/a14/memory",
    "RAIOS/V9/continuity",
    "RAIOS/V9/architecture",
    "RAIOS/V9/V9-BOOTSTRAP-MANIFEST.json",
    "reports",
    "unified-intelligence/reports",
    "unified-intelligence/architecture.manifest.json",
    "unified-intelligence/contracts",
    "intelligence/reports",
    "intelligence/comprehensive_report.json",
    "intelligence/comprehensive_report.md",
    "intelligence/project-memory.json",
    "intelligence/knowledge-base.json",
    "intelligence/knowledge_base",
    "legacy_audit_reports",
    "logs",
    "docs/architecture",
    "tests/performance/results.json",
]

DISK_DIRS = [
    "reports",
    "unified-intelligence/reports",
    "unified-intelligence/contracts",
    "intelligence",
    "legacy_audit_reports",
    "logs",
    "docs/architecture",
    "tests/performance",
    ".architecture-backups",
]

DISK_ROOT_FILES = [
    "full_report.json",
    "eos-health-report.json",
    "health.json",
    "health_report.json",
    "initial_inspection.json",
    "Project_Audit.txt",
    "PROJECT_FILES.txt",
    "project-summary.txt",
    "project-tree.txt",
    "project_tree.txt",
    "folders_tree.txt",
    "app_tree.txt",
    "Real_Project_Files.txt",
    "TECHNICAL_DEBT.txt",
    "DOC_INDEX.txt",
    "DOC_METADATA.csv",
    "notebook8c2d6a9080.ipynb",
    "unified-intelligence/architecture.manifest.json",
]

EXCLUDE_DIR_PARTS = {
    "node_modules",
    ".next",
    ".git",
    "__pycache__",
    "c2-evidence-preparation",
}

EVIDENCE_NAME_RE = re.compile(
    r"(report|audit|manifest|inventory|receipt|diagnostic|forensic|evidence|"
    r"capability|consolidat|duplicate|dependenc|migration|"
    r"RAIOS|raios|NeuroLingua|neurolingua|WAL|event-bus|event_bus|"
    r"C5_|_C5|c5-|GL-?00[45]|qwen|granite|deepseek|foundry|council|"
    r"model.?lab|self-inspect|health|runtime|phase-\d+|architecture|"
    r"EVIDENCE|RECEIPT|INDEX|TREE|TECHNICAL_DEBT|PROJECT_FILES|"
    r"full_report|initial_inspection|notebook)",
    re.I,
)
EVIDENCE_EXT_RE = re.compile(
    r"\.(json|md|txt|log|csv|yml|yaml|html|sha256|jsonl|ipynb)$", re.I
)
SKIP_NAME_RE = re.compile(
    r"(certificates?\.json|legacy_certificates|product\.schema|"
    r"legacy/(markets|products|countries|units|incoterms|categories))",
    re.I,
)

TOPICS = {
    "RAIOS": re.compile(r"raios|v9-bootstrap|cognitive-factory|RAIOS-V8", re.I),
    "C5": re.compile(r"(^|/)c5([_-]|/)|enterprise-brain|c5-book|c5-grind|c5-proof|c5-wave|c5-week|c5-plan|c5-reality|SAY-C5|TEACH-C5|C5-MIND|C5-NEED|C5-WHOAMI|C5-GRANT|C5-LAWBOOK|C5-BOOK", re.I),
    "memory": re.compile(r"memory|knowledge-base|project-memory|persistent.cognitive|storage.fabric|C5-MIND|mind_fill", re.I),
    "retrieval/index": re.compile(r"retriev|index|lexical|a2-search|file-intelligence|magika|tika|capability-dedup", re.I),
    "NeuroLingua": re.compile(r"neurolingua|neuro.lingua|nl-?0|semantic.kernel", re.I),
    "WAL/events": re.compile(r"wal|event-bus|event_bus|/events/|journal/task-execution-wal|experience", re.I),
    "model registry": re.compile(r"model-(capability|execution|lab|merge)|ollama|fingerprints|executor-registry|agent-capability-registry", re.I),
    "Qwen": re.compile(r"qwen", re.I),
    "Granite": re.compile(r"granite", re.I),
    "DeepSeek": re.compile(r"deepseek", re.I),
    "training": re.compile(r"train|curriculum|c5-grind|c5-book|c5-teach|teaching|HF-GYM|colab_day", re.I),
    "continual learning": re.compile(r"continual|live.learning|a17|experience-capture|assimilation|ccee", re.I),
    "council": re.compile(r"council|c1-c10|summon|driver-packet|handoff", re.I),
    "foundry": re.compile(r"foundry", re.I),
    "cloud/nomadic": re.compile(r"kaggle|nomadic|huggingface|work.steal|cloud-(capacity|first|model|move|storage)|hf-", re.I),
    "model lab": re.compile(r"model.lab|merge.lab|merge-engines|adaptive-model", re.I),
    "self-inspection": re.compile(r"self-inspect|census", re.I),
    "consolidation": re.compile(r"consolidat|unification|duplicate|retirement|retire|unique-asset|cross-tree", re.I),
    "GL005/auth": re.compile(r"gl-?00[45]|auth|cookie|credential|session.split|stale-head|falsify|mutation", re.I),
    "runtime": re.compile(r"runtime|heartbeat|boot|keeper|live|health|observability|trace", re.I),
    "architecture": re.compile(r"architecture|phase-\d+|digital.twin|capability-discovery|unified-intelligence|system_architecture", re.I),
}

PR_SOURCES = {
    12: {"title": "Record executor stop-state for the steering assistant", "head": "v9-neurolingua-semantic-kernel", "session": "bc-dd60b5cf-95bd-4f24-9237-cc1b2225f013"},
    11: {"title": "RAIOS V9.NL-0 NeuroLingua Semantic Kernel", "head": "cursor/neurolingua-semantic-kernel-4f9d", "session": None},
    10: {"title": "Connect live assimilation to real CCEE cortex and execution fabric", "head": "cursor/raios-live-assimilation-147d", "session": None},
    9: {"title": "Train RAIOS on GL-GW-001: false LIVE after chat HTTP 500", "head": "cursor/raios-false-pass-training-147d", "session": None},
    8: {"title": "RAIOS diagnostic nervous system, fail-closed boot, WORK_GATE closed without Qwen", "head": "cursor/raios-repair-boot-41f5", "session": None},
    7: {"title": "File intelligence addendum: authority dimensions and DEGRADED_MODE cert", "head": "cursor/file-intelligence-authority-f3c7", "session": None},
    6: {"title": "File intelligence: Magika/Tika adapters, duplicates, shared cognitive state", "head": "cursor/file-intelligence-fabric-f3c7", "session": None},
    5: {"title": "Add RAIOS universal file intelligence fabric (isolated parallel package)", "head": "cursor/file-intelligence-parallel-f3c7", "session": None},
    4: {"title": "Add RAIOS A18 CCEE foundation and A17.13 false-PASS repair", "head": "cursor/a18-ccee-foundation-f3c7", "session": None},
    3: {"title": "Add RAIOS A17.14–A23 cursor parallel live-learning engines", "head": "cursor/a17-cursor-parallel-f3c7", "session": None},
    2: {"title": "A17 X1–X3 integration wave: normalization through knowledge foundations", "head": "cursor/a17-integration-wave-f3c7", "session": None},
    1: {"title": "Set up Cloud Agent dev environment for GREENY LIFE", "head": "cursor/setup-dev-environment-ee89", "session": None},
}


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=check)


def git_sha(rev: str) -> str | None:
    p = run(["git", "rev-parse", "--verify", rev], check=False)
    if p.returncode != 0:
        return None
    return p.stdout.strip()


def iso_from_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_excluded_path(rel: str) -> bool:
    parts = Path(rel).parts
    return any(p in EXCLUDE_DIR_PARTS for p in parts)


def looks_like_evidence(rel: str) -> bool:
    if is_excluded_path(rel):
        return False
    if SKIP_NAME_RE.search(rel):
        return False
    name = Path(rel).name
    if name in {".gitkeep", ".DS_Store"}:
        return False
    if rel.startswith(".architecture-backups/") and "/reports/" not in rel and not re.search(r"comprehensive_report|duplicate-report|migration-decision|cleanup-plan", rel):
        # keep backup copies of reports only, not entire backup trees
        if not EVIDENCE_NAME_RE.search(name):
            return False
    if not EVIDENCE_EXT_RE.search(name) and not name.endswith(".sha256"):
        return False
    if EVIDENCE_NAME_RE.search(rel):
        return True
    # directory prefixes already selected as evidence homes
    evidence_homes = (
        "reports/",
        "unified-intelligence/reports/",
        "intelligence/reports/",
        "legacy_audit_reports/",
        "logs/",
        ".ai-os/",
        "RAIOS/V9/evidence/",
        "RAIOS/V9/continuity/",
        "RAIOS/V9/architecture/",
    )
    return rel.startswith(evidence_homes) or rel in DISK_ROOT_FILES


def topics_for(rel: str, subject: str, keys: list[str]) -> list[str]:
    blob = " ".join([rel, subject, " ".join(keys)])
    hits = [name for name, rx in TOPICS.items() if rx.search(blob)]
    return hits or ["architecture"]


def parse_embedded_time(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return None
    for k in (
        "ts",
        "timestamp",
        "generated_at",
        "generatedAt",
        "GeneratedAt",
        "updated_at",
        "created_at",
        "Timestamp",
    ):
        v = obj.get(k)
        if isinstance(v, str) and len(v) >= 10:
            return v
    return None


def filename_date(path: str) -> str | None:
    m = re.search(r"(20\d{6})-(\d{6})", path)
    if m:
        s = m.group(1) + m.group(2)
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}T{s[8:10]}:{s[10:12]}:{s[12:14]}"
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", path)
    return m.group(1) if m else None


def classify_temporal(embedded: str | None, git_date: str | None, on_disk: bool, path: str = "") -> str:
    # Do not use ref-tip commit date as file time; that would mark old EOS
    # reports copied into a recent branch as "recent".
    source = embedded or filename_date(path)
    if not source:
        return "unknown"
    try:
        d = datetime.fromisoformat(source.replace("Z", "+00:00").replace(" ", "T"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
    except Exception:
        m = re.search(r"(20\d{2}-\d{2}-\d{2})", source)
        if not m:
            return "unknown"
        d = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
    if d >= datetime(2026, 8, 15, tzinfo=timezone.utc):
        return "recent"
    if d <= datetime(2026, 7, 31, 23, 59, tzinfo=timezone.utc):
        return "historical"
    return "unknown"


def decode_text(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", "replace")
    # UTF-16-LE without BOM is common in PowerShell exports (NUL in odd bytes)
    if len(data) >= 8 and data[1:2] == b"\x00" and data[3:4] == b"\x00":
        return data.decode("utf-16-le", "replace")
    text = data.decode("utf-8", "replace")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    return text


def prefix_json_fields(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = re.search(r'"schema"\s*:\s*"([^"]+)"', text)
    if m:
        out["schema"] = m.group(1)
    m = re.search(r'"(?:ts|timestamp|generated_at|generatedAt|GeneratedAt)"\s*:\s*"([^"]+)"', text)
    if m:
        out["embedded_timestamp"] = m.group(1)
    m = re.search(r'"(?:head|HEAD)"\s*:\s*"([^"]+)"', text)
    if m:
        out["claimed_head"] = m.group(1)
    m = re.search(r'"(?:branch|git_branch)"\s*:\s*"([^"]+)"', text)
    if m:
        out["claimed_branch"] = m.group(1)
    m = re.search(r'"canonical_root_proven"\s*:\s*(true|false)', text)
    if m:
        out["claimed_canonical"] = m.group(1) == "true"
    m = re.search(r'"gl005_proven"\s*:\s*(true|false)', text)
    if m:
        out["claimed_gl005_proven"] = m.group(1) == "true"
    m = re.search(r'"(?:status|Status|state_status|knowledge_state)"\s*:\s*"([^"]+)"', text)
    if m:
        out["claimed_status"] = m.group(1)
    return out


def light_peek(data: bytes, path: str, truncated: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "json_keys": [],
        "embedded_timestamp": None,
        "claimed_head": None,
        "claimed_branch": None,
        "claimed_canonical": None,
        "claimed_gl005_proven": None,
        "claimed_status": None,
        "schema": None,
        "subject": None,
        "scalars_sample": {},
    }
    text = decode_text(data[: max(len(data), PEEK_BYTES)])
    if path.endswith(".ipynb"):
        out["subject"] = "RAIOS Kaggle compute certification + Greeny/RAIOS V8.6.2 continuity notebook"
        return out
    if path.endswith((".json", ".jsonl")):
        obj = None
        try:
            if path.endswith(".jsonl"):
                first = decode_text(data.split(b"\n", 1)[0] if b"\n" in data else data)
                obj = json.loads(first or "{}")
            elif truncated or len(data) > FULL_JSON_PEEK_MAX:
                obj = None
            else:
                obj = json.loads(decode_text(data))
        except Exception:
            obj = None
        if isinstance(obj, dict):
            out["json_keys"] = list(obj.keys())[:40]
            out["schema"] = obj.get("schema") if isinstance(obj.get("schema"), str) else None
            out["embedded_timestamp"] = parse_embedded_time(obj)
            for hk, dest in [
                ("head", "claimed_head"),
                ("HEAD", "claimed_head"),
                ("bound_head", "claimed_head"),
                ("branch", "claimed_branch"),
                ("git_branch", "claimed_branch"),
                ("canonical", "claimed_canonical"),
                ("canonical_root_proven", "claimed_canonical"),
                ("gl005_proven", "claimed_gl005_proven"),
                ("status", "claimed_status"),
                ("Status", "claimed_status"),
                ("state_status", "claimed_status"),
                ("knowledge_state", "claimed_status"),
            ]:
                if hk in obj and out[dest] is None:
                    out[dest] = obj[hk]
            scalars = {
                k: v
                for k, v in obj.items()
                if isinstance(v, (str, int, float, bool, type(None)))
            }
            out["scalars_sample"] = {k: scalars[k] for k in list(scalars)[:18]}
            name = Path(path).name
            schema = out["schema"] or ""
            out["subject"] = schema or name
            if obj.get("audit"):
                out["subject"] = str(obj.get("audit"))
            if obj.get("wave"):
                out["subject"] = f"{out['subject']} wave={obj.get('wave')}"
            if obj.get("phase"):
                out["subject"] = f"{out['subject']} phase={obj.get('phase')}"
            if obj.get("name") and not schema:
                out["subject"] = str(obj.get("name"))
            return out
        if isinstance(obj, list):
            out["subject"] = f"JSON array n={len(obj)} ({Path(path).name})"
            return out
        fields = prefix_json_fields(text)
        out.update({k: v for k, v in fields.items() if v is not None})
        subj = fields.get("schema") or Path(path).name
        if truncated:
            out["subject"] = f"{subj} (prefix-only; file larger than peek window)"
        else:
            out["subject"] = subj
        return out
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    # strip UTF-16 leftover spaces between letters for subject
    if first_line.count("\x00") > 3:
        first_line = first_line.replace("\x00", "")
    out["subject"] = first_line[:180] or Path(path).name
    m = re.search(r"(20\d{2}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", text)
    if m:
        out["embedded_timestamp"] = m.group(1)
    return out


def collect_disk_files() -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for rel in DISK_ROOT_FILES:
        p = ROOT / rel
        if p.is_file():
            found[rel.replace("\\", "/")] = {"path": rel.replace("\\", "/"), "abs": str(p)}
    for d in DISK_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in EXCLUDE_DIR_PARTS]
            for fn in filenames:
                abs_p = Path(dirpath) / fn
                rel = str(abs_p.relative_to(ROOT)).replace("\\", "/")
                if looks_like_evidence(rel):
                    found[rel] = {"path": rel, "abs": str(abs_p)}
    return list(found.values())


def collect_git_blobs() -> list[dict[str, Any]]:
    rows = []
    seen_ref_path = set()
    for ref in BRANCHES:
        if git_sha(ref) is None:
            continue
        cmd = ["git", "ls-tree", "-r", "-l", ref, "--"] + GIT_PREFIXES
        p = run(cmd, check=False)
        if p.returncode != 0:
            continue
        for line in p.stdout.splitlines():
            # format: <mode> <type> <object> <size>\t<file>
            try:
                meta, path = line.split("\t", 1)
            except ValueError:
                continue
            parts = meta.split()
            if len(parts) < 4:
                continue
            mode, typ, obj, size_s = parts[0], parts[1], parts[2], parts[3]
            if typ != "blob":
                continue
            path = path.replace("\\", "/")
            if not looks_like_evidence(path):
                continue
            key = (ref, path)
            if key in seen_ref_path:
                continue
            seen_ref_path.add(key)
            try:
                size = int(size_s)
            except ValueError:
                size = None
            rows.append(
                {
                    "ref": ref,
                    "path": path,
                    "git_blob": obj,
                    "git_size": size,
                    "mode": mode,
                }
            )
    return rows


def hash_unique_blobs(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map git blob sha1 -> {sha256, size, peek} hashing each blob once."""
    unique = {}
    for r in rows:
        unique.setdefault(r["git_blob"], None)
    blob_ids = list(unique.keys())
    result: dict[str, dict[str, Any]] = {}
    # batch in chunks
    CHUNK = 200
    for i in range(0, len(blob_ids), CHUNK):
        chunk = blob_ids[i : i + CHUNK]
        proc = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        assert proc.stdin and proc.stdout
        for b in chunk:
            proc.stdin.write((b + "\n").encode())
        proc.stdin.close()
        stdout = proc.stdout
        for b in chunk:
            header = stdout.readline()
            if not header:
                break
            # <sha1> blob <size>\n  OR <sha1> missing
            hs = header.decode("utf-8", "replace").strip().split()
            if len(hs) < 3 or hs[1] == "missing":
                result[b] = {"sha256": None, "size": None, "peek": {}, "error": "missing"}
                continue
            size = int(hs[2])
            data = stdout.read(size)
            # trailing newline after content
            _ = stdout.read(1)
            result[b] = {
                "sha256": sha256_bytes(data),
                "size": size,
                "peek": None,  # filled later per path
                "_data_for_peek": data if size <= FULL_JSON_PEEK_MAX else data[:PEEK_BYTES],
                "_full_small": size <= FULL_JSON_PEEK_MAX,
            }
        proc.wait()
    return result


def git_commit_date_for_path(ref: str, path: str | None = None) -> str | None:
    """Ref-tip date by default. Per-path blame is skipped (not a C3 census)."""
    cmd = ["git", "log", "-1", "--format=%cI", ref]
    if path:
        cmd.extend(["--", path])
    p = run(cmd, check=False)
    if p.returncode != 0:
        return None
    return p.stdout.strip() or None


def branch_head_map() -> dict[str, str]:
    out = {}
    for ref in BRANCHES:
        sha = git_sha(ref)
        if sha:
            out[ref] = sha
    return out


def load_cloud_artifacts() -> list[dict[str, Any]]:
    events_path = Path(
        "/tmp/cursor/cloud-agent-transcripts/2026-08-22T11-25-11Z-7dea/bc-dd60b5cf-95bd-4f24-9237-cc1b2225f013/events.json"
    )
    arts = []
    if events_path.exists():
        ev = json.loads(events_path.read_text())
        for item in ev.get("events", []):
            title = item.get("title") or ""
            if title.startswith("Artifact created:"):
                name = title.split(":", 1)[1].strip()
                arts.append(
                    {
                        "name": name,
                        "session": "bc-dd60b5cf-95bd-4f24-9237-cc1b2225f013",
                        "session_name": "Certifier false-positive forensic",
                        "createdAtMs": item.get("createdAtMs"),
                        "linkUrl": item.get("linkUrl"),
                        "sha256": None,
                        "presence": "cloud_session_artifact_not_on_this_disk",
                    }
                )
    return arts


def source_session_for(ref: str, path: str) -> str | None:
    if ref.endswith("v9-neurolingua-semantic-kernel") or path.startswith(".ai-os/"):
        return "bc-dd60b5cf-95bd-4f24-9237-cc1b2225f013+prior-v9-sessions"
    if "raios-repair-boot" in ref:
        return "PR#8 cursor/raios-repair-boot-41f5"
    if "neurolingua-semantic-kernel-4f9d" in ref:
        return "PR#11 NL-0"
    if "live-assimilation" in ref:
        return "PR#10"
    if "false-pass-training" in ref:
        return "PR#9"
    if "file-intelligence" in ref:
        return "PR#5-7"
    if "a18-ccee" in ref:
        return "PR#4"
    if "a17-cursor-parallel" in ref:
        return "PR#3"
    if "a17-integration" in ref:
        return "PR#2"
    if "gl-005-convergence" in ref:
        return "origin/raios/gl-005-convergence"
    if path.startswith("unified-intelligence/"):
        return "unified-intelligence-phases-2026-07-26"
    if path.startswith("reports/") or path.startswith("intelligence/") or path.startswith("logs/"):
        return "greeny-life-eos-brain-2026-07"
    if path.endswith("notebook8c2d6a9080.ipynb"):
        return "kaggle-notebook-da67f44"
    return None


def referenced_tree(ref: str, peek: dict[str, Any], on_disk: bool) -> str:
    claimed = peek.get("claimed_branch")
    if isinstance(claimed, str) and claimed:
        return f"claimed_in_artifact:{claimed}"
    if on_disk:
        return f"current_checkout:{SESSION['checkout_branch']}@{SESSION['checkout_head'][:12] if SESSION['checkout_head'] else '?'}"
    if ref == "HEAD":
        return f"git:HEAD={SESSION['checkout_head']}"
    return f"git:{ref}"


def reuse_class(rel: str, on_disk: bool, peek: dict[str, Any], temporal: str) -> dict[str, Any]:
    """Classify reuse. Never treat claims as current truth."""
    name = Path(rel).name.upper()
    canonical_claim = peek.get("claimed_canonical")
    gl005 = peek.get("claimed_gl005_proven")
    is_c3ish = any(
        x in name
        for x in (
            "CANONICAL-ROOT",
            "CROSS-TREE",
            "UNIFICATION",
            "NONCANONICAL",
            "UNIQUE-ASSET",
            "ACTOR-BINDING",
            "CAPABILITY-RECONCILIATION",
        )
    )
    is_raios = rel.startswith(".ai-os/") or rel.startswith("RAIOS/") or "RAIOS" in name or "NEUROLINGUA" in name or name.startswith("C5-")
    reasons = []
    reusable_after_c3 = False
    reusable_now = False
    do_not_use_as_current_truth = True  # default: old reports are not current truth

    if on_disk and not is_raios:
        reusable_now = True
        reasons.append("present_on_current_checkout_as_historical_eos_evidence")
        reusable_after_c3 = True
        reasons.append("hash_stable_catalog_entry")
    if is_raios:
        reusable_after_c3 = True
        reasons.append("git_reachable_raios_evidence_bind_after_c3_tree_identity")
        reusable_now = False
        reasons.append("not_present_as_raios_tree_on_this_checkout" if not on_disk else "on_disk_but_still_not_current_runtime_truth")
    if is_c3ish:
        reusable_after_c3 = True
        reasons.append("prior_c3_like_artifact_reuse_do_not_rerun_full_census")
        do_not_use_as_current_truth = True
        reasons.append("canonical_root_or_unification_conclusion_unverified_this_session")
    if canonical_claim is True or canonical_claim == "true":
        do_not_use_as_current_truth = True
        reasons.append("artifact_claims_canonical_true_not_accepted")
    if gl005 is True:
        do_not_use_as_current_truth = True
        reasons.append("artifact_claims_gl005_proven_not_reverified")
    if temporal == "historical":
        reasons.append("historical_timestamp")
    return {
        "reusable_now_as_catalog_metadata": True,
        "reusable_now_as_current_runtime_truth": False,
        "reusable_after_c3_tree_bind": reusable_after_c3 or on_disk,
        "do_not_use_as_current_truth": do_not_use_as_current_truth,
        "reasons": reasons,
    }


def superseded_status(rel: str, refs: list[str], on_disk: bool) -> str:
    if rel.startswith(".architecture-backups/") or rel.startswith("backup/"):
        return "historical_copy_unproven_superseded"
    if rel.startswith("logs/") and on_disk:
        return "historical_runtime_log"
    # multiple refs with same path handled at group level
    if len(set(refs) - {"HEAD", "origin/main"}) >= 1 and on_disk:
        return "path_also_exists_on_other_refs_unresolved"
    return "unknown"


def build_contradictions(entries: list[dict[str, Any]], heads: dict[str, str]) -> list[dict[str, Any]]:
    contr: list[dict[str, Any]] = []

    def add(cid, topic, artifacts, field, values, note):
        contr.append(
            {
                "id": cid,
                "topic": topic,
                "artifacts": artifacts,
                "field": field,
                "values": values,
                "resolution": "UNRESOLVED",
                "must_not_assume": True,
                "note": note,
            }
        )

    checkout = SESSION["checkout_head"]
    checkout_br = SESSION["checkout_branch"]
    add(
        "C-001",
        "architecture",
        [
            "current_checkout",
            "origin/v9-neurolingua-semantic-kernel:.ai-os/reports/CANONICAL-ROOT.json",
        ],
        "workspace_identity",
        {
            "this_session_checkout": f"{checkout_br}@{checkout}",
            "canonical_root_json_claim": "branch=v9-neurolingua-semantic-kernel HEAD=c21dfd71e23b81a5758a8d99beddaac1228cc8ed path=/workspace canonical_root_proven=true ts=2026-08-22T09:40:38Z",
            "current_v9_tip": heads.get("origin/v9-neurolingua-semantic-kernel"),
        },
        "Same absolute path /workspace is claimed as v9 canonical root in a recent report, but this C2 checkout is origin/main without .ai-os or RAIOS/. Report HEAD c21dfd71 is an ancestor of current v9 tip, not this checkout. Do not treat either as proven canonical.",
    )
    add(
        "C-002",
        "consolidation",
        [
            "origin/v9-neurolingua-semantic-kernel:.ai-os/reports/UNIFICATION-RECEIPT.json",
            "origin/v9-neurolingua-semantic-kernel:.ai-os/reports/CANONICAL-ROOT.json",
        ],
        "canonical_vs_unification_flags",
        {
            "CANONICAL_ROOT_PROVEN": True,
            "C3_BOUND_TO_CANONICAL": False,
            "CROSS_TREE_UNIFICATION_PROVEN": False,
            "GL005_PROVEN": False,
            "this_session_CANONICAL_ROOT_PROVEN": False,
        },
        "Prior C2 unification receipt claims canonical proven while C3 still unbound and unification unproven. This session must not inherit CANONICAL_ROOT_PROVEN.",
    )
    add(
        "C-003",
        "architecture",
        [
            "full_report.json",
            "unified-intelligence/reports/discovery/phase-2-summary-20260726-145740.json",
            "unified-intelligence/reports/enterprise-audit/enterprise-audit-summary-20260726-181303.json",
            "CANONICAL-ROOT.json",
            "CROSS-TREE-MANIFEST.json TMP_C5_CLONE_MAIN",
        ],
        "file_counts",
        {
            "full_report.json_total_files": 351,
            "phase_2_TotalFiles": 385,
            "enterprise_audit_files": 31824,
            "canonical_root_tracked_file_count": 2342,
            "cross_tree_manifest_main_dump_tracked": 616,
            "this_session_does_not_census": True,
        },
        "Incompatible inventories. Likely different roots, include-rules, or Windows vs cloud slices. C3 must establish current disk truth; do not pick a count.",
    )
    add(
        "C-004",
        "runtime",
        [
            "reports/system-health.json",
            "health.json",
            "eos-health-report.json",
            "intelligence/comprehensive_report.json",
            "unified-intelligence/reports/architecture/phase-22/phase-22-manifest-20260726-175733.json",
        ],
        "health_or_status",
        {
            "system-health": "HEALTHY @ 2026-07-23 (GL-DOS engines ACTIVE)",
            "health.json": "SUCCESS @ 2026-07-25 12:19:16",
            "eos-health-report.json": "SUCCESS @ 2026-07-24 21:10:34",
            "comprehensive_report.status": "RUNNING with multiple failed scans",
            "phase-22": "DIGITAL_TWIN_ACTIVE / PASSED",
        },
        "EOS health documents disagree with each other and are all historical. None is this-host runtime.",
    )
    add(
        "C-005",
        "Qwen",
        [
            "QWEN-RUNTIME-REALITY.json",
            "RAIOS-LLM-FABRIC-REALITY-AUDIT.json",
            "RAIOS-WAVE1-RECEIPT.json",
            "C5-ENTERPRISE-BRAIN-AUDIT.json",
        ],
        "model_runtime",
        {
            "student_live_qwen2.5:0.5b": True,
            "student_generate_ok": True,
            "cortex_qwen3.6:35b-a3b_loaded": False,
            "granite_generate_ok": False,
            "weight_hash": None,
            "final_backbone": None,
            "llm_fabric_proven": False,
            "extracted_qwen_granite": False,
        },
        "Reports describe a student generate OK on some prior host/session. This checkout has no ollama/Qwen runtime evidence. Do not infer current model liveness.",
    )
    add(
        "C-006",
        "NeuroLingua",
        [
            "NEUROLINGUA-REALITY-AUDIT.json",
            "origin/cursor/neurolingua-semantic-kernel-4f9d",
            "RAIOS-CURRENT-STATE.json",
        ],
        "neurolingua_presence_and_file_count",
        {
            "founder_claimed_file_count": 79,
            "this_checkout_related_files_in_audit": 38,
            "spacy_stanza_camel_tools": False,
            "RAIOS-CURRENT-STATE.branch_observed": "codex-clean",
            "RAIOS-CURRENT-STATE.repository_sha_observed": "1eb0d5944fba7c25977c26c5c5613ddab6d3d33b",
            "PR11_head": "cursor/neurolingua-semantic-kernel-4f9d",
            "current_checkout": "no NeuroLingua tree",
        },
        "File-count claim vs observed related files, plus current-state bound to older codex-clean SHA. Unresolved.",
    )
    add(
        "C-007",
        "GL005/auth",
        [
            "multiple .ai-os/receipts/GL005-*",
            "UNIFICATION-RECEIPT.json",
            "MASTER-RECEIPT.json",
            "RAIOS-WAVE1-RECEIPT.json",
        ],
        "gl005_proven",
        {"all_sampled_reports": False, "receipts_exist": True},
        "GL-005 receipts exist while every sampled proven flag remains false. Receipt presence is not proof.",
    )
    add(
        "C-008",
        "consolidation",
        [
            "POST-CONSOLIDATION-REALITY.json",
            "20260820-cursor-DRIVER-PACKET.json",
            "UNIFICATION-RECEIPT.json",
        ],
        "consolidation_executed",
        {
            "repository_consolidation_proven": False,
            "driver_packet_mission_status": "NOT_EXECUTED",
            "merge_executed": False,
            "deleted": False,
            "retire_count": 0,
        },
        "Driver packet ordered consolidation+deletion; later stamps say not executed. Do not assume estate was compressed.",
    )
    add(
        "C-009",
        "cloud/nomadic",
        ["notebook8c2d6a9080.ipynb", "RAIOS-CURRENT-STATE.json", "v9 reports"],
        "raios_version_label",
        {
            "notebook": "RAIOS-V8.6.2 / raios-cognitive-factory / Kaggle",
            "continuity_state": "V9.0-A14.1 A14_1_CERTIFIED",
            "git_raios_path": "RAIOS/V9 on non-main branches only",
        },
        "Version labels V8.6.2 vs V9.0-A14.1 vs missing-on-main. Do not collapse into one runtime.",
    )
    add(
        "C-010",
        "WAL/events",
        ["RAIOS-CLOUD-MOVE-TRAINING-BOOKS-WAL.json", "POST-CONSOLIDATION-REALITY.json", "UNIFICATION-RECEIPT.json"],
        "wal_written",
        {"wal_written": False, "wal_mtime_unchanged": True, "continuity": "WAL untouched", "cloud_migration_proven": False},
        "WAL reported untouched; this checkout has no WAL file. Do not create another WAL in C2.",
    )
    add(
        "C-011",
        "self-inspection",
        ["SELF-INSPECTION-ENGINE-PROOF.json"],
        "self_inspection_proven",
        {"self_inspection_proven": True, "gl005_proven": False, "host": "prior C2 session"},
        "Self-inspection marked proven on a prior session. Proof hash in-file is not re-verified as current host truth.",
    )
    add(
        "C-012",
        "C5",
        [
            "cloud agents named Test/Demo/Open C5 screen",
            "C5-ENTERPRISE-BRAIN-AUDIT.json",
            "current_checkout",
        ],
        "c5_presence",
        {
            "ui_demo_sessions": "multiple IDLE internal agents on this repo",
            "audit_maturity": "HYBRID_RETRIEVAL_PLUS_TIER0_DETERMINISTIC",
            "audit_canonical": False,
            "this_disk": "no C5 tree",
        },
        "C5 UI sessions and git audits exist; this disk has no C5 implementation. Demo sessions are not capability proof.",
    )
    add(
        "C-013",
        "architecture",
        ["CROSS-TREE-MANIFEST.json", "this_session"],
        "reachable_trees",
        {
            "manifest_ts": "2026-08-22T09:40:38Z",
            "canonical_candidate": "/workspace as v9@c21dfd71",
            "this_session_/workspace": f"{checkout_br}@{checkout}",
            "repair": "unreachable Windows founder copy",
            "tmp_clones": "prior host /tmp paths; not re-walked",
        },
        "Prior manifest enumerated trees on another agent host/session. This C2 run did not repeat that census (C3_WORK_DUPLICATED=false). Paths may no longer exist.",
    )
    add(
        "C-014",
        "runtime",
        ["intelligence/comprehensive_report.json scans vs passed flags"],
        "scan_pass_vs_summary",
        {
            "ouro_loop.passed": True,
            "ouro_loop.summary": "Ouro Loop is not installed. Skipping.",
            "sonarqube.passed": False,
            "archguard.passed": False,
        },
        "passed=true used for skipped/uninstalled tools. Do not treat as measured pass.",
    )
    add(
        "C-015",
        "architecture",
        ["origin/main vs origin/v9-neurolingua-semantic-kernel"],
        "git_divergence",
        {
            "rev_list_left_right_count_main_v9": "176 170",
            "main_has_ai_os": False,
            "main_has_RAIOS": False,
            "v9_has_ai_os_reports": True,
        },
        "Two long-diverged refs. C3 must identify trees; C2 only records the split.",
    )

    # automatic: same path different sha256
    by_path = defaultdict(set)
    by_path_refs = defaultdict(list)
    for e in entries:
        if e.get("sha256"):
            by_path[e["path"]].add(e["sha256"])
            by_path_refs[e["path"]].append(e.get("source_ref"))
    variants = {p: sorted(h) for p, h in by_path.items() if len(h) > 1}
    if variants:
        sample = list(variants.items())[:25]
        add(
            "C-016",
            "consolidation",
            [p for p, _ in sample],
            "same_relative_path_different_hashes",
            {"variant_path_count": len(variants), "sample": {p: hs for p, hs in sample}},
            "Same relative path has multiple SHA256 values across refs. Not resolved; C3 binds which blob is current.",
        )

    # automatic: claimed heads disagree
    heads_claimed = defaultdict(list)
    for e in entries:
        h = (e.get("header_peek") or {}).get("claimed_head")
        if h:
            heads_claimed[str(h)[:40]].append(e["path"])
    if len(heads_claimed) > 1:
        add(
            "C-017",
            "runtime",
            ["header_peek.claimed_head across artifacts"],
            "bound_git_head",
            {k: v[:8] for k, v in list(heads_claimed.items())[:12]},
            "Evidence artifacts bind many different git HEADs. None is this session's current truth.",
        )
    return contr


def future_targets(entries: list[dict[str, Any]], topics_map: dict[str, Any]) -> dict[str, Any]:
    present = {t: bool(topics_map.get(t, {}).get("artifact_ids")) for t in TOPICS}
    gaps = []

    def gap(gid, topic, why, after):
        gaps.append({"id": gid, "topic": topic, "why_new_analysis_required": why, "after": after})

    gap("G-001", "architecture", "Current checkout is origin/main without RAIOS/ or .ai-os/. Tree identity vs v9/Repair/OneDrive/worktrees is not established.", "C3 tree census / current disk truth")
    gap("G-002", "RAIOS", "No RAIOS V9 tree on this disk. Git-reachable V9 reports are not runtime-verified here. Notebook is V8.6.2 Kaggle, not V9.", "C3 bind then capability archaeology on bound tree")
    gap("G-003", "C5", "C5 code/receipts live on other refs/sessions. This disk has no C5. UI demo agents are not capability proof.", "C3 bind + live C5 probe on bound tree")
    gap("G-004", "memory", "Persistent cognitive storage flagged unproven; no WAL/memory fabric on this checkout.", "new analysis after C3")
    gap("G-005", "retrieval/index", "File-intelligence PRs exist on isolated branches; not in this checkout; Magika/Tika not verified.", "new analysis after C3")
    gap("G-006", "NeuroLingua", "NL-0 PR and reality audit disagree on file counts; spaCy/Stanza/CAMeL absent in audit; not on this disk.", "new analysis after C3")
    gap("G-007", "WAL/events", "Existing WAL only on v9 journal paths; reports say wal_written=false. Must not create another WAL. Need C3 to locate the one cognitive WAL if any.", "C3 locate existing WAL; archaeology may read, not rewrite")
    gap("G-008", "model registry", "MODEL-* reports are foundation-only; winner=null; weight_hash=null.", "new measured registry after C3")
    gap("G-009", "Qwen", "Prior student_live claim is host-specific; cortex held; do_not_call_qwen_3_6. No local model files on this checkout.", "new runtime measurement; do not reuse live flags")
    gap("G-010", "Granite", "granite_generate_ok=false and granite_sovereign_backbone=false in sampled reports. No Granite weights here.", "new runtime measurement")
    gap("G-011", "DeepSeek", "Only DEEPSEEK-LOCAL-BENCHMARK.md on some branches; not on this disk; not re-read as current.", "new analysis after C3")
    gap("G-012", "training", "C5 book/grind/week receipts exist in git; training not rerun. Foundry not run.", "do not train C5 in C2; later measured training")
    gap("G-013", "continual learning", "A17/A18/CCEE live-learning engines are isolated PR branches, not this checkout.", "new analysis after C3")
    gap("G-014", "council", "Council packets/handoffs on v9; actor binding matrix exists as claim. Repair unreachable.", "C3 actor/tree bind")
    gap("G-015", "foundry", "POST-CONSOLIDATION-REALITY.foundry='not run'. No foundry evidence on this disk.", "new analysis; do not run weight merge in C2")
    gap("G-016", "cloud/nomadic", "Kaggle notebook + capacity matrices exist; work-stealing proven only as local sim in MASTER-RECEIPT. This host is not Kaggle.", "new analysis on actual workers")
    gap("G-017", "model lab", "MODEL-LAB-REALITY merge_executed=false winner=null.", "new analysis; do not run weight merge")
    gap("G-018", "self-inspection", "Proof artifact exists for a prior host; censuses not rerun (SAME_HASH_REANALYSIS=false).", "reuse hash; C3/archaeology may re-run only after tree bind if hash no longer matches disk")
    gap("G-019", "consolidation", "Consolidation ordered but NOT_EXECUTED. Duplicate EOS inventories vs RAIOS merge inventory. Do not merge/delete.", "C3 then optional consolidation under C1")
    gap("G-020", "GL005/auth", "Many GL-004/GL-005 receipts; gl005_proven false everywhere sampled. Auth discriminator/cookie transport are git receipts only.", "new live auth/GL-005 after C3")
    gap("G-021", "runtime", "This session did not execute brain.py or keepers. Old health SUCCESS/HEALTHY/RUNNING conflict. INSTALL_FAILED on this cloud run.", "C3 current runtime truth")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "law": {
            "FULL_RESEARCH_FROM_ZERO": False,
            "REUSE_EXISTING_EVIDENCE": True,
            "CURRENT_RUNTIME_TRUTH_NOT_ASSUMED": True,
        },
        "topic_coverage_in_index": present,
        "targets": gaps,
        "explicit_non_actions_still_in_force": [
            "do_not_merge",
            "do_not_copy",
            "do_not_delete",
            "do_not_archive",
            "do_not_modify_canonical_files",
            "do_not_create_another_WAL",
            "do_not_create_another_registry",
            "do_not_train_C5",
            "do_not_run_weight_merge",
            "do_not_execute_brain.py",
            "do_not_declare_canonical_root",
            "do_not_duplicate_C3_tree_census",
        ],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION["checkout_head"] = git_sha("HEAD")
    br = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    SESSION["checkout_branch"] = br
    heads = branch_head_map()
    generated_at = datetime.now(timezone.utc).isoformat()

    disk_files = collect_disk_files()
    git_rows = collect_git_blobs()
    blob_map = hash_unique_blobs(git_rows)

    # Hash disk files once; reuse git sha256 when blob matches size+later compare
    disk_hash: dict[str, dict[str, Any]] = {}
    for item in disk_files:
        p = Path(item["abs"])
        st = p.stat()
        data_peek = b""
        size = st.st_size
        if size <= FULL_JSON_PEEK_MAX:
            data = p.read_bytes()
            sha = sha256_bytes(data)
            data_peek = data
        else:
            sha = sha256_file(p)
            with p.open("rb") as f:
                data_peek = f.read(PEEK_BYTES)
        peek = light_peek(data_peek, item["path"], truncated=size > FULL_JSON_PEEK_MAX)
        disk_hash[item["path"]] = {
            "sha256": sha,
            "size": size,
            "mtime": iso_from_ts(st.st_mtime),
            "peek": peek,
        }

    # Fill git peeks once per sha256
    peek_by_sha: dict[str, dict[str, Any]] = {}
    for blob, info in blob_map.items():
        sha = info.get("sha256")
        if not sha or sha in peek_by_sha:
            # already peeked this content
            if sha and info.get("_data_for_peek") is not None:
                info.pop("_data_for_peek", None)
            continue
        data = info.get("_data_for_peek") or b""
        # path hint from first row
        hint = next((r["path"] for r in git_rows if r["git_blob"] == blob), "unknown.json")
        peek_by_sha[sha] = light_peek(data, hint, truncated=not info.get("_full_small", True))
        info.pop("_data_for_peek", None)

    for pth, info in disk_hash.items():
        sha = info["sha256"]
        if sha not in peek_by_sha:
            peek_by_sha[sha] = info["peek"]

    # git dates: once per (ref, path) is expensive; do per unique path on a preferred ref only
    # Use blob commit date from the ref that contains it, cached per (ref, dir prefix) skip
    date_cache: dict[str, str | None] = {}

    def get_date(ref: str, path: str) -> str | None:
        # Ref tip date only. Per-path git log would be a mini-census.
        if ref not in date_cache:
            date_cache[ref] = git_commit_date_for_path(ref)
        return date_cache[ref]

    entries: list[dict[str, Any]] = []
    artifact_id = 0

    # disk entries
    disk_paths = set()
    for item in disk_files:
        rel = item["path"]
        disk_paths.add(rel)
        info = disk_hash[rel]
        peek = peek_by_sha.get(info["sha256"], info["peek"])
        git_date = get_date("HEAD", rel)
        on_disk = True
        temporal = classify_temporal(peek.get("embedded_timestamp"), git_date, on_disk, rel)
        topics = topics_for(rel, str(peek.get("subject") or ""), peek.get("json_keys") or [])
        artifact_id += 1
        entries.append(
            {
                "id": f"E-{artifact_id:04d}",
                "path": rel,
                "absolute_path": str(ROOT / rel),
                "sha256": info["sha256"],
                "size": info["size"],
                "modified_time": {
                    "filesystem_mtime": info["mtime"],
                    "filesystem_mtime_caveat": "this_cloud_checkout_mtime_is_clone_time_not_author_time",
                    "git_ref_tip_date": git_date,
                    "git_ref_tip_date_caveat": "ref_tip_not_file_blame",
                    "embedded_timestamp": peek.get("embedded_timestamp"),
                    "filename_timestamp": filename_date(rel),
                },
                "apparent_subject": peek.get("subject") or Path(rel).name,
                "source_session": source_session_for("HEAD", rel),
                "source_ref": "current_checkout",
                "referenced_tree_or_root": referenced_tree("HEAD", peek, True),
                "temporal_class": temporal,
                "location_class": "current",
                "superseded_status": superseded_status(rel, ["HEAD"], True),
                "topics": topics,
                "header_peek": {
                    "schema": peek.get("schema"),
                    "json_keys": peek.get("json_keys"),
                    "claimed_head": peek.get("claimed_head"),
                    "claimed_branch": peek.get("claimed_branch"),
                    "claimed_canonical": peek.get("claimed_canonical"),
                    "claimed_gl005_proven": peek.get("claimed_gl005_proven"),
                    "claimed_status": peek.get("claimed_status"),
                    "scalars_sample": peek.get("scalars_sample"),
                },
                "reuse": reuse_class(rel, True, peek, temporal),
                "on_current_disk": True,
            }
        )

    # git-only (and git copies of disk files on other refs)
    for r in git_rows:
        rel = r["path"]
        ref = r["ref"]
        # skip HEAD duplicates of disk files (already entered as current_checkout)
        if ref in {"HEAD", "origin/main"} and rel in disk_paths:
            # still record other-ref variants below; skip exact current
            if ref == "HEAD":
                continue
        info = blob_map.get(r["git_blob"]) or {}
        sha = info.get("sha256")
        peek = peek_by_sha.get(sha or "", {})
        on_disk = rel in disk_paths and ref in {"HEAD", "origin/main"}
        if on_disk and ref == "origin/main":
            # same as checkout typically
            continue
        git_date = get_date(ref, rel)
        temporal = classify_temporal(peek.get("embedded_timestamp"), git_date, False, rel)
        topics = topics_for(rel, str(peek.get("subject") or ""), peek.get("json_keys") or [])
        loc = "current" if on_disk else temporal if temporal in {"recent", "historical"} else "unknown"
        artifact_id += 1
        entries.append(
            {
                "id": f"E-{artifact_id:04d}",
                "path": rel,
                "absolute_path": None,
                "sha256": sha,
                "size": info.get("size") if info.get("size") is not None else r.get("git_size"),
                "modified_time": {
                    "filesystem_mtime": None,
                    "filesystem_mtime_caveat": "not_on_this_checkout",
                    "git_ref_tip_date": git_date,
                    "git_ref_tip_date_caveat": "ref_tip_not_file_blame",
                    "embedded_timestamp": peek.get("embedded_timestamp"),
                    "filename_timestamp": filename_date(rel),
                },
                "apparent_subject": peek.get("subject") or Path(rel).name,
                "source_session": source_session_for(ref, rel),
                "source_ref": ref,
                "referenced_tree_or_root": referenced_tree(ref, peek, False),
                "temporal_class": temporal,
                "location_class": loc,
                "superseded_status": superseded_status(rel, [ref], False),
                "topics": topics,
                "header_peek": {
                    "schema": peek.get("schema"),
                    "json_keys": peek.get("json_keys"),
                    "claimed_head": peek.get("claimed_head"),
                    "claimed_branch": peek.get("claimed_branch"),
                    "claimed_canonical": peek.get("claimed_canonical"),
                    "claimed_gl005_proven": peek.get("claimed_gl005_proven"),
                    "claimed_status": peek.get("claimed_status"),
                    "scalars_sample": peek.get("scalars_sample"),
                },
                "reuse": reuse_class(rel, False, peek, temporal),
                "on_current_disk": False,
                "git_blob_sha1": r["git_blob"],
            }
        )

    # Collapse identical (sha256, path) across refs. Dedup hashes, keep ref list.
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    leftovers: list[dict[str, Any]] = []
    for e in entries:
        sha = e.get("sha256")
        if not sha:
            leftovers.append(e)
            continue
        key = (sha, e["path"])
        if key not in merged:
            ne = dict(e)
            ne["source_refs"] = [e["source_ref"]]
            merged[key] = ne
        else:
            tgt = merged[key]
            if e["source_ref"] not in tgt["source_refs"]:
                tgt["source_refs"].append(e["source_ref"])
            if e.get("on_current_disk"):
                tgt["on_current_disk"] = True
                tgt["location_class"] = "current"
                tgt["absolute_path"] = e.get("absolute_path") or tgt.get("absolute_path")
                tgt["source_ref"] = "current_checkout"
                tgt["modified_time"]["filesystem_mtime"] = e["modified_time"].get("filesystem_mtime")
                tgt["modified_time"]["filesystem_mtime_caveat"] = e["modified_time"].get("filesystem_mtime_caveat")
    entries = list(merged.values()) + leftovers
    for i, e in enumerate(entries, 1):
        e["id"] = f"E-{i:04d}"
        if "source_refs" not in e:
            e["source_refs"] = [e.get("source_ref")]

    cloud_arts = load_cloud_artifacts()
    next_id = len(entries) + 1
    for a in cloud_arts:
        name = a["name"]
        topics = topics_for(name, name, [])
        entries.append(
            {
                "id": f"E-{next_id:04d}",
                "path": f"cursor-cloud-artifact://{a['session']}/{name}",
                "absolute_path": None,
                "sha256": None,
                "size": None,
                "modified_time": {
                    "filesystem_mtime": None,
                    "filesystem_mtime_caveat": "cloud_artifact_not_fetched",
                    "git_ref_tip_date": None,
                    "embedded_timestamp": None,
                    "createdAtMs": a.get("createdAtMs"),
                },
                "apparent_subject": name,
                "source_session": a["session"],
                "source_ref": "cloud_agent_artifact",
                "source_refs": ["cloud_agent_artifact"],
                "referenced_tree_or_root": "unknown_prior_agent_workspace",
                "temporal_class": "recent",
                "location_class": "unknown",
                "superseded_status": "unknown",
                "topics": topics,
                "header_peek": {},
                "reuse": {
                    "reusable_now_as_catalog_metadata": True,
                    "reusable_now_as_current_runtime_truth": False,
                    "reusable_after_c3_tree_bind": True,
                    "do_not_use_as_current_truth": True,
                    "reasons": [
                        "filename_pointer_only",
                        "bytes_not_on_this_disk",
                        "sha256_unknown_this_session",
                    ],
                },
                "on_current_disk": False,
                "linkUrl": a.get("linkUrl"),
            }
        )
        next_id += 1

    # Deduplicate identical hashes: HASH GROUPS
    groups: dict[str, list[str]] = defaultdict(list)
    nohash: list[str] = []
    for e in entries:
        if e.get("sha256"):
            groups[e["sha256"]].append(e["id"])
        else:
            nohash.append(e["id"])

    hash_groups = []
    for sha, ids in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        members = [e for e in entries if e["id"] in ids]
        hash_groups.append(
            {
                "sha256": sha,
                "count": len(ids),
                "size": members[0].get("size"),
                "paths": sorted({m["path"] for m in members}),
                "source_refs": sorted({m["source_ref"] for m in members}),
                "artifact_ids": ids,
                "same_hash_reanalyzed": False,
            }
        )
    hash_groups_doc = {
        "generated_at": generated_at,
        "unique_sha256_count": len(groups),
        "duplicate_groups_count": sum(1 for g in hash_groups if g["count"] > 1),
        "artifacts_without_sha256": nohash,
        "law": {"SAME_HASH_REANALYZED": False, "each_blob_hashed_once": True},
        "groups": hash_groups,
    }

    # Topic map
    topic_map: dict[str, Any] = {}
    for t in TOPICS:
        ids = [e["id"] for e in entries if t in e["topics"]]
        topic_map[t] = {
            "artifact_ids": ids,
            "count": len(ids),
            "on_current_disk_count": sum(1 for e in entries if t in e["topics"] and e["on_current_disk"]),
            "git_only_count": sum(1 for e in entries if t in e["topics"] and not e["on_current_disk"] and e.get("sha256")),
            "hash_unknown_count": sum(1 for e in entries if t in e["topics"] and not e.get("sha256")),
            "reusable_after_c3_ids": [
                e["id"]
                for e in entries
                if t in e["topics"] and e["reuse"]["reusable_after_c3_tree_bind"]
            ],
            "gap": None,
        }
    # fill gap flags
    for t, body in topic_map.items():
        if body["on_current_disk_count"] == 0 and t not in {"architecture", "consolidation", "runtime"}:
            body["gap"] = "no_current_disk_evidence"
        elif t in {"Qwen", "Granite", "DeepSeek", "foundry", "WAL/events", "NeuroLingua", "C5", "RAIOS"} and body["on_current_disk_count"] <= 1:
            body["gap"] = "insufficient_current_disk_evidence"

    topic_doc = {
        "generated_at": generated_at,
        "topics": topic_map,
        "multi_topic_allowed": True,
        "note": "Topic assignment is filename/header heuristic, not deep capability analysis.",
    }

    contradictions = build_contradictions(entries, heads)
    targets = future_targets(entries, topic_map)

    reuse_after = [e["id"] for e in entries if e["reuse"]["reusable_after_c3_tree_bind"]]
    reuse_index = {
        "schema": "c2.evidence-reuse-index.v1",
        "generated_at": generated_at,
        "mode": "READ_ONLY",
        "session": SESSION,
        "law": {
            "REUSE_EXISTING_EVIDENCE": True,
            "CURRENT_RUNTIME_TRUTH_NOT_ASSUMED": True,
            "SAME_HASH_REANALYSIS": False,
            "FULL_RESEARCH_FROM_ZERO": False,
            "C3_WORK_DUPLICATED": False,
            "CANONICAL_ROOT_PROVEN": False,
        },
        "scope": {
            "current_checkout_head": SESSION["checkout_head"],
            "current_checkout_branch": SESSION["checkout_branch"],
            "git_refs_scanned_for_evidence_prefixes_only": list(heads.keys()),
            "git_ref_heads": heads,
            "full_tree_census": False,
            "brain_py_executed": False,
            "tmp_clones_walked": False,
            "windows_repair_reached": False,
        },
        "counts": {
            "artifacts": len(entries),
            "on_current_disk": sum(1 for e in entries if e["on_current_disk"]),
            "git_reachable_not_on_disk": sum(1 for e in entries if not e["on_current_disk"] and e.get("sha256")),
            "sha256_unknown": sum(1 for e in entries if not e.get("sha256")),
            "unique_sha256": len(groups),
        },
        "pull_requests_as_evidence_sources": PR_SOURCES,
        "artifacts": entries,
        "reusable_after_c3_tree_bind_ids": reuse_after,
    }

    receipt = {
        "schema": "c2.evidence-preparation-receipt.v1",
        "generated_at": generated_at,
        "order": "C2-EVIDENCE-REUSE-PREPARATION",
        "session": SESSION,
        "outputs": {
            "EVIDENCE-REUSE-INDEX.json": str(OUT_DIR / "EVIDENCE-REUSE-INDEX.json"),
            "EVIDENCE-HASH-GROUPS.json": str(OUT_DIR / "EVIDENCE-HASH-GROUPS.json"),
            "EVIDENCE-TOPIC-MAP.json": str(OUT_DIR / "EVIDENCE-TOPIC-MAP.json"),
            "EVIDENCE-CONTRADICTIONS.json": str(OUT_DIR / "EVIDENCE-CONTRADICTIONS.json"),
            "FUTURE-DEEP-ANALYSIS-TARGETS.json": str(OUT_DIR / "FUTURE-DEEP-ANALYSIS-TARGETS.json"),
            "C2-EVIDENCE-PREPARATION-RECEIPT.json": str(OUT_DIR / "C2-EVIDENCE-PREPARATION-RECEIPT.json"),
        },
        "flags": {
            "MODE": "READ_ONLY",
            "C3_WORK_DUPLICATED": False,
            "SAME_HASH_REANALYZED": False,
            "CURRENT_TRUTH_INFERRED_FROM_OLD_REPORTS": False,
            "CANONICAL_ROOT_PROVEN": False,
            "READY_FOR_CAPABILITY_ARCHAEOLOGY": False,
            "READY_FOR_CAPABILITY_ARCHAEOLOGY_DETAIL": "INDEX_COMPLETE_C3_TREE_BIND_REQUIRED",
        },
        "did_not": [
            "merge",
            "copy_trees",
            "delete",
            "archive",
            "modify_canonical_files",
            "create_another_WAL",
            "create_another_registry",
            "train_C5",
            "run_weight_merge",
            "execute_brain.py",
            "declare_canonical_root",
            "duplicate_C3_tree_census",
            "walk_/tmp_clones",
            "hash_non_evidence_source_trees",
            "full_parse_CROSS-TREE-MANIFEST_file_list",
        ],
        "did": [
            "discover_evidence_by_name_and_known_report_homes",
            "sha256_each_unique_blob_once",
            "light_header_peek_once_per_hash",
            "cluster_topics_heuristically",
            "record_contradictions_unresolved",
            "index_prior_c3_like_reports_for_reuse_not_rerun",
        ],
        "counts": reuse_index["counts"],
        "prior_c3_like_artifacts_indexed_not_rerun": [
            ".ai-os/reports/CANONICAL-ROOT.json",
            ".ai-os/reports/NONCANONICAL-TREES.json",
            ".ai-os/reports/CROSS-TREE-MANIFEST.json",
            ".ai-os/reports/CROSS-TREE-DIFF.json",
            ".ai-os/reports/UNIFICATION-RECEIPT.json",
            ".ai-os/reports/UNIQUE-ASSET-RECONCILIATION.json",
            ".ai-os/reports/ACTOR-BINDING-MATRIX.json",
            ".ai-os/reports/CAPABILITY-RECONCILIATION.json",
        ],
        "this_checkout_observation_not_a_census": {
            "branch": SESSION["checkout_branch"],
            "head": SESSION["checkout_head"],
            "has_.ai-os": (ROOT / ".ai-os").exists(),
            "has_RAIOS": (ROOT / "RAIOS").exists(),
            "has_notebook_raios": (ROOT / "notebook8c2d6a9080.ipynb").exists(),
        },
        "cloud_run": {
            "bcId": "bc-45b80213-d5e4-47bc-9ce4-e63550834247",
            "setupStatus_observed": "INSTALL_FAILED",
            "note": "setupStatus is cloud metadata, not used as project runtime truth",
        },
    }

    contr_doc = {
        "generated_at": generated_at,
        "resolution_policy": "DO_NOT_RESOLVE_BY_ASSUMPTION",
        "current_truth_inferred_from_old_reports": False,
        "contradictions": contradictions,
    }

    def dump(name: str, obj: Any) -> None:
        path = OUT_DIR / name
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {path} bytes={path.stat().st_size}")

    dump("EVIDENCE-REUSE-INDEX.json", reuse_index)
    dump("EVIDENCE-HASH-GROUPS.json", hash_groups_doc)
    dump("EVIDENCE-TOPIC-MAP.json", topic_doc)
    dump("EVIDENCE-CONTRADICTIONS.json", contr_doc)
    dump("FUTURE-DEEP-ANALYSIS-TARGETS.json", targets)
    dump("C2-EVIDENCE-PREPARATION-RECEIPT.json", receipt)
    print("artifacts", len(entries), "unique_sha", len(groups), "contradictions", len(contradictions))
    return 0


if __name__ == "__main__":
    sys.exit(main())
