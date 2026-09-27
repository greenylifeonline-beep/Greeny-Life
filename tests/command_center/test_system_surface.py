from __future__ import annotations

import json
from pathlib import Path

from raios.command_center.system_surface import (
    capability_routing_projection,
    classify_component,
    current_truth_projection,
    fabric_projection,
    factory_estate_projection,
    incidents_projection,
    integration_mesh_projection,
    operator_laws_projection,
    reachability_projection,
    self_heal_projection,
    storage_class_projection,
    system_topology_projection,
)

WAVE04 = (
    Path(".ai-os") / "reports" / "engine-estate"
    / "RAIOS-CANONICAL-ENGINE-RUNTIME-WIRING-WAVE-04"
    / "ACTIVE-CANONICAL-RUNTIME-MAP.json"
)


def _repo(tmp_path: Path, instances: list[dict]) -> Path:
    path = tmp_path / WAVE04
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "active_canonical_total": len(instances),
        "classification_counts": {"TEST_INFRASTRUCTURE": 1},
        "instances": instances,
    }), encoding="utf-8")
    matrix = (
        tmp_path / ".ai-os" / "reports" / "factory-fabric"
        / "RAIOS-FACTORY-FABRIC-CRITICAL-CLOSURE-C6-01" / "FACTORY-STATUS-MATRIX.json"
    )
    matrix.parent.mkdir(parents=True)
    matrix.write_text(json.dumps({
        "resource_factory": {"status": "PASS"},
        "weight_merge": {"status": "PROVEN_EXISTING"},
    }), encoding="utf-8")
    factory_py = tmp_path / "src" / "raios" / "resource_fabric" / "factory.py"
    factory_py.parent.mkdir(parents=True)
    factory_py.write_text("# resource factory\n", encoding="utf-8")
    return tmp_path


def test_classify_does_not_promote_tests_or_gated_to_services():
    assert classify_component({
        "family_id": "COMMAND_FABRIC", "final_role": "TEST_INFRASTRUCTURE",
        "path": "tests/command_fabric/test_control_fabric.py", "test_only": True,
    }) == "DEVELOPMENT_ONLY"
    assert classify_component({
        "family_id": "WORKFLOW_ENGINE", "final_role": "RUNTIME_CORE",
        "path": "canonical/lib/workflowEngine.ts", "runtime_reachable": True,
    }) == "GATED"
    assert classify_component({
        "family_id": "SEMANTIC_ENGINE", "final_role": "RUNTIME_CORE",
        "path": "RAIOS/V9/cognition/semantic/semantic_engine.py", "runtime_reachable": True,
    }) == "REFERENCE_ONLY"
    assert classify_component({
        "family_id": "LEGACY_BRAIN", "final_role": "RUNTIME_CORE", "path": "brain.py",
        "runtime_reachable": True,
    }) == "LEGACY_UNIQUE_VALUE"
    assert classify_component({
        "family_id": "RAIOS_MCP", "final_role": "RUNTIME_SERVICE",
        "path": "scripts/ai-os/raios_mcp/server.py", "runtime_reachable": True,
        "test_only": False,
    }) == "CANONICAL_ACTIVE"
    assert classify_component({
        "family_id": "COGNITIVE_EVENT_BUS", "final_role": "RUNTIME_SERVICE",
        "path": "RAIOS/V9/runtime/cognitive_event_bus.py", "runtime_reachable": True,
    }) == "REFERENCE_ONLY"


