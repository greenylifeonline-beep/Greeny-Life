"""C1-authorized deterministic actions executed by the existing command worker."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..resource_fabric.census import collect_world, run_safe_probes, snapshots

RESOURCE_CENSUS = "RESOURCE_CENSUS"
DEEP_LEGACY_FORENSIC_CENSUS = "DEEP_LEGACY_FORENSIC_CENSUS"
DEEP_LEGACY_SEMANTIC_RECONCILIATION = "DEEP_LEGACY_SEMANTIC_RECONCILIATION"
DEEP_LEGACY_BEHAVIOR_RECOVERY = "DEEP_LEGACY_BEHAVIOR_RECOVERY"
MAX_MODEL_PARAMETERS_BILLION = 32
MAX_FORENSIC_TEXT_BYTES = 2 * 1024 * 1024

FORENSIC_DOMAIN_TERMS = (
    "brain", "intelligence", "commercial", "business", "marketing", "sales",
    "finance", "financial", "pricing", "crm", "customer", "supplier",
    "export", "import", "market", "opportunity", "logistics", "inventory",
    "operations", "governance", "agent", "orchestrat", "search", "learning",
    "knowledge", "model", "forecast", "risk", "quality",
)
FORENSIC_DATA_EXTENSIONS = {
    ".json", ".jsonl", ".yaml", ".yml", ".csv", ".sql", ".prisma",
    ".md", ".mdc", ".txt", ".toml",
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        for attempt in range(6):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.02 * (2**attempt))
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


class TaskActionExecutor:
    """Runs allow-listed system actions; it is not a scheduler or task ledger."""

    def __init__(
        self,
        repo: Path,
        collector: Callable[[], dict[str, Any]] = collect_world,
        prober: Callable[[dict[str, Any]], Any] = run_safe_probes,
        forensic_collector: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        semantic_collector: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        behavior_collector: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ):
        self.repo = repo.resolve()
        self.collector = collector
        self.prober = prober
        self.forensic_collector = forensic_collector
        self.semantic_collector = semantic_collector
        self.behavior_collector = behavior_collector
        self.report_root = (
            self.repo / ".ai-os/reports/command-center/resource-census"
        )
        self.forensic_report_root = (
            self.repo / ".ai-os/reports/deep-legacy-forensic/2026-09"
        )
        self.receipt_root = self.repo / ".ai-os/receipts/command-fabric"
    @staticmethod
    def _eligible(task: dict[str, Any], done: set[str]) -> bool:
        return (
            task.get("status") == "READY"
            and task.get("automation_action") in {
                RESOURCE_CENSUS,
                DEEP_LEGACY_FORENSIC_CENSUS,
                DEEP_LEGACY_SEMANTIC_RECONCILIATION,
                DEEP_LEGACY_BEHAVIOR_RECOVERY,
            }
            and task.get("dispatch_authorized_by") == "C1"
            and not task.get("claimed_by")
            and not task.get("assigned_to")
            and all(dep in done for dep in task.get("dependencies", []))
        )

    def _resource_census(self, task: dict[str, Any]) -> str:
        world = self.collector()
        self.prober(world)
        package = snapshots(world)
        task_id = str(task["id"])
        target = self.report_root / task_id
        for name, payload in package.items():
            atomic(target / name, payload)
        proof = {
            "schema": "raios.automated-resource-census.v1",
            "task_id": task_id,
            "automation_action": RESOURCE_CENSUS,
            "generated_at": utc(),
            "resource_factory_reused": True,
            "inventory": package,
            "safety": {
                "PROVIDER_MUTATION": False,
                "GPU_SESSION_STARTED": False,
                "PAID_RESOURCE_CREATED": False,
                "MODEL_DOWNLOAD_EXECUTED": False,
                "LOCAL_MODEL_STORAGE_MUTATED": False,
                "LOCAL_AG_RESERVED_FOR_CONTROL_AND_MANAGEMENT": True,
                "MAX_MODEL_PARAMETERS_BILLION": MAX_MODEL_PARAMETERS_BILLION,
                "SECOND_SCHEDULER": False,
                "SECOND_TASK_LEDGER": False,
                "SECOND_PROVIDER_REGISTRY": False,
            },
        }
        evidence = target / "AUTOMATED-RESOURCE-CENSUS.json"
        atomic(evidence, proof)
        rel = evidence.relative_to(self.repo).as_posix()
        receipt = {
            "schema": "raios.system-task-action-receipt.v1",
            "task_id": task_id,
            "action": RESOURCE_CENSUS,
            "status": "COMPLETE_EVIDENCE_VERIFIED",
            "evidence": rel,
            "executed_at": utc(),
            **proof["safety"],
        }
        atomic(
            self.receipt_root / f"{task_id}.resource-census.receipt.json", receipt
        )
        return rel
    def _git_output(self, *args: str, timeout: int = 60) -> str:
        env = dict(os.environ)
        env["GIT_OPTIONAL_LOCKS"] = "0"
        proc = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            errors="replace",
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "FORENSIC_GIT_READ_FAILED::"
                + " ".join(args)
                + "::"
                + (proc.stderr or "")[:800]
            )
        return proc.stdout

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _domain_hits(value: str) -> list[str]:
        text = value.lower()
        return sorted({term for term in FORENSIC_DOMAIN_TERMS if term in text})

    def _existing_forensic_evidence(self) -> dict[str, Any]:
        roots = [
            self.repo / ".ai-os/reports/master-estate-census",
            self.repo / "RAIOS/V9/agents/a13",
            self.repo / "intelligence/knowledge_base/assimilated",
            self.repo / "canonical/KNOWLEDGE-BASE",
            self.repo / "canonical/legacy-data",
        ]
        files = []
        missing = []
        for root in roots:
            if not root.exists():
                missing.append(root.relative_to(self.repo).as_posix())
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if self.forensic_report_root in path.parents:
                    continue
                rel = path.relative_to(self.repo).as_posix()
                size = path.stat().st_size
                row = {"path": rel, "bytes": size}
                if size <= 32 * 1024 * 1024:
                    row["sha256"] = self._sha256_file(path)
                else:
                    row["sha256"] = None
                    row["hash_state"] = "DEFERRED_LARGE_FILE_PHASE2"
                row["domain_hits"] = self._domain_hits(rel)
                files.append(row)
        return {
            "roots": [r.relative_to(self.repo).as_posix() for r in roots],
            "missing_roots": missing,
            "files": sorted(files, key=lambda x: x["path"]),
        }

    def _collect_deep_legacy_forensic_census(
        self, task: dict[str, Any]
    ) -> dict[str, Any]:
        tracked = [
            p for p in self._git_output("ls-files", "-z").split("\0") if p
        ]
        current_files = []
        current_candidates = []
        data_schema_knowledge = []
        for rel in tracked:
            if "Greeny-Life-Repair" in rel:
                raise RuntimeError("RETIRED_REPAIR_TREE_REFERENCE_IN_TRACKED_PATH")
            path = self.repo / rel
            if not path.is_file():
                continue
            size = path.stat().st_size
            row = {
                "path": rel.replace("\\", "/"),
                "bytes": size,
                "sha256": self._sha256_file(path),
                "extension": path.suffix.lower(),
                "domain_hits": self._domain_hits(rel),
            }
            current_files.append(row)
            if row["domain_hits"]:
                current_candidates.append(row)
            rel_lower = rel.lower()
            if (
                path.suffix.lower() in FORENSIC_DATA_EXTENSIONS
                and any(
                    token in rel_lower
                    for token in (
                        "canonical", "knowledge", "schema", "data", "crm",
                        "intelligence", "brain", "business", "commercial",
                        "sales", "finance", "marketing", "pricing", "export",
                        "supplier", "customer", "inventory", "governance",
                    )
                )
            ):
                data_schema_knowledge.append(row)

        refs_raw = self._git_output(
            "for-each-ref",
            "--format=%(refname)|%(objectname)|%(committerdate:iso-strict)",
        )
        refs = []
        for line in refs_raw.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                refs.append(
                    {"ref": parts[0], "object": parts[1], "committerdate": parts[2]}
                )

        commit_count_raw = self._git_output("rev-list", "--all", "--count").strip()
        commit_count = int(commit_count_raw or "0")
        objects_raw = self._git_output("rev-list", "--all", "--objects", timeout=120)
        historical_candidates = []
        object_count = 0
        unique_history_paths = set()
        for line in objects_raw.splitlines():
            if not line.strip():
                continue
            object_count += 1
            oid, sep, path = line.partition(" ")
            if not sep or not path:
                continue
            path = path.replace("\\", "/")
            unique_history_paths.add(path)
            hits = self._domain_hits(path)
            if hits:
                historical_candidates.append(
                    {"object": oid, "path": path, "domain_hits": hits}
                )

        evidence = self._existing_forensic_evidence()
        historical_unique = {}
        for row in historical_candidates:
            historical_unique[(row["object"], row["path"])] = row
        historical_candidates = sorted(
            historical_unique.values(), key=lambda x: (x["path"], x["object"])
        )

        domain_counts: dict[str, int] = {}
        for row in current_candidates:
            for term in row["domain_hits"]:
                domain_counts[term] = domain_counts.get(term, 0) + 1
        history_domain_counts: dict[str, int] = {}
        for row in historical_candidates:
            for term in row["domain_hits"]:
                history_domain_counts[term] = history_domain_counts.get(term, 0) + 1

        head = self._git_output("rev-parse", "HEAD").strip()
        generated = utc()
        safety = {
            "READ_ONLY_SOURCE_AUDIT": True,
            "SOURCE_FILE_DELETED": False,
            "SOURCE_FILE_MOVED": False,
            "SOURCE_FILE_EDITED": False,
            "GIT_CHECKOUT_PERFORMED": False,
            "GIT_RESET_PERFORMED": False,
            "GIT_CLEAN_PERFORMED": False,
            "RETIRED_REPAIR_TREE_READ": False,
            "EXTERNAL_WEB_USED": False,
            "PAID_RESOURCE_USED": False,
            "CANONICAL_PROMOTION_EXECUTED": False,
            "SAFE_TO_REMOVE_SOURCE": False,
        }
        return {
            "00-SURFACE-CENSUS.json": {
                "schema": "raios.deep-legacy-forensic.surface-census.v1",
                "task_id": task.get("id"),
                "generated_at": generated,
                "canonical_head": head,
                "tracked_file_count": len(current_files),
                "git_ref_count": len(refs),
                "git_commit_count": commit_count,
                "git_object_count": object_count,
                "unique_history_path_count": len(unique_history_paths),
                "authorized_sources": [
                    "CURRENT_CANONICAL_TREE",
                    "CANONICAL_GIT_HISTORY_AND_REFS",
                    "MASTER_ESTATE_CENSUS",
                    "A13_AGENT_CAPABILITY_DEDUP_EVIDENCE",
                    "ASSIMILATED_CAPABILITY_MANIFESTS",
                    "CANONICAL_KNOWLEDGE_AND_LEGACY_DATA_REPORTS",
                ],
                "forbidden_sources": ["RETIRED_GREENY_LIFE_REPAIR_TREE"],
                "safety": safety,
            },
            "01-CURRENT-HASH-MANIFEST.json": {
                "schema": "raios.deep-legacy-forensic.current-hash-manifest.v1",
                "generated_at": generated,
                "canonical_head": head,
                "files": current_files,
            },
            "02-GIT-HISTORY-LINEAGE.json": {
                "schema": "raios.deep-legacy-forensic.git-lineage.v1",
                "generated_at": generated,
                "canonical_head": head,
                "refs": refs,
                "commit_count": commit_count,
                "object_count": object_count,
                "unique_history_path_count": len(unique_history_paths),
                "legacy_domain_candidate_objects": historical_candidates,
            },
            "03-LEGACY-CAPABILITY-CANDIDATES.json": {
                "schema": "raios.deep-legacy-forensic.capability-candidates.v1",
                "generated_at": generated,
                "current_candidate_count": len(current_candidates),
                "historical_candidate_count": len(historical_candidates),
                "current_domain_counts": domain_counts,
                "history_domain_counts": history_domain_counts,
                "current_candidates": current_candidates,
                "historical_candidates": historical_candidates,
                "classification": "CANDIDATE_ONLY_REQUIRES_SEMANTIC_BEHAVIORAL_REVIEW",
            },
            "04-DATA-SCHEMA-KNOWLEDGE-CENSUS.json": {
                "schema": "raios.deep-legacy-forensic.data-schema-knowledge.v1",
                "generated_at": generated,
                "candidate_count": len(data_schema_knowledge),
                "files": sorted(data_schema_knowledge, key=lambda x: x["path"]),
                "semantic_coverage_proven": False,
            },
            "05-EXISTING-EVIDENCE-INVENTORY.json": {
                "schema": "raios.deep-legacy-forensic.existing-evidence.v1",
                "generated_at": generated,
                **evidence,
            },
            "DELETE-ELIGIBILITY-REPORT.json": {
                "schema": "raios.deep-legacy-forensic.delete-eligibility.v1",
                "generated_at": generated,
                "task_id": task.get("id"),
                "decision": "DENY",
                "safe_to_remove_source": False,
                "legacy_delete_allowed": False,
                "deep_legacy_forensic_audit_pass": False,
                "unique_value_unresolved": "UNKNOWN",
                "missing_proofs": [
                    "SEMANTIC_CAPABILITY_EQUIVALENCE",
                    "BEHAVIOR_EQUIVALENCE_OR_SUPERIOR_REPLACEMENT",
                    "ALL_UNIQUE_VALUE_RECOVERED_OR_RETAINED",
                    "DATA_SCHEMA_KNOWLEDGE_COVERAGE",
                    "RECOVERY_ROLLBACK_PROOF",
                    "ZERO_UNKNOWN_UNCLASSIFIED_UNRESOLVED",
                    "C1_FINAL_DELETE_GATE",
                ],
                "safety": safety,
            },
            "PHASE1-FORENSIC-EVIDENCE.json": {
                "schema": "raios.deep-legacy-forensic.phase1-evidence.v1",
                "generated_at": generated,
                "task_id": task.get("id"),
                "canonical_head": head,
                "phase": "DETERMINISTIC_CENSUS_AND_LINEAGE",
                "status": "COMPLETE_EVIDENCE_VERIFIED",
                "current_tracked_files": len(current_files),
                "historical_unique_paths": len(unique_history_paths),
                "historical_domain_candidates": len(historical_candidates),
                "current_domain_candidates": len(current_candidates),
                "existing_evidence_files": len(evidence["files"]),
                "next_required_phase": "SEMANTIC_BEHAVIORAL_UNIQUE_VALUE_RECONCILIATION",
                "full_forensic_audit_complete": False,
                "safe_to_remove_source": False,
                "safety": safety,
            },
        }

    def _deep_legacy_forensic_census(self, task: dict[str, Any]) -> str:
        package = (
            self.forensic_collector(task)
            if self.forensic_collector is not None
            else self._collect_deep_legacy_forensic_census(task)
        )
        task_id = str(task["id"])
        target = self.forensic_report_root / task_id
        for name, payload in package.items():
            atomic(target / name, payload)
        evidence = target / "PHASE1-FORENSIC-EVIDENCE.json"
        if not evidence.is_file():
            raise RuntimeError("FORENSIC_PHASE1_EVIDENCE_MISSING")
        rel = evidence.relative_to(self.repo).as_posix()
        receipt = {
            "schema": "raios.system-task-action-receipt.v1",
            "task_id": task_id,
            "action": DEEP_LEGACY_FORENSIC_CENSUS,
            "status": "COMPLETE_EVIDENCE_VERIFIED",
            "evidence": rel,
            "executed_at": utc(),
            "source_mutation": False,
            "retired_repair_tree_read": False,
            "safe_to_remove_source": False,
            "full_forensic_audit_complete": False,
            "next_required_phase": "SEMANTIC_BEHAVIORAL_UNIQUE_VALUE_RECONCILIATION",
        }
        atomic(
            self.receipt_root / f"{task_id}.deep-legacy-forensic-census.receipt.json",
            receipt,
        )
        return rel

    @staticmethod
    def _semantic_tokens(text: str) -> set[str]:
        raw = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text.lower())
        stop = {
            "the","and","for","with","from","this","that","true","false","none",
            "return","import","class","function","const","let","var","self","path",
            "json","string","status","schema","task","file","files","data","value",
        }
        return {t.replace("_","-") for t in raw if t not in stop}

    def _current_blob_index(self) -> tuple[dict[str, str], dict[str, list[str]]]:
        raw = self._git_output("ls-files", "-s", "-z")
        by_path: dict[str, str] = {}
        by_oid: dict[str, list[str]] = {}
        for row in raw.split("\0"):
            if not row or "\t" not in row:
                continue
            left, path = row.split("\t", 1)
            parts = left.split()
            if len(parts) < 3:
                continue
            oid = parts[1]
            rel = path.replace("\\", "/")
            by_path[rel] = oid
            by_oid.setdefault(oid, []).append(rel)
        return by_path, by_oid

    def _git_batch_meta(self, oids: list[str]) -> dict[str, dict[str, Any]]:
        unique = list(dict.fromkeys(x for x in oids if x))
        if not unique:
            return {}
        proc = subprocess.run(
            ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
            cwd=self.repo,
            input="\n".join(unique) + "\n",
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
            errors="replace",
        )
        if proc.returncode != 0:
            raise RuntimeError("FORENSIC_BATCH_META_FAILED::" + (proc.stderr or "")[:800])
        out: dict[str, dict[str, Any]] = {}
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[2].isdigit():
                out[parts[0]] = {"type": parts[1], "bytes": int(parts[2])}
        return out

    def _git_blob_text(self, oid: str) -> str:
        proc = subprocess.run(
            ["git", "cat-file", "blob", oid],
            cwd=self.repo,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
            errors="replace",
        )
        if proc.returncode != 0:
            return ""
        return proc.stdout

    def _git_blob_texts(self, oids: list[str]) -> dict[str, str]:
        unique = list(dict.fromkeys(x for x in oids if x))
        if not unique:
            return {}
        proc = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            cwd=self.repo,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proc.stdin is not None and proc.stdout is not None
        out: dict[str, str] = {}
        try:
            for requested in unique:
                proc.stdin.write((requested + "\n").encode("ascii"))
                proc.stdin.flush()
                header = proc.stdout.readline()
                if not header:
                    break
                text = header.decode("utf-8", errors="replace").rstrip("\n")
                if text.endswith(" missing"):
                    continue
                parts = text.split()
                if len(parts) < 3 or not parts[2].isdigit():
                    continue
                oid, obj_type, raw_size = parts[0], parts[1], int(parts[2])
                content = proc.stdout.read(raw_size)
                proc.stdout.read(1)
                if obj_type == "blob" and raw_size <= MAX_FORENSIC_TEXT_BYTES:
                    decoded = content.decode("utf-8", errors="replace")
                    out[requested] = decoded
                    out[oid] = decoded
            proc.stdin.close()
            proc.wait(timeout=120)
        finally:
            if proc.poll() is None:
                proc.kill()
        if proc.returncode not in (0, None):
            err = proc.stderr.read() if proc.stderr is not None else b""
            raise RuntimeError(
                "FORENSIC_BATCH_BLOB_READ_FAILED::"
                + err.decode("utf-8", errors="replace")[:800]
            )
        return out

    def _phase1_package(self, task: dict[str, Any]) -> dict[str, Any]:
        deps = [str(x) for x in (task.get("dependencies") or []) if str(x)]
        if not deps:
            raise RuntimeError("FORENSIC_PHASE2_REQUIRES_PHASE1_DEPENDENCY")
        phase1_id = deps[0]
        root = self.forensic_report_root / phase1_id
        required = {
            "surface": "00-SURFACE-CENSUS.json",
            "current": "01-CURRENT-HASH-MANIFEST.json",
            "lineage": "02-GIT-HISTORY-LINEAGE.json",
            "candidates": "03-LEGACY-CAPABILITY-CANDIDATES.json",
            "data": "04-DATA-SCHEMA-KNOWLEDGE-CENSUS.json",
            "evidence": "PHASE1-FORENSIC-EVIDENCE.json",
        }
        package = {}
        for key, name in required.items():
            path = root / name
            if not path.is_file():
                raise RuntimeError(f"FORENSIC_PHASE1_INPUT_MISSING::{name}")
            package[key] = json.loads(path.read_text(encoding="utf-8-sig"))
        if package["evidence"].get("status") != "COMPLETE_EVIDENCE_VERIFIED":
            raise RuntimeError("FORENSIC_PHASE1_NOT_VERIFIED")
        return package

    def _collect_deep_legacy_semantic_reconciliation(
        self, task: dict[str, Any]
    ) -> dict[str, Any]:
        phase1 = self._phase1_package(task)
        by_path, by_oid = self._current_blob_index()
        historical = list(
            phase1["lineage"].get("legacy_domain_candidate_objects") or []
        )
        current_candidates = list(
            phase1["candidates"].get("current_candidates") or []
        )
        meta = self._git_batch_meta(
            [str(row.get("object") or "") for row in historical]
        )

        exact_rows = []
        changed_same_path = []
        historical_only = []
        for row in historical:
            oid = str(row.get("object") or "")
            path = str(row.get("path") or "").replace("\\", "/")
            if not oid or not path:
                continue
            if oid in by_oid:
                exact_rows.append({
                    "historical_object": oid,
                    "historical_path": path,
                    "current_paths_with_exact_blob": sorted(by_oid[oid]),
                    "coverage": "EXACT_CURRENT_CONTENT_MATCH",
                    "unique_value_unresolved": False,
                })
            elif path in by_path:
                changed_same_path.append({
                    "historical_object": oid,
                    "historical_path": path,
                    "current_object": by_path[path],
                    "coverage": "SAME_PATH_DIFFERENT_CONTENT",
                })
            else:
                historical_only.append({
                    "historical_object": oid,
                    "historical_path": path,
                    "coverage": "HISTORICAL_PATH_NOT_CURRENT",
                })

        text_exts = set(FORENSIC_DATA_EXTENSIONS) | {
            ".py",".ts",".tsx",".js",".jsx",".ps1",".sh",".html",".css",
        }
        current_tokens: dict[str, set[str]] = {}
        inverted: dict[str, set[str]] = {}
        current_meta = {
            str(row.get("path") or ""): row
            for row in current_candidates
            if str(row.get("path") or "")
        }
        for path, row in current_meta.items():
            p = self.repo / path
            if (
                not p.is_file()
                or p.suffix.lower() not in text_exts
                or p.stat().st_size > MAX_FORENSIC_TEXT_BYTES
            ):
                continue
            try:
                tokens = self._semantic_tokens(
                    p.read_text(encoding="utf-8-sig", errors="replace")
                )
            except OSError:
                continue
            if not tokens:
                continue
            current_tokens[path] = tokens
            for token in tokens:
                inverted.setdefault(token, set()).add(path)

        blob_texts = self._git_blob_texts([
            str(row.get("historical_object") or "")
            for row in (changed_same_path + historical_only)
            if (
                (meta.get(str(row.get("historical_object") or "")) or {}).get("type") == "blob"
                and int((meta.get(str(row.get("historical_object") or "")) or {}).get("bytes") or 0)
                    <= MAX_FORENSIC_TEXT_BYTES
                and Path(str(row.get("historical_path") or "")).suffix.lower() in text_exts
            )
        ])

        def compare_old(row: dict[str, Any], same_path: bool) -> dict[str, Any]:
            oid = str(row.get("historical_object") or "")
            old_path = str(row.get("historical_path") or "")
            ext = Path(old_path).suffix.lower()
            m = meta.get(oid) or {}
            if (
                m.get("type") != "blob"
                or int(m.get("bytes") or 0) > MAX_FORENSIC_TEXT_BYTES
                or ext not in text_exts
            ):
                return {
                    **row,
                    "semantic_state": "UNRESOLVED_BINARY_LARGE_OR_NON_TEXT",
                    "best_current_match": None,
                    "score": 0.0,
                    "old_unique_token_ratio": 1.0,
                    "unique_value_unresolved": True,
                }
            old_text = blob_texts.get(oid, "")
            old_tokens = self._semantic_tokens(old_text)
            if not old_tokens:
                return {
                    **row,
                    "semantic_state": "UNRESOLVED_EMPTY_OR_UNTOKENIZABLE",
                    "best_current_match": None,
                    "score": 0.0,
                    "old_unique_token_ratio": 1.0,
                    "unique_value_unresolved": True,
                }
            if same_path and old_path in current_tokens:
                pool = [old_path]
            else:
                counts: dict[str, int] = {}
                for token in old_tokens:
                    for candidate in inverted.get(token, ()):
                        counts[candidate] = counts.get(candidate, 0) + 1
                basename = Path(old_path).name.lower()
                stem = Path(old_path).stem.lower()
                for candidate in current_tokens:
                    cp = Path(candidate)
                    if cp.name.lower() == basename or cp.stem.lower() == stem:
                        counts[candidate] = counts.get(candidate, 0) + max(5, len(old_tokens)//20)
                pool = [
                    p for p, _ in sorted(
                        counts.items(), key=lambda kv: (-kv[1], kv[0])
                    )[:8]
                ]
            best = None
            for candidate in pool:
                cur = current_tokens.get(candidate) or set()
                if not cur:
                    continue
                inter = len(old_tokens & cur)
                union = len(old_tokens | cur) or 1
                score = inter / union
                unique_ratio = len(old_tokens - cur) / max(1, len(old_tokens))
                value = (score, -unique_ratio, candidate)
                if best is None or value > best[0]:
                    best = (value, candidate, score, unique_ratio, inter)
            if best is None:
                return {
                    **row,
                    "semantic_state": "UNRESOLVED_NO_CURRENT_TEXT_MATCH",
                    "best_current_match": None,
                    "score": 0.0,
                    "old_unique_token_ratio": 1.0,
                    "unique_value_unresolved": True,
                }
            _, candidate, score, unique_ratio, inter = best
            if score >= 0.92 and unique_ratio <= 0.03:
                state = "HIGH_SEMANTIC_COVERAGE_CANDIDATE"
                unresolved = False
            elif score >= 0.75 and unique_ratio <= 0.15:
                state = "PARTIAL_COVERAGE_REQUIRES_REVIEW"
                unresolved = True
            else:
                state = "UNRESOLVED_UNIQUE_VALUE_CANDIDATE"
                unresolved = True
            return {
                **row,
                "semantic_state": state,
                "best_current_match": candidate,
                "score": round(score, 6),
                "old_unique_token_ratio": round(unique_ratio, 6),
                "shared_token_count": inter,
                "unique_value_unresolved": unresolved,
            }

        changed_results = [compare_old(row, True) for row in changed_same_path]
        historical_only_results = [compare_old(row, False) for row in historical_only]
        semantic_rows = changed_results + historical_only_results
        unresolved = [r for r in semantic_rows if r.get("unique_value_unresolved") is True]
        high_coverage = [
            r for r in semantic_rows
            if r.get("semantic_state") == "HIGH_SEMANTIC_COVERAGE_CANDIDATE"
        ]
        partial = [
            r for r in semantic_rows
            if r.get("semantic_state") == "PARTIAL_COVERAGE_REQUIRES_REVIEW"
        ]

        by_domain: dict[str, int] = {}
        for row in unresolved:
            for hit in self._domain_hits(str(row.get("historical_path") or "")):
                by_domain[hit] = by_domain.get(hit, 0) + 1

        generated = utc()
        summary = {
            "historical_candidate_rows": len(historical),
            "exact_current_content_matches": len(exact_rows),
            "same_path_changed_rows": len(changed_same_path),
            "historical_only_rows": len(historical_only),
            "high_semantic_coverage_candidates": len(high_coverage),
            "partial_coverage_requiring_review": len(partial),
            "unresolved_unique_value_candidates": len(unresolved),
            "current_text_candidates_indexed": len(current_tokens),
        }
        safety = {
            "READ_ONLY_SOURCE_AUDIT": True,
            "SOURCE_MUTATION": False,
            "GIT_HISTORY_MUTATION": False,
            "RETIRED_REPAIR_TREE_READ": False,
            "EXTERNAL_WEB_USED": False,
            "PAID_RESOURCE_USED": False,
            "SAFE_TO_REMOVE_SOURCE": False,
        }
        return {
            "06-SEMANTIC-RECONCILIATION.json": {
                "schema": "raios.deep-legacy-forensic.semantic-reconciliation.v1",
                "generated_at": generated,
                "task_id": task.get("id"),
                "summary": summary,
                "exact_current_content_matches": exact_rows,
                "same_path_reconciliation": changed_results,
                "historical_only_reconciliation": historical_only_results,
                "classification_policy": {
                    "exact_blob_match": "PROVEN_CONTENT_COVERAGE_ONLY",
                    "high_semantic_threshold": 0.92,
                    "high_semantic_max_old_unique_ratio": 0.03,
                    "partial_threshold": 0.75,
                    "automatic_delete_authority": False,
                },
                "safety": safety,
            },
            "07-UNIQUE-VALUE-LEDGER.json": {
                "schema": "raios.deep-legacy-forensic.unique-value-ledger.v1",
                "generated_at": generated,
                "unresolved_count": len(unresolved),
                "unresolved_by_domain": by_domain,
                "rows": unresolved,
                "zero_unknown_unclassified_unresolved": len(unresolved) == 0,
                "safe_to_remove_source": False,
            },
            "PHASE2-FORENSIC-EVIDENCE.json": {
                "schema": "raios.deep-legacy-forensic.phase2-evidence.v1",
                "generated_at": generated,
                "task_id": task.get("id"),
                "phase": "DETERMINISTIC_SEMANTIC_AND_UNIQUE_VALUE_RECONCILIATION",
                "status": "COMPLETE_EVIDENCE_VERIFIED",
                "summary": summary,
                "semantic_reconciliation_phase_complete": True,
                "behavior_equivalence_proven": False,
                "recovery_rollback_proven": False,
                "full_forensic_audit_complete": False,
                "safe_to_remove_source": False,
                "next_required_phase": "BEHAVIORAL_EQUIVALENCE_AND_RECOVERY_PROOF",
                "safety": safety,
            },
            "DELETE-ELIGIBILITY-REPORT.json": {
                "schema": "raios.deep-legacy-forensic.delete-eligibility.v2",
                "generated_at": generated,
                "decision": "DENY",
                "safe_to_remove_source": False,
                "legacy_delete_allowed": False,
                "deep_legacy_forensic_audit_pass": False,
                "unresolved_unique_value_candidates": len(unresolved),
                "missing_proofs": [
                    "BEHAVIOR_EQUIVALENCE_OR_SUPERIOR_REPLACEMENT",
                    "RECOVERY_ROLLBACK_PROOF",
                    "ZERO_UNKNOWN_UNCLASSIFIED_UNRESOLVED",
                    "C1_FINAL_DELETE_GATE",
                ],
                "safety": safety,
            },
        }

    def _deep_legacy_semantic_reconciliation(self, task: dict[str, Any]) -> str:
        package = (
            self.semantic_collector(task)
            if self.semantic_collector is not None
            else self._collect_deep_legacy_semantic_reconciliation(task)
        )
        task_id = str(task["id"])
        target = self.forensic_report_root / task_id
        for name, payload in package.items():
            atomic(target / name, payload)
        evidence = target / "PHASE2-FORENSIC-EVIDENCE.json"
        if not evidence.is_file():
            raise RuntimeError("FORENSIC_PHASE2_EVIDENCE_MISSING")
        proof = json.loads(evidence.read_text(encoding="utf-8-sig"))
        if proof.get("safe_to_remove_source") is not False:
            raise RuntimeError("FORENSIC_PHASE2_FAIL_CLOSED_VIOLATION")
        rel = evidence.relative_to(self.repo).as_posix()
        atomic(
            self.receipt_root / f"{task_id}.deep-legacy-semantic.receipt.json",
            {
                "schema": "raios.system-task-action-receipt.v1",
                "task_id": task_id,
                "action": DEEP_LEGACY_SEMANTIC_RECONCILIATION,
                "status": "COMPLETE_EVIDENCE_VERIFIED",
                "evidence": rel,
                "executed_at": utc(),
                "source_mutation": False,
                "safe_to_remove_source": False,
                "full_forensic_audit_complete": False,
                "next_required_phase": "BEHAVIORAL_EQUIVALENCE_AND_RECOVERY_PROOF",
            },
        )
        return rel

    def _forensic_dependency_payload(
        self, task: dict[str, Any], filename: str
    ) -> dict[str, Any]:
        for dep in (task.get("dependencies") or []):
            path = self.forensic_report_root / str(dep) / filename
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8-sig"))
        raise RuntimeError(f"FORENSIC_DEPENDENCY_INPUT_MISSING::{filename}")

    @staticmethod
    def _python_behavior_signature(text: str) -> dict[str, Any]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(text)
        except (SyntaxError, ValueError):
            return {
                "parse_ok": False,
                "unit_hashes": [],
                "named_units": [],
                "top_level_hashes": [],
            }
        unit_hashes: list[str] = []
        named_units: list[dict[str, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                dump = ast.dump(node, include_attributes=False)
                digest = hashlib.sha256(dump.encode("utf-8")).hexdigest()
                unit_hashes.append(digest)
                named_units.append({
                    "name": str(getattr(node, "name", "")),
                    "kind": node.__class__.__name__,
                    "hash": digest,
                })
        top_level_hashes: list[str] = []
        for node in tree.body:
            if (
                isinstance(node, ast.Expr)
                and isinstance(getattr(node, "value", None), ast.Constant)
                and isinstance(node.value.value, str)
            ):
                continue
            dump = ast.dump(node, include_attributes=False)
            top_level_hashes.append(
                hashlib.sha256(dump.encode("utf-8")).hexdigest()
            )
        return {
            "parse_ok": True,
            "unit_hashes": sorted(set(unit_hashes)),
            "named_units": named_units,
            "top_level_hashes": sorted(set(top_level_hashes)),
        }

    @staticmethod
    def _json_leaf_signature(text: str) -> dict[str, Any]:
        try:
            value = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {"parse_ok": False, "leaf_hashes": [], "leaf_count": 0}
        leaves: set[str] = set()
        def walk(node: Any, key: str = "$") -> None:
            if isinstance(node, dict):
                for child_key, child_value in node.items():
                    walk(child_value, str(child_key))
            elif isinstance(node, list):
                for child in node:
                    walk(child, key)
            else:
                canonical = json.dumps(
                    node, sort_keys=True, ensure_ascii=False, default=str
                )
                basis = f"{key}={canonical}"
                leaves.add(hashlib.sha256(basis.encode("utf-8")).hexdigest())
        walk(value)
        return {
            "parse_ok": True,
            "leaf_hashes": sorted(leaves),
            "leaf_count": len(leaves),
        }

    @staticmethod
    def _code_symbol_signature(text: str, ext: str) -> set[str]:
        out: set[str] = set()
        if ext in {".ts", ".tsx", ".js", ".jsx", ".cjs"}:
            patterns = (
                r"\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)",
                r"\bclass\s+([A-Za-z_$][\w$]*)",
                r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(",
                r"\bexport\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b",
            )
        elif ext == ".ps1":
            patterns = (r"(?im)^\s*function\s+([A-Za-z0-9_-]+)",)
        elif ext == ".sh":
            patterns = (
                r"(?m)^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)",
                r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{",
            )
        else:
            patterns = ()
        for pattern in patterns:
            for match in re.findall(pattern, text):
                out.add(str(match))
        return out

    @staticmethod
    def _high_value_score(path: str, domains: list[str], ext: str) -> int:
        weights = {
            "brain": 7, "intelligence": 7, "commercial": 7, "business": 6,
            "sales": 6, "pricing": 6, "finance": 6, "customer": 5,
            "supplier": 5, "export": 5, "market": 5, "inventory": 4,
            "logistics": 4, "operations": 4, "learning": 5, "knowledge": 5,
            "governance": 4, "orchestrat": 5, "model": 4, "risk": 3,
            "quality": 3,
        }
        score = sum(weights.get(x, 1) for x in set(domains))
        if ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".cjs", ".ps1", ".sh"}:
            score += 7
        elif ext in {".json", ".jsonl", ".yaml", ".yml", ".sql", ".prisma", ".toml"}:
            score += 5
        elif ext in {".md", ".mdc", ".txt"}:
            score += 3
        if "archive" in path.lower() or "backup" in path.lower():
            score += 1
        return score

    def _collect_deep_legacy_behavior_recovery(
        self, task: dict[str, Any]
    ) -> dict[str, Any]:
        ledger = self._forensic_dependency_payload(
            task, "07-UNIQUE-VALUE-LEDGER.json"
        )
        rows = list(ledger.get("rows") or [])
        oids = [
            str(row.get("historical_object") or "")
            for row in rows if row.get("historical_object")
        ]
        meta = self._git_batch_meta(oids)
        reachable_raw = self._git_output(
            "rev-list", "--all", "--objects", timeout=120
        )
        reachable = {
            line.split(" ", 1)[0]
            for line in reachable_raw.splitlines()
            if line.strip()
        }

        tree_rows: list[dict[str, Any]] = []
        blob_rows: list[dict[str, Any]] = []
        missing_rows: list[dict[str, Any]] = []
        unreachable_rows: list[dict[str, Any]] = []
        recovery_rows: list[dict[str, Any]] = []
        for row in rows:
            oid = str(row.get("historical_object") or "")
            path = str(row.get("historical_path") or "")
            info = meta.get(oid)
            if not info:
                missing_rows.append({"object": oid, "path": path})
                continue
            obj_type = str(info.get("type") or "")
            size = int(info.get("bytes") or 0)
            is_reachable = oid in reachable
            if not is_reachable:
                unreachable_rows.append({"object": oid, "path": path, "type": obj_type})
            recovery_rows.append({
                "object": oid,
                "path": path,
                "type": obj_type,
                "bytes": size,
                "reachable_from_current_refs": is_reachable,
                "retrievable": True,
                "recovery_command": (
                    f"git cat-file blob {oid}"
                    if obj_type == "blob"
                    else f"git ls-tree {oid}"
                    if obj_type == "tree"
                    else f"git cat-file -p {oid}"
                ),
            })
            enriched = {**row, "object_type": obj_type, "object_bytes": size}
            if obj_type == "tree":
                enriched.update(
                    unique_value_carrier=False,
                    classification="STRUCTURAL_LINEAGE_SNAPSHOT",
                    recovery_state="RECOVERABLE_FROM_GIT",
                )
                tree_rows.append(enriched)
            elif obj_type == "blob":
                enriched.update(
                    unique_value_carrier=True,
                    recovery_state="RECOVERABLE_FROM_GIT",
                )
                blob_rows.append(enriched)

        text_exts = {
            ".py", ".ts", ".tsx", ".js", ".jsx", ".cjs", ".ps1", ".sh",
            ".json", ".jsonl", ".yaml", ".yml", ".md", ".mdc", ".txt",
            ".html", ".css", ".sql", ".csv", ".toml", ".prisma", ".log",
            ".patch",
        }
        text_oids = [
            str(row.get("historical_object") or "")
            for row in blob_rows
            if (
                Path(str(row.get("historical_path") or "")).suffix.lower()
                in text_exts
                and int(row.get("object_bytes") or 0) <= MAX_FORENSIC_TEXT_BYTES
            )
        ]
        old_texts = self._git_blob_texts(text_oids)

        tracked = [
            x for x in self._git_output("ls-files", "-z").split("\0") if x
        ]
        current_py_units: dict[str, set[str]] = {}
        current_json_leaves: dict[str, set[str]] = {}
        current_symbols: dict[str, set[str]] = {}
        current_global_tokens: set[str] = set()
        for rel in tracked:
            path = self.repo / rel
            if not path.is_file():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_FORENSIC_TEXT_BYTES:
                continue
            ext = path.suffix.lower()
            if ext not in text_exts:
                continue
            try:
                text = path.read_text(
                    encoding="utf-8-sig", errors="replace"
                )
            except OSError:
                continue
            current_global_tokens.update(self._semantic_tokens(text))
            if ext == ".py":
                sig = self._python_behavior_signature(text)
                if sig["parse_ok"]:
                    for digest in sig["unit_hashes"]:
                        current_py_units.setdefault(digest, set()).add(rel)
                    for digest in sig["top_level_hashes"]:
                        current_py_units.setdefault(digest, set()).add(rel)
            elif ext == ".json":
                sig = self._json_leaf_signature(text)
                if sig["parse_ok"]:
                    for digest in sig["leaf_hashes"]:
                        current_json_leaves.setdefault(digest, set()).add(rel)
            if ext in {".ts", ".tsx", ".js", ".jsx", ".cjs", ".ps1", ".sh"}:
                for symbol in self._code_symbol_signature(text, ext):
                    current_symbols.setdefault(symbol, set()).add(rel)

        behavior_rows: list[dict[str, Any]] = []
        data_rows: list[dict[str, Any]] = []
        review_queue: list[dict[str, Any]] = []
        python_full = 0
        json_full = 0
        symbol_full = 0
        text_token_high = 0
        parse_failures = 0

        for row in blob_rows:
            oid = str(row.get("historical_object") or "")
            path = str(row.get("historical_path") or "")
            ext = Path(path).suffix.lower()
            text = old_texts.get(oid)
            domains = self._domain_hits(path)
            static_state = "UNANALYZED_BINARY_OR_LARGE"
            coverage_ratio = 0.0
            details: dict[str, Any] = {}
            if text is not None:
                if "\x00" in text or (
                    text and text.count("\ufffd") / max(1, len(text)) > 0.02
                ):
                    static_state = "BINARY_LIKE_TEXT_REJECTED"
                elif ext == ".py":
                    sig = self._python_behavior_signature(text)
                    if not sig["parse_ok"]:
                        static_state = "PYTHON_AST_PARSE_FAILED"
                        parse_failures += 1
                    else:
                        units = set(sig["unit_hashes"]) | set(sig["top_level_hashes"])
                        hits = {x for x in units if x in current_py_units}
                        coverage_ratio = len(hits) / max(1, len(units))
                        matched_paths = sorted({
                            p for digest in hits
                            for p in current_py_units.get(digest, set())
                        })
                        static_state = (
                            "STATIC_AST_UNITS_FULLY_PRESENT_CURRENT"
                            if units and coverage_ratio == 1.0
                            else "STATIC_AST_UNITS_PARTIAL_OR_MISSING"
                        )
                        if static_state == "STATIC_AST_UNITS_FULLY_PRESENT_CURRENT":
                            python_full += 1
                        details = {
                            "old_behavior_unit_count": len(units),
                            "exact_current_unit_hits": len(hits),
                            "matched_current_paths": matched_paths[:40],
                            "named_units": sig["named_units"][:80],
                        }
                        behavior_rows.append({
                            "historical_object": oid,
                            "historical_path": path,
                            "language": "PYTHON",
                            "static_state": static_state,
                            "coverage_ratio": round(coverage_ratio, 6),
                            **details,
                        })
                elif ext == ".json":
                    sig = self._json_leaf_signature(text)
                    if not sig["parse_ok"]:
                        static_state = "JSON_PARSE_FAILED"
                        parse_failures += 1
                    else:
                        leaves = set(sig["leaf_hashes"])
                        hits = {x for x in leaves if x in current_json_leaves}
                        coverage_ratio = len(hits) / max(1, len(leaves))
                        matched_paths = sorted({
                            p for digest in hits
                            for p in current_json_leaves.get(digest, set())
                        })
                        static_state = (
                            "STRUCTURED_LEAF_VALUES_FULLY_PRESENT_CURRENT"
                            if leaves and coverage_ratio == 1.0
                            else "STRUCTURED_LEAF_VALUES_PARTIAL_OR_MISSING"
                        )
                        if static_state == "STRUCTURED_LEAF_VALUES_FULLY_PRESENT_CURRENT":
                            json_full += 1
                        details = {
                            "old_leaf_count": len(leaves),
                            "exact_current_leaf_hits": len(hits),
                            "matched_current_paths": matched_paths[:40],
                        }
                        data_rows.append({
                            "historical_object": oid,
                            "historical_path": path,
                            "format": "JSON",
                            "static_state": static_state,
                            "coverage_ratio": round(coverage_ratio, 6),
                            **details,
                        })
                elif ext in {".ts", ".tsx", ".js", ".jsx", ".cjs", ".ps1", ".sh"}:
                    symbols = self._code_symbol_signature(text, ext)
                    hits = {x for x in symbols if x in current_symbols}
                    coverage_ratio = len(hits) / max(1, len(symbols))
                    static_state = (
                        "CODE_SYMBOL_SURFACE_FULLY_PRESENT_CURRENT"
                        if symbols and coverage_ratio == 1.0
                        else "CODE_SYMBOL_SURFACE_PARTIAL_OR_MISSING"
                    )
                    if static_state == "CODE_SYMBOL_SURFACE_FULLY_PRESENT_CURRENT":
                        symbol_full += 1
                    details = {
                        "old_symbols": sorted(symbols),
                        "matched_symbols": sorted(hits),
                        "matched_current_paths": sorted({
                            p for symbol in hits
                            for p in current_symbols.get(symbol, set())
                        })[:40],
                    }
                    behavior_rows.append({
                        "historical_object": oid,
                        "historical_path": path,
                        "language": ext.lstrip(".").upper(),
                        "static_state": static_state,
                        "coverage_ratio": round(coverage_ratio, 6),
                        **details,
                    })
                else:
                    tokens = self._semantic_tokens(text)
                    hits = tokens & current_global_tokens
                    coverage_ratio = len(hits) / max(1, len(tokens))
                    static_state = (
                        "TEXT_TOKEN_SURFACE_HIGH_COVERAGE"
                        if tokens and coverage_ratio >= 0.98
                        else "TEXT_TOKEN_SURFACE_PARTIAL_OR_MISSING"
                    )
                    if static_state == "TEXT_TOKEN_SURFACE_HIGH_COVERAGE":
                        text_token_high += 1
                    details = {
                        "old_token_count": len(tokens),
                        "current_global_token_hits": len(hits),
                    }

            score = self._high_value_score(path, domains, ext)
            if str(row.get("coverage") or "") == "HISTORICAL_PATH_NOT_CURRENT":
                score += 3
            semantic_score = float(row.get("score") or 0.0)
            if semantic_score < 0.5:
                score += 3
            priority = (
                "CRITICAL" if score >= 18
                else "HIGH" if score >= 12
                else "MEDIUM" if score >= 7
                else "LOW"
            )
            review_queue.append({
                "historical_object": oid,
                "historical_path": path,
                "object_bytes": int(row.get("object_bytes") or 0),
                "extension": ext or "<none>",
                "domains": domains,
                "priority_score": score,
                "priority": priority,
                "phase2_semantic_state": row.get("semantic_state"),
                "phase2_best_current_match": row.get("best_current_match"),
                "phase2_score": row.get("score"),
                "static_state": static_state,
                "static_coverage_ratio": round(coverage_ratio, 6),
                "static_details": details,
                "recovery_state": "RECOVERABLE_FROM_GIT",
                "requires_behavior_or_assimilation_review": True,
                "automatic_delete_authority": False,
            })

        review_queue.sort(
            key=lambda x: (-int(x["priority_score"]), x["historical_path"])
        )
        critical_business = [
            row for row in review_queue
            if set(row["domains"]) & {
                "commercial", "business", "sales", "pricing", "finance",
                "customer", "supplier", "export", "market", "inventory",
                "logistics", "operations",
            }
        ]
        recovery_ok = not missing_rows and not unreachable_rows
        generated = utc()
        summary = {
            "phase2_raw_unresolved_rows": len(rows),
            "structural_tree_snapshots_reclassified": len(tree_rows),
            "content_blob_rows_requiring_value_review": len(blob_rows),
            "retrievable_objects": len(recovery_rows),
            "missing_objects": len(missing_rows),
            "unreachable_objects": len(unreachable_rows),
            "object_recovery_proven": recovery_ok,
            "python_static_full_coverage_candidates": python_full,
            "json_static_full_coverage_candidates": json_full,
            "code_symbol_full_coverage_candidates": symbol_full,
            "text_token_high_coverage_candidates": text_token_high,
            "parse_failures": parse_failures,
            "high_value_review_queue": len(review_queue),
            "business_commercial_review_queue": len(critical_business),
        }
        safety = {
            "READ_ONLY_SOURCE_AUDIT": True,
            "SOURCE_MUTATION": False,
            "GIT_HISTORY_MUTATION": False,
            "RETIRED_REPAIR_TREE_READ": False,
            "EXTERNAL_WEB_USED": False,
            "PAID_RESOURCE_USED": False,
            "AUTOMATIC_DELETE_AUTHORITY": False,
            "SAFE_TO_REMOVE_SOURCE": False,
        }
        provenance = [
            "audit_ast_extraction.py",
            "RAIOS/V9/runtime/git_history_search.py",
            "RAIOS/V9/runtime/a13_agent_capability_dedup_certification.py",
        ]
        return {
            "08-OBJECT-TYPE-NORMALIZATION.json": {
                "schema": "raios.deep-legacy-forensic.object-normalization.v1",
                "generated_at": generated,
                "summary": {
                    "input_rows": len(rows),
                    "tree_rows": len(tree_rows),
                    "blob_rows": len(blob_rows),
                    "missing_rows": len(missing_rows),
                },
                "tree_snapshots": tree_rows,
                "classification_rule": (
                    "Git tree objects preserve historical directory structure; "
                    "they are not independent file-content capability assets. "
                    "Their descendant blobs remain subject to value review."
                ),
                "safety": safety,
            },
            "09-STATIC-BEHAVIOR-SIGNATURES.json": {
                "schema": "raios.deep-legacy-forensic.static-behavior.v1",
                "generated_at": generated,
                "method_provenance": provenance,
                "rows": behavior_rows,
                "full_static_coverage_is_not_runtime_equivalence": True,
                "behavior_equivalence_proven": False,
                "safety": safety,
            },
            "10-STRUCTURED-DATA-COVERAGE.json": {
                "schema": "raios.deep-legacy-forensic.structured-data.v1",
                "generated_at": generated,
                "method_provenance": provenance,
                "rows": data_rows,
                "full_static_coverage_is_not_assimilation_proof": True,
                "safety": safety,
            },
            "11-RECOVERY-REACHABILITY-PROOF.json": {
                "schema": "raios.deep-legacy-forensic.recovery-reachability.v1",
                "generated_at": generated,
                "object_recovery_proven": recovery_ok,
                "full_runtime_rollback_proven": False,
                "retrievable_count": len(recovery_rows),
                "missing_objects": missing_rows,
                "unreachable_objects": unreachable_rows,
                "objects": recovery_rows,
                "safety": safety,
            },
            "12-HIGH-VALUE-REVIEW-QUEUE.json": {
                "schema": "raios.deep-legacy-forensic.high-value-review.v1",
                "generated_at": generated,
                "queue_count": len(review_queue),
                "business_commercial_count": len(critical_business),
                "business_commercial_priority": critical_business,
                "queue": review_queue,
                "next_action": (
                    "Target CRITICAL/HIGH business and cognitive assets for "
                    "behavior validation, extraction, assimilation or explicit retention."
                ),
                "safety": safety,
            },
            "PHASE3-FORENSIC-EVIDENCE.json": {
                "schema": "raios.deep-legacy-forensic.phase3-evidence.v1",
                "generated_at": generated,
                "task_id": task.get("id"),
                "phase": "OBJECT_NORMALIZATION_STATIC_BEHAVIOR_AND_RECOVERY",
                "status": "COMPLETE_EVIDENCE_VERIFIED",
                "summary": summary,
                "object_recovery_proven": recovery_ok,
                "behavior_equivalence_proven": False,
                "full_runtime_rollback_proven": False,
                "zero_unknown_unclassified_unresolved": len(blob_rows) == 0,
                "remaining_content_value_review_count": len(blob_rows),
                "full_forensic_audit_complete": False,
                "safe_to_remove_source": False,
                "next_required_phase": (
                    "TARGETED_HIGH_VALUE_BEHAVIOR_VALIDATION_AND_ASSIMILATION"
                ),
                "safety": safety,
            },
            "DELETE-ELIGIBILITY-REPORT.json": {
                "schema": "raios.deep-legacy-forensic.delete-eligibility.v3",
                "generated_at": generated,
                "decision": "DENY",
                "safe_to_remove_source": False,
                "legacy_delete_allowed": False,
                "deep_legacy_forensic_audit_pass": False,
                "remaining_content_value_review_count": len(blob_rows),
                "structural_tree_snapshots_reclassified": len(tree_rows),
                "object_recovery_proven": recovery_ok,
                "missing_proofs": [
                    "TARGETED_HIGH_VALUE_BEHAVIOR_VALIDATION",
                    "UNIQUE_VALUE_EXTRACTION_ASSIMILATION_OR_EXPLICIT_RETENTION",
                    "FULL_RUNTIME_ROLLBACK_OR_EQUIVALENT_RECOVERY_PROOF",
                    "ZERO_UNKNOWN_UNCLASSIFIED_UNRESOLVED",
                    "C1_FINAL_DELETE_GATE",
                ],
                "safety": safety,
            },
        }

    def _deep_legacy_behavior_recovery(self, task: dict[str, Any]) -> str:
        package = (
            self.behavior_collector(task)
            if self.behavior_collector is not None
            else self._collect_deep_legacy_behavior_recovery(task)
        )
        task_id = str(task["id"])
        target = self.forensic_report_root / task_id
        for name, payload in package.items():
            atomic(target / name, payload)
        evidence = target / "PHASE3-FORENSIC-EVIDENCE.json"
        if not evidence.is_file():
            raise RuntimeError("FORENSIC_PHASE3_EVIDENCE_MISSING")
        proof = json.loads(evidence.read_text(encoding="utf-8-sig"))
        if proof.get("safe_to_remove_source") is not False:
            raise RuntimeError("FORENSIC_PHASE3_FAIL_CLOSED_VIOLATION")
        rel = evidence.relative_to(self.repo).as_posix()
        atomic(
            self.receipt_root / f"{task_id}.deep-legacy-behavior-recovery.receipt.json",
            {
                "schema": "raios.system-task-action-receipt.v1",
                "task_id": task_id,
                "action": DEEP_LEGACY_BEHAVIOR_RECOVERY,
                "status": "COMPLETE_EVIDENCE_VERIFIED",
                "evidence": rel,
                "executed_at": utc(),
                "source_mutation": False,
                "safe_to_remove_source": False,
                "full_forensic_audit_complete": False,
                "next_required_phase": (
                    "TARGETED_HIGH_VALUE_BEHAVIOR_VALIDATION_AND_ASSIMILATION"
                ),
            },
        )
        return rel

    def execute_ready(self, data: dict[str, Any]) -> dict[str, int]:
        counts = {"actions_processed": 0, "actions_blocked": 0}
        tasks = data.get("tasks", [])
        done = {str(t.get("id")) for t in tasks if t.get("status") == "DONE"}
        for task in tasks:
            if not self._eligible(task, done):
                continue
            try:
                action = str(task.get("automation_action") or "")
                if action == RESOURCE_CENSUS:
                    evidence = self._resource_census(task)
                    executed_by = "RAIOS-SYSTEM-ACTION:RESOURCE_FACTORY"
                elif action == DEEP_LEGACY_FORENSIC_CENSUS:
                    evidence = self._deep_legacy_forensic_census(task)
                    executed_by = "RAIOS-SYSTEM-ACTION:DETERMINISTIC_FORENSIC_CENSUS"
                elif action == DEEP_LEGACY_SEMANTIC_RECONCILIATION:
                    evidence = self._deep_legacy_semantic_reconciliation(task)
                    executed_by = "RAIOS-SYSTEM-ACTION:DETERMINISTIC_SEMANTIC_RECONCILIATION"
                elif action == DEEP_LEGACY_BEHAVIOR_RECOVERY:
                    evidence = self._deep_legacy_behavior_recovery(task)
                    executed_by = "RAIOS-SYSTEM-ACTION:DETERMINISTIC_BEHAVIOR_RECOVERY"
                else:
                    continue
                task.update(
                    status="DONE",
                    executed_by=executed_by,
                    dispatch_status="AUTOMATION_COMPLETE_EVIDENCE_VERIFIED",
                    evidence=evidence,
                    completed_at=utc(),
                    automation_policy={
                        "c1_authorized": True,
                        "presence_not_required_for_deterministic_system_action": True,
                        "source_mutation_allowed": False,
                    },
                )
                done.add(str(task.get("id")))
                counts["actions_processed"] += 1
            except Exception as exc:
                task.update(
                    status="BLOCKED",
                    dispatch_status="AUTOMATION_BLOCKED",
                    blocker=f"{type(exc).__name__}:{exc}",
                    blocked_at=utc(),
                )
                counts["actions_blocked"] += 1
        return counts


def latest_resource_census(repo: Path) -> dict[str, Any]:
    root = repo.resolve() / ".ai-os/reports/command-center/resource-census"
    candidates = sorted(
        root.glob("*/AUTOMATED-RESOURCE-CENSUS.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return {
            "status": "NOT_RUN",
            "resource_factory_reused": True,
            "live_probe_on_dashboard_refresh": False,
        }
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "UNREADABLE", "error": f"{type(exc).__name__}:{exc}"}
