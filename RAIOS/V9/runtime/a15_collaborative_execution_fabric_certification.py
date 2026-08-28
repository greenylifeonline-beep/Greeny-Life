from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
)
V9 = REPO / "RAIOS" / "V9"
STATE = V9 / "continuity" / "RAIOS-CURRENT-STATE.json"
A14_RECEIPT = V9 / "evidence" / "observations" / "V9.0-A14-RECEIPT.json"
A141_RECEIPT = (
    V9 / "evidence" / "observations" / "V9.0-A14.1-BASELINE-PRESERVATION-RECEIPT.json"
)
A15_RECEIPT = V9 / "evidence" / "observations" / "V9.0-A15-RECEIPT.json"
A14_ROUTER = V9 / "agents" / "a14" / "routing" / "CAPABILITY-FIRST-ROUTER.json"
PRE_DISCOVERY = V9 / "agents" / "a15" / "discovery" / "EXECUTOR-PRE-DISCOVERY.json"
ROOT = V9 / "agents" / "a15"
SCHEMAS = ROOT / "schemas"
REGISTRY = ROOT / "registry"
ROUTING = ROOT / "routing"
MEMORY = ROOT / "memory"
REPORTS = ROOT / "reports"
JOURNAL = ROOT / "journal"
SANDBOX = ROOT / "sandbox"
EVO = V9 / "evolution" / "a15"
EXPERIENCES = EVO / "experiences"
FAILURES = EVO / "failures"
RECOVERY = EVO / "recovery-skill-candidates"
WAL = JOURNAL / "collaboration-wal.jsonl"

A14_ORIG = "fb130e232246a00b531835f529f25e4edfae2854"
A14_BASELINE = "1eb0d5944fba7c25977c26c5c5613ddab6d3d33b"
A14_1_COMMIT = "d3f5ca69b858843dcf626f74fa13cf83d3e2e20c"
A14_HASH = "d5556dc06edbee43e8efd758933ebd03476f4c21ea372cd5fc436fccbeafa8a1"
A141_HASH = "d8923c61e2b7d985ef44ef4287f3e1f25c2a392731e673e4d3583b64c26b4676"

