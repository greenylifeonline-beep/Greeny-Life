from raios.command_center.live_activation import (
    factory_activation_readiness,
    factory_capability_routing,
    factory_live_cycle_blocked,
    storage_authority_resolution,
    storage_writer_cutover_matrix,
    wave08_fabric_reconciliation,
    zero_canonical_island_proof,
    resolve_task_runtime_route,
    capability_factory_binding,
    auto_dispatch_runtime_path,
    safe8_activation_plan,
)


def test_storage_authority_is_split_writers_not_http_service():
    auth = storage_authority_resolution()
    assert auth["STORAGE_AUTHORITY"] == "EXISTING_SPLIT_WRITERS"
    assert auth["http_endpoint"] is None
    assert auth["not_an_http_service"] is True
    assert auth["second_storage_plane"] is False
    assert auth["cutover_executed"] is False
    assert auth["blanket_delete"] is False
    matrix = storage_writer_cutover_matrix()
    assert matrix["recursive_scan"] is False
    assert matrix["delete_old_this_wave"] is False
    classes = {w["data_class"] for w in matrix["writers"]}
    assert "TRANSPORT_HIGH_VOLUME" in classes
    assert "CONTROL_PERSISTENT" in classes
    inbox = next(w for w in matrix["writers"] if "inbox" in w["writer"])
    assert inbox["git_required"] is False
    assert inbox["cutover_readiness"].startswith("BLOCKED_UNTIL_C6")
    assert "COPY" in matrix["method_required"]


def test_factory_readiness_does_not_activate_gated_or_unresolved():
    out = factory_activation_readiness()
    by = {r["factory"]: r for r in out["factories"]}
    assert by["resource_factory"]["readiness"] == "READY_FOR_ON_DEMAND"
    assert by["weight_merge"]["readiness"] == "GATED_BY_DESIGN"
    assert by["model_ecology"]["readiness"] == "READY_FOR_ON_DEMAND"
    assert by["c5_expert_foundry"]["readiness"] == "BLOCKED_AUTHORITY"
    assert out["weight_merge_activated"] is False
    assert out["model_ecology_activated"] is True
    assert out["model_ecology_auto_promote"] is False
    assert out["run_all_invoked"] is False


def test_capability_states_are_not_collapsed_to_active():
    out = factory_capability_routing()
    ollama = next(x for x in out["capabilities"] if x["CAPABILITY"] == "OLLAMA_INFERENCE")
    assert ollama["INSTALLED"] is True
    assert ollama["ACTIVE"] is False
    assert ollama["HEALTHY"] == "UNKNOWN"
    assert ollama["tcp_ne_verified"] is True
    assert out["fabric_routing_available"] is False
    merge = next(x for x in out["capabilities"] if x["CAPABILITY"] == "WEIGHT_MERGE")
    assert merge["AVAILABLE"] == "GATED"
    assert merge["ROUTABLE"] is False
    ecology = next(x for x in out["capabilities"] if x["CAPABILITY"] == "MODEL_ECOLOGY")
    assert ecology["WIRED"] is True
    assert ecology["AVAILABLE"] == "ON_DEMAND"
    fabric = next(x for x in out["capabilities"] if x["CAPABILITY"] == "MODEL_FABRIC")
    assert fabric["WIRED"] is True
    ninerouter = next(x for x in out["capabilities"] if x["CAPABILITY"] == "NINEROUTER")
    assert ninerouter["WIRED"] is True
    assert "RESOURCE_AUTHORITY=false" in ninerouter["note"]


def test_live_cycle_blocked_on_cc_down_is_not_a_fake_pass():
    out = factory_live_cycle_blocked(cc_reachable=False, fabric_healthy=None, task_registered=False)
    assert out["FACTORY_LIVE_CYCLE"] == "BLOCKED"
    assert "COMMAND_CENTER_8770_DOWN" in out["blocking_edge"]
    assert out["bypass_command_fabric"] is False
    assert out["synthetic_receipt"] is False
    assert out["run_all_invoked"] is False
    assert out["task_registration_required"] is True
    assert out["on_demand_probe_is_not_fabric_cycle"] is True


def test_live_cycle_blocked_on_missing_task_when_cc_up():
    out = factory_live_cycle_blocked(cc_reachable=True, fabric_healthy=True, task_registered=False)
    assert out["FACTORY_LIVE_CYCLE"] == "BLOCKED"
    assert "TASK_REGISTRATION_REQUIRED" in out["blocking_edge"]
    assert out["bypass_command_fabric"] is False
    assert out["synthetic_receipt"] is False


def test_zero_island_stays_blocked_with_named_islands():
    out = zero_canonical_island_proof()
    assert out["ZERO_CANONICAL_ISLAND"] == "BLOCKED"
    assert out["zero_canonical_island_proven"] is False
    reasons = {i["island_reason"] for i in out["islands"]}
    assert "ON_DEMAND_SCRIPT_NOT_FABRIC_ROUTER" in reasons
    assert "UNRESOLVED_IDENTITY" not in reasons
    assert "on_demand_call_without_canonical_task_route" in reasons
    by_id = {i["id"]: i for i in out["nodes"]}
    assert by_id["model_ecology"]["island"] is False
    assert by_id["model_ecology"]["authority"] == "CANONICAL_ON_DEMAND"
    assert out["second_message_bus"] is False


def test_wave08_reconciliation_does_not_synthesize():
    out = wave08_fabric_reconciliation()
    assert out["WAVE08_REAL_FABRIC_DELIVERY"] == "PENDING"
    assert out["WAVE08_ACTOR_ACK"] == "PENDING"
    assert out["ACK_SYNTHESIZED"] is False
    assert out["replacement_packet"] is False
    assert out["target_session"] == "dd39bac0-65ea-4909-afcb-1796249c8944"
    assert out["inbox_walk"] is False


def test_wave04_resolver_does_not_claim_live():
    out = resolve_task_runtime_route({"id": "T1", "automation_action": "RESOURCE_CENSUS"})
    assert out["FACTORY"] == "resource_factory"
    assert out["LIVE_DEPLOYED"] is False
    assert out["EXECUTING"] is False
    assert out["PERMANENT_ACTIVATION"] is False
    gated = resolve_task_runtime_route({"capability": "WEIGHT_MERGE"})
    assert gated["SOURCE_READY"] is False


def test_wave04_bindings_reuse_existing_and_skip_control_plane():
    out = capability_factory_binding()
    assert out["second_registry"] is False
    assert out["c8_capabilities_consumed"] == 24
    assert out["LIVE_DEPLOYED"] is False
    by = {r["CAPABILITY"]: r for r in out["bindings"]}
    assert by["CONTROL_PLANE"]["DO_NOT_ACTIVATE"] is True
    assert by["RESOURCE_PLACEMENT"]["FACTORY"] == "resource_factory"


def test_wave04_auto_dispatch_found_without_second_scheduler():
    out = auto_dispatch_runtime_path()
    assert out["AUTO_DISPATCH_FOUND"] is True
    assert out["second_scheduler"] is False
    assert out["connected_to_factory_execution"] is False


def test_wave04_safe8_not_live_activated():
    out = safe8_activation_plan()
    assert out["SAFE8_PREPARED"] == 8
    assert out["SAFE8_LIVE_ACTIVATED"] == 0
    assert out["CONTROL_PLANE_ACTIVATED"] is False
    ctrl = next(x for x in out["components"] if x["id"] == "CONTROL_PLANE")
    assert ctrl["activation_method"] == "FORBIDDEN"
