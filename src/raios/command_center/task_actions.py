"""C1-authorized deterministic actions executed by the existing command worker."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..resource_fabric.census import collect_world, run_safe_probes, snapshots

RESOURCE_CENSUS = "RESOURCE_CENSUS"
DEEP_LEGACY_FORENSIC_CENSUS = "DEEP_LEGACY_FORENSIC_CENSUS"
DEEP_LEGACY_SEMANTIC_RECONCILIATION = "DEEP_LEGACY_SEMANTIC_RECONCILIATION"
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
    ):
        self.repo = repo.resolve()
        self.collector = collector
        self.prober = prober
        self.forensic_collector = forensic_collector
        self.semantic_collector = semantic_collector
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
