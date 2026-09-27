"""Bounded Command Center projections over existing canonical sources.

Not a second control plane, message bus, receipt ledger, scheduler, or factory.
Does not walk command-fabric inboxes or dirty-tree explosions.
Does not activate gated engines or spawn processes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .operational_projection import capability_projection, head_truth
from .live_activation import (
    factory_activation_readiness,
    factory_capability_routing,
    storage_authority_resolution,
    storage_writer_cutover_matrix,
    zero_canonical_island_proof,
)
from .storage_authority import resolve as storage_resolve

OPERATOR_CLASSES = (
    "CANONICAL_ACTIVE",
    "CANONICAL_DORMANT",
    "CAPABILITY_BACKEND",
    "PROVIDER_BACKEND",
    "WORKER",
    "ENGINE",
    "ORCHESTRATOR",
    "DEVELOPMENT_ONLY",
    "REFERENCE_ONLY",
    "LEGACY_UNIQUE_VALUE",
    "DUPLICATE",
    "BROKEN",
    "UNRESOLVED",
    "GATED",
)

MAX_COPY_RECORDS = 80
MAX_SYMBOL_RECORDS = 200
COPY_CLASS_PATH = ".ai-os/reports/inventory/RAIOS-BRANCH-AND-COPY-INVENTORY-C2/CLASSIFICATION.json"
COPY_MATRIX_PATH = ".ai-os/reports/inventory/RAIOS-BRANCH-AND-COPY-INVENTORY-C2/MATRIX.json"
SYMBOL_MATRIX_PATH = ".ai-os/reports/inventory/RAIOS-DEEP-UNIQUE-VALUE-ASSIMILATION-C2/SYMBOL-LEVEL-MATRIX.json"
EXTRACTION_PACKETS_PATH = ".ai-os/reports/inventory/RAIOS-DEEP-UNIQUE-VALUE-ASSIMILATION-C2/EXTRACTION-PACKETS-CONTINUATION.json"
UNIQUE_VALUE_MATRIX_PATH = ".ai-os/reports/inventory/RAIOS-DEEP-UNIQUE-VALUE-ASSIMILATION-C2/UNIQUE-VALUE-MATRIX.json"
WORKTREE_REGISTRY_PATH = ".ai-os/WORKTREE-REGISTRY.json"
FALSE_PASS_WIRED_IDS = frozenset({"SYM-001", "SYM-002", "SYM-003", "SYM-041", "SYM-042", "SYM-043"})
FALSE_PASS_CANONICAL = "src/raios/learning_evidence/false_pass.py"
COPY_WIRE_STATE = {
    "SUPERSEDED": "SUPERSEDED",
    "DUPLICATE": "DUPLICATE",
    "HISTORICAL_EVIDENCE_ONLY": "HISTORICAL_EVIDENCE_ONLY",
    "SEMANTIC_EQUIVALENT": "SEMANTIC_EQUIVALENT",
    "UNIQUE_VALUE": "RETAINED_CATALOG",
    "PARTIAL_OVERLAP": "RETAINED_CATALOG",
    "SCHEMA_VALUE_ONLY": "RETAINED_CATALOG",
    "INVARIANT_VALUE_ONLY": "RETAINED_CATALOG",
    "RECIPE_VALUE_ONLY": "RETAINED_CATALOG",
    "TEST_VALUE_ONLY": "RETAINED_CATALOG",
    "UNSAFE_LEGACY": "C1_REVIEW_OR_HOLD",
    "DUPLICATE_ARCHITECTURE": "DUPLICATE",
    "COVERED": "ALREADY_ASSIMILATED",
    "C1_REVIEW_REQUIRED": "C1_REVIEW_OR_HOLD",
}

WAVE04_TO_OPERATOR = {
    "TEST_INFRASTRUCTURE": "DEVELOPMENT_ONLY",
    "RUNTIME_SERVICE": "CANONICAL_DORMANT",
    "CANONICAL_ADAPTER": "CAPABILITY_BACKEND",
    "CANONICAL_LIBRARY": "REFERENCE_ONLY",
    "RUNTIME_CORE": "ENGINE",
    "DEVELOPMENT_TOOL": "DEVELOPMENT_ONLY",
}

INDEPENDENT_SERVICE_FAMILIES = {"RAIOS_MCP", "TRANSPORT", "CONTROL_PLANE"}
GATED_FAMILIES = {
    "WORKFLOW_ENGINE",
    "AUDIT_ENGINE",
    "DATA_INTEGRITY_ENGINE",
    "CONTROLLED_RUNTIME_ORCHESTRATOR",
}
REFERENCE_FAMILIES = {"SEMANTIC_ENGINE"}
LEGACY_UNIQUE_PATHS = {"brain.py"}
NOT_A_SECOND_BUS = {"COGNITIVE_EVENT_BUS", "COMMAND_FABRIC"}
GATED_ENGINE_IDS = (
    "workflow-engine",
    "audit-engine",
    "data-integrity-engine",
    "controlled-runtime",
    "a13-dedup",
)
REFERENCE_ENGINE_IDS = ("semantic-engine", "engine-registry")
KEEPER_IDS = ("mind-fill", "absorb", "index", "kae", "book", "neurolingua-speak")

CANONICAL_FACTORIES = (
    {
        "id": "resource_factory",
        "path": "src/raios/resource_fabric/factory.py",
        "entrypoint": "raios.factory_fabric.orchestrator.resource_factory_probe",
        "orchestrator": "raios.factory_fabric.orchestrator.run_all",
        "provider_binding": "resource_fabric",
        "capability_binding": "RESOURCE_PLACEMENT",
        "gated": False,
    },
    {
        "id": "assimilation_factory",
        "path": "src/raios/factory_fabric/assimilation.py",
        "entrypoint": "raios.factory_fabric.orchestrator.assimilation_probe",
        "orchestrator": "raios.factory_fabric.orchestrator.run_all",
        "provider_binding": None,
        "capability_binding": "ASSIMILATION",
        "gated": False,
    },
    {
        "id": "cognitive_factory",
        "path": "src/raios/factory_fabric/cognitive.py",
        "entrypoint": "raios.factory_fabric.orchestrator.cognitive_factory_probe",
        "orchestrator": "raios.factory_fabric.orchestrator.run_all",
        "provider_binding": None,
        "capability_binding": "COGNITIVE_FACTORY",
        "gated": False,
    },
    {
        "id": "training_factory",
        "path": "scripts/runtime/verify-training-factory.mjs",
        "entrypoint": "raios.factory_fabric.orchestrator.training_factory_probe",
        "orchestrator": "raios.factory_fabric.orchestrator.run_all",
        "provider_binding": None,
        "capability_binding": "TRAINING",
        "gated": False,
        "auto_train": False,
        "auto_promote": False,
    },
    {
        "id": "c5_expert_foundry",
        "path": "src/raios/factory_fabric/foundry_engine.py",
        "entrypoint": "raios.factory_fabric.orchestrator.foundry_probe",
        "orchestrator": "raios.factory_fabric.orchestrator.run_all",
        "provider_binding": "ollama",
        "capability_binding": "EXPERT_FOUNDRY",
        "gated": False,
        "auto_promote": False,
    },
    {
        "id": "model_ecology",
        "path": "src/raios/factory_fabric/model_ecology.py",
        "entrypoint": "raios.factory_fabric.orchestrator.model_ecology_probe",
        "orchestrator": "raios.factory_fabric.orchestrator.run_all",
        "provider_binding": "ollama",
        "capability_binding": "MODEL_ECOLOGY",
        "gated": False,
    },
    {
        "id": "qwen_granite",
        "path": "src/raios/factory_fabric/foundry_engine.py",
        "entrypoint": "C6_MATRIX",
        "orchestrator": None,
        "provider_binding": None,
        "capability_binding": "MODEL_COMPAT",
        "gated": False,
    },
    {
        "id": "weight_merge",
        "path": "src/raios/factory_fabric/foundry_engine.py",
        "entrypoint": "C6_MATRIX",
        "orchestrator": None,
        "provider_binding": None,
        "capability_binding": "WEIGHT_MERGE",
        "gated": True,
    },
)

WAVE04_MAP = (
    Path(".ai-os") / "reports" / "engine-estate"
    / "RAIOS-CANONICAL-ENGINE-RUNTIME-WIRING-WAVE-04"
    / "ACTIVE-CANONICAL-RUNTIME-MAP.json"
)
FACTORY_MATRIX = (
    Path(".ai-os") / "reports" / "factory-fabric"
    / "RAIOS-FACTORY-FABRIC-CRITICAL-CLOSURE-C6-01"
    / "FACTORY-STATUS-MATRIX.json"
)
COGNITIVE_FACTORY_MAP = (
    Path(".ai-os") / "reports" / "factory-fabric"
    / "RAIOS-COGNITIVE-FACTORY-CANONICAL-CAPABILITY-01"
    / "COGNITIVE-CAPABILITY-MAP.json"
)
MAX_COMPONENTS = 64
MAX_FACTORIES = 16
MAX_EDGES = 48
MAX_INCIDENTS = 64


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


def _exists(repo: Path, rel: str) -> bool:
    if not rel:
        return False
    try:
        return (repo / rel).exists()
    except OSError:
        return False


def classify_component(row: dict[str, Any]) -> str:
    path = str(row.get("path") or "")
    family = str(row.get("family_id") or row.get("family") or "")
    role = str(row.get("final_role") or row.get("role") or "")
    if path.replace("\\", "/") in LEGACY_UNIQUE_PATHS:
        return "LEGACY_UNIQUE_VALUE"
    if family in GATED_FAMILIES:
        return "GATED"
    if family in REFERENCE_FAMILIES:
        return "REFERENCE_ONLY"
    if row.get("dead_canonical") is True:
        return "BROKEN"
    if row.get("test_only") is True or role == "TEST_INFRASTRUCTURE":
        return "DEVELOPMENT_ONLY"
    if row.get("library_only") is True or role == "CANONICAL_LIBRARY":
        return "REFERENCE_ONLY"
    if row.get("adapter_only") is True or role == "CANONICAL_ADAPTER":
        if family == "TRANSPORT":
            return "PROVIDER_BACKEND"
        return "CAPABILITY_BACKEND"
    if family == "CONTROLLED_RUNTIME_ORCHESTRATOR":
        return "GATED"
    if role == "RUNTIME_CORE" and family == "NEURO_LINGUA_ROUTER":
        return "ENGINE"
    if role == "RUNTIME_CORE" and family in {"TASK_ORCHESTRATION", "MASTERMIND_AGENTS"}:
        return "ORCHESTRATOR"
    if role == "RUNTIME_SERVICE" and family == "WORKER_RUNTIME":
        return "REFERENCE_ONLY"
    if family in NOT_A_SECOND_BUS and role == "RUNTIME_SERVICE":
        return "REFERENCE_ONLY"
    if role == "RUNTIME_SERVICE" and family in INDEPENDENT_SERVICE_FAMILIES:
        return "CANONICAL_ACTIVE" if row.get("runtime_reachable") is True else "CANONICAL_DORMANT"
    if role == "RUNTIME_SERVICE":
        return "CANONICAL_DORMANT"
    return WAVE04_TO_OPERATOR.get(role, "UNRESOLVED")


def _operator_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {k: 0 for k in OPERATOR_CLASSES}
    for row in rows:
        cls = str(row.get("operator_class") or "UNRESOLVED")
        counts[cls] = counts.get(cls, 0) + 1
    return counts


def copy_estate_projection(repo: Path) -> dict[str, Any]:
    """Read-only classification of built copies and extracted capabilities.

    Uses existing inventory/assimilation reports. No git scan. No fold-tip checkout.
    Fold-tip prefixes remain provenance. SAFE_TO_REMOVE_SOURCE stays false.
    """
    repo = Path(repo).resolve()
    classification = _load(repo / COPY_CLASS_PATH, {})
    copy_matrix = _load(repo / COPY_MATRIX_PATH, {})
    matrix = _load(repo / SYMBOL_MATRIX_PATH, {})
    packets = _load(repo / EXTRACTION_PACKETS_PATH, {})
    unique_matrix = _load(repo / UNIQUE_VALUE_MATRIX_PATH, {})
    worktrees = _load(repo / WORKTREE_REGISTRY_PATH, {})
    raw_copies = [row for row in (copy_matrix.get("rows") or []) if isinstance(row, dict)]
    copy_class_counts: dict[str, int] = {}
    copies = []
    for raw in raw_copies[:MAX_COPY_RECORDS]:
        cls = str(raw.get("classification") or "UNRESOLVED")
        copy_class_counts[cls] = copy_class_counts.get(cls, 0) + 1
        copies.append({
            "branch": raw.get("branch"),
            "kind": raw.get("kind"),
            "head_sha": raw.get("head_sha"),
            "classification": cls,
            "unique_commit_count": raw.get("unique_commit_count"),
            "changed_file_count": raw.get("changed_file_count"),
            "ahead": raw.get("ahead"),
            "behind": raw.get("behind"),
            "unrelated_history": raw.get("unrelated_history") is True,
            "stale_or_superseded": raw.get("stale_or_superseded") is True,
            "historical_evidence_only": raw.get("historical_evidence_only") is True,
            "extraction_required_now": raw.get("extraction_required_now") is True,
            "merge_executed": False,
            "delete_executed": False,
            "SAFE_TO_REMOVE_SOURCE": False,
        })
    records = [row for row in (matrix.get("records") or []) if isinstance(row, dict)][:MAX_SYMBOL_RECORDS]
    counts: dict[str, int] = {}
    wired = []
    hold = []
    for row in records:
        cls = str(row.get("class") or "UNRESOLVED")
        counts[cls] = counts.get(cls, 0) + 1
        item = {
            "id": row.get("id"),
            "symbol": row.get("symbol"),
            "class": cls,
            "packet": row.get("packet"),
            "path": row.get("path"),
        }
        if str(row.get("id") or "") in FALSE_PASS_WIRED_IDS:
            item["canonical_location"] = FALSE_PASS_CANONICAL
            item["wire_state"] = "CANONICAL_LIBRARY"
            wired.append(item)
        else:
            item["wire_state"] = COPY_WIRE_STATE.get(cls, "C1_REVIEW_OR_HOLD")
            hold.append(item)
    unique_rows = [row for row in (unique_matrix.get("records") or []) if isinstance(row, dict)]
    unique_summary = []
    for row in unique_rows[:MAX_SYMBOL_RECORDS]:
        unique_summary.append({
            "candidate_id": row.get("candidate_id"),
            "decision": row.get("decision"),
            "do_not_assimilate_as_runtime": row.get("do_not_assimilate_as_runtime") is True,
            "recommended_destination": row.get("recommended_destination"),
            "equivalence_level": row.get("equivalence_level"),
        })
    pass2 = classification.get("pass2_primary") or classification.get("pass1_auto_counts") or {}
    legacy = (worktrees.get("legacy_paths") or {}) if isinstance(worktrees, dict) else {}
    physical = copy_matrix.get("physical_copy_truth") if isinstance(copy_matrix.get("physical_copy_truth"), dict) else {}
    packet_list = packets.get("packets") if isinstance(packets, dict) else []
    return {
        "schema": "raios.copy-estate.v1",
        "observed_at": _utc(),
        "git_scan": False,
        "fold_tip_checked_out": False,
        "fold_tip": matrix.get("fold_tip") or unique_matrix.get("source_commit_fold_tip"),
        "SAFE_TO_REMOVE_SOURCE": False,
        "cutover": False,
        "extraction_executed_historical": classification.get("extraction_executed") is True,
        "merge_executed": classification.get("merge_executed") is True,
        "delete_executed": classification.get("delete_executed") is True,
        "worktree_policy": worktrees.get("policy") or "UNKNOWN",
        "worktrees": worktrees.get("worktrees") or {},
        "legacy_paths": {k: v for k, v in list(legacy.items())[:8]},
        "physical_copy_truth": {
            "second_physical_cursor_copy": physical.get("second_physical_cursor_copy") is True,
            "policy": physical.get("policy") or worktrees.get("policy") or "UNKNOWN",
            "legacy_repair_worktrees": physical.get("legacy_repair_worktrees") or "UNKNOWN",
        },
        "classification_authority": "CLASSIFICATION.json#pass2_primary",
        "row_class_is_pass1_auto": True,
        "pass1_auto_counts": classification.get("pass1_auto_counts") or {},
        "copy_pass2": pass2,
        "copy_class_counts": copy_class_counts,
        "copies_total": len(raw_copies),
        "copies": copies,
        "symbol_counts": counts,
        "capabilities_wired": wired[:MAX_SYMBOL_RECORDS],
        "capabilities_retained": hold[:MAX_SYMBOL_RECORDS],
        "unique_value_candidates": unique_summary,
        "packets_declared": len(packet_list) if isinstance(packet_list, list) else 0,
        "false_pass_library": FALSE_PASS_CANONICAL,
        "unique_value_unwired_count": sum(1 for row in hold if row.get("class") == "UNIQUE_VALUE"),
        "models_merged_via": [
            "src/raios/factory_fabric/model_ecology.py",
            "src/raios/c5_gateway/model_fabric.py",
            "src/raios/resource_fabric/live.py",
            "127.0.0.1:20128",
        ],
        "second_ccee_runtime": False,
        "second_mcp": False,
        "law": [
            "ONE_CANONICAL_TREE",
            "CLASSIFY_BEFORE_EXTRACT",
            "EXTRACT_BEFORE_DELETE",
            "NO_SECOND_CCEE_RUNTIME",
            "NO_SECOND_MCP",
            "NO_CUTOVER_THIS_WAVE",
            "SAFE_TO_REMOVE_SOURCE_FALSE",
        ],
    }


def factory_estate_projection(repo: Path, live_runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(repo).resolve()
    wave = _load(repo / WAVE04_MAP, {})
    matrix = _load(repo / FACTORY_MATRIX, {})
    live_runtime = live_runtime if isinstance(live_runtime, dict) else {}
    live_factories = live_runtime.get("factories") if isinstance(live_runtime.get("factories"), dict) else {}
    components: list[dict[str, Any]] = []
    independent = 0
    for raw in (wave.get("instances") or [])[:MAX_COMPONENTS]:
        if not isinstance(raw, dict):
            continue
        cls = classify_component(raw)
        family = raw.get("family_id")
        independent_service = (
            cls == "CANONICAL_ACTIVE"
            and family in INDEPENDENT_SERVICE_FAMILIES
            and raw.get("test_only") is not True
        )
        if independent_service:
            independent += 1
        components.append({
            "family": family,
            "path": raw.get("path"),
            "wave04_role": raw.get("final_role"),
            "operator_class": cls,
            "runtime_reachable": raw.get("runtime_reachable") is True,
            "independent_service": independent_service,
            "inventory_is_execution": False,
            "gated": cls == "GATED",
            "path_exists": _exists(repo, str(raw.get("path") or "")),
        })

    factories: list[dict[str, Any]] = []
    repaired = 0
    active = 0
    gated = 0
    for spec in CANONICAL_FACTORIES[:MAX_FACTORIES]:
        fid = spec["id"]
        path_ok = _exists(repo, spec["path"])
        matrix_row = matrix.get(fid) if isinstance(matrix.get(fid), dict) else {}
        if fid == "cognitive_factory" and not matrix_row:
            cog = _load(repo / COGNITIVE_FACTORY_MAP, {})
            if cog:
                matrix_row = {"status": "PASS", "source": "COGNITIVE-CAPABILITY-MAP"}
        live_row = live_factories.get(fid) if isinstance(live_factories.get(fid), dict) else {}
        live_status = str(live_row.get("status") or "").upper()
        matrix_status = str(matrix_row.get("status") or "").upper()
        proven = matrix_status in {"PASS", "PROVEN_EXISTING"} or live_status.startswith("PASS")
        live_cycle = bool(live_row) and live_status.startswith("PASS")
        if spec.get("gated") is True:
            cls = "GATED"
            gated += 1
        elif live_cycle and path_ok:
            cls = "CANONICAL_ACTIVE"
            active += 1
        elif proven and path_ok:
            cls = "CANONICAL_DORMANT"
        elif not path_ok:
            cls = "BROKEN"
        else:
            cls = "UNRESOLVED"
        if path_ok and proven:
            repaired += 1
        cycle_ok = live_cycle
        factories.append({
            "id": fid,
            "operator_class": cls,
            "path": spec["path"],
            "path_exists": path_ok,
            "entrypoint": spec["entrypoint"],
            "orchestrator": spec["orchestrator"],
            "provider_binding": spec.get("provider_binding"),
            "capability_binding": spec.get("capability_binding"),
            "matrix_status": matrix_status or "UNKNOWN",
            "live_status": live_status or "UNPROVEN",
            "live_cycle_proven": cycle_ok,
            "input_to_receipt_proven": cycle_ok,
            "inventory_is_execution": False,
            "pid_ne_active": True,
            "auto_train": spec.get("auto_train") is True,
            "auto_promote": spec.get("auto_promote") is True,
            "gated": spec.get("gated") is True,
            "activated_this_wave": False,
        })

    return {
        "schema": "raios.factory-estate.v1",
        "observed_at": _utc(),
        "source": str(WAVE04_MAP).replace("\\", "/"),
        "wave04_total": int(wave.get("active_canonical_total") or len(components)),
        "wave04_counts": wave.get("classification_counts") or {},
        "components": components,
        "component_count": len(components),
        "operator_counts": _operator_counts(components + factories),
        "independent_service_count": independent,
        "all_fifty_are_independent_services": False,
        "factories": factories,
        "factories_found": len(factories),
        "factories_active": active,
        "factories_repaired": repaired,
        "factories_gated": gated,
        "live_runtime_claimed": bool(live_runtime),
        "live_runtime_status": live_runtime.get("status") or "UNPROVEN",
        "second_factory_created": False,
        "run_all_invoked": False,
        "recursive_estate_scan": False,
        "gated_activated": False,
        "brain_py_preserved": True,
        "copy_estate": copy_estate_projection(repo),
        "activation_readiness": factory_activation_readiness(),
        "law": [
            "INVENTORY_NE_EXECUTION",
            "FIFTY_COMPONENTS_NE_FIFTY_SERVICES",
            "REPAIR_BEFORE_REPLACE",
            "GATED_NE_ACTIVATE",
            "NO_SECOND_FACTORY",
        ],
    }


def _stamp(value: Any, *, source: str, field: str) -> dict[str, Any]:
    text = "" if value is None else str(value)
    return {
        "value": value if value not in {None, ""} else "UNKNOWN",
        "observed_at": _utc(),
        "source": source,
        "proof_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        "field": field,
    }


def _digest_stamp(path: Path | None, *, field: str, source: str) -> dict[str, Any]:
    if path is None:
        return {**_stamp(None, source=source, field=field), "exists": False}
    p = Path(path)
    if not p.is_file():
        return {**_stamp(None, source=source, field=field), "exists": False}
    raw = p.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    return {
        "value": digest[:16],
        "exists": True,
        "bytes": len(raw),
        "observed_at": _utc(),
        "source": source,
        "proof_hash": digest[:16],
        "field": field,
    }


def current_truth_projection(
    *,
    canonical_head: str | None = None,
    deployed_head: str | None = None,
    runtime_head: str | None = None,
    observed_head: str | None = None,
    deployment: dict[str, Any] | None = None,
    current_state: dict[str, Any] | None = None,
    wave02_task_registered: bool | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    deployment = deployment if isinstance(deployment, dict) else {}
    current_state = current_state if isinstance(current_state, dict) else {}
    deployed = deployed_head or deployment.get("canonical_head")
    runtime = runtime_head or canonical_head
    tx = str(deployment.get("transaction_id") or "")
    overlay_live = tx.startswith("C2-CC-PROMO")
    misleading: list[str] = []
    if current_state.get("verified_facts"):
        misleading.append("CURRENT-STATE.verified_facts is product-narrative STALE; not runtime CURRENT")
    if current_state.get("known_gaps"):
        misleading.append("CURRENT-STATE.known_gaps is product-narrative STALE")
    repo_path = Path(repo) if repo else None
    current_json_path = (repo_path / ".ai-os" / "state" / "CURRENT.json") if repo_path else None
    current_json_absent = True if current_json_path is None else not current_json_path.is_file()
    leases_root = (repo_path / ".ai-os" / "state" / "command-fabric" / "leases") if repo_path else None
    leases_present = bool(leases_root and leases_root.is_dir())
    authority = {
        "tasks": _digest_stamp(
            (repo_path / ".ai-os" / "state" / "TASKS.json") if repo_path else None,
            field="tasks_digest",
            source=".ai-os/state/TASKS.json",
        ),
        "locks": _digest_stamp(
            (repo_path / ".ai-os" / "state" / "LOCKS.json") if repo_path else None,
            field="locks_digest",
            source=".ai-os/state/LOCKS.json",
        ),
        "seat_map": _digest_stamp(
            (repo_path / ".ai-os" / "mcp" / "SEAT-MAP.json") if repo_path else None,
            field="seat_map_digest",
            source=".ai-os/mcp/SEAT-MAP.json",
        ),
        "leases_root": {
            "value": "PRESENT" if leases_present else ("ABSENT" if repo_path else "UNKNOWN"),
            "exists": leases_present,
            "listed": False,
            "observed_at": _utc(),
            "source": ".ai-os/state/command-fabric/leases",
            "proof_hash": hashlib.sha256(str(leases_root or "").encode("utf-8")).hexdigest()[:16],
            "field": "leases_root",
        },
        "CURRENT_json": _digest_stamp(
            current_json_path,
            field="CURRENT_json",
            source=".ai-os/state/CURRENT.json",
        ),
        "CURRENT_STATE_json": _digest_stamp(
            (repo_path / ".ai-os" / "state" / "CURRENT-STATE.json") if repo_path else None,
            field="CURRENT_STATE_json",
            source=".ai-os/state/CURRENT-STATE.json",
        ),
    }
    return {
        "schema": "raios.current-truth.v1",
        "observed_at": _utc(),
        "projection_ne_authority": True,
        "CURRENT_json_absent": current_json_absent,
        "generic_head_omitted": True,
        "canonical_head": _stamp(canonical_head, source="git / RAIOS_CANONICAL_HEAD", field="canonical_head"),
        "deployed_head": _stamp(deployed, source="~/.raios/runtime/command-center/deployment.json", field="deployed_head"),
        "runtime_head": _stamp(runtime, source="CC process env", field="runtime_head"),
        "observed_head": _stamp(observed_head or canonical_head, source="C2 actor observation", field="observed_head"),
        "heads": head_truth(
            canonical_head=canonical_head,
            deployed_head=deployed,
            runtime_head=runtime,
            actor_observed_head=observed_head or canonical_head,
        ),
        "authority": authority,
        "deployment_transaction_id": tx or "UNKNOWN",
        "c2_overlay_deployed": overlay_live,
        "current_state_file": {
            "path": ".ai-os/state/CURRENT-STATE.json",
            "role": "STALE_PRODUCT_NARRATIVE",
            "is_runtime_current": False,
            "misleading_fields": ["verified_facts", "known_gaps", "unproven", "project_status"],
        },
        "wave02_task_registered": wave02_task_registered,
        "misleading": misleading,
        "law": ["CURRENT_IS_PROJECTION", "GENERIC_HEAD_FORBIDDEN", "SOURCE_READY_NE_LIVE_DEPLOYED"],
    }


def system_topology_projection(
    *,
    plane: dict[str, Any] | None = None,
    worker: dict[str, Any] | None = None,
    continuity: dict[str, Any] | None = None,
    ollama_listening: bool | None = None,
    heads: dict[str, Any] | None = None,
    canonical_head: str | None = None,
    canonical_branch: str | None = None,
    deployment: dict[str, Any] | None = None,
    current_state: dict[str, Any] | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    plane = plane if isinstance(plane, dict) else {}
    worker = worker if isinstance(worker, dict) else {}
    continuity = continuity if isinstance(continuity, dict) else {}
    heads = heads if isinstance(heads, dict) else head_truth(canonical_head=canonical_head)
    nodes: list[dict[str, Any]] = []

    def _add(name: str, state: str, **fields: Any) -> None:
        row = {"name": name, "state": state or "UNKNOWN"}
        row.update(fields)
        nodes.append(row)

    self_row = plane.get("self") if isinstance(plane.get("self"), dict) else {
        "name": "CommandCenter", "port": 8770, "state": "ONLINE", "probe": "SELF",
    }
    _add(str(self_row.get("name") or "CommandCenter"), str(self_row.get("state") or "UNKNOWN"),
         kind="COMMAND_CENTER", port=self_row.get("port"), probe=self_row.get("probe"),
         authority="PROJECTION_NOT_AUTHORITY")
    for svc in plane.get("services") or []:
        if not isinstance(svc, dict):
            continue
        _add(str(svc.get("name") or "UNKNOWN"), str(svc.get("state") or "UNKNOWN"),
             kind="RUNTIME_SERVICE", port=svc.get("port"), probe=svc.get("probe") or "HTTP",
             http=svc.get("http"), identity_proven=svc.get("state") == "ONLINE" and svc.get("probe") != "TCP_ONLY")
    fabric_state = worker.get("state") or ("ONLINE" if worker.get("healthy") is True else "UNKNOWN")
    if worker.get("healthy") is False:
        fabric_state = "DEGRADED"
    elif not worker:
        fabric_state = "UNKNOWN"
    _add("CommandFabric", str(fabric_state), kind="COMMAND_FABRIC",
         probe="MESSAGE_WORKER_STATUS", worker_id=worker.get("worker_id"),
         thread_alive=worker.get("thread_alive"), heartbeat_current=worker.get("heartbeat_current"),
         message_worker_ne_cc_readiness=True, inbox_scanned=False)
    if ollama_listening is True:
        ollama_state = "UNKNOWN"
        ollama_detail = "TCP_LISTENING_IDENTITY_UNPROVEN"
    elif ollama_listening is False:
        ollama_state = "OFFLINE"
        ollama_detail = "TCP_CLOSED"
    else:
        ollama_state = "UNKNOWN"
        ollama_detail = "NOT_PROBED"
    _add("Ollama", ollama_state, kind="PROVIDER", port=11434, probe="TCP_ONLY",
         identity="UNPROVEN", detail=ollama_detail, port_ne_service_identity=True)
    _add("StorageAuthority", "IDENTIFIED", kind="STORAGE", probe="WRITER_MAP",
         http_endpoint=None, identity="EXISTING_SPLIT_WRITERS",
         detail="NOT_AN_HTTP_SERVICE", git_ne_event_store=True, cutover_executed=False)
    cont_state = str(continuity.get("status") or "UNKNOWN").upper() or "UNKNOWN"
    if cont_state in {"", "NONE", "NULL"}:
        cont_state = "UNKNOWN"
    _add("Continuity", cont_state, kind="SELF_HEAL", probe="CONTINUITY_STATUS_FILE",
         source="~/.raios/runtime/continuity/status.json", c6_owned=True)

    edges = [
        {"from": "RAIOS Bootstrap", "to": "StorageAuthority", "class": "IDENTIFIED_SPLIT_WRITERS"},
        {"from": "StorageAuthority", "to": "NATS", "class": "DECLARED"},
        {"from": "NATS", "to": "C5", "class": "DECLARED"},
        {"from": "C5", "to": "UniversalMCP", "class": "DECLARED"},
        {"from": "UniversalMCP", "to": "CommandCenter", "class": "LIVE_IF_MCP_ONLINE"},
        {"from": "CommandCenter", "to": "CommandFabric", "class": "PROJECTION"},
        {"from": "CommandFabric", "to": "Seat Bindings", "class": "EXISTING_ACTOR_ROUTES"},
        {"from": "Seat Bindings", "to": "Workers/Engines/Factories", "class": "ON_DEMAND"},
        {"from": "Workers/Engines/Factories", "to": "Receipts/Health", "class": "EXISTING_LEDGER"},
        {"from": "Receipts/Health", "to": "Continuity", "class": "C6_OWNED"},
    ]
    return {
        "schema": "raios.system-topology.v1",
        "observed_at": _utc(),
        "canonical_head": canonical_head or plane.get("canonical_head") or heads.get("CANONICAL_HEAD") or "UNKNOWN",
        "canonical_branch": canonical_branch or "UNKNOWN",
        "heads": heads,
        "current_truth": current_truth_projection(
            canonical_head=canonical_head or plane.get("canonical_head"),
            deployed_head=(deployment or {}).get("canonical_head") if isinstance(deployment, dict) else None,
            runtime_head=canonical_head or plane.get("canonical_head"),
            observed_head=canonical_head or plane.get("canonical_head"),
            deployment=deployment if isinstance(deployment, dict) else {},
            current_state=current_state if isinstance(current_state, dict) else {},
            repo=Path(repo) if repo else None,
        ),
        "projection_ne_authority": True,
        "second_control_plane": False,
        "nodes": nodes,
        "edges": edges[:MAX_EDGES],
        "unknown_preserved": True,
        "fake_online": False,
        "recursive_scan": False,
        "law": [
            "COMMAND_CENTER_IS_PROJECTION",
            "PORT_NE_SERVICE_IDENTITY",
            "TCP_NE_OLLAMA_IDENTITY",
            "UNKNOWN_STAYS_UNKNOWN",
        ],
    }


def fabric_projection(worker: dict[str, Any] | None = None, receipts: dict[str, Any] | None = None) -> dict[str, Any]:
    worker = worker if isinstance(worker, dict) else {}
    receipts = receipts if isinstance(receipts, dict) else {}
    state = worker.get("state") or "UNKNOWN"
    if worker.get("healthy") is True:
        state = worker.get("state") or "ONLINE"
    elif worker.get("healthy") is False:
        state = "DEGRADED"
    elif not worker:
        state = "UNKNOWN"
    return {
        "schema": "raios.fabric-projection.v1",
        "observed_at": _utc(),
        "ingress": "COMMAND_FABRIC_INTERNAL_BUS",
        "worker_state": state,
        "worker_id": worker.get("worker_id"),
        "thread_alive": worker.get("thread_alive"),
        "heartbeat_current": worker.get("heartbeat_current"),
        "heartbeat_thread_alive": worker.get("heartbeat_thread_alive"),
        "workflow_enabled": worker.get("workflow_enabled") is True,
        "last_error": worker.get("last_error"),
        "consecutive_errors": worker.get("consecutive_errors"),
        "pending": "UNKNOWN",
        "delivery": "UNKNOWN",
        "receive": "UNKNOWN",
        "ack": "UNKNOWN",
        "dead_letter": "UNKNOWN",
        "orphan_deliveries": "UNKNOWN",
        "idempotency": "EXISTING_MESSAGE_ID",
        "backlog": "UNKNOWN",
        "inbox_files_scanned": False,
        "synthetic_ack": False,
        "delivery_ack_ne_actor_ack": True,
        "receipts_window": receipts.get("count"),
        "receipts_recent": (receipts.get("recent") or [])[:20],
        "second_message_bus": False,
        "second_receipt_ledger": False,
        "source": "MESSAGE_WORKER.status",
        "law": [
            "NO_INBOX_WALK_ON_DASHBOARD",
            "NO_SYNTHETIC_ACK",
            "DELIVERY_ACK_NE_ACTOR_ACK",
            "WORKER_STATUS_NE_RECONCILIATION",
        ],
    }


def self_heal_projection(continuity: dict[str, Any] | None = None) -> dict[str, Any]:
    continuity = continuity if isinstance(continuity, dict) else {}
    status = str(continuity.get("status") or "UNKNOWN").upper() or "UNKNOWN"
    if not continuity:
        status = "UNKNOWN"
    return {
        "schema": "raios.self-heal-projection.v1",
        "observed_at": _utc(),
        "current_continuity_run": continuity.get("run_id") or continuity.get("current_run") or "UNKNOWN",
        "status": status,
        "last_successful_cycle": continuity.get("last_success") or continuity.get("last_successful_cycle") or "UNKNOWN",
        "active_recovery": continuity.get("active_recovery"),
        "component_repaired": continuity.get("component_repaired") or continuity.get("repaired"),
        "failure_classification": continuity.get("failure_classification") or continuity.get("classification"),
        "recovery_outcome": continuity.get("recovery_outcome") or continuity.get("outcome"),
        "cooldown": continuity.get("cooldown"),
        "next_eligible_recovery": continuity.get("next_eligible") or continuity.get("next_eligible_recovery"),
        "services": continuity.get("services") if isinstance(continuity.get("services"), dict) else {},
        "source": "~/.raios/runtime/continuity/status.json",
        "c6_owned": True,
        "c2_mutated": False,
        "maintain_script_touched": False,
        "unknown_if_missing": not bool(continuity),
        "law": ["C6_OWNS_CONTINUITY", "C2_PROJECTS_ONLY", "UNKNOWN_IF_FILE_ABSENT"],
    }


def capability_routing_projection(repo: Path) -> dict[str, Any]:
    repo = Path(repo).resolve()
    caps = capability_projection(repo)
    keepers = []
    for kid in KEEPER_IDS:
        keepers.append({
            "id": kid,
            "role": "LIVE_KEEPER",
            "activation_mode": "ON_DEMAND",
            "activated_this_wave": False,
            "independent_process": False,
        })
    gated = [{"id": gid, "role": "GATED", "activated_this_wave": False, "readiness_proven": False}
             for gid in GATED_ENGINE_IDS]
    reference = [{"id": rid, "role": "REFERENCE_ONLY", "activated_this_wave": False}
                 for rid in REFERENCE_ENGINE_IDS]
    chain = [
        "TASK_AUTHORITY",
        "LIVE_SEAT_BINDING",
        "CAPABILITY_REQUIREMENTS",
        "CAPABILITY_ROUTER",
        "QUALIFIED_WORKER_ENGINE",
        "EXECUTION",
        "RECEIPT",
        "ACK",
        "HEALTH",
    ]
    routers = [
        {"id": "ActorRouteRegistry", "path": "src/raios/command_center/actor_routing.py", "hardcoded_agent": False},
        {"id": "ModelRouter", "path": "src/raios/ai_gateway/router.py", "hardcoded_agent": False},
        {"id": "NeuroLinguaProviderRouter", "path": "src/raios/neuro_lingua/router.py", "hardcoded_agent": False},
        {"id": "FactoryFabricOrchestrator", "path": "src/raios/factory_fabric/orchestrator.py", "hardcoded_agent": False},
    ]
    return {
        "schema": "raios.capability-routing.v1",
        "observed_at": _utc(),
        "chain": chain,
        "routers": routers,
        "keepers": keepers,
        "providers_declared": caps.get("providers") or [],
        "capabilities": caps.get("capabilities") or [],
        "gated": gated,
        "reference_only": reference,
        "capability_map": caps,
        "no_synthetic_binding": True,
        "no_synthetic_ack": True,
        "no_orphan_delivery_claimed": True,
        "no_duplicate_execution": True,
        "gated_activated": False,
        "classification_ne_process_activation": True,
        "provider_ne_core": True,
        "second_provider_plane": False,
        "hardcoded_agent_assignment": False,
        "routing_states": factory_capability_routing(),
        "law": [
            "CAPABILITY_THEN_PROVIDER",
            "PROVIDER_NE_CORE",
            "GATED_NE_ACTIVATE",
            "INVENTORY_NE_EXECUTION",
        ],
    }


def reachability_projection() -> dict[str, Any]:
    edges = [
        {"id": "mind-fill", "kind": "KEEPER", "inbound": "C5_ON_DEMAND_CLI", "outbound": "absorb",
         "wal": "FORBIDDEN", "terminal": False, "live_chain": "ON_DEMAND_SCRIPT"},
        {"id": "absorb", "kind": "KEEPER", "inbound": "mind-fill", "outbound": "index",
         "wal": "FORBIDDEN", "terminal": False, "live_chain": "ON_DEMAND_SCRIPT"},
        {"id": "index", "kind": "KEEPER", "inbound": "absorb", "outbound": "kae+search-cortex",
         "wal": "FORBIDDEN", "terminal": False, "live_chain": "ON_DEMAND_SCRIPT"},
        {"id": "kae", "kind": "KEEPER", "inbound": "index", "outbound": "book",
         "wal": "FORBIDDEN", "terminal": False, "live_chain": "ON_DEMAND_SCRIPT"},
        {"id": "book", "kind": "KEEPER", "inbound": "kae", "outbound": "neurolingua-speak",
         "wal": "FORBIDDEN", "terminal": False, "live_chain": "ON_DEMAND_SCRIPT"},
        {"id": "neurolingua-speak", "kind": "KEEPER", "inbound": "book", "outbound": "SPEAK_OUTPUT",
         "wal": "FORBIDDEN", "terminal": True, "live_chain": "ON_DEMAND_SCRIPT",
         "terminal_reason": "speak is output; not a fabric router"},
        {"id": "search-cortex", "kind": "RUNTIME_CORE", "inbound": "index+CC_/api/search",
         "outbound": "C5_GROUNDING", "terminal": False, "live_chain": "LIBRARY_IN_CC"},
        {"id": "rapidfuzz", "kind": "LIBRARY", "inbound": "absorb/kae_import", "outbound": None,
         "terminal": True, "terminal_reason": "library-only", "live_chain": "IMPORT"},
        {"id": "ollama", "kind": "PROVIDER", "inbound": "C5_GATEWAY", "outbound": "MODEL_INFERENCE",
         "terminal": False, "provider_ne_core": True, "live_chain": "EXTERNAL"},
        {"id": "nats", "kind": "PROVIDER", "inbound": "TRANSPORT_STAGE04", "outbound": "COMMAND_FABRIC",
         "terminal": False, "provider_ne_core": True, "live_chain": "EXTERNAL"},
        {"id": "workflow-engine", "kind": "GATED", "inbound": None, "outbound": None,
         "terminal": True, "terminal_reason": "gated_no_readiness", "activated": False},
        {"id": "audit-engine", "kind": "GATED", "inbound": None, "outbound": None,
         "terminal": True, "terminal_reason": "library_gated", "activated": False},
        {"id": "data-integrity-engine", "kind": "GATED", "inbound": None, "outbound": None,
         "terminal": True, "terminal_reason": "library_gated", "activated": False},
        {"id": "controlled-runtime", "kind": "GATED", "inbound": None, "outbound": None,
         "terminal": True, "terminal_reason": "gated_no_readiness", "activated": False},
        {"id": "a13-dedup", "kind": "GATED", "inbound": None, "outbound": None,
         "terminal": True, "terminal_reason": "gated_no_readiness", "activated": False},
        {"id": "semantic-engine", "kind": "REFERENCE_ONLY", "inbound": None, "outbound": None,
         "terminal": True, "terminal_reason": "reference_only", "activated": False},
        {"id": "engine-registry", "kind": "REFERENCE_ONLY", "inbound": None, "outbound": None,
         "terminal": True, "terminal_reason": "reference_only", "activated": False},
    ]
    return {
        "schema": "raios.reachability-edges.v1",
        "observed_at": _utc(),
        "entrypoint_to_wal": [
            "ENTRYPOINT", "ROUTER", "ORCHESTRATOR", "ENGINE", "TASK",
            "PROVIDER_WORKER", "EVENT_RECEIPT", "STATE/WAL",
        ],
        "zero_canonical_island": "CANDIDATE",
        "zero_canonical_island_proven": False,
        "island_proof": zero_canonical_island_proof(),
        "keeper_chain_is_fabric_router": False,
        "keepers_write_cognitive_wal": False,
        "edges": edges[:MAX_EDGES],
        "gated_activated": False,
        "second_message_bus": False,
        "law": ["INVENTORY_NE_EXECUTION", "ON_DEMAND_NE_FABRIC_ROUTER", "GATED_NE_ACTIVATE"],
    }


def storage_class_projection() -> dict[str, Any]:
    classes = [
        {"class": "PERSISTENT_CONTROL_STATE", "paths": [
            ".ai-os/state/TASKS.json", ".ai-os/state/LOCKS.json", ".ai-os/state/CURRENT-STATE.json",
            ".ai-os/governance/", ".ai-os/mcp/SEAT-MAP.json", ".ai-os/mcp/ROUTE-REGISTRY.json",
            ".ai-os/mcp/POLICY.json", ".ai-os/mcp/AI-GATEWAY.json",
        ], "delete": False},
        {"class": "DURABLE_EVIDENCE", "paths": [
            ".ai-os/receipts/", ".ai-os/handoffs/", ".ai-os/reports/",
        ], "delete": False},
        {"class": "HIGH_VOLUME_RUNTIME_TRANSPORT", "paths": [
            ".ai-os/receipts/command-fabric/",
            "%USERPROFILE%/.raios/runtime/command-center/",
            "C2 delivery inbox (thousands of json)",
        ], "delete": False, "git_ne_event_store": True},
        {"class": "CACHE", "paths": [".pytest-tmp*", "__pycache__", ".ai-os/.pytest*"], "delete": False},
        {"class": "TEMP", "paths": ["%USERPROFILE%/.raios/runtime/test-temp/"], "delete": False},
        {"class": "LEGACY_VALUE", "paths": ["brain.py", "canonical/fix_brain.py"], "delete": False},
        {"class": "UNKNOWN", "paths": [], "delete": False},
    ]
    writers = storage_writer_cutover_matrix()
    authority = storage_authority_resolution()
    return {
        "schema": "raios.storage-class.v1",
        "observed_at": _utc(),
        "recursive_scan": False,
        "blanket_delete": False,
        "second_storage_plane": False,
        "canonical_git_ne_runtime_event_store": True,
        "classes": classes,
        "STORAGE_AUTHORITY": authority.get("STORAGE_AUTHORITY"),
        "http_endpoint": None,
        "authority": authority,
        "writers": writers.get("writers") or [],
        "cutover_executed": False,
        "resolve": {
            "CONTROL_PERSISTENT": storage_resolve("CONTROL_PERSISTENT"),
            "TRANSPORT_HIGH_VOLUME": storage_resolve("TRANSPORT_HIGH_VOLUME"),
            "EVIDENCE_PERSISTENT": storage_resolve("EVIDENCE_PERSISTENT"),
        },
        "migration_ready": False,
        "migration_plan_schema": "raios.storage-migration-plan.v1",
        "law": ["NO_BLIND_DELETE", "SUPPORT_EXISTING_STORAGE_AUTHORITY", "GIT_NE_EVENT_STORE",
                "COPY_VERIFY_CUTOVER_OBSERVE"],
    }


def incidents_projection(
    *,
    attention: dict[str, Any] | None = None,
    worker: dict[str, Any] | None = None,
    topology_nodes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    attention = attention if isinstance(attention, dict) else {}
    for row in (attention.get("items") or [])[:MAX_INCIDENTS]:
        if isinstance(row, dict):
            item = dict(row)
            item["fabricated_score"] = False
            items.append(item)
    worker = worker if isinstance(worker, dict) else {}
    if worker and worker.get("healthy") is not True:
        items.append({
            "category": "RUNTIME_DEGRADED",
            "surface": "COMMAND_FABRIC_WORKER",
            "state": worker.get("state") or "UNKNOWN",
            "last_error": worker.get("last_error"),
            "fabricated_score": False,
        })
    for node in (topology_nodes or [])[:32]:
        if not isinstance(node, dict):
            continue
        state = str(node.get("state") or "").upper()
        if state in {"DEGRADED", "OFFLINE", "STALE"}:
            items.append({
                "category": "RUNTIME_DEGRADED" if state == "DEGRADED" else state,
                "surface": node.get("name"),
                "state": state,
                "probe": node.get("probe"),
                "fabricated_score": False,
            })
        elif state == "UNKNOWN":
            items.append({
                "category": "UNKNOWN",
                "surface": node.get("name"),
                "state": "UNKNOWN",
                "probe": node.get("probe"),
                "fabricated_score": False,
            })
    seen: set[tuple[Any, Any]] = set()
    unique: list[dict[str, Any]] = []
    for row in items:
        key = (row.get("category"), row.get("surface") or row.get("task_id") or row.get("engine"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return {
        "schema": "raios.incidents.v1",
        "observed_at": _utc(),
        "fabricated_score": False,
        "items": unique[:MAX_INCIDENTS],
        "count": min(len(unique), MAX_INCIDENTS),
        "law": ["NO_FAKE_ONLINE", "UNKNOWN_STAYS_UNKNOWN", "STALE_STAYS_STALE"],
    }


SINGLE_TRUTH_POLICY_REL = Path(".ai-os") / "governance" / "RAIOS-SINGLE-TRUTH-POLICY.json"
CORE_CONTRACT_REL = Path(".ai-os") / "CORE-CONTRACT.md"

CANONICAL_OPERATOR_LAWS: tuple[dict[str, str], ...] = (
    {"id": "COMPLETE_ASSIGNED_WORK", "en": "Assigned work must be finished. Incomplete stop is forbidden.",
     "ar": "العمل الموكول يُتم. التوقف الناقص ممنوع."},
    {"id": "NO_ABBREVIATION", "en": "No silent shortcut that drops discovery, proof, validation, or handoff.",
     "ar": "لا اختزال صامت يسقط الاكتشاف أو الإثبات أو التحقق أو التسليم."},
    {"id": "NO_CONFLICT", "en": "Do not contradict canonical law, an active lock, or another live writer.",
     "ar": "لا تضارب مع القانون أو القفل الحي أو كاتب آخر على نفس النطاق."},
    {"id": "NO_DUPLICATION", "en": "Existing-first. No second control plane, ledger, bus, or Command Center.",
     "ar": "الموجود أولاً. لا سطح سيطرة ثانٍ ولا دفتر ولا حافلة ولا مركز أوامر بديل."},
    {"id": "NO_FAKE_RESULT", "en": "HTTP 200 is not Actor ACK. TIMEOUT is not empty success. Presence is not execution.",
     "ar": "HTTP 200 ليست قراءة الممثل. المهلة ليست نجاحاً فارغاً. الحضور ليس تنفيذاً."},
    {"id": "NO_FAKE_DONE", "en": "TASKS DONE requires recorded evidence. Do not stamp complete to hide unfinished work.",
     "ar": "DONE يتطلب دليلاً مسجلاً. لا تُختم مكتملة لإخفاء عمل ناقص."},
    {"id": "NO_HANGING_WITHOUT_NOTICE", "en": "Open READY/IN_PROGRESS/BLOCKED work stays visible on Command Center.",
     "ar": "العمل المفتوح يبقى ظاهراً على مركز الأوامر حتى يُغلق أو يُحجب بصدق."},
    {"id": "LAWS_SYSTEM_VISIBLE", "en": "Laws must be projected by Command Center to every operator, not chat-only.",
     "ar": "القوانين ظاهرة في النظام لكل المقاعد، وليست قوانين محادثة فقط."},
    {"id": "EXISTING_FIRST", "en": "Discover, prove, reuse, upgrade in place before creating.",
     "ar": "اكتشف وأثبت وأعد الاستخدام ثم رقِّ في المكان قبل الإنشاء."},
    {"id": "ONE_COMMAND_CENTER", "en": "Repair and promote the existing Command Center. Do not replace it.",
     "ar": "أصلح ورقِّ مركز الأوامر القائم. لا تستبدله."},
    {"id": "DELIVERY_ACK_NE_ACTOR_ACK", "en": "Fabric delivery is not a human/agent read. Interaction is required.",
     "ar": "إيصال التسليم ليس قراءة. التفاعل مطلوب قبل اعتبار الطرف مستلماً."},
    {"id": "C5_RUNTIME_NE_SEAT_PRESENCE", "en": "RAIOS/C5 is runtime. It is not a fabric council seat.",
     "ar": "RAIOS/C5 زمن تشغيل وليس مقعد مجلس."},
)


def operator_laws_projection(repo: Path | None = None) -> dict[str, Any]:
    """Project C1 operator laws from CORE-CONTRACT + SINGLE-TRUTH. Not a second constitution."""
    policy: dict[str, Any] = {}
    contract_present = False
    if repo is not None:
        root = Path(repo)
        policy = _load(root / SINGLE_TRUTH_POLICY_REL, {})
        contract_present = (root / CORE_CONTRACT_REL).is_file()
    block = policy.get("completion_operator_laws") if isinstance(policy, dict) else {}
    if not isinstance(block, dict):
        block = {}
    extra_ids = [str(x) for x in (block.get("laws") or []) if str(x).strip()]
    by_id = {row["id"]: dict(row) for row in CANONICAL_OPERATOR_LAWS}
    for law_id in extra_ids:
        by_id.setdefault(law_id, {"id": law_id, "en": law_id, "ar": law_id})
    laws = list(by_id.values())
    return {
        "schema": "raios.operator-laws.v1",
        "observed_at": _utc(),
        "authority": block.get("authority") or "C1",
        "state_owner": block.get("state_owner") or "RAIOS_SYSTEM",
        "chat_only": False,
        "binds": list(block.get("binds") or ["ALL_SEATS", "COMMAND_CENTER", "ENGINES", "CLIENTS", "WORKERS"]),
        "surface": block.get("surface") or "/api/laws",
        "mandatory": block.get("mandatory") is not False,
        "sources": [str(CORE_CONTRACT_REL), str(SINGLE_TRUTH_POLICY_REL)],
        "core_contract_present": contract_present,
        "policy_present": bool(block),
        "second_constitution": False,
        "count": len(laws),
        "laws": laws,
        "ids": [row["id"] for row in laws],
    }


def integration_mesh_projection(
    *,
    plane: dict[str, Any] | None = None,
    worker: dict[str, Any] | None = None,
    hanging: dict[str, Any] | None = None,
    laws: dict[str, Any] | None = None,
    c5_http: int | None = None,
    mcp_http: int | None = None,
    mcp_live: bool | None = None,
    factory_runtime: dict[str, Any] | None = None,
    live_bound_count: int = 0,
    ecology_source_present: bool | None = None,
    direct_second_bus: bool = False,
) -> dict[str, Any]:
    """Honest CC↔runtime interconnection. TIMEOUT/TCP-only stay UNKNOWN. Not a second bus."""
    plane = plane if isinstance(plane, dict) else {}
    worker = worker if isinstance(worker, dict) else {}
    hanging = hanging if isinstance(hanging, dict) else {}
    laws = laws if isinstance(laws, dict) else {}
    factory_runtime = factory_runtime if isinstance(factory_runtime, dict) else {}
    by_name = {
        str(row.get("name") or ""): row
        for row in (plane.get("services") or [])
        if isinstance(row, dict)
    }

    def _svc(name: str) -> dict[str, Any]:
        return by_name.get(name) or {}

    c5_tcp = str((_svc("C5") or {}).get("state") or "").upper()
    if c5_http == 200:
        c5_state = "ONLINE"
    elif c5_tcp in {"ONLINE", "UNKNOWN"} and c5_http != 200:
        c5_state = "UNKNOWN"
    elif c5_tcp == "OFFLINE":
        c5_state = "OFFLINE"
    else:
        c5_state = c5_tcp or "UNKNOWN"

    mcp_tcp = str((_svc("UniversalMCP") or {}).get("state") or "").upper()
    if mcp_live is True or mcp_http == 200:
        mcp_state = "ONLINE"
    elif mcp_http == 0 or mcp_tcp in {"UNKNOWN", "ONLINE"}:
        mcp_state = "UNKNOWN" if mcp_http != 200 else "ONLINE"
    else:
        mcp_state = mcp_tcp or "UNKNOWN"

    nr_state = str((_svc("9Router") or {}).get("state") or "UNKNOWN").upper() or "UNKNOWN"
    nats_state = str((_svc("NATS") or {}).get("state") or "UNKNOWN").upper() or "UNKNOWN"
    if worker.get("healthy") is True:
        fabric_state = str(worker.get("state") or "ONLINE")
    elif worker.get("healthy") is False:
        fabric_state = "DEGRADED"
    else:
        fabric_state = str(worker.get("state") or "UNKNOWN") or "UNKNOWN"
    factory_status = str(
        factory_runtime.get("status") or factory_runtime.get("FACTORY_FABRIC") or ""
    ).upper()
    if factory_runtime.get("ok") is True:
        factory_status = "PASS"
    if not factory_runtime:
        factory_status = "UNPROVEN"
    ecology_state = "WIRED" if ecology_source_present is True else (
        "ABSENT" if ecology_source_present is False else "UNKNOWN"
    )
    laws_state = "VISIBLE" if int(laws.get("count") or 0) > 0 and laws.get("chat_only") is False else "MISSING"
    hanging_state = "INFORMED" if hanging.get("system_informed") is True else "UNPROVEN"
    seats_state = "BOUND" if int(live_bound_count or 0) > 0 else "UNBOUND"
    direct_state = "WIRED" if direct_second_bus is False else "SECOND_BUS_FORBIDDEN"

    links = [
        {"id": "command-center", "name": "CommandCenter", "state": "ONLINE", "port": 8770,
         "role": "PROJECTION_SURFACE", "probe": "SELF"},
        {"id": "c5", "name": "C5", "state": c5_state, "port": 8766,
         "role": "RUNTIME", "http": c5_http, "tcp_ne_http": c5_http != 200},
        {"id": "mcp", "name": "UniversalMCP", "state": mcp_state, "port": 8788,
         "role": "CLIENT_GATEWAY", "http": mcp_http, "live": mcp_live is True},
        {"id": "ninerouter", "name": "9Router", "state": nr_state, "port": 20128,
         "role": "MODEL_ROUTER", "probe": "TCP_ONLY"},
        {"id": "nats", "name": "NATS", "state": nats_state, "port": 4222,
         "role": "TRANSPORT", "optional": False, "probe": "TCP_ONLY"},
        {"id": "command-fabric", "name": "CommandFabric", "state": fabric_state,
         "role": "SEAT_BUS", "healthy": worker.get("healthy") is True},
        {"id": "direct-conversation", "name": "DirectConversation", "state": direct_state,
         "role": "ONE_TO_ONE", "second_bus": direct_second_bus},
        {"id": "operator-laws", "name": "OperatorLaws", "state": laws_state,
         "role": "SYSTEM_VISIBLE", "count": laws.get("count")},
        {"id": "hanging-work", "name": "HangingWork", "state": hanging_state,
         "role": "TASK_NOTICE", "open_count": hanging.get("open_count")},
        {"id": "factory-fabric", "name": "FactoryFabric", "state": factory_status or "UNPROVEN",
         "role": "FACTORIES", "file_present": bool(factory_runtime)},
        {"id": "ecomodel", "name": "EcoModel", "state": ecology_state,
         "role": "MODEL_ECOLOGY", "source": "src/raios/factory_fabric/model_ecology.py"},
        {"id": "live-seats", "name": "LiveBoundSeats", "state": seats_state,
         "role": "CONSUMERS", "count": int(live_bound_count or 0)},
    ]

    by_id = {row["id"]: row for row in links}

    def _critical_ok(link_id: str, want: str) -> bool:
        state = str((by_id.get(link_id) or {}).get("state") or "").upper()
        if link_id == "command-fabric":
            return worker.get("healthy") is True or state in {"ONLINE", "HEALTHY"}
        return state == want

    critical_ok = all(
        _critical_ok(k, v)
        for k, v in {
            "command-center": "ONLINE",
            "c5": "ONLINE",
            "mcp": "ONLINE",
            "ninerouter": "ONLINE",
            "nats": "ONLINE",
            "command-fabric": "ONLINE",
            "operator-laws": "VISIBLE",
            "direct-conversation": "WIRED",
            "hanging-work": "INFORMED",
        }.items()
    )
    ninerouter_ok = nr_state == "ONLINE"
    if critical_ok and int(live_bound_count or 0) > 0 and ninerouter_ok:
        overall = "CONTROL_PLANE_AND_SEATS_BOUND"
    elif critical_ok:
        overall = "CONTROL_PLANE_BOUND_SEATS_UNBOUND"
    elif any(str(x.get("state") or "").upper() in {"ONLINE", "VISIBLE", "WIRED", "INFORMED", "PASS"} for x in links):
        overall = "PARTIAL"
    else:
        overall = "UNPROVEN"
    return {
        "schema": "raios.integration-mesh.v1",
        "observed_at": _utc(),
        "overall": overall,
        "fully_integrated": overall == "CONTROL_PLANE_AND_SEATS_BOUND",
        "fake_integrated": False,
        "second_command_center": False,
        "second_message_bus": False,
        "live_bound_count": int(live_bound_count or 0),
        "actor_ack_proven": False,
        "hanging_open_count": hanging.get("open_count"),
        "links": links,
        "law": [
            "UNKNOWN_STAYS_UNKNOWN",
            "TCP_NE_HTTP_IDENTITY",
            "NO_FAKE_INTEGRATED",
            "LIVE_BOUND_REQUIRED_FOR_ACTOR_ACK",
            "ONE_COMMAND_CENTER",
        ],
    }
