"""Read-only repository inventories. Never mutate inspected trees."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .config import PACKAGE, canonical_json, package_root, repo_root_from, run, sha256_obj, utc_now
from .tools import inventory as tool_inventory
from .versions import VersionDetector

SKIP_PREFIX = (".git/", "node_modules/", "__pycache__/", ".next/")


def git_files(repo: Path) -> list[str]:
    proc = run(["git", "ls-files", "-z"], cwd=repo)
    if proc.returncode != 0:
        return []
    return [p.replace("\\", "/") for p in proc.stdout.split("\x00") if p]


def root_inventory(repo: Path) -> dict[str, Any]:
    files = git_files(repo)
    tops = Counter(p.split("/")[0] for p in files)
    dirs = sorted({p.split("/")[0] for p in files if "/" in p})
    detector = VersionDetector(repo)
    return {
        "generated_at": utc_now(),
        "repo": str(repo),
        "tracked_files": len(files),
        "top_level_counts": dict(tops.most_common()),
        "top_level_dirs": dirs,
        "active_project_roots": [
            {"path": "app", "kind": "greeny-life-next-app", "evidence": ["app/", "package.json name=greeny-life"]},
            {"path": ".", "kind": "repo-manifest", "evidence": ["package.json"]},
        ],
        "older_or_reference_roots": [
            {
                "path": "archive/old_folders/GREENY-LIFE-EOS-PRODUCTION",
                "kind": "archive-eos",
                "evidence": ["production-manifest-v1.json", "path contains old_folders"],
                "assumed_older": False,
            },
            {"path": "canonical", "kind": "canonical-data", "evidence": ["system_manifest.json"]},
            {"path": "application", "kind": "application-alt", "evidence": ["directory exists"]},
        ],
        "raios_v9": {"path": "RAIOS/V9", "write": False, "inspected": "read-only"},
        "a17_a18_artifacts": [
            "_raios-a17-integration-wave",
            "_raios-a17-cursor-parallel",
            "_raios-a17-native-cortex",
        ],
        "this_package": PACKAGE,
        "generated_output_folders": ["archive", "E3-RECON-OUTPUT", "intelligence"],
        "databases": ["database", "prisma"],
        "reports_evidence": ["docs", "_GREENY_DIAGNOSTIC_20260809_233236", "NO_CURRENT_EQUIVALENT_PROVEN"],
        "version_candidates": detector.roots(),
        "source": "git ls-files",
    }


def file_type_inventory(repo: Path) -> dict[str, Any]:
    files = git_files(repo)
    ext = Counter()
    buckets = Counter()
    for rel in files:
        suffix = Path(rel).suffix.lower() or "<none>"
        ext[suffix] += 1
        buckets[_bucket(suffix, rel)] += 1
    return {
        "generated_at": utc_now(),
        "tracked_files": len(files),
        "by_extension": dict(ext.most_common(80)),
        "by_class_hint": dict(buckets),
        "note": "extension hint only; runtime classification uses signature+probe and may disagree",
        "extension_trusted": False,
    }


def _bucket(suffix: str, rel: str) -> str:
    rel_l = rel.lower()
    if "evidence" in rel_l.split("/"):
        return "EVIDENCE"
    if any(p in rel_l for p in ("/archive/", "generated", "node_modules")):
        return "GENERATED_HINT"
    mapping = {
        ".py": "CODE",
        ".ts": "CODE",
        ".tsx": "CODE",
        ".js": "CODE",
        ".ps1": "CODE",
        ".sql": "CODE",
        ".sh": "CODE",
        ".md": "DOCUMENT",
        ".html": "DOCUMENT",
        ".xml": "DOCUMENT",
        ".pdf": "DOCUMENT",
        ".json": "DATA",
        ".csv": "DATA",
        ".yaml": "CONFIG",
        ".yml": "CONFIG",
        ".toml": "CONFIG",
        ".sqlite": "DATABASE",
        ".db": "DATABASE",
        ".zip": "ARCHIVE",
        ".png": "MEDIA",
        ".jpg": "MEDIA",
        ".gguf": "MODEL",
        ".bin": "BINARY",
    }
    return mapping.get(suffix, "UNKNOWN")


def existing_capability_map(repo: Path) -> dict[str, Any]:
    return {
        "generated_at": utc_now(),
        "reuse": [
            {
                "path": "_raios-a17-integration-wave/src/raios_wave/cas.py",
                "capability": "content-addressed SHA-256 store",
                "action": "PATTERN_COPIED",
                "note": "wave CAS write-guards native-cortex; this package uses a local CAS",
            },
            {
                "path": "_raios-a17-native-cortex/ccee",
                "capability": "fail-closed hashing, FTS5, dual-brain, doctor",
                "action": "PATTERN_REUSED",
                "write": False,
            },
            {
                "path": "_raios-a17-cursor-parallel/src/raios_parallel/store.py",
                "capability": "SQLite index + identity guards",
                "action": "PATTERN_REUSED",
            },
            {
                "path": "standalone_ast_analysis.py",
                "capability": "Python ast.parse",
                "action": "REUSED_VIA_STDLIB",
            },
            {
                "path": "greenlines_brain/dna/ast_analyzer.py",
                "capability": "historical Python AST analyzer",
                "action": "AVAILABLE_NOT_IMPORTED",
            },
            {
                "path": "intelligence/knowledge_base/tools_manifest.json",
                "capability": "historical tool manifest",
                "action": "READ_ONLY_REFERENCE",
            },
            {
                "path": "MASTERMIND-TOOL-REGISTRY.md",
                "capability": "39 historical capabilities READ_ONLY_READY vs BLOCKED",
                "action": "READ_ONLY_REFERENCE",
            },
            {
                "path": "brain.py",
                "capability": "scan_project_metadata",
                "action": "AVAILABLE_NOT_IMPORTED",
                "note": "stale metadata; not authoritative",
            },
        ],
        "local_tools": tool_inventory(),
    }


def reuse_map(repo: Path) -> dict[str, Any]:
    cap = existing_capability_map(repo)
    return {
        "generated_at": utc_now(),
        "policy": "REUSE > ADAPT > WRAP > CREATE",
        "reused": [c for c in cap["reuse"] if c["action"].startswith(("PATTERN", "REUSED"))],
        "wrapped": [
            {"name": "git ls-files", "role": "discovery preferred"},
            {"name": "rg", "role": "lexical search stage 2"},
            {"name": "python ast.parse", "role": "python symbols"},
            {"name": "sqlite FTS5", "role": "text index"},
            {"name": "zipfile", "role": "archive manifest"},
            {"name": "file(1)", "role": "signature fallback; Magika missing"},
        ],
        "created_in_this_package": [
            "File Intelligence SPI",
            "FileObject + deterministic ids",
            "staged search compiler",
            "version differential",
            "shadow modification txn",
            "archive lineage records",
        ],
        "not_duplicated": ["RAIOS/V9 runtime", "CCEE var", "A17 harvest writers"],
    }


def gap_map(tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    tools = tools or tool_inventory()
    missing = [t for t in tools if t.get("missing")]
    return {
        "generated_at": utc_now(),
        "missing_tools": missing,
        "do_not_install_in_this_wave": True,
        "gaps": [
            {"id": "magika", "impact": "content-type accuracy", "fallback": "signature+parser-probe", "status": "MISSING"},
            {"id": "tika", "impact": "PDF/Office extraction", "fallback": "UNAVAILABLE status, no OCR", "status": "MISSING"},
            {"id": "tree-sitter", "impact": "TS/JS/PS structural parse", "fallback": "regex heuristic", "status": "MISSING"},
            {"id": "universal-ctags", "impact": "multi-language symbols", "fallback": "python ast only", "status": "MISSING"},
            {"id": "ast-grep", "impact": "structural search", "fallback": "ripgrep+symbols", "status": "MISSING", "note": "/usr/bin/sg is Linux set-group, not ast-grep"},
            {"id": "ollama", "impact": "Qwen/teacher synthesis", "fallback": "fail-closed skip STAGE 8", "status": "MISSING"},
            {"id": "docker", "impact": "isolated extractors", "fallback": "none", "status": "MISSING"},
        ],
    }


def write_inventories(repo: Path | None = None, dest: Path | None = None) -> dict[str, Path]:
    repo = repo or repo_root_from()
    dest = dest or (package_root(repo) / "reports")
    dest.mkdir(parents=True, exist_ok=True)
    tools = tool_inventory()
    payloads = {
        "ROOT-INVENTORY.json": root_inventory(repo),
        "FILE-TYPE-INVENTORY.json": file_type_inventory(repo),
        "TOOL-INVENTORY.json": {"generated_at": utc_now(), "tools": tools, "install": False},
        "EXISTING-CAPABILITY-MAP.json": existing_capability_map(repo),
        "REUSE-MAP.json": reuse_map(repo),
        "GAP-MAP.json": gap_map(tools),
        "TOOL-GAP-MAP.json": gap_map(tools),
    }
    written = {}
    for name, payload in payloads.items():
        path = dest / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        written[name] = path
    return written