def test_factory_estate_fifty_are_not_independent_services(tmp_path):
    repo = _repo(tmp_path, [
        {"family_id": "COMMAND_FABRIC", "path": "tests/x.py", "final_role": "TEST_INFRASTRUCTURE",
         "runtime_reachable": False, "test_only": True, "library_only": False, "adapter_only": False},
        {"family_id": "RAIOS_MCP", "path": "scripts/ai-os/raios_mcp/server.py", "final_role": "RUNTIME_SERVICE",
         "runtime_reachable": True, "test_only": False, "library_only": False, "adapter_only": False},
        {"family_id": "WORKFLOW_ENGINE", "path": "canonical/lib/workflowEngine.ts", "final_role": "RUNTIME_CORE",
         "runtime_reachable": True, "test_only": False, "library_only": False, "adapter_only": False},
        {"family_id": "AUDIT_ENGINE", "path": "canonical/intelligence/intelligence/engines/audit-engine.ts",
         "final_role": "CANONICAL_LIBRARY", "runtime_reachable": False, "test_only": False,
         "library_only": True, "adapter_only": False},
    ])
    out = factory_estate_projection(repo)
    assert out["schema"] == "raios.factory-estate.v1"
    assert out["all_fifty_are_independent_services"] is False
    assert out["run_all_invoked"] is False
    assert out["gated_activated"] is False
    assert out["second_factory_created"] is False
    assert out["recursive_estate_scan"] is False
    assert out["brain_py_preserved"] is True
    assert out["activation_readiness"]["weight_merge_activated"] is False
    assert "resource_factory" in out["activation_readiness"]["ready_for_on_demand"]
    assert out["independent_service_count"] == 1
    classes = {row["path"]: row["operator_class"] for row in out["components"]}
    assert classes["tests/x.py"] == "DEVELOPMENT_ONLY"
    assert classes["canonical/lib/workflowEngine.ts"] == "GATED"
    factories = {row["id"]: row for row in out["factories"]}
    assert factories["resource_factory"]["operator_class"] == "CANONICAL_DORMANT"
    assert factories["resource_factory"]["path_exists"] is True
    assert factories["resource_factory"]["input_to_receipt_proven"] is False
    assert factories["weight_merge"]["operator_class"] == "GATED"
    assert factories["weight_merge"]["activated_this_wave"] is False
    assert out["copy_estate"]["SAFE_TO_REMOVE_SOURCE"] is False
    assert out["copy_estate"]["cutover"] is False


def test_live_factory_cycle_promotes_only_that_factory(tmp_path):
    repo = _repo(tmp_path, [])
    live = {"status": "PASS", "factories": {
        "resource_factory": {"factory": "RESOURCE_FACTORY", "status": "PASS"},
    }}
    out = factory_estate_projection(repo, live_runtime=live)
    row = next(x for x in out["factories"] if x["id"] == "resource_factory")
    assert row["operator_class"] == "CANONICAL_ACTIVE"
    assert row["live_cycle_proven"] is True
    assert out["factories_active"] == 1
    assert out["gated_activated"] is False


def test_topology_keeps_unknown_and_tcp_is_not_ollama_online():
    out = system_topology_projection(
        plane={"canonical_head": "abc", "self": {"name": "CommandCenter", "port": 8770, "state": "ONLINE", "probe": "SELF"},
               "services": [{"name": "NATS", "state": "ONLINE", "port": 4222, "probe": "TCP_ONLY"}]},
        worker={"healthy": True, "state": "ONLINE", "worker_id": "w1"},
        continuity={},
        ollama_listening=True,
        canonical_head="abc",
        canonical_branch="ai-evolution-202608051809",
    )
    by = {n["name"]: n for n in out["nodes"]}
    assert by["Ollama"]["state"] == "UNKNOWN"
    assert by["Ollama"]["port_ne_service_identity"] is True
    assert by["StorageAuthority"]["state"] == "IDENTIFIED"
    assert by["StorageAuthority"]["http_endpoint"] is None
    assert by["StorageAuthority"]["identity"] == "EXISTING_SPLIT_WRITERS"
    assert by["StorageAuthority"]["state"] != "ONLINE"
    assert by["Continuity"]["state"] == "UNKNOWN"
    assert out["fake_online"] is False
    assert out["second_control_plane"] is False
    assert out["projection_ne_authority"] is True
    listening_off = system_topology_projection(ollama_listening=False)
    ollama = next(n for n in listening_off["nodes"] if n["name"] == "Ollama")
    assert ollama["state"] == "OFFLINE"


