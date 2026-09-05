from __future__ import annotations

from raios.command_center.coordination_truth import (
    build_dispatch_plan,
    build_founder_brief,
    build_work_lifecycle,
    canonical_seat,
    dispatch_priority_score,
    destructive_task_requested,
    founder_gate_satisfied,
    global_legacy_delete_gate_satisfied,
    legacy_delete_gate_satisfied,
)


def test_lifecycle_distinguishes_done_current_required_waiting_and_stale():
    tasks = [
        {"id": "D", "status": "DONE"},
        {"id": "A", "status": "IN_PROGRESS", "claimed_by": "CHATGPT-NORMAL",
         "dispatch_status": "SYSTEM_FIRST_ACTIVE"},
        {"id": "N", "status": "READY", "dependencies": ["D"]},
        {"id": "W", "status": "READY", "dependencies": ["MISSING"]},
        {"id": "S", "status": "IN_PROGRESS", "claimed_by": "cursor"},
    ]
    out = build_work_lifecycle(tasks)
    assert out["counts"]["DONE"] == 1
    assert out["counts"]["ACTIVE_VERIFIED"] == 1
    assert out["counts"]["REQUIRED_NEXT"] == 1
    assert out["counts"]["WAITING_DEPENDENCIES"] == 1
    assert out["counts"]["STALE_CLAIM_REQUIRES_RECONCILIATION"] == 1
    assert out["required_backlog_count"] == 4


def test_soft_target_window_can_fast_track_before_planned_month():
    tasks = [
        {"id": "NOW", "status": "READY", "dependencies": []},
        {"id": "JAN", "status": "READY", "dependencies": [],
         "not_before": "2999-01-01T00:00:00+00:00",
         "program_id": "P1", "target_month": "2999-01",
         "acceleration_allowed": True, "hard_not_before": False},
    ]
    life = build_work_lifecycle(tasks)
    assert life["counts"]["REQUIRED_NEXT"] == 2
    assert life["counts"]["FUTURE_PLANNED"] == 0
    jan = next(x for x in life["buckets"]["REQUIRED_NEXT"] if x["id"] == "JAN")
    assert jan["ahead_of_plan"] is True
    assert jan["acceleration_allowed"] is True
    rows = [{"seat": "C2", "aliases": ["CURSOR"], "alias_prefixes": [],
             "auto_routable": True, "coordination_available": True}]
    plan = build_dispatch_plan(tasks, rows)
    by = {row["task_id"]: row for row in plan["queue"]}
    assert set(by) == {"NOW", "JAN"}
    assert by["JAN"]["ahead_of_plan"] is True
    assert by["JAN"]["acceleration_bonus"] > 0


def test_hard_not_before_remains_a_real_execution_gate():
    tasks = [
        {"id": "LOCKED", "status": "READY", "dependencies": [],
         "not_before": "2999-01-01T00:00:00+00:00",
         "hard_not_before": True, "acceleration_allowed": True},
    ]
    life = build_work_lifecycle(tasks)
    assert life["counts"]["FUTURE_PLANNED"] == 1
    rows = [{"seat": "C2", "aliases": ["CURSOR"], "alias_prefixes": [],
             "auto_routable": True, "coordination_available": True}]
    assert build_dispatch_plan(tasks, rows)["queue"] == []


def test_superseded_task_is_closed_but_not_done_or_required():
    tasks = [
        {"id": "D", "status": "DONE"},
        {"id": "S", "status": "SUPERSEDED",
         "superseded_by": "ACTIVE",
         "closure_reason": "DUPLICATE_TASK_MERGED"},
        {"id": "R", "status": "READY", "dependencies": []},
    ]
    out = build_work_lifecycle(tasks)
    assert out["counts"]["DONE"] == 1
    assert out["counts"]["SUPERSEDED_OR_CANCELLED"] == 1
    assert out["counts"]["REQUIRED_NEXT"] == 1
    assert out["required_backlog_count"] == 1
    row = out["buckets"]["SUPERSEDED_OR_CANCELLED"][0]
    assert row["superseded_by"] == "ACTIVE"