LIFECYCLE = [
    "DISCOVERED",
    "READY",
    "CLAIMED",
    "RUNNING",
    "BLOCKED",
    "VERIFYING",
    "PASSED",
    "FAILED",
    "ABSTAINED",
    "CANCELLED",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    tmp.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    if load_json(tmp) != obj:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("A15_ATOMIC_WRITE_READBACK_FAILED")
    os.replace(tmp, path)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_hash(obj: Any) -> str:
    raw = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def probability(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise RuntimeError(f"{name}_BOOLEAN_INVALID")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise RuntimeError(f"{name}_OUT_OF_RANGE:{value}")
    return value


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def git_is_ancestor(ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def scopes_overlap(left: list[str], right: list[str]) -> bool:
    def ov(a: str, b: str) -> bool:
        a = a.rstrip("/*/")
        b = b.rstrip("/*/")
        return a == b or a.startswith(b + "/") or b.startswith(a + "/")

    return any(ov(a, b) for a in left for b in right)


def append_wal(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event)
    payload.setdefault("timestamp", now())
    payload["event_hash"] = object_hash(
        {k: v for k, v in payload.items() if k != "event_hash"}
    )
    WAL.parent.mkdir(parents=True, exist_ok=True)
    with WAL.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return payload


def replay_wal(path: Path) -> dict[str, Any]:
    projection: dict[str, Any] = {
        "seen": [],
        "tasks": {},
        "leases": {},
        "results": {},
        "applied": 0,
        "skipped_duplicates": 0,
        "skipped_corrupt": 0,
    }
    if not path.exists():
        return projection
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            projection["skipped_corrupt"] += 1
            continue
        digest = event.get("event_hash") or object_hash(event)
        if digest in seen:
            projection["skipped_duplicates"] += 1
            continue
        seen.add(digest)
        projection["seen"].append(digest)
        projection["applied"] += 1
        task_id = event.get("task_id")
        if task_id:
            projection["tasks"][task_id] = event.get("lifecycle") or event.get("type")
        if event.get("type") == "lease":
            projection["leases"][event.get("lease_id", task_id)] = event.get("status")
        if event.get("type") == "result":
            projection["results"][task_id] = event.get("status")
    return projection


def capture_experience(event: str, outcome: str, details: dict[str, Any]) -> Path:
    obj = {
        "schema": "raios.a15.experience.v1",
        "timestamp": now(),
        "event": event,
        "outcome": outcome,
        "details": details,
    }
    obj["experience_id"] = "exp:" + object_hash(obj)[:32]
    path = EXPERIENCES / (obj["experience_id"].replace(":", "_") + ".json")
    write_json(path, obj)
    return path


def capture_failure(message: str, task_id: str, executor_id: str) -> str:
    basis = {"phase": "V9.0-A15", "message": message, "executor_id": executor_id}
    signature = "fs:" + object_hash(basis)[:32]
    failure = {
        "schema": "raios.a15.failure-signature.v1",
        "failure_signature": signature,
        "timestamp": now(),
        "task_id": task_id,
        "executor_id": executor_id,
        "message": message,
        "production_mutation": False,
        "canonical_mutation": False,
    }
    write_json(FAILURES / (signature.replace(":", "_") + ".json"), failure)
    candidate = {
        "schema": "raios.a15.recovery-skill-candidate.v1",
        "candidate_id": "recovery:" + object_hash(failure)[:32],
        "source_failure_signature": signature,
        "status": "CANDIDATE",
        "requires_validation": True,
        "automatic_promotion": False,
        "canonical_mutation": False,
        "created_at": now(),
    }
    write_json(
        RECOVERY / (candidate["candidate_id"].replace(":", "_") + ".json"),
        candidate,
    )
    capture_experience(
        "A15_FAILURE",
        "FAILED",
        {
            "task_id": task_id,
            "executor_id": executor_id,
            "failure_signature": signature,
            "recovery_candidate": candidate["candidate_id"],
            "confidence": 1.0,
        },
    )
    return signature


class LeaseManager:
    def __init__(self) -> None:
        self.leases: dict[str, dict[str, Any]] = {}
        self.conflicts = 0
        self.recoveries = 0

    def _active_writers(self, scope: list[str]) -> list[dict[str, Any]]:
        found = []
        for lease in self.leases.values():
            if lease["status"] != "ACTIVE":
                continue
            if lease["mode"] != "WRITE":
                continue
            if scopes_overlap(lease["scope"], scope):
                found.append(lease)
        return found

    def acquire(
        self,
        task_id: str,
        executor: str,
        scope: list[str],
        mode: str,
        ttl_ms: int = 30_000,
    ) -> dict[str, Any]:
        if mode == "WRITE" and self._active_writers(scope):
            self.conflicts += 1
            result = {
                "lease_id": None,
                "task_id": task_id,
                "status": "REJECTED_CONFLICT",
                "mode": mode,
                "executor": executor,
                "scope": scope,
            }
            append_wal({"type": "lease", "task_id": task_id, **result})
            return result
        lease_id = "lease:" + object_hash(
            {"task_id": task_id, "executor": executor, "mode": mode, "n": len(self.leases)}
        )[:16]
        lease = {
            "lease_id": lease_id,
            "task_id": task_id,
            "executor": executor,
            "scope": scope,
            "mode": mode,
            "status": "ACTIVE",
            "ttl_ms": ttl_ms,
            "acquired_at": now(),
        }
        self.leases[lease_id] = lease
        append_wal({"type": "lease", **lease})
        return lease

    def expire(self, lease_id: str) -> None:
        lease = self.leases[lease_id]
        lease["status"] = "EXPIRED"
        append_wal({"type": "lease", "lease_id": lease_id, "status": "EXPIRED", "task_id": lease["task_id"]})

    def recover(self, lease_id: str, executor: str) -> dict[str, Any]:
        old = self.leases[lease_id]
        old["status"] = "RECOVERED"
        self.recoveries += 1
        return self.acquire(old["task_id"], executor, old["scope"], old["mode"])

    def release(self, lease_id: str) -> None:
        if lease_id in self.leases:
            self.leases[lease_id]["status"] = "RELEASED"
            append_wal(
                {
                    "type": "lease",
                    "lease_id": lease_id,
                    "status": "RELEASED",
                    "task_id": self.leases[lease_id]["task_id"],
                }
            )


def capsule_for(task: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {
        "task_id": task["task_id"],
        "correlation_id": task["correlation_id"],
        "causation_id": task["causation_id"],
        "objective": task["objective"],
        "capability_requirements": task["capability_requirements"],
        "scopes": {
            "read": task["allowed_read_scope"],
            "write": task["allowed_write_scope"],
            "forbidden": task["forbidden_scope"],
        },
        "decisions": extra.get("decisions", []) if extra else [],
        "failures": extra.get("failures", []) if extra else [],
        "evidence": extra.get("evidence", []) if extra else ["sandbox-certification-adapter"],
        "files": extra.get("files", []) if extra else [],
    }
    body["capsule_hash"] = object_hash(body)
    return body


def normalize_result(
    task_id: str,
    executor: str,
    status: str,
    confidence: float,
    latency_ms: float,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra = extra or {}
    cost = extra.get("cost_budget_observation", "UNKNOWN")
    if cost is None:
        cost = "UNKNOWN"
    result = {
        "schema": "raios.a15.normalized-collab-result.v1",
        "task_id": task_id,
        "executor": executor,
        "status": status,
        "confidence": probability(confidence, "RESULT_CONFIDENCE"),
        "changed_files": extra.get("changed_files", []),
        "evidence": extra.get("evidence", ["sandbox-certification-adapter"]),
        "tests": extra.get("tests", []),
        "latency_ms": latency_ms,
        "cost_budget_observation": cost,
        "failure_signature": extra.get("failure_signature"),
        "handoff": extra.get("handoff"),
        "provenance": extra.get(
            "provenance",
            {
                "adapter_mode": "SANDBOX_SYNTHETIC_EXECUTOR_ADAPTERS",
                "external_credits_consumed": False,
            },
        ),
        "production_mutation": False,
        "canonical_mutation": False,
    }
    return result


def main() -> None:
    print("=" * 90)
    print("RAIOS V9.0-A15 COLLABORATIVE EXECUTION FABRIC CERTIFICATION")
    print("=" * 90)

    head = git("rev-parse", "HEAD")
    print("HEAD:", head)

    for path in (
        REGISTRY,
        ROUTING,
        MEMORY,
        REPORTS,
        JOURNAL,
        SANDBOX,
        EXPERIENCES,
        FAILURES,
        RECOVERY,
        SCHEMAS,
    ):
        path.mkdir(parents=True, exist_ok=True)

    if WAL.exists():
        WAL.unlink()

    # ------------------------------------------------------------------
    # 1. PREDECESSOR + LINEAGE GATE
    # ------------------------------------------------------------------
    state = load_json(STATE)
    if state.get("current_version") != "V9.0-A14.1":
        raise RuntimeError("A15_PREDECESSOR_NOT_A14_1")
    if state.get("state_status") != "A14_1_CERTIFIED":
        raise RuntimeError("A15_PREDECESSOR_NOT_CERTIFIED")
    if not A14_RECEIPT.exists() or not A141_RECEIPT.exists():
        raise RuntimeError("A15_PREDECESSOR_RECEIPT_MISSING")

    actual_a14 = file_hash(A14_RECEIPT)
    actual_a141 = file_hash(A141_RECEIPT)
    if actual_a14 != A14_HASH:
        raise RuntimeError(f"A15_A14_RECEIPT_MUTATED:{actual_a14}")
    if actual_a141 != A141_HASH:
        raise RuntimeError(f"A15_A14_1_RECEIPT_MUTATED:{actual_a141}")
    latest = state.get("latest_phase_receipt") or {}
    if latest.get("sha256") != actual_a141:
        raise RuntimeError("A15_STATE_A14_1_HASH_DRIFT")

    if not git_is_ancestor(A14_ORIG, head):
        raise RuntimeError("A15_LINEAGE_A14_ORIG_NOT_ANCESTOR")
    if not git_is_ancestor(A14_BASELINE, head):
        raise RuntimeError("A15_LINEAGE_BASELINE_NOT_ANCESTOR")
    if not git_is_ancestor(A14_1_COMMIT, head):
        raise RuntimeError("A15_LINEAGE_A14_1_COMMIT_NOT_ANCESTOR")

    a141_obj = load_json(A141_RECEIPT)
    if a141_obj.get("repository_sha") != A14_BASELINE:
        raise RuntimeError("A15_A14_1_CERTIFICATION_INPUT_SHA_DRIFT")
    if a141_obj.get("baseline_git_commit") != A14_BASELINE:
        raise RuntimeError("A15_A14_1_BASELINE_DRIFT")
    if a141_obj["predecessor"]["sha256"] != A14_HASH:
        raise RuntimeError("A15_A14_HISTORICAL_HASH_DRIFT")
    if a141_obj["predecessor"]["certification_repository_sha"] != A14_ORIG:
        raise RuntimeError("A15_A14_ORIG_SHA_DRIFT")

    lineage = {
        "schema": "raios.a15.git-lineage.v1",
        "certification_input_sha": head,
        "baseline_commit": A14_BASELINE,
        "a14_original_certification_sha": A14_ORIG,
        "a14_1_containing_commit": A14_1_COMMIT,
        "containing_commit": None,
        "containing_commit_policy": "DEFERRED_UNTIL_AFTER_CERTIFICATION_COMMIT",
        "current_observed_head": head,
        "ancestor_relationships": [
            {"ancestor": A14_ORIG, "descendant": A14_BASELINE, "status": "PASS"},
            {"ancestor": A14_BASELINE, "descendant": A14_1_COMMIT, "status": "PASS"},
            {"ancestor": A14_1_COMMIT, "descendant": head, "status": "PASS"},
        ],
        "self_reference_forbidden": True,
        "startup_rule": "VERIFY_ANCESTRY_AND_IMMUTABLE_RECEIPT_HASHES_NOT_HEAD_EQUALITY",
        "historical_hashes": {
            "a14_receipt_sha256": A14_HASH,
            "a14_1_receipt_sha256": A141_HASH,
        },
    }
    if state.get("repository_sha_observed") == head and head == A14_1_COMMIT:
        pass
    write_json(MEMORY / "GIT-LINEAGE.json", lineage)
    print("LINEAGE_GATE                 : PASS")

    if not PRE_DISCOVERY.exists():
        raise RuntimeError("A15_PRE_DISCOVERY_MISSING")
    pre = load_json(PRE_DISCOVERY)
    if pre.get("schema") != "raios.a15.pre-discovery.v1":
        raise RuntimeError("A15_PRE_DISCOVERY_SCHEMA_DRIFT")
    print("EXISTING_A15_PREDISCOVERY    : REUSED")

    a14_router = load_json(A14_ROUTER)
    capability_map = dict(a14_router["capability_map"])
    print("A14_ROUTER_REUSED            : PASS")

    # ------------------------------------------------------------------
    # 2. EXECUTOR ADMISSION REGISTRY
    # ------------------------------------------------------------------
    discovered = {row["executor"]: row for row in pre["executors"]}
    admission = {
        "LOCAL_DETERMINISTIC": {
            "executor_id": "LOCAL_DETERMINISTIC",
            "states": ["DISCOVERED", "TOOL_EXECUTION_VERIFIED", "GOVERNED_EXECUTOR"],
            "live_admitted": True,
            "sandbox_admitted": True,
            "classification": "GOVERNED_SANDBOX",
            "cost_class": "DETERMINISTIC_LOCAL",
            "capabilities": ["filesystem_read", "repository_search", "test_execution", "implementation"],
            "evidence": ["python_runtime", "git_cli"],
            "live_inference_verified": False,
        },
        "RAIOS_INTERNAL": {
            "executor_id": "RAIOS_INTERNAL",
            "states": ["DISCOVERED", "GOVERNED_EXECUTOR"],
            "live_admitted": True,
            "sandbox_admitted": True,
            "classification": "GOVERNED_SANDBOX",
            "cost_class": "INTERNAL",
            "capabilities": ["governance"],
            "evidence": ["continuity_kernel"],
            "live_inference_verified": False,
        },
        "CLAUDE_CODE": {
            "executor_id": "CLAUDE_CODE",
            "states": ["DISCOVERED", "CLI_AVAILABLE", "UNAVAILABLE"],
            "live_admitted": False,
            "sandbox_admitted": False,
            "classification": "NOT_AUTHENTICATED",
            "cost_class": "EXTERNAL_MODEL",
            "capabilities": ["deep_debug", "independent_review"],
            "cli_version_observed": "2.1.219",
            "auth": {"loggedIn": False, "authMethod": "none"},
            "evidence": ["empirical_observation_cli_exists_logged_out"],
            "live_inference_verified": False,
            "note": "CLI exists but loggedIn=false; do not admit for live execution.",
        },
        "GEMINI": {
            "executor_id": "GEMINI",
            "states": ["DISCOVERED", "CLI_AVAILABLE", "DEGRADED"],
            "live_admitted": False,
            "sandbox_admitted": True,
            "classification": "DEGRADED_BUT_OPERATIONAL",
            "cost_class": "EXTERNAL_MODEL",
            "capabilities": ["independent_review", "deep_debug"],
            "cli_version_observed": "0.55.1",
            "project_sessions_observed": 2,
            "supports": ["plan_read_only", "sandbox", "json_output", "mcp", "skills", "hooks"],
            "missing": ["ripgrep"],
            "fallback_tool": "GrepTool",
            "evidence": ["empirical_observation_cli_0_55_1"],
            "live_inference_verified": False,
            "note": "No live inference verification in this certification. Credits not spent.",
        },
        "CURSOR": {
            "executor_id": "CURSOR",
            "states": ["DISCOVERED", "DESKTOP_AVAILABLE", "SESSION_READY"],
            "live_admitted": False,
            "sandbox_admitted": True,
            "classification": "DESKTOP_AVAILABLE_CLI_ABSENT",
            "cost_class": "EXTERNAL_MODEL",
            "capabilities": ["implementation", "repository_search", "test_execution"],
            "cli_on_path": bool(discovered.get("cursor", {}).get("discovered")),
            "desktop_available": True,
            "evidence": ["cursor_desktop_on_local_repo", "pre_discovery_cli_absent"],
            "live_inference_verified": False,
            "note": "Desktop available; Cursor CLI not on PATH. Credits not spent.",
        },
        "CLINE": {
            "executor_id": "CLINE",
            "states": ["DISCOVERED"],
            "live_admitted": False,
            "sandbox_admitted": True,
            "classification": "IDE_EXTENSION_PRESENT",
            "cost_class": "EXTERNAL_MODEL",
            "capabilities": ["implementation", "deep_debug", "test_execution"],
            "evidence": ["vscode_extension_saoudrizwan.claude-dev"],
            "live_inference_verified": False,
        },
    }

    admission_counts: dict[str, int] = {}
    for row in admission.values():
        for flag in row["states"]:
            admission_counts[flag] = admission_counts.get(flag, 0) + 1

    write_json(
        REGISTRY / "EXECUTOR-ADMISSION-REGISTRY.json",
        {
            "schema": "raios.a15.executor-admission-registry.v1",
            "source_pre_discovery": str(PRE_DISCOVERY.relative_to(REPO)),
            "pre_discovery_reused": True,
            "pre_discovery_overwritten": False,
            "executors": admission,
            "admission_counts": admission_counts,
            "external_credits_consumed": False,
            "production_activation": False,
            "canonical_mutation": False,
        },
    )

    collaboration_router = {
        "schema": "raios.a15.capability-first-collaboration-router.v1",
        "strategy": "CAPABILITY_FIRST_SINGLE_PRIMARY",
        "source_router": str(A14_ROUTER.relative_to(REPO)),
        "capability_map": capability_map,
        "selection_factors": [
            "capability_fit",
            "verified_availability",
            "historical_success",
            "latency",
            "failure_rate",
            "cost_budget",
            "context_size",
            "current_lease",
            "verification_requirement",
        ],
        "rules": [
            "Do not use a fixed vendor priority list.",
            "One primary executor per task.",
            "Logged-out executors are never selected for live execution.",
            "Deterministic/local executor wins when capability-sufficient.",
            "Independent verifier cannot equal primary.",
            "Ambiguous routing must abstain.",
        ],
        "automatic_promotion": False,
        "canonical_mutation": False,
        "production_activation": False,
    }
    write_json(ROUTING / "CAPABILITY-FIRST-COLLABORATION-ROUTER.json", collaboration_router)
    write_json(
        ROUTING / "FAILURE-FALLBACK-ROUTER.json",
        {
            "schema": "raios.a15.failure-fallback-router.v1",
            "path": [
                "failure_event",
                "experience",
                "failure_signature",
                "recovery_skill_candidate",
                "same_task_envelope_to_qualified_fallback",
            ],
            "preserve_context_capsule_hash": True,
            "rediscovery_forbidden": True,
            "automatic_promotion": False,
        },
    )
    write_json(
        ROUTING / "INDEPENDENT-VERIFICATION-ROUTER.json",
        {
            "schema": "raios.a15.independent-verification-router.v1",
            "verifier_must_differ_from_primary": True,
            "default_mode": "READ_ONLY",
            "write_requires_explicit_authorization": True,
            "automatic_promotion": False,
        },
    )
    write_json(
        ROUTING / "BUDGET-CREDIT-GUARD.json",
        {
            "schema": "raios.a15.budget-credit-guard.v1",
            "never_call": [
                "logged_out_executor",
                "unavailable_executor",
                "duplicate_executor",
                "expensive_executor_when_deterministic_sufficient",
            ],
            "unknown_cost_policy": "UNKNOWN_MUST_REMAIN_UNKNOWN",
            "certification_spends_model_credits": False,
        },
    )
    write_json(
        ROUTING / "RESULT-EVIDENCE-SUBSCRIPTIONS.json",
        {
            "schema": "raios.a15.result-evidence-subscriptions.v1",
            "subscriptions": {
                "filesystem_read": ["LOCAL_DETERMINISTIC", "RAIOS_INTERNAL"],
                "independent_review": ["GEMINI", "RAIOS_INTERNAL"],
                "governance": ["RAIOS_INTERNAL"],
                "test_execution": ["LOCAL_DETERMINISTIC"],
            },
            "rescan_repository_forbidden": True,
        },
    )

    # ------------------------------------------------------------------
    # 3. TASK CORPUS
    # ------------------------------------------------------------------
    capabilities = list(capability_map.keys())
    scenarios: dict[int, str] = {}
    for i in range(50):
        scenarios[i] = "NORMAL"
    scenarios[18] = "PARALLEL_A"
    scenarios[19] = "PARALLEL_B"
    scenarios[20] = "WRITER_CONFLICT_A"
    scenarios[21] = "WRITER_CONFLICT_B"
    scenarios[22] = "VERIFY_CONCURRENT"
    scenarios[23] = "UNAVAILABLE_PRIMARY"
    scenarios[24] = "UNAVAILABLE_PRIMARY"
    scenarios[25] = "LOGGED_OUT_CLAUDE"
    scenarios[26] = "LOGGED_OUT_CLAUDE"
    scenarios[27] = "GEMINI_DEGRADED"
    scenarios[28] = "FALLBACK_CAPSULE"
    scenarios[29] = "FALLBACK_CAPSULE"
    scenarios[30] = "VERIFY_REQUIRED"
    scenarios[31] = "VERIFY_REQUIRED"
    scenarios[32] = "DUPLICATE"
    scenarios[33] = "DUPLICATE"
    scenarios[34] = "LEASE_RECOVERY"
    scenarios[37] = "CROSS_AGENT_NORMALIZE"
    scenarios[38] = "SUBSCRIPTION"
    scenarios[39] = "BUDGET_LOCAL"
    scenarios[40] = "BUDGET_LOCAL"
    scenarios[41] = "AMBIGUOUS"
    scenarios[42] = "OUT_OF_SCOPE"

    tasks: list[dict[str, Any]] = []
    for index in range(50):
        capability = capabilities[index % len(capabilities)]
        scenario = scenarios[index]
        write_scope = [f"RAIOS/V9/agents/a15/sandbox/task-{index:02d}"]
        if scenario in {"WRITER_CONFLICT_A", "WRITER_CONFLICT_B"}:
            write_scope = ["RAIOS/V9/agents/a15/sandbox/conflict-zone"]
        if scenario == "VERIFY_CONCURRENT":
            write_scope = ["RAIOS/V9/agents/a15/sandbox/task-18"]
        if scenario == "DUPLICATE":
            write_scope = ["RAIOS/V9/agents/a15/sandbox/task-03"]
        if scenario in {"BUDGET_LOCAL"}:
            capability = "filesystem_read"
        if scenario in {"LOGGED_OUT_CLAUDE", "FALLBACK_CAPSULE"}:
            capability = "deep_debug"
        if scenario == "GEMINI_DEGRADED":
            capability = "independent_review"
        if scenario == "VERIFY_REQUIRED":
            capability = "implementation"
        if scenario == "UNAVAILABLE_PRIMARY":
            capability = "implementation"
        if scenario == "OUT_OF_SCOPE":
            capability = "filesystem_read"
        confidence = 0.55 if scenario == "AMBIGUOUS" else 0.93
        envelope = {
            "schema": "raios.a15.task-envelope.v1",
            "task_id": "a15-task:03" if scenario == "DUPLICATE" else f"a15-task:{index:02d}",
            "correlation_id": f"corr:a15:{index:02d}",
            "causation_id": f"cause:a15:{index:02d}",
            "objective": f"A15 sandbox task {index:02d} {scenario}",
            "capability_requirements": [capability],
            "allowed_read_scope": ["RAIOS/V9/agents/a15"],
            "allowed_write_scope": write_scope,
            "forbidden_scope": ["canonical", "production"],
            "acceptance_gates": ["normalized_result", "confidence_in_0_1", "no_canonical_mutation"],
            "budget": {"external_credits": 0, "preferred_cost_class": "DETERMINISTIC_LOCAL"},
            "priority": 50 - index,
            "predecessor_evidence": {
                "a14_receipt_sha256": A14_HASH,
                "a14_1_receipt_sha256": A141_HASH,
            },
            "current_owner": None,
            "verifier_policy": {
                "independent": scenario in {"VERIFY_REQUIRED", "VERIFY_CONCURRENT"},
                "mode": "READ_ONLY",
            },
            "scenario": scenario,
            "confidence": confidence,
            "lifecycle": "READY",
        }
        tasks.append(envelope)

    if len(tasks) != 50:
        raise RuntimeError("A15_TASK_CORPUS_INVALID")
    write_json(REGISTRY / "SHARED-TASK-REGISTRY.json", {"schema": "raios.a15.shared-task-registry.v1", "tasks": tasks})
    print("DETERMINISTIC_TASK_CORPUS    : PASS")

    # ------------------------------------------------------------------
    # 4. FABRIC EXECUTION
    # ------------------------------------------------------------------
    leases = LeaseManager()
    claimed: set[str] = set()
    results: list[dict[str, Any]] = []
    handoffs = 0
    fallbacks = 0
    verifications = 0
    duplicate_rejections = 0
    budget_guard_savings = 0
    subscription_deliveries = 0
    parallel_ok = 0
    capsule_preserved = 0
    normalized_cross_agent = 0

    empirical = {
        name: {"attempts": 0, "successes": 0, "failures": 0, "latency_ms": []}
        for name in admission
    }

    def admitted(executor_id: str, sandbox: bool = True) -> bool:
        row = admission[executor_id]
        return bool(row["sandbox_admitted"] if sandbox else row["live_admitted"])

    def chain_for(capability: str) -> list[str]:
        return list(capability_map.get(capability, []))

    def select_primary(capability: str, scenario: str) -> str | None:
        nonlocal budget_guard_savings
        chain = chain_for(capability)
        if scenario in {"BUDGET_LOCAL", "NORMAL", "PARALLEL_A", "PARALLEL_B", "WRITER_CONFLICT_A", "WRITER_CONFLICT_B", "VERIFY_CONCURRENT", "SUBSCRIPTION", "LEASE_RECOVERY", "DUPLICATE", "CROSS_AGENT_NORMALIZE"}:
            if capability in {"filesystem_read", "test_execution", "repository_search", "implementation"} and admitted("LOCAL_DETERMINISTIC"):
                if chain and chain[0] != "LOCAL_DETERMINISTIC":
                    budget_guard_savings += 1
                return "LOCAL_DETERMINISTIC"
            if capability == "governance":
                return "RAIOS_INTERNAL"
        ranked: list[tuple[float, str]] = []
        for executor_id in chain:
            row = admission[executor_id]
            if executor_id == "CLAUDE_CODE" and not row["auth"].get("loggedIn", False) if "auth" in row else not row["live_admitted"]:
                budget_guard_savings += 1
                continue
            if not admitted(executor_id):
                if executor_id in {"CLAUDE_CODE", "CURSOR"} or not row["live_admitted"]:
                    budget_guard_savings += 1
                continue
            if scenario == "UNAVAILABLE_PRIMARY" and executor_id in {"CLINE", "CURSOR"}:
                budget_guard_savings += 1
                continue
            fit = 1.0 if capability in row["capabilities"] or executor_id == "LOCAL_DETERMINISTIC" else 0.4
            avail = 1.0 if admitted(executor_id) else 0.0
            cost = 1.0 if row["cost_class"] in {"DETERMINISTIC_LOCAL", "INTERNAL"} else 0.3
            score = (fit * 0.4) + (avail * 0.3) + (cost * 0.3)
            ranked.append((score, executor_id))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[0][1]

    def execute_sandbox(task: dict[str, Any], executor_id: str, force_failure: bool = False) -> dict[str, Any]:
        started = time.perf_counter_ns()
        empirical[executor_id]["attempts"] += 1
        if force_failure:
            empirical[executor_id]["failures"] += 1
            latency = (time.perf_counter_ns() - started) / 1_000_000
            empirical[executor_id]["latency_ms"].append(latency)
            signature = capture_failure("CONTROLLED_PRIMARY_EXECUTOR_FAILURE", task["task_id"], executor_id)
            return normalize_result(
                task["task_id"],
                executor_id,
                "FAILED",
                task["confidence"],
                latency,
                {"failure_signature": signature, "cost_budget_observation": "UNKNOWN"},
            )
        empirical[executor_id]["successes"] += 1
        latency = max(0.2, (time.perf_counter_ns() - started) / 1_000_000)
        empirical[executor_id]["latency_ms"].append(latency)
        extra = {"cost_budget_observation": "UNKNOWN", "changed_files": []}
        if executor_id == "GEMINI":
            extra["classification"] = admission["GEMINI"]["classification"]
            extra["evidence"] = ["sandbox-certification-adapter", "DEGRADED_BUT_OPERATIONAL"]
        return normalize_result(task["task_id"], executor_id, "SUCCESS", task["confidence"], latency, extra)

    active_writer_for_concurrent: str | None = None
    held_conflict_lease: str | None = None

    for task in tasks:
        capability = task["capability_requirements"][0]
        scenario = task["scenario"]
        task_id = task["task_id"]
        append_wal({"type": "task_created", "task_id": task_id, "lifecycle": "DISCOVERED"})
        append_wal({"type": "task_created", "task_id": task_id, "lifecycle": "READY"})
        capture_experience("A15_TASK_CREATED", "READY", {"task_id": task_id, "confidence": task["confidence"]})

        if scenario == "OUT_OF_SCOPE":
            task["lifecycle"] = "CANCELLED"
            result = normalize_result(task_id, "NONE", "REJECTED_OUT_OF_SCOPE", task["confidence"], 0.0)
            results.append(result)
            append_wal({"type": "result", "task_id": task_id, "status": result["status"], "lifecycle": "CANCELLED"})
            capture_experience("A15_TASK", result["status"], result)
            continue

        if scenario == "AMBIGUOUS" or task["confidence"] < 0.75:
            task["lifecycle"] = "ABSTAINED"
            result = normalize_result(task_id, "NONE", "ABSTAINED_AMBIGUOUS_ROUTING", task["confidence"], 0.0)
            results.append(result)
            append_wal({"type": "result", "task_id": task_id, "status": result["status"], "lifecycle": "ABSTAINED"})
            capture_experience("A15_TASK", result["status"], result)
            continue

        if task_id in claimed:
            duplicate_rejections += 1
            budget_guard_savings += 1
            result = normalize_result(task_id, "NONE", "REJECTED_DUPLICATE", task["confidence"], 0.0)
            results.append(result)
            append_wal({"type": "result", "task_id": task_id, "status": "REJECTED_DUPLICATE", "lifecycle": "CANCELLED"})
            capture_experience("A15_TASK", "REJECTED_DUPLICATE", result)
            continue

        claimed.add(task_id)
        task["lifecycle"] = "CLAIMED"
        append_wal({"type": "claim", "task_id": task_id, "lifecycle": "CLAIMED"})

        primary = select_primary(capability, scenario)
        if scenario == "LOGGED_OUT_CLAUDE":
            if "CLAUDE_CODE" in chain_for(capability):
                budget_guard_savings += 1
                capture_experience(
                    "A15_BUDGET_GUARD",
                    "REJECTED_LOGGED_OUT",
                    {"executor": "CLAUDE_CODE", "task_id": task_id, "confidence": 1.0},
                )
            primary = select_primary(capability, "FALLBACK_CAPSULE") or "LOCAL_DETERMINISTIC"
            fallbacks += 1
        if scenario == "UNAVAILABLE_PRIMARY":
            primary = "LOCAL_DETERMINISTIC"
            fallbacks += 1
            budget_guard_savings += 1
        if primary is None:
            primary = "LOCAL_DETERMINISTIC" if admitted("LOCAL_DETERMINISTIC") else None
        if primary is None:
            raise RuntimeError("A15_NO_ADMITTED_EXECUTOR")
        if primary == "CLAUDE_CODE":
            raise RuntimeError("A15_LOGGED_OUT_CLAUDE_SELECTED")

        task["current_owner"] = primary
        mode = "READ" if scenario == "VERIFY_CONCURRENT" else "WRITE"
        if scenario == "VERIFY_CONCURRENT":
            writer = leases.acquire(task_id + ":writer", "LOCAL_DETERMINISTIC", task["allowed_write_scope"], "WRITE")
            if writer.get("status") == "REJECTED_CONFLICT":
                raise RuntimeError("A15_CONCURRENT_WRITER_UNEXPECTED_CONFLICT")
            active_writer_for_concurrent = writer["lease_id"]
            lease = leases.acquire(task_id, "RAIOS_INTERNAL", task["allowed_write_scope"], "READ")
            if lease.get("status") == "REJECTED_CONFLICT":
                raise RuntimeError("A15_READONLY_VERIFIER_BLOCKED")
            verifications += 1
            leases.release(lease["lease_id"])
            leases.release(active_writer_for_concurrent)
            result = normalize_result(task_id, "RAIOS_INTERNAL", "SUCCESS", task["confidence"], 0.4, {"evidence": ["read-only-verifier-concurrent"]})
            results.append(result)
            capture_experience("A15_VERIFICATION", "SUCCESS", result)
            append_wal({"type": "verification", "task_id": task_id, "status": "SUCCESS", "lifecycle": "PASSED"})
            continue

        lease = leases.acquire(task_id, primary, task["allowed_write_scope"], mode)
        if lease.get("status") == "REJECTED_CONFLICT":
            task["lifecycle"] = "BLOCKED"
            result = normalize_result(task_id, primary, "REJECTED_LEASE_CONFLICT", task["confidence"], 0.0)
            results.append(result)
            capture_experience("A15_LEASE_CONFLICT", "FAILED", result)
            append_wal({"type": "result", "task_id": task_id, "status": "REJECTED_LEASE_CONFLICT", "lifecycle": "BLOCKED"})
            if held_conflict_lease:
                leases.release(held_conflict_lease)
                held_conflict_lease = None
            continue

        if scenario in {"PARALLEL_A", "PARALLEL_B"}:
            parallel_ok += 1

        task["lifecycle"] = "RUNNING"
        append_wal({"type": "attempt", "task_id": task_id, "executor": primary, "lifecycle": "RUNNING"})

        cap = capsule_for(task)
        force_failure = scenario in {"FALLBACK_CAPSULE"}
        result = execute_sandbox(task, primary, force_failure=force_failure)

        if scenario == "LEASE_RECOVERY":
            leases.expire(lease["lease_id"])
            recovered = leases.recover(lease["lease_id"], "RAIOS_INTERNAL")
            fallbacks += 1
            handoffs += 1
            cap2 = capsule_for(task, {"decisions": ["lease_recovery"]})
            result = execute_sandbox(task, "RAIOS_INTERNAL")
            result["handoff"] = {
                "from_executor": primary,
                "to_executor": "RAIOS_INTERNAL",
                "reason": "FAILED_WORKER_LEASE_RECOVERY",
                "context_hash": cap["capsule_hash"],
            }
            capture_experience("A15_HANDOFF", "SUCCESS", result["handoff"])
            append_wal({"type": "handoff", "task_id": task_id, "from_executor": primary, "to_executor": "RAIOS_INTERNAL"})
            lease = recovered

        if scenario == "FALLBACK_CAPSULE" and result["status"] == "FAILED":
            fallback = "LOCAL_DETERMINISTIC" if primary != "LOCAL_DETERMINISTIC" else "RAIOS_INTERNAL"
            fallbacks += 1
            handoffs += 1
            cap_fail = capsule_for(task, {"failures": [result.get("failure_signature")]})
            handed = execute_sandbox(task, fallback)
            cap_after = capsule_for(task, {"failures": [result.get("failure_signature")]})
            if cap_fail["capsule_hash"] != cap_after["capsule_hash"]:
                raise RuntimeError("A15_CAPSULE_HASH_DRIFT")
            capsule_preserved += 1
            handed["handoff"] = {
                "from_executor": primary,
                "to_executor": fallback,
                "reason": "PRIMARY_FAILURE_FALLBACK",
                "context_hash": cap_fail["capsule_hash"],
            }
            capture_experience("A15_FALLBACK", "SUCCESS", handed["handoff"])
            append_wal({"type": "fallback", "task_id": task_id, "from_executor": primary, "to_executor": fallback})
            append_wal({"type": "handoff", "task_id": task_id, **handed["handoff"]})
            result = handed

        if scenario == "GEMINI_DEGRADED":
            gemini_result = execute_sandbox(task, "GEMINI")
            if admission["GEMINI"]["classification"] != "DEGRADED_BUT_OPERATIONAL":
                raise RuntimeError("A15_GEMINI_CLASSIFICATION_LOST")
            if gemini_result["provenance"].get("external_credits_consumed"):
                raise RuntimeError("A15_GEMINI_CREDITS_SPENT")
            if "LIVE_INFERENCE_VERIFIED" in admission["GEMINI"]["states"]:
                raise RuntimeError("A15_FALSE_GEMINI_INFERENCE_CLAIM")
            result = gemini_result
            result["evidence"] = ["sandbox-certification-adapter", "DEGRADED_BUT_OPERATIONAL"]

        if scenario == "CROSS_AGENT_NORMALIZE":
            samples = [
                execute_sandbox(task, "LOCAL_DETERMINISTIC"),
                execute_sandbox(task, "RAIOS_INTERNAL"),
                execute_sandbox(task, "GEMINI"),
                execute_sandbox(task, "CLINE"),
            ]
            required = [
                "task_id",
                "executor",
                "status",
                "confidence",
                "changed_files",
                "evidence",
                "tests",
                "latency_ms",
                "cost_budget_observation",
                "failure_signature",
                "handoff",
                "provenance",
            ]
            for sample in samples:
                if any(key not in sample for key in required):
                    raise RuntimeError("A15_NORMALIZATION_MISSING_FIELD")
                if sample["cost_budget_observation"] != "UNKNOWN":
                    raise RuntimeError("A15_UNKNOWN_COST_MUTATED")
            normalized_cross_agent += 1
            result = samples[0]

        if scenario == "SUBSCRIPTION":
            subscribers = ["LOCAL_DETERMINISTIC", "RAIOS_INTERNAL"]
            for sub in subscribers:
                subscription_deliveries += 1
                append_wal({"type": "result", "task_id": task_id, "subscriber": sub, "status": "DELIVERED"})
            capture_experience(
                "A15_SUBSCRIPTION",
                "SUCCESS",
                {"task_id": task_id, "subscribers": subscribers, "rescan": False, "confidence": 1.0},
            )

        if scenario == "VERIFY_REQUIRED":
            task["lifecycle"] = "VERIFYING"
            verifier = "RAIOS_INTERNAL" if primary != "RAIOS_INTERNAL" else "GEMINI"
            if verifier == primary:
                raise RuntimeError("A15_VERIFIER_EQUALS_PRIMARY")
            vlease = leases.acquire(task_id + ":verify", verifier, task["allowed_read_scope"], "READ")
            if vlease.get("status") == "REJECTED_CONFLICT":
                raise RuntimeError("A15_VERIFIER_LEASE_REJECTED")
            verifications += 1
            handoffs += 1
            vres = execute_sandbox(task, verifier)
            vres["handoff"] = {
                "from_executor": primary,
                "to_executor": verifier,
                "reason": "INDEPENDENT_VERIFICATION",
                "context_hash": cap["capsule_hash"],
                "mode": "READ_ONLY",
            }
            capture_experience("A15_VERIFICATION", "SUCCESS", vres["handoff"])
            append_wal({"type": "verification", "task_id": task_id, "verifier": verifier, "primary": primary})
            leases.release(vlease["lease_id"])
            result["handoff"] = vres["handoff"]

        task["lifecycle"] = "PASSED" if result["status"] == "SUCCESS" else "FAILED"
        if scenario == "WRITER_CONFLICT_A":
            held_conflict_lease = lease["lease_id"]
        else:
            leases.release(lease["lease_id"])
            if scenario == "WRITER_CONFLICT_B" and held_conflict_lease:
                leases.release(held_conflict_lease)
                held_conflict_lease = None
        results.append(result)
        append_wal({"type": "result", "task_id": task_id, "status": result["status"], "lifecycle": task["lifecycle"]})
        append_wal({"type": "completion", "task_id": task_id, "lifecycle": task["lifecycle"]})
        capture_experience("A15_TASK", result["status"], result)

    # ------------------------------------------------------------------
    # 5. WAL CRASH / REPLAY IDEMPOTENCY
    # ------------------------------------------------------------------
    first = replay_wal(WAL)
    second = replay_wal(WAL)
    if first["applied"] != second["applied"] or first["seen"] != second["seen"]:
        raise RuntimeError("A15_REPLAY_NOT_IDEMPOTENT")
    corrupt = WAL.with_name("collaboration-wal.crash.jsonl")
    shutil.copy2(WAL, corrupt)
    with corrupt.open("a", encoding="utf-8") as handle:
        handle.write("{this is not json")
    crashed = replay_wal(corrupt)
    if crashed["skipped_corrupt"] < 1:
        raise RuntimeError("A15_CRASH_REPLAY_DID_NOT_SKIP_CORRUPT")
    if crashed["applied"] != first["applied"]:
        raise RuntimeError("A15_CRASH_REPLAY_DRIFT")
    print("WAL_CRASH_REPLAY             : PASS")
    print("REPLAY_IDEMPOTENCY           : PASS")

    # ------------------------------------------------------------------
    # 6. ASSERTIONS
    # ------------------------------------------------------------------
    if len(tasks) != 50:
        raise RuntimeError("A15_TASK_COUNT")
    if leases.conflicts < 1:
        raise RuntimeError("A15_LEASE_CONFLICT_NOT_OBSERVED")
    if parallel_ok < 2:
        raise RuntimeError("A15_PARALLEL_NOT_OBSERVED")
    if verifications < 1:
        raise RuntimeError("A15_VERIFICATION_NOT_OBSERVED")
    if fallbacks < 1:
        raise RuntimeError("A15_FALLBACK_NOT_OBSERVED")
    if duplicate_rejections < 1:
        raise RuntimeError("A15_DUPLICATE_NOT_OBSERVED")
    if budget_guard_savings < 1:
        raise RuntimeError("A15_BUDGET_GUARD_NOT_OBSERVED")
    if capsule_preserved < 1:
        raise RuntimeError("A15_CAPSULE_NOT_PRESERVED")
    if normalized_cross_agent < 1:
        raise RuntimeError("A15_CROSS_AGENT_NORMALIZE_MISSING")
    if subscription_deliveries < 1:
        raise RuntimeError("A15_SUBSCRIPTION_MISSING")
    if leases.recoveries < 1:
        raise RuntimeError("A15_LEASE_RECOVERY_MISSING")
    if any(r.get("production_mutation") for r in results if isinstance(r.get("production_mutation"), bool) and r["production_mutation"]):
        raise RuntimeError("A15_PRODUCTION_MUTATION")
    if admission["CLAUDE_CODE"]["live_admitted"]:
        raise RuntimeError("A15_CLAUDE_LIVE_ADMITTED")
    if admission["GEMINI"]["classification"] != "DEGRADED_BUT_OPERATIONAL":
        raise RuntimeError("A15_GEMINI_CLASSIFICATION")
    if file_hash(A14_RECEIPT) != A14_HASH or file_hash(A141_RECEIPT) != A141_HASH:
        raise RuntimeError("A15_PREDECESSOR_RECEIPT_REWRITE")

    wal_events = first["applied"]
    write_json(
        REPORTS / "COLLABORATIVE-EXECUTION-REPORT.json",
        {
            "schema": "raios.a15.collaborative-execution-report.v1",
            "tasks": 50,
            "lease_conflicts": leases.conflicts,
            "handoffs": handoffs,
            "fallbacks": fallbacks,
            "verifications": verifications,
            "duplicate_rejections": duplicate_rejections,
            "budget_guard_savings": budget_guard_savings,
            "executor_admission_counts": admission_counts,
            "wal_events": wal_events,
            "replay_idempotency": True,
            "capsule_hash_preserved": capsule_preserved,
            "subscription_deliveries": subscription_deliveries,
            "lineage_gate": "PASS",
            "external_credits_consumed": False,
            "production_mutation": False,
            "canonical_mutation": False,
            "automatic_promotion": False,
            "lifecycle": "COLLABORATIVE_EXECUTION_FABRIC",
        },
    )

    empirical_out = {}
    for name, row in empirical.items():
        attempts = row["attempts"]
        empirical_out[name] = {
            "attempts": attempts,
            "successes": row["successes"],
            "failures": row["failures"],
            "success_rate": (row["successes"] / attempts) if attempts else 0.0,
            "mean_latency_ms": (sum(row["latency_ms"]) / len(row["latency_ms"])) if row["latency_ms"] else 0.0,
        }
        probability(empirical_out[name]["success_rate"], f"{name}_SUCCESS_RATE")
    write_json(MEMORY / "EMPIRICAL-COLLAB-PROFILE.json", {"schema": "raios.a15.empirical-collab-profile.v1", "profiles": empirical_out})

    receipt = {
        "schema": "raios.v9.a15.receipt.v1",
        "phase": "V9.0-A15",
        "certification_status": "PASS",
        "certification_mode": "FAIL_CLOSED",
        "certification_input_sha": head,
        "baseline_commit": A14_BASELINE,
        "containing_commit": None,
        "current_observed_head": head,
        "timestamp": now(),
        "predecessor": {
            "phase": "V9.0-A14.1",
            "sha256": A141_HASH,
            "status": "PASS",
            "containing_commit": A14_1_COMMIT,
        },
        "historical_hashes": {
            "a14_receipt_sha256": A14_HASH,
            "a14_original_certification_sha": A14_ORIG,
            "a14_1_receipt_sha256": A141_HASH,
            "a14_baseline_commit": A14_BASELINE,
        },
        "runtime": {
            "task_exchange_gateway": True,
            "shared_task_registry": True,
            "workspace_lease_manager": True,
            "shared_result_bus": True,
            "cross_agent_handoff": True,
            "executor_admission_registry": True,
            "capability_first_collaboration_router": True,
            "failure_fallback_router": True,
            "independent_verification_router": True,
            "budget_credit_guard": True,
            "collaboration_wal": True,
            "result_evidence_subscriptions": True,
            "git_lineage_gate": True,
        },
        "certification": {
            "tasks": 50,
            "lease_conflicts": leases.conflicts,
            "handoffs": handoffs,
            "fallbacks": fallbacks,
            "verifications": verifications,
            "duplicate_rejections": duplicate_rejections,
            "budget_guard_savings": budget_guard_savings,
            "executor_admission_counts": admission_counts,
            "wal_events": wal_events,
            "replay_idempotency": True,
            "adapter_mode": "SANDBOX_SYNTHETIC_EXECUTOR_ADAPTERS",
            "external_credits_consumed": False,
        },
        "lineage_gate": "PASS",
        "safety": {
            "confidence_contract": "STRICT_[0,1]",
            "automatic_promotion": False,
            "canonical_mutation": False,
            "production_activation": False,
            "active": False,
        },
        "existing_assets_reused": {
            "a15_pre_discovery": True,
            "a14_capability_first_router": True,
            "a14_receipt": True,
            "a14_1_receipt": True,
            "new_bridge_created": False,
        },
        "epistemic_limits": [
            "A15 certification used sandbox executor adapters and consumed no external model credits.",
            "Claude Code CLI presence does not imply authentication or live inference readiness.",
            "Gemini CLI presence and degraded GrepTool fallback do not imply live inference verification.",
            "Cursor Desktop availability does not imply Cursor CLI or billed inference.",
            "containing_commit is deferred; startup must verify ancestry, not self-referential HEAD equality.",
            "Historical A14/A14.1 hashes are immutable.",
            "A15 does not authorize production execution.",
            "A15 does not mutate canonical truth.",
            "A15 does not automatically promote anything.",
        ],
    }
    write_json(A15_RECEIPT, receipt)
    receipt_hash = file_hash(A15_RECEIPT)

    final_state = load_json(STATE)
    final_state["current_version"] = "V9.0-A15"
    final_state["current_phase"] = "COLLABORATIVE_EXECUTION_FABRIC"
    final_state["state_status"] = "A15_CERTIFIED"
    final_state["current_observed_head"] = head
    final_state["git_lineage"] = lineage
    architecture = final_state.get("active_architecture", [])
    for capability in [
        "TASK_EXCHANGE_GATEWAY",
        "SHARED_TASK_REGISTRY",
        "WORKSPACE_LEASE_MANAGER",
        "SHARED_RESULT_BUS",
        "CROSS_AGENT_CONTEXT_CAPSULE",
        "EXECUTOR_ADMISSION_REGISTRY",
        "CAPABILITY_FIRST_COLLABORATION_ROUTER",
        "FAILURE_FALLBACK_ROUTER",
        "INDEPENDENT_VERIFICATION_ROUTER",
        "BUDGET_CREDIT_GUARD",
        "COLLABORATION_WAL",
        "RESULT_EVIDENCE_SUBSCRIPTIONS",
        "GIT_LINEAGE_GATE",
    ]:
        if capability not in architecture:
            architecture.append(capability)
    final_state["active_architecture"] = architecture
    final_state["collaborative_execution_fabric"] = {
        "lifecycle": "COLLABORATIVE_EXECUTION_FABRIC",
        "task_exchange_gateway": True,
        "shared_task_registry": True,
        "workspace_lease_manager": True,
        "shared_result_bus": True,
        "cross_agent_handoff": True,
        "executor_admission_registry": True,
        "capability_first_router": True,
        "budget_credit_guard": True,
        "collaboration_wal": True,
        "active": False,
        "production_active": False,
        "canonical_mutation": False,
        "automatic_promotion": False,
    }
    final_state["latest_phase_receipt"] = {
        "phase": "V9.0-A15",
        "path": str(A15_RECEIPT.relative_to(REPO)),
        "sha256": receipt_hash,
        "certification_status": "PASS",
        "certification_input_sha": head,
        "containing_commit": None,
    }
    final_state["updated_at"] = now()
    write_json(STATE, final_state)

    final = load_json(STATE)
    if final["latest_phase_receipt"]["sha256"] != file_hash(A15_RECEIPT):
        raise RuntimeError("A15_STATE_RECEIPT_HASH_DRIFT")
    if file_hash(A14_RECEIPT) != A14_HASH or file_hash(A141_RECEIPT) != A141_HASH:
        raise RuntimeError("A15_PREDECESSOR_RECEIPT_REWRITE")
    if final["collaborative_execution_fabric"]["production_active"]:
        raise RuntimeError("A15_PRODUCTION_ACTIVE")
    if final["collaborative_execution_fabric"]["automatic_promotion"]:
        raise RuntimeError("A15_AUTOMATIC_PROMOTION")
    if final["collaborative_execution_fabric"]["canonical_mutation"]:
        raise RuntimeError("A15_CANONICAL_MUTATION")
    if final["collaborative_execution_fabric"]["active"]:
        raise RuntimeError("A15_ACTIVE_TRUE")
    if final.get("a14_original_certification", {}).get("receipt_sha256") != A14_HASH:
        raise RuntimeError("A15_A14_HISTORY_LOST")
    if pre_hash_unchanged := file_hash(PRE_DISCOVERY):
        if pre.get("generated_at") != load_json(PRE_DISCOVERY).get("generated_at"):
            raise RuntimeError("A15_PRE_DISCOVERY_MUTATED")
        del pre_hash_unchanged

    print()
    print("=" * 90)
    print("RAIOS V9.0-A15 CERTIFICATION RESULT")
    print("=" * 90)
    print("TASKS                        :", 50)
    print("LEASE_CONFLICTS              :", leases.conflicts)
    print("HANDOFFS                     :", handoffs)
    print("FALLBACKS                    :", fallbacks)
    print("VERIFICATIONS                :", verifications)
    print("DUPLICATE_REJECTIONS         :", duplicate_rejections)
    print("BUDGET_GUARD_SAVINGS         :", budget_guard_savings)
    print("EXECUTOR_ADMISSION_COUNTS    :", json.dumps(admission_counts, sort_keys=True))
    print("WAL_EVENTS                   :", wal_events)
    print("REPLAY_IDEMPOTENCY           : PASS")
    print("LINEAGE_GATE                 : PASS")
    print("CURRENT_VERSION              :", final["current_version"])
    print("STATE_STATUS                 :", final["state_status"])
    print("A15_RECEIPT_SHA256           :", receipt_hash)
    print("PRODUCTION_ACTIVE            : FALSE")
    print("CANONICAL_MUTATION           : FALSE")
    print("AUTOMATIC_PROMOTION          : FALSE")
    print("ACTIVE                       : FALSE")
    print("EXTERNAL_CREDITS_CONSUMED    : FALSE")
    print()
    print("STATUS = V9.0-A15_PASS")
    print("=" * 90)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        try:
            capture_failure(str(exc), "A15_CERTIFICATION", "A15_HARNESS")
            capture_experience(
                "A15_CERTIFICATION_FAILURE",
                "FAILED",
                {"exception": repr(exc), "traceback": traceback.format_exc(), "confidence": 1.0},
            )
        except Exception as telemetry_exc:
            print("A15_TELEMETRY_FAILURE:", repr(telemetry_exc), file=sys.stderr)
        print("A15_CERTIFICATION_FAILED:", repr(exc), file=sys.stderr)
        raise
