"""Local tool inventory. Detect only; never blindly install."""
from __future__ import annotations

from typing import Any

from .config import which, run

CATALOG = (
    ("git", "git", ["--version"], "version control / ls-files discovery", "high"),
    ("rg", "rg", ["--version"], "lexical search", "high"),
    ("fd", "fd", ["--version"], "file enumeration", "medium"),
    ("magika", "magika", ["--version"], "content-type detection", "high"),
    ("tree-sitter", "tree-sitter", ["--version"], "AST parsing", "high"),
    ("ctags", "ctags", ["--version"], "symbol extraction", "medium"),
    ("ast-grep", "ast-grep", ["--version"], "structural search", "high"),
    ("semgrep", "semgrep", ["--version"], "semantic grep", "medium"),
    ("7z", "7z", [], "archives", "medium"),
    ("tika", "tika", ["--version"], "document extraction", "high"),
    ("java", "java", ["-version"], "tika runtime", "medium"),
    ("sqlite3", "sqlite3", ["--version"], "metadata + FTS5", "high"),
    ("python3", "python3", ["--version"], "runtime + ast", "high"),
    ("node", "node", ["--version"], "js/ts ecosystem", "medium"),
    ("npm", "npm", ["--version"], "js packages", "low"),
    ("pnpm", "pnpm", ["--version"], "js packages", "low"),
    ("ollama", "ollama", ["--version"], "local models", "high"),
    ("docker", "docker", ["--version"], "containers", "low"),
    ("jq", "jq", ["--version"], "json query", "medium"),
    ("yq", "yq", ["--version"], "yaml query", "medium"),
    ("file", "file", ["--version"], "signature probe", "high"),
    ("unzip", "unzip", ["-v"], "zip archives", "medium"),
)


def detect_tools() -> list[dict[str, Any]]:
    return inventory()


def inventory() -> list[dict[str, Any]]:
    rows = []
    for name, binary, args, purpose, reuse in CATALOG:
        path = which(binary)
        version = None
        if path and args:
            try:
                proc = run([binary, *args])
                version = ((proc.stdout or proc.stderr or "").strip().splitlines() or [""])[0][:160]
            except Exception as exc:  # noqa: BLE001
                version = f"ERROR:{exc}"
        # GNU emacs ctags is not universal ctags
        limited = name == "ctags" and version and "Emacs" in version
        rows.append(
            {
                "name": name,
                "path": path,
                "version": version,
                "available": bool(path) and not limited,
                "limited": bool(limited),
                "purpose": purpose,
                "overlap": None,
                "reuse_value": reuse if path else "none",
                "missing": not bool(path) or bool(limited),
                "recommended": not bool(path) and reuse == "high",
                "install": False,
            }
        )
    # overlaps
    by = {r["name"]: r for r in rows}
    if by["rg"]["available"] and by["fd"]["missing"]:
        by["fd"]["overlap"] = "rg+git ls-files covers enumeration"
        by["fd"]["recommended"] = False
    if by["magika"]["missing"] and by["file"]["available"]:
        by["file"]["overlap"] = "signature fallback for Magika"
    if by["tree-sitter"]["missing"] and by["python3"]["available"]:
        by["python3"]["overlap"] = "ast.parse for Python; regex/heuristic for TS"
    if by["tika"]["missing"] and by["java"]["available"]:
        by["tika"]["recommended"] = True
        by["java"]["overlap"] = "Java present but Tika jar not installed; do not download"
    return rows
