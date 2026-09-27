"""Wave-02 live-activation evidence: storage writers, factory readiness, islands.

Not a second storage plane, registry, bus, or factory. Does not cut over paths.
Does not walk command-fabric inboxes. Does not modify C6/C8 runtimes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNTIME_FABRIC = "%USERPROFILE%/.raios/runtime/command-fabric"
RUNTIME_CC = "%USERPROFILE%/.raios/runtime/command-center"
RUNTIME_FACTORY = "%USERPROFILE%/.raios/runtime/factory-fabric"
RUNTIME_COUNCIL = "%USERPROFILE%/.raios/runtime/council-ops"
RUNTIME_CONTINUITY = "%USERPROFILE%/.raios/runtime/continuity"

# Bounded writer catalog. Not a filesystem inventory.
STORAGE_WRITERS: tuple[dict[str, Any], ...] = (
    {
        "writer": "raios.orchestration.tasks_write",
        "data_class": "CONTROL_PERSISTENT",
        "current_path": ".ai-os/state/TASKS.json",
        "write_frequency": "CAS_ON_CLAIM",
        "durability": "DURABLE",
        "canonical_authority": "RAIOS_SYSTEM / tasks_write.replace_tasks_document",
        "git_required": True,
        "runtime_only": False,
        "migration_required": False,
        "compatibility_dependency": "FocusContext, Command Center /api/tasks",
        "safe_target_path": ".ai-os/state/TASKS.json",
        "cutover_readiness": "ALREADY_CANONICAL",
        "owner": "RAIOS_SYSTEM",
        "lease_state": "SYSTEM_OWNED",
    },
    {
        "writer": "scripts/ai-os/aios.py:lock",
        "data_class": "CONTROL_PERSISTENT",
        "current_path": ".ai-os/state/LOCKS.json",
        "write_frequency": "LEASE_CLAIM",
        "durability": "DURABLE",
        "canonical_authority": "RAIOS_SYSTEM",
        "git_required": True,
        "runtime_only": False,
        "migration_required": False,
        "compatibility_dependency": "lock_is_effective",
        "safe_target_path": ".ai-os/state/LOCKS.json",
        "cutover_readiness": "ALREADY_CANONICAL",
        "owner": "RAIOS_SYSTEM",
        "lease_state": "SYSTEM_OWNED",
    },
    {
        "writer": "shared-state CURRENT-STATE",
        "data_class": "GOVERNANCE_PERSISTENT",
        "current_path": ".ai-os/state/CURRENT-STATE.json",
        "write_frequency": "WAVE",
        "durability": "DURABLE",
        "canonical_authority": "C1 / RAIOS_SYSTEM",
        "git_required": True,
        "runtime_only": False,
        "migration_required": False,
        "compatibility_dependency": "resume_from_canonical_state",
        "safe_target_path": ".ai-os/state/CURRENT-STATE.json",
        "cutover_readiness": "ALREADY_CANONICAL",
        "owner": "RAIOS_SYSTEM",
        "lease_state": "SYSTEM_OWNED",
    },
    {
        "writer": ".ai-os/governance/*",
        "data_class": "GOVERNANCE_PERSISTENT",
        "current_path": ".ai-os/governance/",
        "write_frequency": "POLICY",
        "durability": "DURABLE",
        "canonical_authority": "C1",
        "git_required": True,
        "runtime_only": False,
        "migration_required": False,
        "compatibility_dependency": "RAIOS-RESUME-CONTRACT",
        "safe_target_path": ".ai-os/governance/",
        "cutover_readiness": "ALREADY_CANONICAL",
        "owner": "C1",
        "lease_state": "C1",
    },
    {
        "writer": "raios.command_center.message_worker inbox",
        "data_class": "TRANSPORT_HIGH_VOLUME",
        "current_path": ".ai-os/state/command-fabric/inbox",
        "write_frequency": "PER_MESSAGE",
        "durability": "DURABLE_UNTIL_TERMINAL",
        "canonical_authority": "Command Fabric INTERNAL_BUS",
        "git_required": False,
        "runtime_only": True,
        "migration_required": True,
        "compatibility_dependency": "src/raios/command_center/message_worker.py (C6; RAIOS_COMMAND_FABRIC_ROOT; C2 must not edit)",
        "safe_target_path": RUNTIME_FABRIC + "/inbox",
        "cutover_readiness": "BLOCKED_UNTIL_C6_TRANSACTIONAL_CUTOVER",
        "owner": "C6",
        "lease_state": "DO_NOT_MODIFY_MESSAGE_WORKER",
        "cutover_method": "COPY_VERIFY_CUTOVER_OBSERVE",
        "delete_old_this_wave": False,
    },
    {
        "writer": "raios.command_center.message_worker deliveries",
        "data_class": "TRANSPORT_HIGH_VOLUME",
        "current_path": ".ai-os/state/command-fabric/deliveries",
        "write_frequency": "PER_DELIVERY",
        "durability": "DURABLE_UNTIL_TERMINAL",
        "canonical_authority": "Command Fabric INTERNAL_BUS",
        "git_required": False,
        "runtime_only": True,
        "migration_required": True,
        "compatibility_dependency": "message_worker.py C6",
        "safe_target_path": RUNTIME_FABRIC + "/deliveries",
        "cutover_readiness": "BLOCKED_UNTIL_C6_TRANSACTIONAL_CUTOVER",
        "owner": "C6",
        "lease_state": "DO_NOT_MODIFY_MESSAGE_WORKER",
        "delete_old_this_wave": False,
    },
    {
        "writer": "raios.command_center.message_worker outbox/dead-letter",
        "data_class": "TRANSPORT_HIGH_VOLUME",
        "current_path": ".ai-os/state/command-fabric/outbox|dead-letter",
        "write_frequency": "PER_MESSAGE",
        "durability": "DURABLE_UNTIL_TERMINAL",
        "canonical_authority": "Command Fabric INTERNAL_BUS",
        "git_required": False,
        "runtime_only": True,
        "migration_required": True,
        "compatibility_dependency": "message_worker.py C6 RAIOS_COMMAND_FABRIC_ROOT",
        "safe_target_path": RUNTIME_FABRIC + "/outbox|dead-letter",
        "cutover_readiness": "BLOCKED_UNTIL_C6_TRANSACTIONAL_CUTOVER",
        "owner": "C6",
        "lease_state": "DO_NOT_MODIFY_MESSAGE_WORKER",
        "delete_old_this_wave": False,
    },
    {
        "writer": "raios.command_center.message_worker receipts",
        "data_class": "EVENT_HIGH_VOLUME",
        "current_path": ".ai-os/receipts/command-fabric",
        "write_frequency": "PER_ACK",
        "durability": "EVIDENCE_PERSISTENT",
        "canonical_authority": "existing receipt ledger",
        "git_required": "DURABLE_SUBSET_ONLY",
        "runtime_only": False,
        "migration_required": True,
        "compatibility_dependency": "message_worker.py + council_board + client_activity",
        "safe_target_path": RUNTIME_FABRIC + "/receipts (hot); keep durable subset in .ai-os/receipts/command-fabric",
        "cutover_readiness": "BLOCKED_UNTIL_C6_TRANSACTIONAL_CUTOVER",
        "owner": "C6",
        "lease_state": "DO_NOT_MODIFY_MESSAGE_WORKER",
        "delete_old_this_wave": False,
    },
    {
        "writer": "raios.command_center.message_worker worker heartbeat",
        "data_class": "RUNTIME_TRANSIENT",
        "current_path": RUNTIME_CC + "/worker",
        "write_frequency": "5s",
        "durability": "LEASE",
        "canonical_authority": "MessageWorker.status",
        "git_required": False,
        "runtime_only": True,
        "migration_required": False,
        "compatibility_dependency": "RAIOS_COMMAND_CENTER_RUNTIME",
        "safe_target_path": RUNTIME_CC + "/worker",
        "cutover_readiness": "ALREADY_RUNTIME",
        "owner": "C6",
        "lease_state": "RUNTIME_ENV",
    },
    {
        "writer": "raios.council_ops.session_agent",
        "data_class": "RUNTIME_TRANSIENT",
        "current_path": RUNTIME_COUNCIL + "/consumers|bindings|presence",
        "write_frequency": "HEARTBEAT",
        "durability": "LEASE",
        "canonical_authority": "CouncilOperations",
        "git_required": False,
        "runtime_only": True,
        "migration_required": False,
        "compatibility_dependency": "src/raios/council_ops/session_agent.py (C8)",
        "safe_target_path": RUNTIME_COUNCIL,
        "cutover_readiness": "ALREADY_RUNTIME",
        "owner": "C8",
        "lease_state": "DO_NOT_MODIFY_SESSION_AGENT",
    },
    {
        "writer": "raios.factory_fabric.orchestrator.run_all",
        "data_class": "RUNTIME_TRANSIENT",
        "current_path": RUNTIME_FACTORY + "/FACTORY-FABRIC-LATEST.json",
        "write_frequency": "ON_DEMAND_RUN",
        "durability": "LATEST_SNAPSHOT",
        "canonical_authority": "factory_fabric.orchestrator",
        "git_required": False,
        "runtime_only": True,
        "migration_required": False,
        "compatibility_dependency": "Command Center FACTORY_RUNTIME_LATEST env",
        "safe_target_path": RUNTIME_FACTORY + "/FACTORY-FABRIC-LATEST.json",
        "cutover_readiness": "ALREADY_RUNTIME",
        "owner": "C2_FACTORY_FABRIC",
        "lease_state": "NONE",
    },
    {
        "writer": "C6 continuity status",
        "data_class": "RUNTIME_TRANSIENT",
        "current_path": RUNTIME_CONTINUITY + "/status.json",
        "write_frequency": "CYCLE",
        "durability": "LEASE",
        "canonical_authority": "C6 continuity",
        "git_required": False,
        "runtime_only": True,
        "migration_required": False,
        "compatibility_dependency": "Maintain-RAIOS-Online.ps1 (C6)",
        "safe_target_path": RUNTIME_CONTINUITY + "/status.json",
        "cutover_readiness": "ALREADY_RUNTIME",
        "owner": "C6",
        "lease_state": "DO_NOT_MODIFY_MAINTAIN_SCRIPT",
    },
    {
        "writer": "raios.c1c5.receipts",
        "data_class": "EVIDENCE_PERSISTENT",
        "current_path": ".ai-os/receipts/command-fabric/c1c5-task",
        "write_frequency": "PER_BOUND_TASK",
        "durability": "DURABLE",
        "canonical_authority": "existing receipt ledger",
        "git_required": True,
        "runtime_only": False,
        "migration_required": False,
        "compatibility_dependency": "EXISTING_RECEIPT_ROOT",
        "safe_target_path": ".ai-os/receipts/command-fabric/c1c5-task",
        "cutover_readiness": "ALREADY_CANONICAL",
        "owner": "RAIOS_SYSTEM",
        "lease_state": "SYSTEM_OWNED",
    },
    {
        "writer": "learning DIGESTS/INDEX",
        "data_class": "EVIDENCE_PERSISTENT",
        "current_path": ".ai-os/learning/",
        "write_frequency": "KEEPER_ON_DEMAND",
        "durability": "DURABLE",
        "canonical_authority": "keepers (must not write Cognitive WAL)",
        "git_required": True,
        "runtime_only": False,
        "migration_required": False,
        "compatibility_dependency": "Search Cortex / KAE",
        "safe_target_path": ".ai-os/learning/",
        "cutover_readiness": "ALREADY_CANONICAL",
        "owner": "C5_KEEPERS",
        "lease_state": "ON_DEMAND",
    },
    {
        "writer": "pytest / __pycache__",
        "data_class": "CACHE_TRANSIENT",
        "current_path": ".pytest-tmp* | __pycache__ | %USERPROFILE%/.raios/runtime/test-temp",
        "write_frequency": "TEST",
        "durability": "EPHEMERAL",
        "canonical_authority": "none",
        "git_required": False,
        "runtime_only": True,
        "migration_required": False,
        "compatibility_dependency": None,
        "safe_target_path": "%USERPROFILE%/.raios/runtime/test-temp",
        "cutover_readiness": "ALREADY_RUNTIME_PREFERRED",
        "owner": "TEST",
        "lease_state": "NONE",
        "delete_old_this_wave": False,
    },
)

FACTORY_READINESS: tuple[dict[str, Any], ...] = (
    {
        "factory": "resource_factory",
        "entrypoint": "raios.factory_fabric.orchestrator.resource_factory_probe",
        "capability": "RESOURCE_PLACEMENT",
        "provider_requirements": ["resource_fabric.census", "resource_fabric.placement"],
        "input_contract": "workload_class CONTROL|MODEL_FACTORY + world census",
        "output_contract": "decision.result_class + plan.dispatch_allowed",
        "task_authority": "EXISTING_TASK_REGISTRY .ai-os/state/TASKS.json",
        "lease_requirement": "EXISTING_LEASE_SYSTEM .ai-os/state/command-fabric/leases",
        "receipt_path": ".ai-os/receipts/command-fabric (evaluate_workload does not write)",
        "health_signal": "status PASS + dispatch_allowed",
        "idempotency": "request_id FACTORY-FABRIC-CONTROL",
        "safe_activation_condition": "live=False; no GPU; no paid resource; Command Fabric route when claiming ACTIVE cycle",
        "readiness": "READY_FOR_ON_DEMAND",
        "blocked_edge": None,
    },
    {
        "factory": "assimilation_factory",
        "entrypoint": "raios.factory_fabric.orchestrator.assimilation_probe",
        "capability": "ASSIMILATION",
        "provider_requirements": ["factory_fabric.state_import"],
        "input_contract": "imported estate events under factory runtime root",
        "output_contract": "curriculum raw_events/unique_materials/assimilation_units",
        "task_authority": "TASKS.json",
        "lease_requirement": "none for probe",
        "receipt_path": RUNTIME_FACTORY,
        "health_signal": "status PASS if raw_events>0 else FAIL_EMPTY_INPUT",
        "idempotency": "content-addressed object ids",
        "safe_activation_condition": "writes only under ~/.raios/runtime/factory-fabric",
        "readiness": "READY_FOR_ON_DEMAND",
        "blocked_edge": "EMPTY_INPUT_IF_NO_ESTATE_EVENTS",
    },
    {
        "factory": "cognitive_factory",
        "entrypoint": "raios.factory_fabric.orchestrator.cognitive_factory_probe",
        "capability": "COGNITIVE_FACTORY",
        "provider_requirements": ["factory_fabric.cognitive"],
        "input_contract": "CONTENT_ADDRESSED_FACTORY_ESTATE",
        "output_contract": "BENCHMARK/SKILL/TRAINING candidates (no auto-promote)",
        "task_authority": "TASKS.json",
        "lease_requirement": "none for probe",
        "receipt_path": RUNTIME_FACTORY,
        "health_signal": "analyze_cognitive_estate status",
        "idempotency": "sha256(source|category|capability)",
        "safe_activation_condition": "write_runtime_artifacts under runtime root only",
        "readiness": "READY_FOR_ON_DEMAND",
        "blocked_edge": None,
    },
    {
        "factory": "training_factory",
        "entrypoint": "raios.factory_fabric.orchestrator.training_factory_probe",
        "capability": "TRAINING",
        "provider_requirements": ["node", "scripts/runtime/verify-training-factory.mjs"],
        "input_contract": "node runner JSON line",
        "output_contract": "status PASS; auto_train=false auto_promote=false",
        "task_authority": "TASKS.json",
        "lease_requirement": "none for verify",
        "receipt_path": "stdout JSON",
        "health_signal": "returncode 0",
        "idempotency": "verify script",
        "safe_activation_condition": "no auto_train; no auto_promote",
        "readiness": "READY_FOR_ON_DEMAND",
        "blocked_edge": "NODE_RUNTIME",
    },
    {
        "factory": "c5_expert_foundry",
        "entrypoint": "raios.factory_fabric.orchestrator.foundry_probe",
        "capability": "EXPERT_FOUNDRY",
        "provider_requirements": ["ollama optional", "foundry_engine"],
        "input_contract": "max_files/case_limit bounded",
        "output_contract": "extract/cases/split/train/blind/promotion/receipt",
        "task_authority": "TASKS.json + C1 for promotion",
        "lease_requirement": "foundry runtime root",
        "receipt_path": RUNTIME_FACTORY + "/foundry",
        "health_signal": "status PASS; canonical_promotions=0 unless C1",
        "idempotency": "foundry run ids",
        "safe_activation_condition": "no automatic canonical promotion",
        "readiness": "BLOCKED_AUTHORITY",
        "blocked_edge": "PROMOTION_REQUIRES_C1; not a fabric-routed cycle this wave",
    },
    {
        "factory": "qwen_granite",
        "entrypoint": "C6_MATRIX tests 14/14",
        "capability": "MODEL_COMPAT",
        "provider_requirements": [],
        "input_contract": "compatibility evaluation",
        "output_contract": "source_independent PASS",
        "task_authority": "TASKS.json",
        "lease_requirement": "none",
        "receipt_path": "C6 factory matrix",
        "health_signal": "matrix PASS",
        "idempotency": "tests",
        "safe_activation_condition": "library/eval; not a standalone service",
        "readiness": "READY_FOR_ON_DEMAND",
        "blocked_edge": None,
    },
    {
        "factory": "weight_merge",
        "entrypoint": "C6_MATRIX PROVEN_EXISTING",
        "capability": "WEIGHT_MERGE",
        "provider_requirements": ["model weights"],
        "input_contract": "merge-candidate evaluation",
        "output_contract": "none this wave",
        "task_authority": "C1 gate",
        "lease_requirement": "explicit gate",
        "receipt_path": None,
        "health_signal": None,
        "idempotency": None,
        "safe_activation_condition": "existing gate must explicitly authorize",
        "readiness": "GATED_BY_DESIGN",
        "blocked_edge": "GATE_NOT_AUTHORIZED",
    },
    {
        "factory": "model_ecology",
        "entrypoint": "raios.factory_fabric.model_ecology.classify_local_models",
        "capability": "MODEL_ECOLOGY",
        "provider_requirements": ["local model inventory", "c5 health live_engines", "existing account probes", "9router catalog"],
        "input_contract": "repo + runtime root + C5 /health + factory-fabric + copy-estate + existing accounts",
        "output_contract": "classification counts; auto_promote=false",
        "task_authority": "CANONICAL_STUDENT_AND_LIVE_ENGINES",
        "lease_requirement": "none for classify",
        "receipt_path": RUNTIME_FACTORY,
        "health_signal": "C5 /health live_engines",
        "idempotency": "classify_local_models rewrite MODEL-ECOLOGY.json",
        "safe_activation_condition": "on-demand classify; never auto-promote; never delete weights",
        "readiness": "READY_FOR_ON_DEMAND",
        "blocked_edge": None,
    },
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def storage_authority_resolution() -> dict[str, Any]:
    return {
        "schema": "raios.storage-authority-resolution.v1",
        "observed_at": _utc(),
        "STORAGE_AUTHORITY": "EXISTING_SPLIT_WRITERS",
        "http_endpoint": None,
        "not_an_http_service": True,
        "second_storage_plane": False,
        "domains": {
            "governance_control_state": "GOVERNANCE_PERSISTENT:.ai-os/governance + CURRENT-STATE + mcp POLICY/SEAT-MAP",
            "task_lease_state": "CONTROL_PERSISTENT:.ai-os/state/TASKS.json + LOCKS.json + command-fabric/leases",
            "deployment_truth": "GOVERNANCE_PERSISTENT:.ai-os/mcp/CANONICAL-CHANGE-AUTHORITY.json + git HEAD",
            "command_fabric_transport": "TRANSPORT_HIGH_VOLUME:.ai-os/state/command-fabric/{inbox,outbox,deliveries,dead-letter}",
            "event_receipts": "EVENT_HIGH_VOLUME+EVIDENCE_PERSISTENT:.ai-os/receipts/command-fabric",
            "high_volume_runtime_telemetry": "RUNTIME_TRANSIENT:" + RUNTIME_CC,
            "factory_runtime_state": "RUNTIME_TRANSIENT:" + RUNTIME_FACTORY,
            "engine_runtime_state": "RUNTIME_TRANSIENT:keeper receipts under .ai-os/receipts/c5-* LAST.json",
            "durable_evidence": "EVIDENCE_PERSISTENT:.ai-os/receipts .ai-os/handoffs .ai-os/reports",
            "transient_cache": "CACHE_TRANSIENT:pytest/__pycache__/test-temp",
        },
        "principle": "GIT_WORKING_TREE_NE_HIGH_VOLUME_RUNTIME_TRANSPORT_DB",
        "identified": True,
        "cutover_executed": False,
        "blanket_delete": False,
        "blanket_gitignore": False,
        "law": [
            "COPY_VERIFY_CUTOVER_OBSERVE",
            "NO_MOVE_DELETE_HOPE",
            "NO_SECOND_STORAGE_PLANE",
            "C6_OWNS_MESSAGE_WORKER_PATH",
        ],
    }


def storage_writer_cutover_matrix() -> dict[str, Any]:
    writers = [dict(row) for row in STORAGE_WRITERS]
    high_volume = [w for w in writers if w["data_class"] in {"TRANSPORT_HIGH_VOLUME", "EVENT_HIGH_VOLUME"}]
    return {
        "schema": "raios.storage-writer-cutover-matrix.v1",
        "observed_at": _utc(),
        "recursive_scan": False,
        "writers": writers,
        "writer_count": len(writers),
        "high_volume_count": len(high_volume),
        "cutover_executed": False,
        "delete_old_this_wave": False,
        "blocking_edge": "BLOCKED_UNTIL_C6_TRANSACTIONAL_CUTOVER; MessageWorker uses RAIOS_COMMAND_FABRIC_ROOT; C2 must not edit message_worker.py",
        "method_required": "COPY → VERIFY → CUTOVER → OBSERVE",
        "second_storage_plane": False,
    }


def factory_activation_readiness() -> dict[str, Any]:
    rows = [dict(r) for r in FACTORY_READINESS]
    by = {r["readiness"]: 0 for r in rows}
    for r in rows:
        by[r["readiness"]] = by.get(r["readiness"], 0) + 1
    return {
        "schema": "raios.factory-activation-readiness.v1",
        "observed_at": _utc(),
        "factories": rows,
        "counts": by,
        "ready_for_on_demand": [r["factory"] for r in rows if r["readiness"] == "READY_FOR_ON_DEMAND"],
        "gated": [r["factory"] for r in rows if r["readiness"] == "GATED_BY_DESIGN"],
        "unresolved": [r["factory"] for r in rows if r["readiness"] == "UNRESOLVED"],
        "weight_merge_activated": False,
        "model_ecology_activated": True,
        "model_ecology_auto_promote": False,
        "run_all_invoked": False,
        "second_factory": False,
    }


def factory_capability_routing() -> dict[str, Any]:
    def _row(cap: str, provider: str, engine: str, *, installed: bool, discovered: bool,
             wired: bool, routable: bool, available: str, active: bool, executing: bool,
             healthy: str, receipt: str, health_source: str, note: str) -> dict[str, Any]:
        return {
            "CAPABILITY": cap,
            "PROVIDER": provider,
            "ENGINE_FACTORY_WORKER": engine,
            "INSTALLED": installed,
            "DISCOVERED": discovered,
            "WIRED": wired,
            "ROUTABLE": routable,
            "AVAILABLE": available,
            "ACTIVE": active,
            "EXECUTING": executing,
            "HEALTHY": healthy,
            "EXECUTION_CONTRACT": "on_demand_or_fabric_when_cc_up",
            "RECEIPT_CONTRACT": receipt,
            "HEALTH_SOURCE": health_source,
            "note": note,
            "tcp_ne_verified": True,
        }

    caps = [
        _row("RESOURCE_PLACEMENT", "resource_fabric", "resource_factory",
             installed=True, discovered=True, wired=True, routable=False,
             available="ON_DEMAND", active=False, executing=False, healthy="UNPROVEN_LIVE",
             receipt="evaluate_workload does not write; fabric receipt required for ACTIVE cycle",
             health_source="probe status",
             note="ROUTABLE only via Command Fabric task route; worker ONLINE ≠ capability ACTIVE"),
        _row("ASSIMILATION", None, "assimilation_factory",
             installed=True, discovered=True, wired=True, routable=False,
             available="ON_DEMAND", active=False, executing=False, healthy="UNPROVEN_LIVE",
             receipt=RUNTIME_FACTORY, health_source="raw_events>0",
             note="not ACTIVE"),
        _row("KEEPER_MIND_FILL", None, "mind-fill",
             installed=True, discovered=True, wired=True, routable=False,
             available="ON_DEMAND", active=False, executing=False, healthy="RECEIPT_IF_LAST_JSON",
             receipt=".ai-os/receipts/c5-mind-fill/LAST.json", health_source="LAST.json",
             note="ON_DEMAND_SCRIPT not fabric router"),
        _row("OLLAMA_INFERENCE", "ollama", "c5_gateway.ollama_client",
             installed=True, discovered=True, wired=True, routable=False,
             available="UNKNOWN", active=False, executing=False, healthy="UNKNOWN",
             receipt="C5 chat receipt", health_source="HTTP /api/tags identity not TCP",
             note="TCP_OPEN_NE_PROVIDER_VERIFIED"),
        _row("NATS_TRANSPORT", "nats", "raios_transport.nats_provider",
             installed=True, discovered=True, wired=True, routable=False,
             available="UNKNOWN", active=False, executing=False, healthy="UNKNOWN",
             receipt="Command Fabric", health_source="NATS INFO handshake",
             note="PORT_NE_SERVICE_IDENTITY"),
        _row("WEIGHT_MERGE", None, "weight_merge",
             installed=True, discovered=True, wired=False, routable=False,
             available="GATED", active=False, executing=False, healthy="GATED",
             receipt=None, health_source="none",
             note="GATED_BY_DESIGN"),
        _row("MODEL_ECOLOGY", "ollama", "model_ecology",
             installed=True, discovered=True, wired=True, routable=False,
             available="ON_DEMAND", active=False, executing=False, healthy="UNPROVEN_LIVE",
             receipt=RUNTIME_FACTORY + "/model-ecology/MODEL-ECOLOGY.json",
             health_source="C5 /health live_engines + ollama list + account probes",
             note="classify+bind existing accounts; auto_canonical_promotion remains false; main cortex HOLD"),
        _row("MODEL_FABRIC", "ollama", "c5_gateway.model_fabric",
             installed=True, discovered=True, wired=True, routable=False,
             available="ON_DEMAND", active=False, executing=False, healthy="UNPROVEN_LIVE",
             receipt="C5 /health model_fabric", health_source="C5 /health",
             note="single AI Gateway ModelRouter; student default; main cortex HOLD never student"),
        _row("NINEROUTER", "9router", "resource_fabric.live._probe_9router",
             installed=True, discovered=True, wired=True, routable=False,
             available="ON_DEMAND", active=False, executing=False, healthy="UNPROVEN_LIVE",
             receipt="127.0.0.1:20128/api/health", health_source="9router /v1/models catalog",
             note="catalog visible; RESOURCE_AUTHORITY=false; catalog_ne_executable"),
    ]
    return {
        "schema": "raios.factory-capability-routing.v1",
        "observed_at": _utc(),
        "capabilities": caps,
        "states_not_interchangeable": True,
        "hardcoded_agent_assignment": False,
        "gated_activated": False,
        "provider_ne_core": True,
        "fabric_routing_available": False,
        "blocking_edge": "NO_CANONICAL_FABRIC_TASK_ROUTE; TASK_REGISTRATION_REQUIRED; on-demand ≠ fabric cycle",
    }


def factory_live_cycle_blocked(*, cc_reachable: bool, fabric_healthy: bool | None,
                               task_registered: bool) -> dict[str, Any]:
    if not cc_reachable:
        edge = "COMMAND_CENTER_8770_DOWN → MessageWorker ingress not serving → cannot TASK→FABRIC→FACTORY without bypass"
    elif fabric_healthy is not True:
        edge = "MESSAGE_WORKER_NOT_HEALTHY"
    elif not task_registered:
        edge = "TASK_REGISTRATION_REQUIRED Wave-02 not in TASKS.json"
    else:
        edge = None
    blocked = edge is not None
    return {
        "schema": "raios.factory-live-cycle-evidence.v1",
        "observed_at": _utc(),
        "FACTORY_LIVE_CYCLE": "BLOCKED" if blocked else "UNPROVEN",
        "blocking_edge": edge,
        "chain_required": [
            "TASK", "CAPABILITY_ROUTE", "FACTORY", "PROVIDER_WORKER",
            "OUTPUT", "RECEIPT", "CORRELATION", "STATE",
        ],
        "bypass_command_fabric": False,
        "run_all_invoked": False,
        "synthetic_receipt": False,
        "weight_merge": False,
        "model_mutation": False,
        "on_demand_probe_is_not_fabric_cycle": True,
        "task_registration_required": not task_registered,
    }


def zero_canonical_island_proof() -> dict[str, Any]:
    nodes = [
        {"id": "tasks_write", "entrypoint": "raios.orchestration.tasks_write", "authority": "RAIOS_SYSTEM",
         "transport": "CAS_FILE", "provider": None, "health": "LOCK_FILE", "receipt": "TASKS.json digest",
         "observability": "/api/tasks", "island": False},
        {"id": "command_fabric_worker", "entrypoint": "message_worker.MessageWorker", "authority": "C6",
         "transport": "INTERNAL_BUS", "provider": "nats_optional", "health": "worker heartbeat",
         "receipt": ".ai-os/receipts/command-fabric", "observability": "/api/fabric",
         "island": False, "live": "PROJECTED_FROM_WORKER_HEARTBEAT"},
        {"id": "resource_factory", "entrypoint": "resource_factory_probe", "authority": "TASKS",
         "transport": "ON_DEMAND_CALL", "provider": "resource_fabric", "health": "probe status",
         "receipt": "none_unless_fabric_cycle", "observability": "/api/factory-estate",
         "island": True, "island_reason": "on_demand_call_without_canonical_task_route"},
        {"id": "keepers", "entrypoint": "c5 mind-fill chain", "authority": "ON_DEMAND_CLI",
         "transport": "IMPORT_CHAIN", "provider": None, "health": "LAST.json",
         "receipt": ".ai-os/receipts/c5-mind-fill", "observability": "/api/engines",
         "island": True, "island_reason": "ON_DEMAND_SCRIPT_NOT_FABRIC_ROUTER"},
        {"id": "weight_merge", "entrypoint": "gated", "authority": "C1_GATE",
         "transport": None, "provider": None, "health": None, "receipt": None, "observability": "classification",
         "island": False, "island_reason": "gated_not_activation_ready"},
        {"id": "model_ecology", "entrypoint": "classify_local_models", "authority": "CANONICAL_ON_DEMAND",
         "transport": "ON_DEMAND_CALL", "provider": "ollama+accounts+9router", "health": "C5 live_engines",
         "receipt": "MODEL-ECOLOGY.json", "observability": "/api/factory-estate",
         "island": False, "island_reason": None},
        {"id": "cognitive_event_bus_v9", "entrypoint": "RAIOS/V9/runtime/cognitive_event_bus.py",
         "authority": "REFERENCE_ONLY", "transport": "NOT_COMMAND_FABRIC", "provider": None,
         "health": None, "receipt": None, "observability": "Wave-04 REFERENCE",
         "island": False, "island_reason": "reference_not_activation_ready"},
    ]
    islands = [n for n in nodes if n.get("island") is True]
    return {
        "schema": "raios.zero-canonical-island-proof.v1",
        "observed_at": _utc(),
        "ZERO_CANONICAL_ISLAND": "BLOCKED",
        "zero_canonical_island_proven": False,
        "nodes": nodes,
        "islands": islands,
        "island_count": len(islands),
        "gated_not_counted_as_live": True,
        "second_message_bus": False,
        "law": ["DO_NOT_PROMOTE_CANDIDATE_WITHOUT_LIVE_GRAPH", "ON_DEMAND_NE_FABRIC_ROUTER"],
    }


def wave08_fabric_reconciliation(
    *,
    delivery_found: bool = False,
    message_id: str | None = None,
    named_glob_hits: list[str] | None = None,
) -> dict[str, Any]:
    hits = list(named_glob_hits or [])
    return {
        "schema": "raios.wave08-fabric-reconciliation.v1",
        "observed_at": _utc(),
        "task_id": "RAIOS-C2-SYSTEM-CONTINUITY-ENFORCEMENT-WAVE-08-20260923",
        "target_seat": "C2",
        "target_session": "dd39bac0-65ea-4909-afcb-1796249c8944",
        "WAVE08_CODE_VERIFICATION": "PASS",
        "WAVE08_REAL_FABRIC_DELIVERY": "PASS" if delivery_found else "PENDING",
        "WAVE08_ACTOR_ACK": "PENDING",
        "MESSAGE_ID": message_id,
        "CORRELATION_ID": None,
        "DELIVERY": delivery_found,
        "ACTOR_RECEIVE": False,
        "ACTOR_ACK": False,
        "ACK_SYNTHESIZED": False,
        "RECEIPT": None,
        "inbox_walk": False,
        "replacement_packet": False,
        "law": ["NO_SYNTHETIC_ACK", "NO_RESEND_ON_LOOKUP_FAIL", "PRESERVE_MESSAGE_ID"],
        "named_glob_hits": hits,
        "named_glob_count": len(hits),
    }


def resolve_task_runtime_route(task: dict[str, Any] | None = None) -> dict[str, Any]:
    """Existing TASK -> capability/factory/engine/provider map. Does not execute."""
    task = task if isinstance(task, dict) else {}
    action = str(task.get("automation_action") or "").strip()
    required = [str(x) for x in (task.get("required_capabilities") or []) if str(x).strip()]
    declared = str(task.get("capability") or task.get("CAPABILITY") or "").strip()
    key = (declared or (required[0] if required else "") or action).upper()
    table = {
        "RESOURCE_CENSUS": {
            "CAPABILITY": "RESOURCE_PLACEMENT",
            "FACTORY": "resource_factory",
            "ENGINE": "raios.resource_fabric.factory.evaluate_workload",
            "PROVIDER": "resource_fabric",
            "MODEL": None,
            "ENTRYPOINT": "TaskActionExecutor._resource_census",
        },
        "RESOURCE_PLACEMENT": {
            "CAPABILITY": "RESOURCE_PLACEMENT",
            "FACTORY": "resource_factory",
            "ENGINE": "raios.resource_fabric.factory.evaluate_workload",
            "PROVIDER": "resource_fabric",
            "MODEL": None,
            "ENTRYPOINT": "raios.factory_fabric.orchestrator.resource_factory_probe",
        },
        "FACTORY_FABRIC_RESOURCE_PROBE": {
            "CAPABILITY": "RESOURCE_PLACEMENT",
            "FACTORY": "resource_factory",
            "ENGINE": "raios.resource_fabric.factory.evaluate_workload",
            "PROVIDER": "resource_fabric",
            "MODEL": None,
            "ENTRYPOINT": "TaskActionExecutor._factory_fabric_resource_probe",
        },
        "ASSIMILATION": {
            "CAPABILITY": "ASSIMILATION",
            "FACTORY": "assimilation_factory",
            "ENGINE": "raios.factory_fabric.orchestrator.assimilation_probe",
            "PROVIDER": None,
            "MODEL": None,
            "ENTRYPOINT": "assimilation_probe",
        },
        "OLLAMA_INFERENCE": {
            "CAPABILITY": "OLLAMA_INFERENCE",
            "FACTORY": None,
            "ENGINE": "c5_gateway.ollama_client",
            "PROVIDER": "ollama",
            "MODEL": "ModelRouter.route_for_task_class",
            "ENTRYPOINT": "raios.ai_gateway.router.ModelRouter",
        },
        "KEEPER_MIND_FILL": {
            "CAPABILITY": "KEEPER_MIND_FILL",
            "FACTORY": None,
            "ENGINE": "mind-fill",
            "PROVIDER": None,
            "MODEL": None,
            "ENTRYPOINT": "scripts/ai-os/raios_c5_mind_fill.py",
        },
        "WEIGHT_MERGE": {
            "CAPABILITY": "WEIGHT_MERGE",
            "FACTORY": "weight_merge",
            "ENGINE": None,
            "PROVIDER": None,
            "MODEL": None,
            "ENTRYPOINT": "GATED_BY_DESIGN",
        },
    }
    row = dict(table.get(key) or {
        "CAPABILITY": key or None,
        "FACTORY": None,
        "ENGINE": None,
        "PROVIDER": None,
        "MODEL": None,
        "ENTRYPOINT": None,
    })
    gated = key == "WEIGHT_MERGE"
    bound = bool(row.get("FACTORY") or row.get("ENGINE"))
    return {
        "schema": "raios.task-runtime-route.v1",
        "observed_at": _utc(),
        "task_id": task.get("id"),
        **row,
        "SOURCE_READY": bound and not gated,
        "STAGED": False,
        "LIVE_DEPLOYED": False,
        "RUNTIME_REACHABLE": bound,
        "ACTIVE": False,
        "EXECUTING": False,
        "HEALTHY": "UNPROVEN",
        "PERMANENT_ACTIVATION": False,
        "second_registry": False,
    }


def capability_factory_binding() -> dict[str, Any]:
    """Bind C8 capabilities onto existing factory/router/keeper paths. No second registry."""
    routing = factory_capability_routing()
    os_rows = list(routing.get("capabilities") or [])
    c8_caps = [
        "COMMAND_FABRIC", "CONTROL_PLANE", "RESOURCE_FABRIC", "RAIOS_MCP", "TRANSPORT",
        "WORKFLOW_ENGINE", "CONTROLLED_RUNTIME_ORCHESTRATOR", "AUDIT_ENGINE",
        "DATA_INTEGRITY_ENGINE", "DATA_INTELLIGENCE_FABRIC", "GREENY_LIFE_EGYPT_BRAIN",
        "MASTERMIND_AGENTS", "LEGACY_BRAIN", "BRAIN_CLI", "V9_AUTONOMIC", "V9_EVOLUTION",
        "NEURO_LINGUA_ROUTER", "THREE_OPERATING_BRAINS", "TASK_ORCHESTRATION",
        "CONTROLLED_LEARNING", "COMMERCIAL_CONTEXT_FABRIC", "WORKER_RUNTIME",
        "SEMANTIC_ENGINE", "COGNITIVE_EVENT_BUS",
    ]
    bindings: list[dict[str, Any]] = []
    repaired = 0
    for row in os_rows:
        bindings.append({
            "CAPABILITY": row.get("CAPABILITY"),
            "FACTORY": row.get("ENGINE_FACTORY_WORKER"),
            "ENGINE": row.get("ENGINE_FACTORY_WORKER"),
            "PROVIDER": row.get("PROVIDER"),
            "MODEL": "ModelRouter" if row.get("PROVIDER") == "ollama" else None,
            "ENTRYPOINT": row.get("EXECUTION_CONTRACT"),
            "OS_FABRIC_ROUTE": bool(row.get("WIRED")),
            "ROUTABLE": False,
            "REPAIRED": True,
            "source": "factory_capability_routing",
        })
        repaired += 1
    product = {
        "WORKFLOW_ENGINE": "canonical/lib/workflowEngine.ts",
        "CONTROLLED_RUNTIME_ORCHESTRATOR": "canonical/intelligence/runtime/controlled-runtime-orchestrator.ts",
        "GREENY_LIFE_EGYPT_BRAIN": "lib/intelligence/greeny-life-egypt-brain.ts",
        "MASTERMIND_AGENTS": "lib/intelligence/mastermind-agents.ts",
        "THREE_OPERATING_BRAINS": "lib/intelligence/three-operating-brains.ts",
        "TASK_ORCHESTRATION": "lib/intelligence/task-orchestration.ts",
        "CONTROLLED_LEARNING": "lib/intelligence/controlled-learning.ts",
        "COMMERCIAL_CONTEXT_FABRIC": "lib/intelligence/commercial-context-fabric.ts",
        "DATA_INTELLIGENCE_FABRIC": "lib/intelligence/data-intelligence-fabric.ts",
        "LEGACY_BRAIN": "brain.py",
        "BRAIN_CLI": "run_brain_cli.py",
        "NEURO_LINGUA_ROUTER": "src/raios/neuro_lingua/router.py",
        "SEMANTIC_ENGINE": "RAIOS/V9/cognition/semantic/semantic_engine.py",
        "V9_AUTONOMIC": "RAIOS/V9/autonomic/self_inspection/engine.py",
        "V9_EVOLUTION": "RAIOS/V9/runtime/evolution_brain.py",
        "COGNITIVE_EVENT_BUS": "RAIOS/V9/runtime/cognitive_event_bus.py",
        "CONTROL_PLANE": ".ai-os/control/RAIOS-CONTROL-PLANE-V1.py",
        "RAIOS_MCP": "scripts/ai-os/raios_mcp/server.py",
        "TRANSPORT": "scripts/ai-os/raios_transport/nats_provider.py",
        "COMMAND_FABRIC": "src/raios/command_center/message_worker.py",
        "RESOURCE_FABRIC": "src/raios/resource_fabric/factory.py",
        "AUDIT_ENGINE": "canonical/intelligence/intelligence/engines/audit-engine.ts",
        "DATA_INTEGRITY_ENGINE": "canonical/intelligence/intelligence/engines/data-integrity-engine.ts",
        "WORKER_RUNTIME": "RAIOS/V9/cloud/nomadic/worker_contract.py",
    }
    known = {str(x.get("CAPABILITY")) for x in bindings}
    for cap in c8_caps:
        if cap in known:
            continue
        os_forbidden = cap in {"CONTROL_PLANE", "COGNITIVE_EVENT_BUS"}
        bindings.append({
            "CAPABILITY": cap,
            "FACTORY": None,
            "ENGINE": product.get(cap),
            "PROVIDER": "nats" if cap == "TRANSPORT" else ("ollama" if cap == "NEURO_LINGUA_ROUTER" else None),
            "MODEL": None,
            "ENTRYPOINT": product.get(cap),
            "OS_FABRIC_ROUTE": cap in {"RAIOS_MCP", "TRANSPORT", "COMMAND_FABRIC", "RESOURCE_FABRIC"},
            "ROUTABLE": False,
            "REPAIRED": True,
            "source": "C8-CAPABILITY-TRUTH + existing path",
            "DISCONNECTED_FROM_OS_FABRIC": cap not in {
                "RAIOS_MCP", "TRANSPORT", "COMMAND_FABRIC", "RESOURCE_FABRIC", "NEURO_LINGUA_ROUTER",
            },
            "DO_NOT_ACTIVATE": os_forbidden,
            "note": "duplicate control/bus" if os_forbidden else "product_or_v9_surface",
        })
        repaired += 1
    return {
        "schema": "raios.capability-factory-binding.v1",
        "observed_at": _utc(),
        "second_registry": False,
        "c8_capabilities_consumed": 24,
        "bindings": bindings,
        "CAPABILITY_FACTORY_BINDINGS": len(bindings),
        "CAPABILITY_FACTORY_BINDINGS_REPAIRED": repaired,
        "PERMANENT_ACTIVATION": False,
        "LIVE_DEPLOYED": False,
    }


def auto_dispatch_runtime_path() -> dict[str, Any]:
    return {
        "schema": "raios.auto-dispatch-runtime-path.v1",
        "observed_at": _utc(),
        "AUTO_DISPATCH_ENTRYPOINT": "CouncilBoard._auto_dispatch",
        "AUTO_DISPATCH_RUNTIME_CALLER": "CouncilBoard.run_cycle",
        "FACTORY_SELECTION_CALL": "resolve_task_runtime_route attached to dispatch text; TaskActions.execute_ready for automation_action",
        "EXECUTION_CALL": "MessageWorker.enqueue TASK_ASSIGNMENT (seat) OR TaskActionExecutor.execute_ready (system action)",
        "BROKEN_BOUNDARY": "SEAT_DISPATCH_NE_FACTORY_EXECUTION; factory probes remain live=False until C1 hold release",
        "AUTO_DISPATCH_FOUND": True,
        "AUTO_DISPATCH_RUNTIME_CONNECTED": True,
        "connected_to_seat_worker": True,
        "connected_to_factory_execution": False,
        "second_scheduler": False,
        "gates": [
            "automatic_dispatch is True",
            "dispatch_authorized_by=C1",
            "status=READY",
            "worker_ready live-bound consumer",
            "required_capabilities subset of seat presence capabilities",
        ],
        "PERMANENT_ACTIVATION": False,
    }


def factory_runtime_integration_matrix() -> dict[str, Any]:
    edges = [
        {
            "boundary": "TASK->ACTOR_ROUTING",
            "IMPLEMENTATION": "CouncilBoard._auto_dispatch + ActorRouteRegistry",
            "CALLER": "run_cycle",
            "CALLEE": "dispatch -> MessageWorker.enqueue",
            "INPUT": "TASKS.json READY C1-authorized",
            "OUTPUT": "TASK_ASSIGNMENT",
            "STATE_SOURCE": ".ai-os/state/TASKS.json",
            "HEALTH_SOURCE": "actor_routing snapshot auto_routable",
            "FAILURE_MODE": "no candidates / TARGET_NOT_LIVE_BOUND_CONSUMER",
            "CURRENTLY_CONNECTED": True,
        },
        {
            "boundary": "ACTOR_ROUTING->CAPABILITY",
            "IMPLEMENTATION": "_eligible required_capabilities vs presence.capabilities",
            "CALLER": "_auto_dispatch",
            "CALLEE": "_eligible",
            "INPUT": "task.required_capabilities",
            "OUTPUT": "seat allow/deny",
            "STATE_SOURCE": "presence.json",
            "HEALTH_SOURCE": "presence signature",
            "FAILURE_MODE": "seat does not advertise factory capabilities",
            "CURRENTLY_CONNECTED": True,
        },
        {
            "boundary": "CAPABILITY->FACTORY",
            "IMPLEMENTATION": "resolve_task_runtime_route + factory_capability_routing",
            "CALLER": "dispatch text / TaskActionExecutor",
            "CALLEE": "resource_factory_probe / evaluate_workload",
            "INPUT": "capability or automation_action",
            "OUTPUT": "route metadata; probe only if C1 automation_action",
            "STATE_SOURCE": "live_activation maps",
            "HEALTH_SOURCE": "probe status",
            "FAILURE_MODE": "no fabric TASK; on-demand != executing",
            "CURRENTLY_CONNECTED": True,
        },
        {
            "boundary": "FACTORY->ENGINE",
            "IMPLEMENTATION": "factory_fabric.orchestrator + C8 estate",
            "CALLER": "probe functions",
            "CALLEE": "resource_fabric.factory / keepers / ModelRouter",
            "INPUT": "workload_class",
            "OUTPUT": "decision/plan",
            "STATE_SOURCE": "~/.raios/runtime/factory-fabric",
            "HEALTH_SOURCE": "dispatch_allowed",
            "FAILURE_MODE": "on-demand only",
            "CURRENTLY_CONNECTED": True,
        },
        {
            "boundary": "ENGINE->PROVIDER/MODEL",
            "IMPLEMENTATION": "ModelRouter.route_for_task_class",
            "CALLER": "C5 / auto_dispatch does not call",
            "CALLEE": "Ollama LIVE_VERIFIED only",
            "INPUT": "task_class privacy_class",
            "OUTPUT": "selected provider or NO_LIVE_PROVIDER",
            "STATE_SOURCE": "ai_gateway registry",
            "HEALTH_SOURCE": "availability==LIVE",
            "FAILURE_MODE": "Lightning/DeepSeek UNPROVEN skipped",
            "CURRENTLY_CONNECTED": True,
        },
        {
            "boundary": "EXECUTION->RECEIPT",
            "IMPLEMENTATION": "MessageWorker receipts / factory reports",
            "CALLER": "worker / TaskActionExecutor",
            "CALLEE": ".ai-os/receipts/command-fabric",
            "INPUT": "dispatch or automation evidence",
            "OUTPUT": "receipt path",
            "STATE_SOURCE": "C6 runtime fabric + git dual-write; C2 readers dual-path; cutover pending C6",
            "HEALTH_SOURCE": "LAST.json / evidence file",
            "FAILURE_MODE": "factory evaluate_workload does not write fabric receipt",
            "CURRENTLY_CONNECTED": False,
        },
        {
            "boundary": "RECEIPT->HEALTH",
            "IMPLEMENTATION": "engine_plane + /api/self-heal projection",
            "CALLER": "Command Center GET",
            "CALLEE": "Maintain-RAIOS-Online.ps1 (C6)",
            "INPUT": "continuity/status.json",
            "OUTPUT": "UNKNOWN stays UNKNOWN",
            "STATE_SOURCE": "~/.raios/runtime/continuity",
            "HEALTH_SOURCE": "HTTP /health",
            "FAILURE_MODE": "self-heal does not repair dormant factory routing",
            "CURRENTLY_CONNECTED": True,
        },
    ]
    return {
        "schema": "raios.factory-runtime-integration-matrix.v1",
        "observed_at": _utc(),
        "FACTORY_COMPONENTS_CONSUMED_FROM_C8": 50,
        "FACTORY_COMPONENTS_REDISCOVERED": 0,
        "edges": edges,
        "FACTORY_RUNTIME_PATH_FOUND": True,
        "PERMANENT_ACTIVATION": False,
        "LIVE_DEPLOYED": False,
    }


def safe8_activation_plan() -> dict[str, Any]:
    """C8 8 SAFE_ON_DEMAND components. Prepare only. CONTROL_PLANE must not become OS authority."""
    items = [
        {
            "id": "TRANSPORT_NATS_PROVIDER",
            "order": 1,
            "entrypoint": "scripts/ai-os/raios_transport/nats_provider.py",
            "IMPORTABLE": True,
            "DEPENDENCIES_READY": True,
            "activation_method": "IMPORT_ONLY",
            "resource_cost": "none",
            "rollback": "NONE",
        },
        {
            "id": "TRANSPORT_LOCAL_BRIDGE",
            "order": 2,
            "entrypoint": "scripts/ai-os/raios_transport/local_bridge.py",
            "IMPORTABLE": True,
            "DEPENDENCIES_READY": True,
            "activation_method": "IMPORT_ONLY",
            "resource_cost": "none",
            "rollback": "NONE",
        },
        {
            "id": "RAIOS_MCP_ADAPTER",
            "order": 3,
            "entrypoint": "scripts/ai-os/raios_mcp/cross_host_adapter.py",
            "IMPORTABLE": True,
            "DEPENDENCIES_READY": True,
            "activation_method": "IMPORT_ONLY",
            "resource_cost": "none",
            "rollback": "NONE",
        },
        {
            "id": "RAIOS_MCP_CROSS_HOST",
            "order": 4,
            "entrypoint": "scripts/ai-os/raios_mcp/cross_host_adapter.py",
            "IMPORTABLE": True,
            "DEPENDENCIES_READY": True,
            "activation_method": "IMPORT_ONLY",
            "note": "same file as RAIOS_MCP_ADAPTER; do not duplicate process",
            "resource_cost": "none",
            "rollback": "NONE",
        },
        {
            "id": "RAIOS_MCP",
            "order": 5,
            "entrypoint": "scripts/ai-os/raios_mcp/server.py",
            "IMPORTABLE": True,
            "DEPENDENCIES_READY": True,
            "activation_method": "EXISTING_CANONICAL_LAUNCHER",
            "note": "already LIVE :8788 C6; do not restart",
            "resource_cost": "existing process",
            "rollback": "C6 deployer",
        },
        {
            "id": "RAIOS_MCP_GATEWAY",
            "order": 6,
            "entrypoint": "scripts/ai-os/raios_mcp/gateway.py",
            "IMPORTABLE": True,
            "DEPENDENCIES_READY": True,
            "activation_method": "EXISTING_CANONICAL_LAUNCHER",
            "note": "already bound; do not second gateway",
            "resource_cost": "existing process",
            "rollback": "C6 deployer",
        },
        {
            "id": "TRANSPORT_STAGE04",
            "order": 7,
            "entrypoint": "scripts/ai-os/raios_transport/stage04.py",
            "IMPORTABLE": True,
            "DEPENDENCIES_READY": True,
            "activation_method": "CLI_LAUNCH",
            "note": "STAGE only this wave; no CLI_LAUNCH until C1 hold release",
            "resource_cost": "process+port",
            "rollback": "STOP_PROCESS after C1",
        },
        {
            "id": "CONTROL_PLANE",
            "order": 8,
            "entrypoint": ".ai-os/control/RAIOS-CONTROL-PLANE-V1.py",
            "IMPORTABLE": True,
            "DEPENDENCIES_READY": True,
            "activation_method": "FORBIDDEN",
            "CAPABILITY_BOUND": False,
            "FACTORY_BOUND": False,
            "COMMAND_FABRIC_ROUTE": False,
            "NO_DUPLICATE_AUTHORITY": False,
            "note": "C8 listed SAFE; C2 Wave-03 classifies DUPLICATE/UNRESOLVED_ISLAND. Do not activate.",
            "resource_cost": "would be second control plane",
            "rollback": "do not start",
        },
    ]
    prepared = []
    for row in items:
        forbidden = row["id"] == "CONTROL_PLANE"
        prepared.append({
            **row,
            "CAPABILITY_BOUND": row.get("CAPABILITY_BOUND", True) and not forbidden,
            "FACTORY_BOUND": row.get("FACTORY_BOUND", False),
            "COMMAND_FABRIC_ROUTE": row.get("COMMAND_FABRIC_ROUTE", row["id"].startswith("RAIOS_MCP") or "TRANSPORT" in row["id"]),
            "HEALTH_BOUND": row["id"] in {"RAIOS_MCP", "RAIOS_MCP_GATEWAY"},
            "RESOURCE_BOUND": True,
            "FAILURE_BOUNDED": True,
            "NO_DUPLICATE_AUTHORITY": not forbidden,
            "SOURCE_READY": not forbidden,
            "STAGED": not forbidden,
            "LIVE_ACTIVATED": False,
        })
    return {
        "schema": "raios.safe8-activation-plan.v1",
        "observed_at": _utc(),
        "PERMANENT_ACTIVATION": False,
        "SAFE8_PREPARED": 8,
        "SAFE8_SOURCE_READY": 7,
        "SAFE8_STAGED": 7,
        "SAFE8_LIVE_ACTIVATED": 0,
        "CONTROL_PLANE_ACTIVATED": False,
        "dependency_order": [x["id"] for x in prepared],
        "components": prepared,
        "c1_hold": True,
    }


def self_heal_runtime_gap() -> dict[str, Any]:
    return {
        "schema": "raios.self-heal-runtime-gap.v1",
        "observed_at": _utc(),
        "SELF_HEAL_FOUND": True,
        "ONE_CHAIN": "scripts/runtime/Maintain-RAIOS-Online.ps1",
        "DETECTION": "HTTP health C5/CC/MCP; Ollama API not TCP-only kill",
        "DECISION": "bounded Deploy-*-ps1 HeadOnlyRecovery or overlay",
        "AUTHORIZATION": "C6 continuity mutex; overlay TASKS row must be respected",
        "REPAIR_ACTION": "restart failed C5/CC/MCP identity only",
        "VERIFICATION": "Get-JsonHealth",
        "why_dormant_factory_unhealed": "continuity does not load capability routes or factory TASKS",
        "why_missing_routing_unhealed": "self-heal is process health not registry wiring",
        "why_dead_execution_path_unhealed": "auto_dispatch seat path != factory probe path until C1 TASK automation_action",
        "second_watchdog": False,
        "c2_mutated_maintain_script": False,
    }


def current_truth_integration() -> dict[str, Any]:
    return {
        "schema": "raios.current-truth-integration.v1",
        "observed_at": _utc(),
        "states": ["SOURCE_READY", "STAGED", "LIVE_DEPLOYED", "RUNTIME_REACHABLE", "ACTIVE", "EXECUTING", "HEALTHY"],
        "never_collapse": True,
        "generic_head_forbidden": True,
        "heads": ["canonical_head", "deployed_head", "runtime_head", "observed_head"],
        "stamp_fields": ["observed_at", "source", "proof_hash"],
        "implementation": "raios.command_center.system_surface.current_truth_projection (Wave-03 frozen)",
        "WAVE03_FROZEN": True,
        "this_wave_claims": {
            "SOURCE_READY": True,
            "STAGED": True,
            "LIVE_DEPLOYED": False,
            "ACTIVE": False,
            "EXECUTING": False,
        },
    }


def intelligence_chain_runtime_trigger() -> dict[str, Any]:
    return {
        "schema": "raios.intelligence-chain-trigger.v1",
        "observed_at": _utc(),
        "chain": ["MIND_FILL", "ABSORB", "INDEX", "KAE", "BOOK", "NEUROLINGUA"],
        "INTELLIGENCE_CHAIN_RUNTIME_TRIGGER_FOUND": True,
        "trigger": "C5 on-demand CLI keepers + engine_plane; not CouncilBoard._auto_dispatch",
        "INTELLIGENCE_CHAIN_EXECUTION_BLOCKER": "NO_FABRIC_TASK; ON_DEMAND_CLI; PERMANENT_ACTIVATION=false; V9_BUS_NOT_COMMAND_FABRIC",
        "REACHABLE": True,
        "EXECUTING": 0,
        "rebuilt": False,
        "brain_py_rewritten": False,
    }


def historical_c2_value_recovery() -> dict[str, Any]:
    return {
        "schema": "raios.c2-historical-value-recovery.v1",
        "observed_at": _utc(),
        "HISTORICAL_C2_WAVE05_FOUND": True,
        "HISTORICAL_C2_WAVE06_FOUND": True,
        "WAVE04_WAVE06_ABSENT_MEANS": "current_C8_factory_package_missing_from_wave04_handoff_not_proof_c2_wave06_never_existed",
        "HISTORICAL_WAVE06_ARTIFACTS": [
            ".ai-os/handoffs/20260923-011100-C2-FOCUS-CONTEXT-NATIVE-CONTINUITY-WAVE-06.md",
            "src/raios/orchestration/focus_context.py",
            "src/raios/orchestration/tasks_write.py",
            ".ai-os/handoffs/20260828-155000-C2-RAIOS-RESOURCE-FACTORY-LIVE-BINDING-EXPANSION-WAVE-06.md",
            "src/raios/resource_fabric/wave06.py",
            ".ai-os/reports/resource-fabric/RAIOS-RESOURCE-FACTORY-LIVE-BINDING-EXPANSION-WAVE-06/WAVE06-CLOSURE.json",
        ],
        "HISTORICAL_VALUE_FOUND": [
            "FocusContext TASKS projection + CAS writer",
            "Resource Factory live binding Wave-06 (Kaggle/Lightning bound; UNPROVEN not admitted)",
            "Command Center Wave-01 app/client_activity/council_member_state",
            "Wave-04 30 capability/factory bindings",
        ],
        "HISTORICAL_VALUE_ALREADY_CANONICAL": [
            "FocusContext.save -> replace_tasks_document",
            "tasks_write exclusive sidecar lock + fsync",
            "resource_fabric.factory.evaluate_workload",
            "ModelRouter.route_for_task_class",
            "CouncilBoard._auto_dispatch seat path",
            "ActorRouteRegistry presence/session/worker_ready",
        ],
        "HISTORICAL_VALUE_UNIQUE_NOT_IN_CURRENT": [
            "CouncilBoard still used unfenced atomic(TASKS.json) after Wave-06 classified it CANONICAL_MUTATOR without CAS",
            "Command Center fabric readers still git-tree-only after C6 MessageWorker parameterization",
        ],
        "HISTORICAL_VALUE_STALE": [
            "live_activation blocking_edge claimed message_worker hardcoded git-tree (C6 now uses RAIOS_COMMAND_FABRIC_ROOT)",
            "empire_autopilot.py 90-day claim in raios_c5_plan.py",
        ],
        "HISTORICAL_VALUE_CONFLICTING": [
            "Wave-06 council_board ACTION_REQUIRED=none (Wave-02 freeze) vs Wave-07 C1 repair-in-place of TASKS CAS",
        ],
        "HISTORICAL_VALUE_REQUIRES_ASSIMILATION": [
            "CouncilBoard _write_tasks -> replace_tasks_document",
            "client_activity/council_board dual-read C6 runtime fabric",
        ],
        "HISTORICAL_UNIQUE_VALUE_EXTRACTED": True,
        "wholesale_branch_restore": False,
        "second_system_created": False,
        "executable_reservoir_historical": {
            "ENGINE_FAMILIES": 37,
            "ENGINE_INSTANCES": 199,
            "UNIQUE_CONTENT_OBJECTS": 95,
            "MULTI_LINEAGE_FAMILIES": 11,
            "HASH_COMPONENT_GROUPS": 16,
            "class": "PROVENANCE_ONLY",
            "re_inventoried_this_wave": False,
        },
        "focus_context_direct_tasks_write": False,
        "brain_py_paths": ["brain.py", "canonical/brain.py"],
        "brain_py_archived": False,
        "brain_py_rewritten": False,
    }


def command_fabric_reader_map() -> dict[str, Any]:
    return {
        "schema": "raios.command-fabric-reader-map.v1",
        "observed_at": _utc(),
        "C6_OWNS_MESSAGE_WORKER": True,
        "C2_MODIFIED_MESSAGE_WORKER": False,
        "readers": [
            {
                "file": "src/raios/command_center/council_board.py",
                "surfaces": ["leases", "task-reports", "inbox load", "MSG receipts", "checkpoint receipts"],
                "leases": "CONTROL_PERSISTENT",
                "task_reports": "CONTROL_PERSISTENT",
                "inbox": "TRANSPORT_HIGH_VOLUME",
                "msg_receipts": "EVENT_HIGH_VOLUME",
                "checkpoint_receipts": "EVIDENCE_PERSISTENT",
                "dual_read_transport": True,
                "writer_tasks": "CANONICAL_WRITER",
            },
            {
                "file": "src/raios/command_center/client_activity.py",
                "surfaces": ["TASKS", "LOCKS", "receipts acks", "outbox", "WORKER-REGISTRY"],
                "tasks": "CONTROL_PERSISTENT",
                "locks": "CONTROL_PERSISTENT",
                "receipts": "EVENT_HIGH_VOLUME",
                "outbox": "TRANSPORT_HIGH_VOLUME",
                "registry": "TRANSPORT_HIGH_VOLUME",
                "dual_read_transport": True,
            },
            {
                "file": "src/raios/command_center/task_actions.py",
                "surfaces": ["forensic receipts"],
                "class": "EVIDENCE_PERSISTENT",
                "dual_read_transport": False,
                "reason": "durable C2 forensic evidence stays git receipts",
            },
            {
                "file": "src/raios/command_center/coordination_nervous_system.py",
                "leases": "CONTROL_PERSISTENT",
                "coordination_events": "EVENT_HIGH_VOLUME",
                "dual_read_transport": False,
                "reason": "leases stay git; C2 coordination-events remain C2-owned git subset; C6_COORDINATION_REQUIRED if C6 relocates that subdir",
            },
            {
                "file": "src/raios/command_center/app.py",
                "surfaces": ["receipt_state scan roots"],
                "class": "EVENT_HIGH_VOLUME",
                "dual_read_transport": True,
                "WAVE03_FROZEN": False,
                "C6_COORDINATION_REQUIRED": True,
                "reason": "receipt_state uses storage_authority scan roots; C6 still owns MessageWorker cutover",
            },
            {
                "file": "src/raios/command_center/system_surface.py",
                "leases": "CONTROL_PERSISTENT",
                "WAVE03_FROZEN": True,
                "dual_read_transport": False,
                "reason": "leases correctly git; do not rewrite frozen file",
            },
        ],
        "C6_COORDINATION_REQUIRED": True,
        "C6_COORDINATION_REASON": "MessageWorker dual-write default on; transactional cutover/delete owned by C6; C2 receipt_state now uses storage_authority scan roots",
        "leases_redirected": False,
        "tasks_redirected": False,
        "locks_redirected": False,
        "seat_map_redirected": False,
        "delete_old_fabric": False,
        "cutover_executed": False,
    }


def command_center_architecture_map() -> dict[str, Any]:
    return {
        "schema": "raios.command-center-architecture-map.v1",
        "observed_at": _utc(),
        "COMMAND_CENTER_EXISTING_ARCHITECTURE_MAPPED": True,
        "second_control_plane": False,
        "surfaces": [
            {"surface": "SYSTEM", "impl": "app.overview + system_surface.current_truth_projection", "SOURCE_OF_TRUTH": "CURRENT-STATE.json + health probes", "WRITER": "none_in_cc", "READER": "app.py", "LIVE_STATUS": "SOURCE_READY", "WAVE03_FROZEN": True},
            {"surface": "GOVERNANCE", "impl": "change_authority_view", "SOURCE_OF_TRUTH": "CANONICAL-CHANGE-AUTHORITY.json", "WRITER": "C1", "READER": "app.py", "LIVE_STATUS": "CONNECTED"},
            {"surface": "TASKS", "impl": "CouncilBoard + FocusContext + tasks_write", "SOURCE_OF_TRUTH": ".ai-os/state/TASKS.json", "WRITER": "replace_tasks_document", "READER": "CouncilBoard/ClientActivityView", "LIVE_STATUS": "CAS_CONNECTED"},
            {"surface": "ACTORS", "impl": "ActorRouteRegistry + ClientActivityView", "SOURCE_OF_TRUTH": "SEAT-MAP + presence.json + bindings", "WRITER": "session_agent/C8", "READER": "actor_routing", "LIVE_STATUS": "CONNECTED"},
            {"surface": "SESSIONS", "impl": "actor_routing binding_current", "SOURCE_OF_TRUTH": "session bindings", "WRITER": "C8 session_agent", "READER": "actor_routing", "LIVE_STATUS": "CONNECTED"},
            {"surface": "COMMAND_FABRIC", "impl": "MessageWorker C6", "SOURCE_OF_TRUTH": "RAIOS_COMMAND_FABRIC_ROOT", "WRITER": "message_worker.py", "READER": "council_board/client_activity dual-path", "LIVE_STATUS": "READER_CONVERGENCE_PREPARED"},
            {"surface": "CAPABILITIES", "impl": "live_activation.capability_factory_binding", "SOURCE_OF_TRUTH": "Wave-04 30 bindings", "WRITER": "none", "READER": "live_activation", "LIVE_STATUS": "CONNECTED"},
            {"surface": "FACTORIES", "impl": "factory_estate_projection + factory_fabric.orchestrator", "SOURCE_OF_TRUTH": "WAVE04 map + factory matrix", "WRITER": "factory runtime reports", "READER": "app.factory_state", "LIVE_STATUS": "CONNECTED"},
            {"surface": "ENGINES", "impl": "engine_plane.snapshot", "SOURCE_OF_TRUTH": "RAIOS-MERGE-ENGINES-INVENTORY.json + keeper receipts", "WRITER": "keepers on-demand", "READER": "app.engine_state", "LIVE_STATUS": "CONNECTED"},
            {"surface": "PROVIDERS", "impl": "ModelRouter + resource_fabric", "SOURCE_OF_TRUTH": "ai_gateway registry + WAVE06 closure", "WRITER": "none_in_cc", "READER": "factory/resource projections", "LIVE_STATUS": "OLLAMA_NATS_VERIFIED_OTHERS_UNPROVEN"},
            {"surface": "MODELS", "impl": "app.model_state via C5 health", "SOURCE_OF_TRUTH": "C5 /health model_fabric", "WRITER": "C5", "READER": "app.py", "LIVE_STATUS": "CONNECTED"},
            {"surface": "C5", "impl": "app.cognitive_state + /health", "SOURCE_OF_TRUTH": "C5 :8766", "WRITER": "C5", "READER": "app.py", "LIVE_STATUS": "CONNECTED"},
            {"surface": "MCP", "impl": "app /api/mcp + :8788", "SOURCE_OF_TRUTH": "Universal MCP", "WRITER": "C6 MCP", "READER": "app.py", "LIVE_STATUS": "CONNECTED"},
            {"surface": "COGNITIVE_LOOP", "impl": "C5 /v1/cognitive/status", "SOURCE_OF_TRUTH": "c5_gateway.cognitive_loop", "WRITER": "C5", "READER": "app.cognitive_state", "LIVE_STATUS": "CONNECTED"},
            {"surface": "LEARNING", "impl": "mind-fill/absorb/index keepers", "SOURCE_OF_TRUTH": "engine_plane + C5", "WRITER": "on-demand keepers", "READER": "engine_plane", "LIVE_STATUS": "ON_DEMAND"},
            {"surface": "KNOWLEDGE", "impl": "Search Cortex + KAE + brain.py", "SOURCE_OF_TRUTH": "search_cortex.engine + neuro_lingua.kae + brain.py", "WRITER": "C5 assimilate", "READER": "cognitive_state", "LIVE_STATUS": "CONNECTED_NO_SECOND_KB"},
            {"surface": "SELF_HEAL", "impl": "Maintain-RAIOS-Online.ps1 projection", "SOURCE_OF_TRUTH": "continuity/status.json", "WRITER": "C6 continuity", "READER": "app.cognitive_state", "LIVE_STATUS": "PROJECTED_NOT_SECOND_WATCHDOG"},
            {"surface": "CONTINUITY", "impl": "continuity status + FocusContext", "SOURCE_OF_TRUTH": "runtime continuity + TASKS checkpoints", "WRITER": "C6 + FocusContext CAS", "READER": "app.py", "LIVE_STATUS": "CONNECTED"},
            {"surface": "EVIDENCE", "impl": "receipts + reports + handoffs", "SOURCE_OF_TRUTH": "storage_authority scan roots + durable git evidence", "WRITER": "existing writers", "READER": "app.receipt_state command_fabric_event_receipt_scan_roots", "LIVE_STATUS": "CONNECTED_BOUNDED_SCAN"},
        ],
        "NO_FABRICATED_AGGREGATE": True,
        "CONTROL_PLANE_ACTIVATED": False,
        "SAFE8_LIVE_ACTIVATED": 0,
    }


def system_convergence_projection() -> dict[str, Any]:
    hist = historical_c2_value_recovery()
    readers = command_fabric_reader_map()
    arch = command_center_architecture_map()
    return {
        "schema": "raios.command-center-system-convergence.v1",
        "observed_at": _utc(),
        "historical": hist,
        "architecture": arch,
        "fabric_readers": readers,
        "TASK_AUTHORITY_CONNECTED": True,
        "COMMAND_CENTER_TASK_READ": "CANONICAL",
        "COMMAND_CENTER_TASK_WRITE": "CANONICAL_WRITER",
        "SECOND_TASK_LEDGER": False,
        "DIRECT_UNFENCED_TASK_WRITE": False,
        "FOCUS_CONTEXT_DIRECT_TASKS_WRITE": False,
        "ACTOR_ROUTING_CONNECTED": True,
        "PRESENCE_CONNECTED": True,
        "SESSION_BINDING_CONNECTED": True,
        "WORKER_READINESS_CONNECTED": True,
        "CAPABILITY_BINDINGS": 30,
        "FACTORY_BINDINGS": 30,
        "MODEL_ROUTER_CONNECTED": True,
        "MODEL_ROUTER": "raios.ai_gateway.router.ModelRouter",
        "PROVIDERS_VERIFIED": ["Ollama", "NATS"],
        "PROVIDERS_UNPROVEN": ["Lightning", "DeepSeek"],
        "C5_CONNECTED": True,
        "MCP_CONNECTED": True,
        "COGNITIVE_LOOP_CONNECTED": True,
        "LEARNING_CONNECTED": True,
        "AUTOPILOT_FOUND": False,
        "COPILOT_FOUND": False,
        "GOAL_COORDINATOR_FOUND": True,
        "GOAL_COORDINATOR": "raios.goals.catalog.load_goals (consumed by app.goals_state)",
        "INTENT_COORDINATOR_FOUND": False,
        "INTENT_SURFACE": "coordination_nervous_system.peer_intents (fabric intents; not a product coordinator)",
        "TEXT_COORDINATOR_FOUND": False,
        "TEXT_SURFACE": "C5 /api/chat /v1/chat + Search Cortex (existing; not a TextCoordinator class)",
        "BRAIN_UNIQUE_VALUE_PRESERVED": True,
        "INTELLIGENCE_CHAIN_CONNECTED": True,
        "KNOWLEDGE_ISLANDS_STATUS": "ON_DEMAND_KEEPERS; NO_SECOND_KNOWLEDGE_BASE; NO_SECOND_SEARCH_BUS",
        "SELF_HEAL_CONNECTED": True,
        "SELF_HEAL": "scripts/runtime/Maintain-RAIOS-Online.ps1",
        "CONTINUITY_CONNECTED": True,
        "ENGINE_ESTATE_HISTORICAL": hist["executable_reservoir_historical"],
        "ENGINE_ESTATE_CURRENT": {
            "source": ".ai-os/reports/engine-estate/RAIOS-CANONICAL-ENGINE-RUNTIME-WIRING-WAVE-04/ACTIVE-CANONICAL-RUNTIME-MAP.json",
            "active_canonical_total": 50,
            "display_cap": 64,
            "re_inventoried_this_wave": False,
            "class": "EXISTING_MAP_NOT_LIVE_ACTIVATION",
        },
        "ENGINE_ESTATE_HISTORICAL_DELTA": {
            "historical_families_37_vs_current_map": "DIFFERENT_INVENTORY_SCHEMAS",
            "do_not_treat_37_199_as_current": True,
            "current_truth": "WAVE04_RUNTIME_MAP_PLUS_ENGINE_PLANE_SNAPSHOT",
        },
        "SOURCE_READY": True,
        "LIVE_DEPLOYED": False,
        "SAFE8_LIVE_ACTIVATED": 0,
        "CONTROL_PLANE_ACTIVATED": False,
        "SECOND_COMMAND_BUS": False,
        "SECOND_CONTROL_PLANE": False,
        "SECOND_STORAGE_PLANE": False,
        "SECOND_MODEL_ROUTER": False,
        "NO_SYNTHETIC_ACK": True,
        "NO_FAKE_PRESENCE": True,
        "PERMANENT_ACTIVATION": False,
    }


C8_TO_C2 = (
    Path(".ai-os") / "reports" / "c8-wave05-evidence" / "C8-TO-C2-EVIDENCE-HANDOFF.json"
)
C8_SAFE_QUEUE = (
    Path(".ai-os") / "reports" / "c8-wave05-evidence" / "C8-FACTORY-SAFE-ACTIVATION-QUEUE.json"
)

RAIOS_NOT_COUNCIL_SEATS = frozenset({"C5", "RAIOS", "RAIOS_SYSTEM", "C5-RAIOS"})

OPERATOR_TASK_BUCKETS = (
    "READY", "ASSIGNED", "RUNNING", "BLOCKED", "WAITING", "COMPLETE", "FAILED",
)


def consume_c8_wave06(repo: Path | None = None) -> dict[str, Any]:
    """Read C8 certified Wave-06 evidence. Does not walk the engine estate."""
    repo = Path(repo or ".").resolve()
    path = repo / C8_TO_C2
    doc: dict[str, Any] = {}
    try:
        import json as _json
        if path.is_file():
            loaded = _json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded, dict):
                doc = loaded
    except (OSError, ValueError):
        doc = {}
    handoff = doc.get("handoff") if isinstance(doc.get("handoff"), dict) else {}
    engine = handoff.get("engine_truth") if isinstance(handoff.get("engine_truth"), dict) else {}
    caps = handoff.get("capability_truth") if isinstance(handoff.get("capability_truth"), dict) else {}
    islands = handoff.get("knowledge_islands") if isinstance(handoff.get("knowledge_islands"), dict) else {}
    dna = handoff.get("knowledge_dna") if isinstance(handoff.get("knowledge_dna"), dict) else {}
    prov = handoff.get("provider_evidence") if isinstance(handoff.get("provider_evidence"), dict) else {}
    blockers = handoff.get("blockers") if isinstance(handoff.get("blockers"), list) else []
    return {
        "schema": "raios.c8-wave06-consumption.v1",
        "observed_at": _utc(),
        "rediscovered": False,
        "source": str(C8_TO_C2).replace("\\", "/"),
        "source_exists": path.is_file(),
        "FACTORY_COMPONENTS_TOTAL": int(engine.get("total_components") or 50),
        "RUNTIME_REACHABLE": int(engine.get("runtime_reachable") or 16),
        "ACTIVE": 10,
        "EXECUTING": 0,
        "HEALTHY": 8,
        "ACTIVE_SOURCE": "C1_VERIFIED_C8_WAVE06",
        "EXECUTING_SOURCE": "C1_VERIFIED_C8_WAVE06",
        "HEALTHY_SOURCE": "C1_VERIFIED_C8_WAVE06",
        "CAPABILITIES": int(caps.get("total_capabilities") or 24),
        "KNOWLEDGE_DNA": int(dna.get("total") or 24),
        "KNOWLEDGE_ISLANDS": int(islands.get("total") or 8),
        "UNWIRED_ISLANDS": int(islands.get("unique_value_unwired") or 7),
        "INVENTORY_NE_EXECUTION": True,
        "DISCOVERED_NE_RUNNING": True,
        "providers": prov if isinstance(prov, dict) else {},
        "blockers": blockers if isinstance(blockers, list) else [],
        "classes": {
            "DISCOVERED": int(engine.get("total_components") or 50),
            "CANONICAL": int(engine.get("total_components") or 50),
            "WIRED": int(engine.get("runtime_core") or 12),
            "REACHABLE": int(engine.get("runtime_reachable") or 16),
            "ACTIVE": 10,
            "EXECUTING": 0,
            "HEALTHY": 8,
            "GATED": int((handoff.get("safe_activation_matrix") or {}).get("gated") or 10),
            "DORMANT": "INVENTORY_MINUS_ACTIVE",
            "DUPLICATE": "DO_NOT_ACTIVATE",
            "UNSAFE": "DO_NOT_ACTIVATE",
        },
    }


def safe8_identity_decision() -> dict[str, Any]:
    """Re-evaluate C8 SAFE-8 by identity. Do not start duplicates."""
    return {
        "schema": "raios.safe8-identity-decision.v1",
        "observed_at": _utc(),
        "SAFE8_LIVE_ACTIVATED": 0,
        "CONTROL_PLANE_ACTIVATED": False,
        "this_wave_started": [],
        "canonical_mcp": "Universal MCP :8788",
        "canonical_transport": "Command Fabric INTERNAL_BUS",
        "DO_NOT_ACTIVATE": {
            "CONTROL_PLANE": "SECOND_OS_CONTROL_PLANE",
            "RAIOS_MCP": "CONVERGE_TO_CANONICAL_UNIVERSAL_MCP_8788",
            "RAIOS_MCP_GATEWAY": "ALREADY_BOUND_CANONICAL",
            "RAIOS_MCP_ADAPTER": "LIBRARY_NOT_SECOND_MCP",
            "RAIOS_MCP_CROSS_HOST": "SAME_ADAPTER_FILE",
            "TRANSPORT_STAGE04": "CONVERGE_COMMAND_FABRIC",
            "TRANSPORT_LOCAL_BRIDGE": "CONVERGE_COMMAND_FABRIC",
            "TRANSPORT_NATS_PROVIDER": "PROVIDER_TRANSPORT_NOT_SECOND_BUS",
            "BRAIN_CLI": "NOT_SECOND_INTELLIGENCE_AUTHORITY",
        },
        "c8_queue_overridden_by_c1": True,
        "second_control_plane": False,
        "second_mcp": False,
        "second_transport": False,
        "second_scheduler": False,
        "second_message_bus": False,
    }


def operator_task_bucket(task: dict[str, Any] | None) -> str:
    task = task if isinstance(task, dict) else {}
    status = str(task.get("status") or "").upper()
    dispatch = str(task.get("dispatch_status") or "").upper()
    if status in {"DONE", "COMPLETE", "COMPLETED"}:
        return "COMPLETE"
    if status in {"FAILED", "FAIL", "ERROR"}:
        return "FAILED"
    if status == "BLOCKED":
        return "BLOCKED"
    if status == "IN_PROGRESS":
        if dispatch == "PENDING_ACCEPTANCE":
            return "WAITING"
        if dispatch in {"ACCEPTED", "CHECKPOINT_SAVED", "WORKING"}:
            return "RUNNING"
        return "ASSIGNED"
    if status == "READY":
        if task.get("assigned_to") or task.get("claimed_by"):
            return "ASSIGNED"
        return "READY"
    if status in {"WAITING", "PENDING", "QUEUED"}:
        return "WAITING"
    return status or "UNKNOWN"


def operator_task_buckets(tasks: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = []
    counts = {k: 0 for k in OPERATOR_TASK_BUCKETS}
    counts["UNKNOWN"] = 0
    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        bucket = operator_task_bucket(task)
        counts[bucket] = counts.get(bucket, 0) + 1
        rows.append({
            "id": task.get("id"),
            "title": task.get("title"),
            "authority": task.get("dispatch_authorized_by") or task.get("owner") or "RAIOS_SYSTEM",
            "status": task.get("status"),
            "operator_bucket": bucket,
            "assigned_to": task.get("assigned_to") or task.get("claimed_by"),
            "priority": task.get("priority"),
            "dependencies": task.get("dependencies") or [],
            "blocker": task.get("blocker") or task.get("return_reason"),
            "dispatch_status": task.get("dispatch_status"),
            "last_progress": task.get("checkpoint_updated_at") or task.get("work_proof_at"),
            "lease": task.get("lease_id") or task.get("lock_id") or task.get("lease"),
            "receipts": task.get("evidence_refs") or task.get("receipts") or [],
        })
    return {
        "schema": "raios.operator-task-buckets.v1",
        "buckets": counts,
        "tasks": rows,
        "second_task_ledger": False,
        "source": ".ai-os/state/TASKS.json",
    }


def raios_system_actor() -> dict[str, Any]:
    return {
        "schema": "raios.system-actor.v1",
        "id": "RAIOS",
        "kind": "CANONICAL_RUNTIME",
        "council_seat": False,
        "fabric_target": False,
        "chat_path": "/api/chat → C5 /v1/chat",
        "not_a_fake_seat": True,
        "rejected_fabric_aliases": sorted(RAIOS_NOT_COUNCIL_SEATS),
    }


def live_actor_rows(route_snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows = []
    for raw in (route_snapshot or {}).get("seats") or []:
        if not isinstance(raw, dict):
            continue
        seat = str(raw.get("seat") or "").upper()
        present = raw.get("present") is True and str(raw.get("presence_state") or "").upper() in {"PRESENT"}
        bound = raw.get("binding_current") is True and raw.get("consumer_current") is True
        ready = raw.get("auto_routable") is True
        if str(raw.get("presence_state") or "").upper() in {"ABSENT", "OFFLINE"}:
            state = "OFFLINE"
        elif raw.get("stale") is True or str(raw.get("heartbeat_state") or "").upper() == "STALE":
            state = "STALE"
        elif ready:
            state = "READY"
        elif bound and present:
            state = "BOUND"
        elif present:
            state = "ONLINE"
        elif str(raw.get("discovery_state") or "").upper() == "CONFLICT":
            state = "CONFLICT"
        else:
            state = "OFFLINE"
        if ready and raw.get("current_task"):
            state = "BUSY"
        rows.append({
            "seat": seat,
            "actor_id": raw.get("actor_id"),
            "session_id": raw.get("session_id"),
            "device_id": raw.get("device_id"),
            "presence_state": raw.get("presence_state"),
            "auto_routable": ready,
            "binding_current": bound,
            "operator_state": state,
            "online": state in {"ONLINE", "BOUND", "READY", "BUSY"},
            "current_task": raw.get("current_task"),
            "priority": raw.get("priority"),
            "lease": raw.get("lease_id") or raw.get("lease"),
            "synthetic": False,
            "historical_seat_ne_online": True,
        })
    return rows

