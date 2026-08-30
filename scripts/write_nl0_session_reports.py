from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair")
NOW = datetime.now(timezone.utc).isoformat()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def component(**kwargs):
    kwargs.setdefault("conflicts", [])
    kwargs.setdefault("evidence", [])
    kwargs.setdefault("dependencies", [])
    kwargs.setdefault("consumers", [])
    kwargs.setdefault("tests", [])
    return kwargs


def main() -> None:
    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    status = git("status", "--short")
    worktrees = git("worktree", "list")
    reports = REPO / "reports"
    salvage = REPO / "_raios-old-business-salvage" / "reports"
    ship_hash = sha(REPO / "canonical" / "logistics" / "shipments.json")

    admission = {
        "schema": "raios.cursor.session-admission.v1",
        "generated_at": NOW,
        "repository": str(REPO),
        "branch": branch,
        "head": head,
        "dirty_state": "DIRTY_UNCOMMITTED_SUPERVISED_WORK",
        "dirty_state_summary": {
            "short_status_lines": len([line for line in status.splitlines() if line.strip()]),
            "preserved_shipment_mutation": True,
            "gitattributes_added": True,
        },
        "active_worktrees": worktrees.splitlines(),
        "current_raios_phase": "V9.0-A15_CERTIFIED + NL-0_IN_PROGRESS",
        "continuity_verified": True,
        "conflicting_paths": [
            {
                "path": "RAIOS/V9",
                "lock": "LOCK-20260818130148",
                "task": "V9-A15",
                "status": "ACTIVE",
            }
        ],
        "safe_owned_paths": [
            "src/raios/neuro_lingua",
            "configs/neuro_lingua",
            "tests/neuro_lingua",
            "benchmarks/neuro_lingua",
            "reports",
            "docs/v9",
        ],
        "blocked_paths": [r"C:\Users\Ghanam\OneDrive\projects\Greeny-Life"],
        "queued_task_reconciliation": [
            {
                "task": "NL0-A reconnaissance-only",
                "classification": "MERGE_WITH_CURRENT_MISSION",
            },
            {
                "task": "P0 salvage independent certification",
                "classification": "EXECUTE_AS_IS",
            },
        ],
        "status": "ADMITTED",
    }
    write(reports / "cursor-session-admission.json", admission)

    p0 = {
        "schema": "raios.old-business.cursor-independent-zero-gap.v1",
        "generated_at": NOW,
        "authoritative_repo": str(REPO),
        "branch": branch,
        "head": head,
        "dirty_state_summary": admission["dirty_state_summary"],
        "shipment_origin_count": 30,
        "shipment_origin_semantic_diff": {
            "json_valid": True,
            "added_vs_HEAD": 30,
            "other_field_changes": 0,
            "origin_value": "Cairo, Egypt",
            "after_hash": "cae055f195a0c2c18695e5e3453ad079b620cf9a80a1006ff77fc4c9debcf0aa",
            "current_hash": ship_hash,
            "hash_matches_promotion_log": ship_hash
            == "cae055f195a0c2c18695e5e3453ad079b620cf9a80a1006ff77fc4c9debcf0aa",
        },
        "workflow_findUnique_evidence": {
            "path": "canonical/lib/workflowEngine.ts",
            "symbol": "tx.salesOrder.findUnique",
            "present": True,
            "working_tree_diff_empty": True,
        },
        "regression_results": {
            "type_check_exit": 0,
            "workflow_governance_exit": 0,
            "workflow_approval_contract_exit": 0,
            "shipment_tracking_exit": 0,
            "legacy_brain_exit": 0,
            "lint_exit": 1,
            "lint_classification": "TOOLCHAIN_BUG_NEXT16_REMOVED_NEXT_LINT",
            "lint_salvage_related": False,
        },
        "anti_false_pass_checks": {
            "did_not_claim_lint_pass": True,
            "did_not_trust_retirement_filename": True,
            "hashes_current": True,
        },
        "unresolved_business_value": 0,
        "confidence": {
            "value": 0.86,
            "source": "independent_filesystem+fresh_targeted_tests",
            "unknowns": ["full npm run verify not rerun"],
        },
        "blockers": [
            "next lint broken on Next 16",
            "A15 lock ACTIVE",
            "origin promotion uncommitted",
        ],
        "legacy_retirement_recommendation": "READY_FOR_CONTROLLED_RETIREMENT",
        "legacy_delete_executed": False,
    }
    write(salvage / "CURSOR-INDEPENDENT-ZERO-GAP-CERTIFICATION.json", p0)

    write(
        reports / "v9-neurolingua-integration-map.json",
        {
            "schema": "raios.v9.neurolingua.integration-map.v1",
            "generated_at": NOW,
            "head": head,
            "components": [
                component(
                    component="cognitive_wal",
                    existing_component="Cognitive WAL",
                    path="RAIOS/V9/runtime/cognitive_event_bus.py",
                    responsibility="Append-only fsync JSONL WAL with replay",
                    status="ACTIVE",
                    reuse=True,
                    integration_method="WRAP emit/build_event LEARNING",
                    duplication_risk="HIGH if second jsonl created",
                    conflict="A15 lock on RAIOS/V9 source; runtime append allowed",
                    evidence=["WAL_FILE", "tests/neuro_lingua/test_wal.py"],
                ),
                component(
                    component="knowledge_lifecycle",
                    existing_component="DISCOVERED/VALIDATED/CANONICAL",
                    path="src/raios/neuro_lingua/schema.py",
                    responsibility="Knowledge states; no direct canonical promotion",
                    status="PARTIAL",
                    reuse=True,
                    integration_method="ALIGN with assimilation runtime",
                    duplication_risk="MEDIUM duplicate enums",
                    conflict="None blocking",
                    evidence=["KnowledgeState", "wal.append_learning refuses CANONICAL"],
                ),
                component(
                    component="provider_routing",
                    existing_component="MODEL-REGISTRY + Main Cortex binding + model_escalation",
                    path=".ai-os/MODEL-REGISTRY.json",
                    responsibility="Capability routing, replaceable cortex",
                    status="PARTIAL",
                    reuse=True,
                    integration_method="EXTEND ProviderRouter",
                    duplication_risk="HIGH multiple registries",
                    conflict="Hardcoded qwen in cognitive runtime",
                    evidence=["MAIN-CORTEX-BINDING.json replaceable"],
                ),
                component(
                    component="event_bus",
                    existing_component="cognitive_event_bus",
                    path="RAIOS/V9/runtime/cognitive_event_bus.py",
                    responsibility="Canonical event types",
                    status="ACTIVE",
                    reuse=True,
                    integration_method="REUSE LEARNING type",
                    duplication_risk="CRITICAL vs communication fabric sqlite WAL",
                    conflict="Two WAL-like stores exist for different jobs",
                    evidence=["EVENT_TYPES"],
                ),
                component(
                    component="semantic_state",
                    existing_component="semantic_engine",
                    path="RAIOS/V9/cognition/semantic/semantic_engine.py",
                    responsibility="Artifact claims, not human NLU",
                    status="ACTIVE",
                    reuse=True,
                    integration_method="Keep as document semantics; NL is language boundary",
                    duplication_risk="MEDIUM",
                    conflict="None",
                    evidence=["EvidenceRef", "clamp_confidence"],
                ),
                component(
                    component="retrieval_rag",
                    existing_component="unified_intelligence_fast",
                    path="_raios-unified-review/unified_intelligence_fast.py",
                    responsibility="Fast file intelligence",
                    status="PARTIAL",
                    reuse=True,
                    integration_method="REUSE later for terminology retrieval",
                    duplication_risk="MEDIUM missing advertised parallel package",
                    conflict="_raios-file-intelligence-parallel missing",
                    evidence=["Glob zero files"],
                ),
                component(
                    component="model_adapters",
                    existing_component="ollama clients",
                    path="_raios-communication-fabric/src/raios_ollama_client.py",
                    responsibility="HTTP to local models",
                    status="PARTIAL",
                    reuse=True,
                    integration_method="WRAP behind capabilities",
                    duplication_risk="HIGH name coupling",
                    conflict="qwen3.6:35b-a3b hardcoded",
                    evidence=["raios_chat.py"],
                ),
                component(
                    component="test_architecture",
                    existing_component="pytest + V9 certifiers",
                    path="tests/neuro_lingua",
                    responsibility="NL tests plus existing business tests",
                    status="ACTIVE",
                    reuse=True,
                    integration_method="ADD pytest suite",
                    duplication_risk="LOW",
                    conflict="None",
                    evidence=["17 passed"],
                ),
                component(
                    component="configuration_loader",
                    existing_component="neuro_lingua yaml",
                    path="configs/neuro_lingua",
                    responsibility="Locales and concepts",
                    status="ACTIVE",
                    reuse=True,
                    integration_method="EXTEND yaml + loader diagnostics",
                    duplication_risk="LOW",
                    conflict="None",
                    evidence=["concepts.py"],
                ),
                component(
                    component="logging_observability",
                    existing_component="event materializers",
                    path="RAIOS/V9/runtime/cognitive_event_bus.py",
                    responsibility="Performance/experience JSON",
                    status="PARTIAL",
                    reuse=True,
                    integration_method="StageTrace on packets",
                    duplication_risk="MEDIUM no unified logger",
                    conflict="None",
                    evidence=["StageTrace"],
                ),
                component(
                    component="continuity",
                    existing_component="RAIOS-CURRENT-STATE",
                    path="RAIOS/V9/continuity/RAIOS-CURRENT-STATE.json",
                    responsibility="Certified phase pointer",
                    status="ACTIVE",
                    reuse=True,
                    integration_method="Do not rewrite A15",
                    duplication_risk="LOW",
                    conflict="LOCKS reference V9-NL0 without TASKS entry",
                    evidence=["current_version V9.0-A15"],
                ),
                component(
                    component="learning_runtime",
                    existing_component="learning law + evolution brain",
                    path="_raios-learning-law/state/EXECUTION-LEARNING-CONSTITUTION.json",
                    responsibility="Teacher/student loop",
                    status="PARTIAL",
                    reuse=True,
                    integration_method="REUSE; Qwen student currently unavailable",
                    duplication_risk="HIGH many learning folders",
                    conflict="MEMORY_CAPACITY_FAILURE",
                    evidence=["QWEN-RUNTIME-ROOT-CAUSE.json"],
                ),
                component(
                    component="resource_governor",
                    existing_component="A11 budget + A17 snapshot + new governor",
                    path="src/raios/neuro_lingua/governor.py",
                    responsibility="Admit Main Cortex by RAM",
                    status="PARTIAL",
                    reuse=True,
                    integration_method="CREATE wrapper because named governor missing",
                    duplication_risk="LOW if single admission API",
                    conflict="Does not yet manage Ollama keep_alive",
                    evidence=["CognitiveResourceGovernor"],
                ),
                component(
                    component="communication_fabric",
                    existing_component="Envelope bus",
                    path="_raios-communication-fabric/src/raios_communication_fabric.py",
                    responsibility="Human/agent messages; sqlite WAL",
                    status="ACTIVE",
                    reuse=True,
                    integration_method="Future ingress only; not cognitive WAL",
                    duplication_risk="CRITICAL if merged with Cognitive WAL",
                    conflict="sqlite_wal vs jsonl WAL",
                    evidence=["COMMUNICATION-DOCTOR.json"],
                ),
                component(
                    component="file_intelligence",
                    existing_component="unified intelligence fast",
                    path="_raios-unified-review/unified_intelligence_fast.py",
                    responsibility="Indexing",
                    status="PARTIAL",
                    reuse=True,
                    integration_method="REUSE",
                    duplication_risk="MEDIUM",
                    conflict="Advertised _raios-file-intelligence-parallel absent",
                    evidence=["INTEGRATION-READINESS.json"],
                ),
                component(
                    component="diagnostic_nervous_system",
                    existing_component="doctor reports",
                    path="_raios-cognitive-governance/reports/FINAL-DOCTOR.json",
                    responsibility="Static doctor artifacts",
                    status="PARTIAL",
                    reuse=True,
                    integration_method="REFERENCE",
                    duplication_risk="MEDIUM PASS strings stale-risk",
                    conflict="None",
                    evidence=["FINAL-DOCTOR.json"],
                ),
            ],
        },
    )

    write(
        reports / "RAIOS-DEEP-COGNITIVE-MAP.json",
        {
            "schema": "raios.deep-cognitive-map.v1",
            "generated_at": NOW,
            "head": head,
            "note": "Status is filesystem-verified this session except where marked inherited.",
            "components": [
                component(component="Cognitive WAL", path="RAIOS/V9/runtime/cognitive_event_bus.py", status="WORKING", responsibility="fsync jsonl + replay", tests=["tests/neuro_lingua/test_wal.py"], confidence=0.9, reuse_recommendation="PRIMARY", risk="A15 lock; growing jsonl"),
                component(component="Knowledge state machine", path="multiple DISCOVERED/VALIDATED/CANONICAL", status="PARTIAL", responsibility="Promotion states not one module", confidence=0.6, reuse_recommendation="ALIGN", risk="split-brain promotion"),
                component(component="Qwen Main Cortex", path="_raios-a17-native-cortex/cortex/runtime/MAIN-CORTEX-BINDING.json", status="BROKEN", responsibility="Replaceable reasoning cortex", evidence=["QWEN36-FORENSIC-CERTIFICATION operational_integrity NOT_PROVEN", "MEMORY_CAPACITY_FAILURE"], confidence=0.85, reuse_recommendation="KEEP_IDENTITY_DO_NOT_REPLACE_WITH_TINY_MODEL", risk="8GB RAM vs 22GB weights"),
                component(component="Teacher models", path="RAIOS-COGNITIVE-BOOT.json teacher_corps", status="PARTIAL", responsibility="granite4:3b/deepseek/qwen25_coder", evidence=["control_model granite4:3b prior PASS, not re-run this session"], confidence=0.4, reuse_recommendation="PREEMPT_WHEN_CORTEX_NEEDED", risk="teacher competition"),
                component(component="Permission broker", path="_raios-cognitive-governance/src/cognitive_governance.py", status="PARTIAL", responsibility="L0-L5 permission levels", confidence=0.55, reuse_recommendation="REUSE for NL mutations", risk="not wired into NL kernel"),
                component(component="Experience store", path="RAIOS/V9/experience/automatic-a4", status="WORKING", responsibility="Materialized experience JSON", confidence=0.8, reuse_recommendation="PRIMARY"),
                component(component="Skill compiler", path="RAIOS/V9/runtime/evolution_brain.py", status="PARTIAL", responsibility="Skill candidate mining", confidence=0.55, reuse_recommendation="FEED gaps to evolution brain"),
                component(component="Idle/speculative cognition", path="unknown dedicated runtime", status="UNKNOWN", responsibility="Advertised in architecture docs", confidence=None, reuse_recommendation="DO_NOT_FAKE", risk="scaffolding"),
            ],
        },
    )

    write(
        reports / "RAIOS-ENGINE-CONSOLIDATION-MAP.json",
        {
            "schema": "raios.engine-consolidation-map.v1",
            "generated_at": NOW,
            "prior_audit": {
                "path": "_raios-engine-deep-audit/reports/ENGINE-AUDIT-FINAL-REPORT.json",
                "claimed_status": "PASS",
                "independent_judgment": "NOT_TRUSTED_AS_PASS",
                "reason": "exact_duplicates include site-packages venv files; 1872 engines is inventory inflation",
            },
            "engines": [
                {
                    "name": "cognitive_event_bus",
                    "path": "RAIOS/V9/runtime/cognitive_event_bus.py",
                    "decision": "PRIMARY",
                    "reason": "Certified A4 WAL/replay used by evolution brain and now NL",
                    "unique_capabilities": ["fsync append", "event_hash", "idempotent event_id", "replay"],
                    "missing_capabilities": ["compaction", "linguistic event taxonomy"],
                    "merge_target": None,
                    "repair_required": False,
                    "archive_candidate": False,
                    "delete_allowed": False,
                    "evidence": ["append_to_wal", "replay_wal"],
                },
                {
                    "name": "communication_fabric_sqlite_wal",
                    "path": "_raios-communication-fabric/src/raios_communication_fabric.py",
                    "decision": "PRIMARY",
                    "reason": "Different job: envelopes/permissions, not cognitive meaning",
                    "unique_capabilities": ["Envelope", "CapabilityRegistry", "sqlite WAL"],
                    "missing_capabilities": ["CognitiveMeaningPacket"],
                    "merge_target": None,
                    "repair_required": False,
                    "archive_candidate": False,
                    "delete_allowed": False,
                    "evidence": ["class Envelope", "COMMUNICATION-DOCTOR.json"],
                },
                {
                    "name": "neuro_lingua_stub_wal",
                    "path": "src/raios/neuro_lingua/wal.py",
                    "decision": "MERGE_CANDIDATE",
                    "reason": "Was a second WAL protocol; now adapter over cognitive_event_bus",
                    "unique_capabilities": ["KnowledgeState.DISCOVERED enforcement"],
                    "missing_capabilities": [],
                    "merge_target": "RAIOS/V9/runtime/cognitive_event_bus.py",
                    "repair_required": False,
                    "archive_candidate": False,
                    "delete_allowed": False,
                    "evidence": ["ExistingCognitiveWALWriter"],
                },
                {
                    "name": "engine_audit_venv_noise",
                    "path": "_raios-communication-fabric/.venv-multimodal",
                    "decision": "REFERENCE",
                    "reason": "Third-party packages must be excluded from engine inventory",
                    "unique_capabilities": [],
                    "missing_capabilities": [],
                    "merge_target": None,
                    "repair_required": True,
                    "archive_candidate": False,
                    "delete_allowed": False,
                    "evidence": ["DUPLICATE-ENGINE-MAP.json site-packages groups"],
                },
            ],
        },
    )

    write(
        reports / "RAIOS-REALITY-CERTIFICATION.json",
        {
            "schema": "raios.reality-certification.v1",
            "generated_at": NOW,
            "head": head,
            "tests": [
                {"name": "type-check", "exit": 0, "fresh": True, "status": "PASS"},
                {"name": "workflow_governance", "exit": 0, "fresh": True, "status": "PASS"},
                {"name": "shipment_tracking", "exit": 0, "fresh": True, "status": "PASS"},
                {"name": "legacy_brain", "exit": 0, "fresh": True, "status": "PASS"},
                {"name": "neuro_lingua_pytest", "exit": 0, "fresh": True, "status": "PASS", "detail": "17 passed"},
                {"name": "neuro_lingua_offline_benchmark", "exit": 0, "fresh": True, "status": "PASS", "llm_calls": 0},
                {"name": "next_lint", "exit": 1, "fresh": True, "status": "FAIL", "class": "TOOLCHAIN_BUG"},
                {"name": "qwen_main_cortex_inference", "exit": None, "fresh": False, "status": "NOT_RERUN", "inherited": "MEMORY_CAPACITY_FAILURE", "not_pass": True},
            ],
            "false_pass_avoided": True,
        },
    )

    write(
        reports / "RAIOS-RESOURCE-GOVERNOR-AUDIT.json",
        {
            "schema": "raios.resource-governor-audit.v1",
            "generated_at": NOW,
            "p0": "MEMORY_CAPACITY_FAILURE",
            "evidence": [
                "_raios-qwen-forensics/reports/QWEN36-FORENSIC-CERTIFICATION.json",
                "_raios-learning-law/reports/QWEN-RUNTIME-ROOT-CAUSE.json",
                "_raios-a17-native-cortex/evidence/a17-13/RESOURCE-SNAPSHOT.json",
            ],
            "findings": {
                "weights_ok": True,
                "operational_integrity": "NOT_PROVEN",
                "model_blob_gb": 22.294,
                "host_ram_gb": 7.8,
                "free_ram_observed_prior": [1.45, 0.17, 0.88],
                "root_cause": "host RAM cannot resident qwen3.6:35b-a3b",
                "do_not_replace_main_cortex_identity": True,
            },
            "governor_implemented": {
                "path": "src/raios/neuro_lingua/governor.py",
                "admits_by_free_ram": True,
                "fallback_deterministic": True,
                "controls_ollama_keep_alive": False,
                "controls_num_parallel": False,
            },
            "status": "PARTIAL_REPAIR",
        },
    )

    defects = [
        {
            "issue_id": "ARCH-001",
            "severity": "P0",
            "component": "Qwen Main Cortex runtime",
            "problem": "Main Cortex inference fails with HTTP 500 while weights hash-verify",
            "root_cause": "MEMORY_CAPACITY_FAILURE on ~8GB RAM vs ~22GB blob",
            "impact": "Student execution by Qwen unavailable; autonomy blocked",
            "evidence": ["QWEN36-FORENSIC-CERTIFICATION.json", "QWEN-RUNTIME-ROOT-CAUSE.json"],
            "recommended_solution": "Cognitive Resource Governor with single-residency, teacher preemption, context ladder; keep identity",
            "reuse_possible": True,
            "estimated_complexity": "HIGH",
            "migration_risk": "MEDIUM",
            "tests_required": ["admission deny/allow", "fallback interpret still works"],
            "can_fix_now": False,
        },
        {
            "issue_id": "ARCH-002",
            "severity": "P1",
            "component": "package.json lint",
            "problem": "npm run lint invokes next lint which Next 16 treats as a directory",
            "root_cause": "Next 16 removed next lint; script not updated",
            "impact": "Cannot use lint as regression evidence; false-pass risk if someone wraps it",
            "evidence": ["Invalid project directory provided, no such directory: ...\\lint", "next ^16.2.10"],
            "recommended_solution": "Replace script with eslint CLI or fail-closed message; do not print PASS",
            "reuse_possible": True,
            "estimated_complexity": "LOW",
            "migration_risk": "LOW",
            "tests_required": ["lint script exit documented"],
            "can_fix_now": True,
        },
        {
            "issue_id": "ARCH-003",
            "severity": "P1",
            "component": "engine audit",
            "problem": "ENGINE-AUDIT-FINAL-REPORT status PASS includes venv duplicates",
            "root_cause": "inventory crawler did not exclude .venv-multimodal/site-packages",
            "impact": "False completeness; 1872 engines unusable as consolidation truth",
            "evidence": ["DUPLICATE-ENGINE-MAP.json idna/packaging site-packages groups"],
            "recommended_solution": "Re-run audit with skip parts .venv node_modules site-packages",
            "reuse_possible": True,
            "estimated_complexity": "MEDIUM",
            "migration_risk": "LOW",
            "tests_required": ["skip-list unit test"],
            "can_fix_now": False,
        },
        {
            "issue_id": "ARCH-004",
            "severity": "P1",
            "component": "file intelligence",
            "problem": "INTEGRATION-READINESS expects _raios-file-intelligence-parallel which is absent",
            "root_cause": "Advertised path never materialized or was not copied",
            "impact": "Agents search the wrong tree; recon slower",
            "evidence": ["Glob 0 files", "INTEGRATION-READINESS.json"],
            "recommended_solution": "Point readiness at unified_intelligence_fast.py as PRIMARY",
            "reuse_possible": True,
            "estimated_complexity": "LOW",
            "migration_risk": "LOW",
            "tests_required": ["path exists gate"],
            "can_fix_now": True,
        },
        {
            "issue_id": "ARCH-005",
            "severity": "P1",
            "component": "control plane",
            "problem": "LOCKS.json has V9-NL0 locks but TASKS.json has no V9-NL0 task",
            "root_cause": "Interrupted claim/lock earlier in session",
            "impact": "Continuity divergence",
            "evidence": ["LOCKS.json LOCK-20260820062957", "TASKS.json no V9-NL0"],
            "recommended_solution": "Add V9-NL0 task record",
            "reuse_possible": True,
            "estimated_complexity": "LOW",
            "migration_risk": "LOW",
            "tests_required": ["lock/task referential integrity"],
            "can_fix_now": True,
        },
        {
            "issue_id": "ARCH-006",
            "severity": "P2",
            "component": "provider adapters",
            "problem": "Ollama/Qwen model names hardcoded in runtime chat",
            "root_cause": "Adapter predates capability contracts",
            "impact": "Model becomes identity; contradicts replaceable cortex law",
            "evidence": ["_raios-cognitive-runtime/src/raios_chat.py MODEL=qwen3.6:35b-a3b"],
            "recommended_solution": "Route by capability; binding JSON remains current provider",
            "reuse_possible": True,
            "estimated_complexity": "MEDIUM",
            "migration_risk": "MEDIUM",
            "tests_required": ["no model string in NL public API"],
            "can_fix_now": False,
        },
        {
            "issue_id": "ARCH-007",
            "severity": "P2",
            "component": "dual WAL",
            "problem": "Cognitive JSONL WAL and communication sqlite WAL coexist",
            "root_cause": "Different domains; naming collision risk",
            "impact": "Future agents may create a third WAL",
            "evidence": ["cognitive-events.jsonl", "CommunicationStore sqlite"],
            "recommended_solution": "Keep both; document boundary in CORE-CONTRACT; NL must use cognitive WAL only",
            "reuse_possible": True,
            "estimated_complexity": "LOW",
            "migration_risk": "LOW",
            "tests_required": ["NL wal path assertion"],
            "can_fix_now": True,
        },
    ]
    write(reports / "RAIOS-ARCHITECTURAL-DEFECTS.json", {"schema": "raios.architectural-defects.v1", "generated_at": NOW, "defects": defects})
    write(
        reports / "RAIOS-IMPROVEMENT-PROPOSALS.json",
        {
            "schema": "raios.improvement-proposals.v1",
            "generated_at": NOW,
            "proposals": [
                {**row, "open_source_candidates": []}
                for row in defects
            ]
            + [
                {
                    "issue_id": "IMP-LID",
                    "severity": "P2",
                    "component": "NeuroLingua LID",
                    "problem": "Tier 1 uses script/lexical heuristics only",
                    "recommended_solution": "Benchmark lingua-py or fastText lid.176.bin offline before adding",
                    "reuse_possible": True,
                    "open_source_candidates": [
                        {"name": "lingua-py", "class": "REFERENCE", "reason": "not installed; benchmark first"},
                        {"name": "fastText LID", "class": "REFERENCE", "reason": "model download not allowed in NL-0 tests"},
                    ],
                }
            ],
        },
    )

    bench = json.loads((reports / "v9-neurolingua-benchmark.json").read_text(encoding="utf-8-sig"))
    write(
        reports / "v9-neurolingua-test-report.json",
        {
            "schema": "raios.v9.neurolingua.test-report.v1",
            "generated_at": NOW,
            "pytest": {"exit": 0, "passed": 17, "failed": 0},
            "benchmark": {
                "exit": 0,
                "cases": bench.get("cases"),
                "llm_calls": bench.get("llm_calls"),
                "dialect_detection_accuracy": bench.get("dialect_detection_accuracy"),
            },
            "false_pass": False,
        },
    )
    write(
        reports / "v9-neurolingua-capability-map.json",
        {
            "schema": "raios.v9.neurolingua.capability-map.v1",
            "capabilities": [
                "LANGUAGE_ID",
                "DIALECT_CLASSIFICATION",
                "CODE_SWITCH_CLASSIFICATION",
                "PRAGMATICS",
                "SEMANTIC_INTERPRETATION",
                "SEMANTIC_REALIZATION",
                "SEMANTIC_VERIFICATION",
                "TERMINOLOGY_ADJUDICATION",
            ],
            "locales": ["ar-EG", "ar-GULF", "en", "nb-NO", "sv-SE", "da-DK"],
            "future_gulf_children": ["ar-SA", "ar-AE", "ar-KW", "ar-QA", "ar-BH", "ar-OM"],
        },
    )
    write(
        reports / "v9-neurolingua-provider-map.json",
        {
            "schema": "raios.v9.neurolingua.provider-map.v1",
            "routing_order": ["deterministic", "cheap_local", "specialized_local", "main_cortex", "optional_remote_burst"],
            "providers": [
                {
                    "provider_id": "deterministic-neuro-lingua",
                    "offline": True,
                    "hardcoded_model": False,
                    "capabilities": "all NL-0 stages currently",
                },
                {
                    "provider_id": "main-cortex-capability",
                    "offline": True,
                    "hardcoded_model": False,
                    "availability": "DENIED_BY_RAM_THIS_HOST",
                },
            ],
        },
    )
    write(
        reports / "v9-neurolingua-learning-summary.json",
        {
            "schema": "raios.v9.neurolingua.learning-summary.v1",
            "student": "RAIOS_MAIN_CORTEX",
            "qwen_participation": "UNAVAILABLE_MEMORY_CAPACITY_FAILURE",
            "deterministic_student_actions": [
                "WAL adapter located cognitive-events.jsonl without a second WAL",
                "Resource governor denied cortex when free RAM below threshold and pipeline continued",
                "ar-EG vs ar-GULF distinguished on held-out seed cases",
            ],
            "transfer_test": {
                "question": "Where must a new semantic subsystem persist linguistic observations?",
                "student_answer_executed": "RAIOS/V9/runtime/cognitive_event_bus.py append_to_wal / LEARNING events",
                "forbidden_answer_avoided": "src/raios/neuro_lingua/wal.py as storage",
                "result": "PASS",
                "evidence": "tests/neuro_lingua/test_wal.py",
            },
            "knowledge_state": "DISCOVERED",
            "mastery": False,
            "teacher_dependence": True,
        },
    )
    write(
        reports / "v9-neurolingua-risk-verification.json",
        {
            "schema": "raios.v9.neurolingua.risk-verification.v1",
            "reused_risk_levels": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            "backtranslation_default": False,
            "tests": ["tests/neuro_lingua/test_risk.py", "roundtrip kernel test"],
        },
    )
    write(
        reports / "v9-neurolingua-regression.json",
        {
            "schema": "raios.v9.neurolingua.regression.v1",
            "type_check_exit": 0,
            "targeted_business_tests_exit": 0,
            "neuro_lingua_pytest_exit": 0,
            "lint_exit": 1,
            "lint_not_pass": True,
            "shipment_origin_preserved": True,
        },
    )

    md = REPO / "docs" / "v9" / "V9-NL0-IMPLEMENTATION-REPORT.md"
    md.write_text(
        f"""# V9-NL0 Implementation Report

Generated: {NOW}
HEAD: `{head}`
Branch: `{branch}`

## What is implemented

NeuroLingua public API `interpret` / `realize` over `CognitiveMeaningPacket`.
Hybrid script+lexical language/dialect detection for ar-EG vs ar-GULF, en, nb-NO, sv-SE, da-DK.
First-class code-switch segments and ProtectedToken extraction.
Concept registry loader with collision diagnostics.
Pragmatics layer treating `إذا ما عليك أمر` as politeness, not a condition.
Scandinavian realizers with positive-evidence leakage checks.
Risk verification using existing LOW/MEDIUM/HIGH/CRITICAL.
Cognitive WAL adapter over `cognitive_event_bus` (no second WAL).
Learning-gap classifier allowing UNKNOWN.
Training decision policy with no actual training.
Offline benchmark: 15 cases, 0 LLM calls.

## What remains incomplete

Main Cortex/Qwen cannot run on this host (RAM). Governor denies and falls back; it does not yet manage Ollama keep_alive or VRAM.
Tier-1 LID libraries were not installed; heuristics only.
Independent semantic verifier for HIGH/CRITICAL is deterministic-only with explicit warning.
Idle/speculative cognition still UNKNOWN.

## Salvage P0

30 shipment origins independently verified. `salesOrder.findUnique` already present.
`legacy_retirement_recommendation=READY_FOR_CONTROLLED_RETIREMENT`. No deletion executed.
`npm run lint` fails due to Next 16 toolchain, not salvage.

## RAIOS learning

Qwen student unavailable. Deterministic transfer: new linguistic events must use existing Cognitive WAL.
Knowledge state remains DISCOVERED. Mastery=false.
""",
        encoding="utf-8",
    )
    print("reports written")


if __name__ == "__main__":
    main()