def test_dispatch_plan_required_capabilities_match_runtime_eligibility():
    task = {
        "id": "CAP", "status": "READY", "dependencies": [],
        "allowed_agents": ["C6"], "required_capabilities": ["FILE_INTELLIGENCE"],
        "automatic_dispatch": True, "dispatch_authorized_by": "C1",
    }
    base_row = {
        "seat": "C6", "actor_id": "C6-ACTOR", "aliases": ["C6"],
        "alias_prefixes": [], "auto_routable": True, "coordination_available": True,
    }
    missing = build_dispatch_plan([task], [dict(base_row)])
    assert missing["queue"][0]["eligible_seats"] == []
    assert missing["queue"][0]["blocker"] == "NO_ELIGIBLE_COUNCIL_SEAT"
    proven_row = dict(base_row, capabilities=["FILE_INTELLIGENCE"])
    proven = build_dispatch_plan([task], [proven_row])
    assert proven["queue"][0]["eligible_seats"] == ["C6"]
    assert proven["queue"][0]["dispatchable_now"] is True


def test_founder_brief_prepares_when_offline_and_holds_explicit_decision():
    tasks = [
        {"id": "NEXT", "status": "READY", "dependencies": []},
        {"id": "DECIDE", "status": "READY", "requires_c1_decision": True,
         "founder_question": "Promote this change?", "recommended_decision": "HOLD"},
    ]
    out = build_founder_brief(tasks, founder_available=False)
    assert out["consultation_mode"] == "PREPARE_AND_HOLD_GOVERNED_DECISIONS"
    assert out["prepared_for_founder_return"] is True
    assert out["decision_count"] == 1
    assert out["decisions_required"][0]["task_id"] == "DECIDE"
    assert {x["id"] for x in out["must_do_next"]} == {"NEXT", "DECIDE"}


def test_founder_gate_requires_explicit_c1_approval_when_marked():
    task = {"id": "X", "requires_c1_decision": True}
    assert founder_gate_satisfied(task) is False
    task.update(founder_decision_status="APPROVED", founder_decision_by="C1")
    assert founder_gate_satisfied(task) is True
    assert founder_gate_satisfied({"id": "Y", "status": "READY"}) is True


def test_dispatch_priority_favors_tasks_that_unlock_more_work():
    tasks = [
        {"id": "HIGH", "status": "READY", "dependencies": [], "allowed_agents": ["cursor"]},
        {"id": "LOW", "status": "READY", "dependencies": [], "allowed_agents": ["cursor"]},
        {"id": "CHILD", "status": "READY", "dependencies": ["HIGH"]},
    ]
    assert dispatch_priority_score(tasks[0], tasks)["score"] > dispatch_priority_score(tasks[1], tasks)["score"]


def test_dispatch_plan_explains_eligibility_readiness_and_blocker():
    tasks = [
        {"id": "HIGH", "status": "READY", "dependencies": [], "allowed_agents": ["cursor"],
         "automatic_dispatch": True, "dispatch_authorized_by": "C1"},
        {"id": "LOW", "status": "READY", "dependencies": [], "allowed_agents": ["github-agent"],
         "automatic_dispatch": True, "dispatch_authorized_by": "C1"},
        {"id": "CHILD", "status": "READY", "dependencies": ["HIGH"]},
    ]
    rows = [
        {"seat": "C2", "aliases": ["CURSOR", "C2@AG"], "alias_prefixes": ["C2@"],
         "auto_routable": True, "coordination_available": True},
        {"seat": "C6", "aliases": ["GITHUB-AGENT"], "alias_prefixes": ["C6@"],
         "auto_routable": False, "coordination_available": True},
    ]
    plan = build_dispatch_plan(tasks, rows)
    by = {row["task_id"]: row for row in plan["queue"]}
    assert plan["queue"][0]["task_id"] == "HIGH"
    assert by["HIGH"]["dispatchable_now"] is True
    assert by["HIGH"]["execution_ready_seats"] == ["C2"]
    assert by["LOW"]["blocker"] == "ELIGIBLE_SEAT_NOT_EXECUTION_READY"
    assert "CHILD" not in by


def test_actor_aliases_are_unambiguous_and_canonical():
    seat_map = {"seats": {
        "C2": {"instance_role": "cursor", "aliases": ["CURSOR", "C2@AG"], "alias_prefixes": ["C2@"]},
        "C6": {"instance_role": "c6-runtime", "aliases": ["GITHUB-AGENT"], "alias_prefixes": ["C6@"]},
    }}
    assert canonical_seat("cursor", seat_map) == "C2"
    assert canonical_seat("C2@AG", seat_map) == "C2"
    assert canonical_seat("C6@AG", seat_map) == "C6"
    assert canonical_seat("CODEX", seat_map) is None