def test_current_truth_separates_heads_and_rejects_stale_current_state(tmp_path):
    out = current_truth_projection(
        canonical_head="abc",
        deployed_head="def",
        runtime_head="abc",
        observed_head="abc",
        current_state={"verified_facts": ["next.js"], "known_gaps": ["uae"]},
        deployment={"transaction_id": "C6-CF-RESILIENCE-20260923-002", "canonical_head": "def"},
    )
    assert out["generic_head_omitted"] is True
    assert out["projection_ne_authority"] is True
    assert out["canonical_head"]["field"] == "canonical_head"
    assert out["deployed_head"]["value"] == "def"
    assert out["c2_overlay_deployed"] is False
    assert out["current_state_file"]["is_runtime_current"] is False
    assert out["heads"]["drift"]
    assert out["authority"]["CURRENT_json"]["exists"] is False
    assert out["CURRENT_json_absent"] is True
    topo = system_topology_projection(
        canonical_head="abc",
        deployment={"transaction_id": "C6-CF-RESILIENCE-20260923-002", "canonical_head": "def"},
    )
    assert topo["current_truth"]["c2_overlay_deployed"] is False
    assert "canonical_head" in topo["current_truth"]
    (tmp_path / ".ai-os" / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-os" / "mcp").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-os" / "state" / "TASKS.json").write_text('{"tasks":[]}\n', encoding="utf-8")
    (tmp_path / ".ai-os" / "state" / "LOCKS.json").write_text('{"locks":[]}\n', encoding="utf-8")
    (tmp_path / ".ai-os" / "mcp" / "SEAT-MAP.json").write_text('{"seats":{}}\n', encoding="utf-8")
    (tmp_path / ".ai-os" / "state" / "command-fabric" / "leases").mkdir(parents=True, exist_ok=True)
    stamped = current_truth_projection(canonical_head="abc", repo=tmp_path, current_state={"verified_facts": ["x"]})
    assert stamped["authority"]["tasks"]["exists"] is True
    assert stamped["authority"]["locks"]["exists"] is True
    assert stamped["authority"]["seat_map"]["exists"] is True
    assert stamped["authority"]["leases_root"]["listed"] is False
    assert stamped["authority"]["leases_root"]["exists"] is True
    assert stamped["CURRENT_json_absent"] is True
    assert stamped["misleading"]


def test_fabric_does_not_scan_inbox_or_synthesize_ack():
    out = fabric_projection({"healthy": False, "state": "DEGRADED", "last_error": "x"})
    assert out["inbox_files_scanned"] is False
    assert out["synthetic_ack"] is False
    assert out["second_message_bus"] is False
    assert out["second_receipt_ledger"] is False
    assert out["worker_state"] == "DEGRADED"
    assert out["pending"] == "UNKNOWN"
    empty = fabric_projection(None)
    assert empty["worker_state"] == "UNKNOWN"


def test_self_heal_missing_file_is_unknown_not_offline():
    out = self_heal_projection({})
    assert out["status"] == "UNKNOWN"
    assert out["c2_mutated"] is False
    assert out["maintain_script_touched"] is False
    present = self_heal_projection({"status": "DEGRADED", "run_id": "r1"})
    assert present["status"] == "DEGRADED"
    assert present["current_continuity_run"] == "r1"


def test_reachability_island_remains_candidate(tmp_path):
    repo = _repo(tmp_path, [])
    routing = capability_routing_projection(repo)
    reach = reachability_projection()
    assert routing["gated_activated"] is False
    assert routing["classification_ne_process_activation"] is True
    assert routing["hardcoded_agent_assignment"] is False
    assert "workflow-engine" in {x["id"] for x in routing["gated"]}
    assert reach["zero_canonical_island"] == "CANDIDATE"
    assert reach["zero_canonical_island_proven"] is False
    assert reach["keepers_write_cognitive_wal"] is False
    assert reach["gated_activated"] is False
    storage = storage_class_projection()
    assert storage["recursive_scan"] is False
    assert storage["blanket_delete"] is False
    assert storage["canonical_git_ne_runtime_event_store"] is True
    assert storage["STORAGE_AUTHORITY"] == "EXISTING_SPLIT_WRITERS"
    assert storage["http_endpoint"] is None
    assert storage["cutover_executed"] is False
    assert any(w["data_class"] == "TRANSPORT_HIGH_VOLUME" for w in storage["writers"])
    assert routing["routing_states"]["fabric_routing_available"] is False
    assert reach["island_proof"]["ZERO_CANONICAL_ISLAND"] == "BLOCKED"
    assert reach["island_proof"]["zero_canonical_island_proven"] is False


def test_incidents_preserve_unknown_without_fake_score():
    out = incidents_projection(
        attention={"items": [{"category": "HEAD_DRIFT", "task_id": "T1"}]},
        worker={"healthy": False, "state": "DEGRADED"},
        topology_nodes=[{"name": "StorageAuthority", "state": "UNKNOWN", "probe": "NONE"}],
    )
    cats = {x["category"] for x in out["items"]}
    assert "HEAD_DRIFT" in cats
    assert "RUNTIME_DEGRADED" in cats
    assert "UNKNOWN" in cats
    assert out["fabricated_score"] is False
    assert all(x.get("fabricated_score") is False for x in out["items"])


