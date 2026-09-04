from __future__ import annotations

from raios.command_center.coordination_truth import (
    build_founder_brief,
    build_work_lifecycle,
    canonical_seat,
    founder_gate_satisfied,
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


def test_actor_aliases_are_unambiguous_and_canonical():
    seat_map = {"seats": {
        "C2": {"instance_role": "cursor", "aliases": ["CURSOR", "C2@AG"], "alias_prefixes": ["C2@"]},
        "C6": {"instance_role": "c6-runtime", "aliases": ["GITHUB-AGENT"], "alias_prefixes": ["C6@"]},
    }}
    assert canonical_seat("cursor", seat_map) == "C2"
    assert canonical_seat("C2@AG", seat_map) == "C2"
    assert canonical_seat("C6@AG", seat_map) == "C6"
    assert canonical_seat("CODEX", seat_map) is None