def _passing_exact_delete_gate():
    return {
        "status": "PASS",
        "authorized_surface_census_complete": True,
        "hash_and_lineage_complete": True,
        "semantic_capability_extraction_complete": True,
        "data_schema_knowledge_extraction_complete": True,
        "current_vs_legacy_coverage_complete": True,
        "unique_value_extracted_merged_migrated_or_retained": True,
        "behavior_equivalence_or_superior_replacement_proven": True,
        "provenance_preserved": True,
        "recovery_or_rollback_proven": True,
        "safe_to_remove_source": True,
        "unknown_unclassified_unresolved_unique_value": 0,
        "exact_redundancy": True,
        "standing_c1_duplicate_authority": True,
    }


def test_destructive_task_is_fail_closed_until_deep_legacy_gate_passes():
    task = {
        "id": "DEL",
        "title": "Delete old duplicate source",
        "status": "READY",
        "dependencies": [],
        "allowed_agents": ["cursor"],
        "automatic_dispatch": True,
        "dispatch_authorized_by": "C1",
    }
    assert destructive_task_requested(task) is True
    assert legacy_delete_gate_satisfied(task) is False
    rows = [{"seat": "C2", "aliases": ["CURSOR"], "alias_prefixes": [],
             "auto_routable": True, "coordination_available": True}]
    plan = build_dispatch_plan([task], rows)
    assert plan["queue"][0]["blocker"] == "DEEP_LEGACY_FORENSIC_AUDIT_REQUIRED"
    assert plan["queue"][0]["dispatchable_now"] is False


def test_exact_redundancy_can_pass_only_after_all_deep_gates():
    task = {
        "id": "DEL",
        "title": "Delete old duplicate source",
        "status": "READY",
        "dependencies": [],
        "deep_legacy_forensic_gate": _passing_exact_delete_gate(),
    }
    assert legacy_delete_gate_satisfied(task) is True
    assert founder_gate_satisfied(task) is True


def test_non_exact_retirement_requires_specific_c1_decision_even_after_audit():
    gate = _passing_exact_delete_gate()
    gate["exact_redundancy"] = False
    gate["c1_specific_deletion_approval"] = True
    task = {
        "id": "RETIRE",
        "title": "Retire legacy project after migration",
        "status": "READY",
        "deep_legacy_forensic_gate": gate,
    }
    assert legacy_delete_gate_satisfied(task) is True
    assert founder_gate_satisfied(task) is False
    task.update(founder_decision_status="APPROVED", founder_decision_by="C1")
    assert founder_gate_satisfied(task) is True


def test_predelete_audit_task_is_explicitly_non_destructive():
    task = {
        "id": "AUDIT",
        "title": "Deep legacy forensic pre-delete audit",
        "destructive_action_requested": False,
    }
    assert destructive_task_requested(task) is False
    assert legacy_delete_gate_satisfied(task) is True


def test_no_delete_language_is_not_misclassified_as_destructive():
    assert destructive_task_requested({
        "id": "AUDIT",
        "title": "Audit old sources",
        "objective": "No delete, never remove, and without retirement during this audit.",
    }) is False


def test_global_delete_gate_is_fail_closed_until_every_foundation_fact_passes():
    closed = {"facts": {
        "DEEP_LEGACY_FORENSIC_AUDIT_PASS": False,
        "LEGACY_DELETE_ALLOWED": False,
        "SAFE_TO_REMOVE_SOURCE": False,
        "LEGACY_UNIQUE_VALUE_UNRESOLVED": "UNKNOWN",
    }}
    assert global_legacy_delete_gate_satisfied(closed) is False
    open_gate = {"facts": {
        "DEEP_LEGACY_FORENSIC_AUDIT_PASS": True,
        "LEGACY_DELETE_ALLOWED": True,
        "SAFE_TO_REMOVE_SOURCE": True,
        "LEGACY_UNIQUE_VALUE_UNRESOLVED": 0,
    }}
    assert global_legacy_delete_gate_satisfied(open_gate) is True