def test_operator_laws_are_system_visible_not_chat_only(tmp_path):
    gov = tmp_path / ".ai-os" / "governance"
    gov.mkdir(parents=True)
    (tmp_path / ".ai-os" / "CORE-CONTRACT.md").write_text("# CORE\n## Completion\nCOMPLETE_ASSIGNED_WORK\n", encoding="utf-8")
    (gov / "RAIOS-SINGLE-TRUTH-POLICY.json").write_text(
        '{"completion_operator_laws":{"authority":"C1","chat_only":false,"laws":["COMPLETE_ASSIGNED_WORK","NO_FAKE_RESULT"]}}',
        encoding="utf-8",
    )
    out = operator_laws_projection(tmp_path)
    assert out["schema"] == "raios.operator-laws.v1"
    assert out["chat_only"] is False
    assert out["second_constitution"] is False
    assert out["core_contract_present"] is True
    ids = set(out["ids"])
    assert "COMPLETE_ASSIGNED_WORK" in ids
    assert "NO_FAKE_RESULT" in ids
    assert "NO_HANGING_WITHOUT_NOTICE" in ids
    assert "LAWS_SYSTEM_VISIBLE" in ids
    assert "ONE_COMMAND_CENTER" in ids


def test_integration_mesh_does_not_fake_full_bind():
    laws = operator_laws_projection(None)
    unbound = integration_mesh_projection(
        plane={"services": [
            {"name": "C5", "state": "ONLINE", "port": 8766},
            {"name": "UniversalMCP", "state": "ONLINE", "port": 8788},
            {"name": "9Router", "state": "ONLINE", "port": 20128},
            {"name": "NATS", "state": "OFFLINE", "port": 4222},
        ]},
        worker={"healthy": True, "state": "ONLINE"},
        hanging={"system_informed": True, "open_count": 4},
        laws=laws,
        c5_http=200,
        mcp_http=200,
        mcp_live=True,
        factory_runtime={"status": "PASS"},
        live_bound_count=0,
        ecology_source_present=True,
        direct_second_bus=False,
    )
    assert unbound["fake_integrated"] is False
    assert unbound["fully_integrated"] is False
    assert unbound["overall"] == "PARTIAL"
    assert unbound["actor_ack_proven"] is False
    by = {row["id"]: row for row in unbound["links"]}
    assert by["c5"]["state"] == "ONLINE"
    assert by["nats"]["state"] == "OFFLINE"
    assert by["live-seats"]["state"] == "UNBOUND"
    tcp_only = integration_mesh_projection(
        plane={"services": [{"name": "C5", "state": "ONLINE", "port": 8766}]},
        worker={"healthy": True, "state": "ONLINE"},
        hanging={"system_informed": True},
        laws=laws,
        c5_http=0,
        mcp_http=0,
        mcp_live=False,
        live_bound_count=0,
        ecology_source_present=True,
        direct_second_bus=False,
    )
    by2 = {row["id"]: row for row in tcp_only["links"]}
    assert by2["c5"]["state"] == "UNKNOWN"
    assert tcp_only["fully_integrated"] is False
    bound = integration_mesh_projection(
        plane={"services": [
            {"name": "C5", "state": "ONLINE", "port": 8766},
            {"name": "UniversalMCP", "state": "ONLINE", "port": 8788},
            {"name": "9Router", "state": "ONLINE", "port": 20128},
            {"name": "NATS", "state": "ONLINE", "port": 4222},
        ]},
        worker={"healthy": True, "state": "ONLINE"},
        hanging={"system_informed": True, "open_count": 1},
        laws=laws,
        c5_http=200,
        mcp_http=200,
        mcp_live=True,
        factory_runtime={"status": "PASS"},
        live_bound_count=2,
        ecology_source_present=True,
        direct_second_bus=False,
    )
    assert bound["overall"] == "CONTROL_PLANE_AND_SEATS_BOUND"
    assert bound["fully_integrated"] is True
    assert bound["fake_integrated"] is False
    by3 = {row["id"]: row for row in bound["links"]}
    assert by3["nats"]["state"] == "ONLINE"
    assert by3["live-seats"]["state"] == "BOUND"
