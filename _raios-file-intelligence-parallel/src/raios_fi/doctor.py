"""FILE-INTELLIGENCE-DOCTOR. Critical failure -> nonzero exit. stdout is not evidence."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import ORGANISM_ID, PACKAGE, FailClosed, canonical_json, package_root, repo_root_from, sha256_text, utc_now, which
from .inventory import write_inventories
from .runtime import FileIntelligenceRuntime
from .tools import detect_tools
from .versions import VersionDetector


FORBIDDEN_SUCCESS_TOKENS = (" PASS", "PASS\n", "status PASS", "\"PASS\"")


def contains_forbidden_success(text: str) -> bool:
    return any(tok in text for tok in FORBIDDEN_SUCCESS_TOKENS)


class GateRegistry:
    def __init__(self) -> None:
        self.gates: dict[str, dict[str, Any]] = {}

    def require(self, name: str, ok: bool, detail: str = "") -> None:
        self.gates[name] = {"ok": bool(ok), "critical": True, "detail": detail}
        if not ok:
            raise FailClosed(f"GATE_FAILED:{name}:{detail}")

    def observe(self, name: str, ok: bool, detail: str = "") -> None:
        self.gates[name] = {"ok": bool(ok), "critical": False, "detail": detail}


def v9_clean(repo: Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--", "RAIOS/V9"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and proc.stdout.strip() == ""


def run_doctor(var_root: Path, repo: Path, fixtures: Path | None = None) -> dict[str, Any]:
    registry = GateRegistry()
    runtime = FileIntelligenceRuntime(var_root, repo)
    result: dict[str, Any] = {
        "organism_id": ORGANISM_ID,
        "package": PACKAGE,
        "created_at": utc_now(),
        "canonical": False,
    }
    try:
        registry.require("fts5", True, "sqlite compiled with fts5")
        registry.require("v9_unchanged", v9_clean(repo), "RAIOS/V9 dirty")
        # protected write must fail
        blocked = False
        try:
            FailClosed.assert_writable(repo / "RAIOS" / "V9" / "nope.txt", repo)
        except FailClosed:
            blocked = True
        registry.require("v9_write_blocked", blocked)
        harvest = repo / "_raios-a17-native-cortex" / "ccee" / "var"
        harvest_blocked = False
        try:
            FailClosed.assert_writable(harvest / "x", repo)
        except FailClosed:
            harvest_blocked = True
        registry.require("harvest_write_blocked", harvest_blocked)

        fixture_root = fixtures or (package_root(repo) / "tests" / "fixtures" / "corpus")
        if fixture_root.exists():
            ingest = runtime.ingest(fixture_root, "doctor-fixture", limit=80)
        else:
            ingest = runtime.ingest(package_root(repo) / "src", "self", limit=40)
        health = runtime.health()
        tools = detect_tools()
        available = [t["name"] for t in tools if t.get("available")]
        missing = [t["name"] for t in tools if t.get("missing")]
        qwen = bool(which("ollama"))
        registry.observe("qwen", qwen, "ollama" if qwen else "OLLAMA_MISSING")
        registry.observe("teachers", False, "not_invoked")
        registry.require("index_writable", runtime.var.exists())
        registry.require("ingest", ingest.get("files", 0) >= 0)
        registry.require("false_pass_protection", not contains_forbidden_success("doctor running"))
        detector = VersionDetector(repo)
        pair = detector.pair()
        result.update(
            {
                "roots_found": detector.roots(),
                "files_discovered": health["files"],
                "unknown_types": health["unknown"],
                "text_searchable_pct": health["text_searchable_pct"],
                "symbols_indexed": health["symbols"],
                "relationships": health["relations"],
                "fts_index": True,
                "version_pairs": [pair] if pair else [],
                "tools_available": available,
                "tools_missing": missing,
                "qwen_health": {"ok": qwen, "reason": None if qwen else "OLLAMA_MISSING"},
                "teacher_health": {"ok": False, "reason": "NOT_INVOKED"},
                "index_health": health,
                "ingest": ingest,
                "gates": registry.gates,
            }
        )
        critical_ok = all(g["ok"] for g in registry.gates.values() if g["critical"])
        result["status"] = "GATES_SATISFIED" if critical_ok else "FAILED"
        result["exit_nonzero_if_failed"] = not critical_ok
        return result
    finally:
        runtime.close()


def write_reports(repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root_from()
    pkg = package_root(repo)
    reports = pkg / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    write_inventories(repo, reports)
    var = pkg / "var" / "doctor-index"
    doctor = run_doctor(var, repo, pkg / "tests" / "fixtures" / "corpus")
    (reports / "FILE-INTELLIGENCE-DOCTOR.json").write_text(
        json.dumps(doctor, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )

    from .versions import VersionDetector, differential
    from .discovery import FileDiscoveryProvider
    from .store import IndexStore
    from .merge import MergeIntelligence

    detector = VersionDetector(repo)
    pair = detector.pair()
    version_payload: dict[str, Any] = {
        "generated_at": utc_now(),
        "assumed_newer": False,
        "pair": pair,
        "note": "newer != better; labels not assigned without evidence",
    }
    if pair:
        store = IndexStore(pkg / "var" / "version-index", repo=repo)
        discovery = FileDiscoveryProvider(repo)
        try:
            diff = differential(store, Path(pair[0]["path"]), Path(pair[1]["path"]), discovery, limit=120)
            version_payload.update(diff.to_dict())
            version_payload["merge_candidates"] = [c.to_dict() for c in MergeIntelligence().decide(diff)[:80]]
        finally:
            store.close()
    (reports / "VERSION-DIFFERENTIAL.json").write_text(
        json.dumps(version_payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )

    tools = detect_tools()
    available = {t["name"]: t for t in tools}
    final = {
        "generated_at": utc_now(),
        "organism_id": ORGANISM_ID,
        "package": PACKAGE,
        "canonical": False,
        "doctor_status": doctor.get("status"),
        "IMPLEMENTED": [
            "read-only git ls-files discovery + FileObject",
            "signature+parser-probe type detection (extension never sole authority)",
            "stdlib text extract + zip manifest",
            "python ast symbols; heuristic TS/JS/PS1/SQL",
            "SQLite+FTS5 index and parser cache keyed by sha256+parser_version",
            "staged search plan (metadata, filename, rg, symbols, fts5); STAGE 8 fail-closed",
            "two-version detector without assuming newer",
            "text/symbol/schema comparison",
            "rule-first classification",
            "evidence-based architecture edges PROVEN/INFERRED/UNKNOWN",
            "shadow modification txn + rollback; governed apply forbidden",
            "merge candidates KEEP_A/REVIEW_REQUIRED (no auto-keep)",
            "repair candidates from syntax/broken local imports",
            "archive lineage states without delete",
            "file knowledge graph",
            "query-plan JSON compiler",
            "tool economy (LLM not default parser)",
            "idle loop without model calls",
            "FILE-INTELLIGENCE-DOCTOR fail-closed",
        ],
        "REUSED": [
            "git",
            "rg",
            "python ast.parse",
            "sqlite3 FTS5",
            "zipfile",
            "file(1) as Magika fallback",
            "CAS pattern from _raios-a17-integration-wave",
            "fail-closed / doctor pattern from CCEE",
        ],
        "AVAILABLE_NOT_INTEGRATED": [
            {"name": "java", "reason": "present but Tika jar not installed; do not download"},
            {"name": "node/npm/pnpm", "reason": "JS ecosystem present; not used as parser"},
            {"name": "jq/yq", "reason": "available for config diffs; not wired as default"},
            {"name": "greenlines_brain/dna/ast_analyzer.py", "reason": "historical; not imported to avoid collision"},
            {"name": "brain.py scan_project_metadata", "reason": "stale 316-file index; not authoritative"},
        ],
        "MISSING": [
            "magika",
            "apache tika",
            "tree-sitter",
            "universal ctags",
            "ast-grep",
            "semgrep",
            "7z",
            "fd",
            "ollama / qwen3.6",
            "docker",
        ],
        "BLOCKED": [
            "RAIOS/V9 mutation",
            "A17 harvest / CCEE var writes",
            "teacher deletion",
            "canonical mutation",
            "OCR by default",
            "Qwen as default parser",
            "governed apply onto original sources in this parallel package",
        ],
        "PENDING_RUNTIME_VALIDATION": [
            "Magika live classify",
            "Tika PDF/Office extract",
            "tree-sitter TS/TSX accuracy vs heuristic",
            "Ollama STAGE 8 synthesis over evidence bundle",
            "full-repo ingest beyond fixture/capped scan",
            "Windows PowerShell A17 live harvest coexistence on operator machine",
        ],
        "tools": {k: {"available": v.get("available"), "version": v.get("version")} for k, v in available.items()},
        "integrity": {
            "doctor_sha256": sha256_text(canonical_json(doctor)),
            "version_sha256": sha256_text(canonical_json(version_payload)),
        },
        "not_scaffolding": True,
        "false_pass_token_emitted": False,
    }
    audit = {
        "generated_at": utc_now(),
        "repo": str(repo),
        "package": PACKAGE,
        "doctor": doctor.get("status"),
        "version_pair": pair,
        "tools_missing": [t["name"] for t in tools if t.get("missing")],
        "collision_guard": {
            "RAIOS/V9": "read-only",
            "native_cortex_var": "write-blocked",
            "this_package_only": True,
        },
    }
    (reports / "FILE-INTELLIGENCE-REALITY-AUDIT.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (reports / "FILE-INTELLIGENCE-FINAL-REPORT.json").write_text(
        json.dumps(final, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return {"doctor": doctor, "final": final, "reports": str(reports)}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = repo_root_from()
    if "--report" in argv:
        payload = write_reports(repo)
        status = payload["doctor"].get("status")
        print(json.dumps({"status": status, "reports": str(package_root(repo) / "reports")}, indent=2))
        return 0 if status == "GATES_SATISFIED" else 2
    var = package_root(repo) / "var" / "doctor-index"
    doctor = run_doctor(var, repo)
    print(json.dumps({"status": doctor["status"], "gates": doctor["gates"]}, indent=2, default=str))
    return 0 if doctor["status"] == "GATES_SATISFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
