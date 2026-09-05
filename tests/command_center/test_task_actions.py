import json
from pathlib import Path

from src.raios.command_center.council_board import CouncilBoard
from src.raios.command_center.task_actions import TaskActionExecutor


class Worker:
    def enqueue(self, *args, **kwargs):
        raise AssertionError("deterministic system action must not dispatch to a seat")


def make_board(tmp_path: Path, authorized: bool = True):
    repo = tmp_path / "Greeny-Life"
    (repo / ".ai-os/state").mkdir(parents=True)
    task = {
        "id": "RESOURCE-CENSUS-1",
        "title": "inventory",
        "status": "READY",
        "dependencies": [],
        "automation_action": "RESOURCE_CENSUS",
        "dispatch_authorized_by": "C1" if authorized else None,
    }
    (repo / ".ai-os/state/TASKS.json").write_text(
        json.dumps({"tasks": [task]}), encoding="utf-8"
    )
    board = CouncilBoard(repo, tmp_path / "presence.json")
    return board, repo


def fake_package(_world):
    return {
        "RESOURCE-CENSUS.json": {
            "status": {
                "providers_total": 8,
                "accounts_total": 7,
                "accounts_reachable": 4,
            }
        },
        "ACCOUNTS.json": [
            {"account_id": "ORACLE_01", "status": "BLOCKED_C1_ACTION"},
            {"account_id": "MODAL_01", "status": "REACHABLE"},
            {"account_id": "LIGHTNING_01", "status": "REACHABLE"},
        ],
    }


def test_c1_authorized_census_runs_without_present_seat(tmp_path, monkeypatch):
    board, repo = make_board(tmp_path)
    board.actions = TaskActionExecutor(
        repo, collector=lambda: {"accounts": []}, prober=lambda world: []
    )
    monkeypatch.setattr(
        "src.raios.command_center.task_actions.snapshots", fake_package
    )
    out = board.run_cycle(Worker())
    task = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][0]
    assert out["actions_processed"] == 1
    assert out["tasks_dispatched"] == 0
    assert task["status"] == "DONE"
    assert task["executed_by"] == "RAIOS-SYSTEM-ACTION:RESOURCE_FACTORY"
    proof = repo / task["evidence"]
    payload = json.loads(proof.read_text(encoding="utf-8"))
    safety = payload["safety"]
    assert safety["GPU_SESSION_STARTED"] is False
    assert safety["PAID_RESOURCE_CREATED"] is False
    assert safety["MODEL_DOWNLOAD_EXECUTED"] is False
    assert safety["MAX_MODEL_PARAMETERS_BILLION"] == 32
    accounts = payload["inventory"]["ACCOUNTS.json"]
    assert {row["account_id"] for row in accounts} == {
        "ORACLE_01",
        "MODAL_01",
        "LIGHTNING_01",
    }


def test_census_without_c1_authorization_stays_ready(tmp_path, monkeypatch):
    board, repo = make_board(tmp_path, authorized=False)
    board.actions = TaskActionExecutor(
        repo, collector=lambda: {"accounts": []}, prober=lambda world: []
    )
    monkeypatch.setattr(
        "src.raios.command_center.task_actions.snapshots", fake_package
    )
    out = board.run_cycle(Worker())
    task = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][0]
    assert out["actions_processed"] == 0
    assert task["status"] == "READY"
    assert not list(
        (repo / ".ai-os/reports/command-center/resource-census").glob("**/*.json")
    )


def test_census_exception_is_fail_closed(tmp_path):
    board, _repo = make_board(tmp_path)

    def fail():
        raise RuntimeError("probe exploded")

    board.actions = TaskActionExecutor(
        board.repo, collector=fail, prober=lambda world: []
    )
    out = board.run_cycle(Worker())
    task = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][0]
    assert out["actions_blocked"] == 1
    assert task["status"] == "BLOCKED"
    assert task["dispatch_status"] == "AUTOMATION_BLOCKED"
    assert "probe exploded" in task["blocker"]


def make_forensic_board(tmp_path: Path, authorized: bool = True):
    repo = tmp_path / "Greeny-Life"
    (repo / ".ai-os/state").mkdir(parents=True)
    task = {
        "id": "FORENSIC-CENSUS-1",
        "title": "read only forensic phase one",
        "status": "READY",
        "dependencies": [],
        "automation_action": "DEEP_LEGACY_FORENSIC_CENSUS",
        "dispatch_authorized_by": "C1" if authorized else None,
        "destructive_action_requested": False,
    }
    (repo / ".ai-os/state/TASKS.json").write_text(
        json.dumps({"tasks": [task]}), encoding="utf-8"
    )
    return CouncilBoard(repo, tmp_path / "presence.json"), repo


def fake_forensic_package(_task):
    safety = {
        "READ_ONLY_SOURCE_AUDIT": True,
        "SOURCE_FILE_DELETED": False,
        "SOURCE_FILE_EDITED": False,
        "RETIRED_REPAIR_TREE_READ": False,
        "SAFE_TO_REMOVE_SOURCE": False,
    }
    return {
        "00-SURFACE-CENSUS.json": {
            "tracked_file_count": 4,
            "historical_unique_paths": 8,
            "safety": safety,
        },
        "DELETE-ELIGIBILITY-REPORT.json": {
            "decision": "DENY",
            "safe_to_remove_source": False,
            "unique_value_unresolved": "UNKNOWN",
            "safety": safety,
        },
        "PHASE1-FORENSIC-EVIDENCE.json": {
            "schema": "raios.deep-legacy-forensic.phase1-evidence.v1",
            "status": "COMPLETE_EVIDENCE_VERIFIED",
            "full_forensic_audit_complete": False,
            "safe_to_remove_source": False,
            "next_required_phase": "SEMANTIC_BEHAVIORAL_UNIQUE_VALUE_RECONCILIATION",
            "safety": safety,
        },
    }


def test_forensic_census_runs_as_read_only_system_action_without_seat(tmp_path):
    board, repo = make_forensic_board(tmp_path)
    source = repo / "valuable-old-brain.txt"
    source.write_text("unique commercial intelligence", encoding="utf-8")
    before = source.read_bytes()
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        forensic_collector=fake_forensic_package,
    )
    out = board.run_cycle(Worker())
    task = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][0]
    assert out["actions_processed"] == 1
    assert out["tasks_dispatched"] == 0
    assert task["status"] == "DONE"
    assert task["executed_by"] == "RAIOS-SYSTEM-ACTION:DETERMINISTIC_FORENSIC_CENSUS"
    assert source.read_bytes() == before
    proof = json.loads((repo / task["evidence"]).read_text(encoding="utf-8"))
    assert proof["full_forensic_audit_complete"] is False
    assert proof["safe_to_remove_source"] is False
    delete_report = repo / ".ai-os/reports/deep-legacy-forensic/2026-09/FORENSIC-CENSUS-1/DELETE-ELIGIBILITY-REPORT.json"
    assert json.loads(delete_report.read_text(encoding="utf-8"))["decision"] == "DENY"
    receipt = repo / ".ai-os/receipts/command-fabric/FORENSIC-CENSUS-1.deep-legacy-forensic-census.receipt.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["source_mutation"] is False
    assert payload["retired_repair_tree_read"] is False
    assert payload["safe_to_remove_source"] is False


def test_forensic_census_without_c1_authorization_does_not_run(tmp_path):
    board, repo = make_forensic_board(tmp_path, authorized=False)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        forensic_collector=fake_forensic_package,
    )
    out = board.run_cycle(Worker())
    task = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][0]
    assert out["actions_processed"] == 0
    assert task["status"] == "READY"
    assert not (repo / ".ai-os/reports/deep-legacy-forensic/2026-09").exists()


def test_forensic_census_missing_phase1_evidence_fails_closed(tmp_path):
    board, repo = make_forensic_board(tmp_path)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        forensic_collector=lambda task: {
            "DELETE-ELIGIBILITY-REPORT.json": {
                "decision": "DENY",
                "safe_to_remove_source": False,
            }
        },
    )
    out = board.run_cycle(Worker())
    task = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][0]
    assert out["actions_blocked"] == 1
    assert task["status"] == "BLOCKED"
    assert "FORENSIC_PHASE1_EVIDENCE_MISSING" in task["blocker"]


def make_semantic_board(tmp_path: Path, authorized: bool = True, phase1_done: bool = True):
    repo = tmp_path / "Greeny-Life"
    (repo / ".ai-os/state").mkdir(parents=True)
    phase1 = {
        "id": "FORENSIC-PHASE1",
        "status": "DONE" if phase1_done else "READY",
        "dependencies": [],
    }
    phase2 = {
        "id": "FORENSIC-PHASE2",
        "title": "semantic reconciliation",
        "status": "READY",
        "dependencies": ["FORENSIC-PHASE1"],
        "automation_action": "DEEP_LEGACY_SEMANTIC_RECONCILIATION",
        "dispatch_authorized_by": "C1" if authorized else None,
        "destructive_action_requested": False,
    }
    (repo / ".ai-os/state/TASKS.json").write_text(
        json.dumps({"tasks": [phase1, phase2]}), encoding="utf-8"
    )
    return CouncilBoard(repo, tmp_path / "presence.json"), repo


def fake_semantic_package(_task, safe=False):
    safety = {
        "READ_ONLY_SOURCE_AUDIT": True,
        "SOURCE_MUTATION": False,
        "RETIRED_REPAIR_TREE_READ": False,
        "SAFE_TO_REMOVE_SOURCE": safe,
    }
    return {
        "06-SEMANTIC-RECONCILIATION.json": {
            "summary": {
                "historical_candidate_rows": 10,
                "exact_current_content_matches": 6,
                "unresolved_unique_value_candidates": 4,
            },
            "safety": safety,
        },
        "07-UNIQUE-VALUE-LEDGER.json": {
            "unresolved_count": 4,
            "zero_unknown_unclassified_unresolved": False,
            "safe_to_remove_source": safe,
        },
        "PHASE2-FORENSIC-EVIDENCE.json": {
            "schema": "raios.deep-legacy-forensic.phase2-evidence.v1",
            "status": "COMPLETE_EVIDENCE_VERIFIED",
            "full_forensic_audit_complete": False,
            "safe_to_remove_source": safe,
            "next_required_phase": "BEHAVIORAL_EQUIVALENCE_AND_RECOVERY_PROOF",
            "safety": safety,
        },
        "DELETE-ELIGIBILITY-REPORT.json": {
            "decision": "DENY" if not safe else "ALLOW",
            "safe_to_remove_source": safe,
        },
    }


def test_semantic_reconciliation_runs_read_only_without_seat(tmp_path):
    board, repo = make_semantic_board(tmp_path)
    source = repo / "valuable-history.txt"
    source.write_text("preserve me", encoding="utf-8")
    before = source.read_bytes()
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        semantic_collector=lambda task: fake_semantic_package(task, safe=False),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE2")
    assert out["actions_processed"] == 1
    assert task["status"] == "DONE"
    assert task["executed_by"] == "RAIOS-SYSTEM-ACTION:DETERMINISTIC_SEMANTIC_RECONCILIATION"
    assert source.read_bytes() == before
    proof = json.loads((repo / task["evidence"]).read_text(encoding="utf-8"))
    assert proof["safe_to_remove_source"] is False
    assert proof["full_forensic_audit_complete"] is False


def test_semantic_reconciliation_rejects_safe_to_remove_true(tmp_path):
    board, repo = make_semantic_board(tmp_path)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        semantic_collector=lambda task: fake_semantic_package(task, safe=True),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE2")
    assert out["actions_blocked"] == 1
    assert task["status"] == "BLOCKED"
    assert "FORENSIC_PHASE2_FAIL_CLOSED_VIOLATION" in task["blocker"]


def test_semantic_reconciliation_waits_for_phase1_dependency(tmp_path):
    board, repo = make_semantic_board(tmp_path, phase1_done=False)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        semantic_collector=lambda task: fake_semantic_package(task, safe=False),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE2")
    assert out["actions_processed"] == 0
    assert task["status"] == "READY"


def make_behavior_board(tmp_path: Path, phase2_done: bool = True):
    repo = tmp_path / "Greeny-Life"
    (repo / ".ai-os/state").mkdir(parents=True)
    phase2 = {
        "id": "FORENSIC-PHASE2",
        "status": "DONE" if phase2_done else "READY",
        "dependencies": [],
    }
    phase3 = {
        "id": "FORENSIC-PHASE3",
        "title": "behavior and recovery",
        "status": "READY",
        "dependencies": ["FORENSIC-PHASE2"],
        "automation_action": "DEEP_LEGACY_BEHAVIOR_RECOVERY",
        "dispatch_authorized_by": "C1",
        "destructive_action_requested": False,
    }
    (repo / ".ai-os/state/TASKS.json").write_text(
        json.dumps({"tasks": [phase2, phase3]}), encoding="utf-8"
    )
    return CouncilBoard(repo, tmp_path / "presence.json"), repo


def fake_behavior_package(_task, safe=False):
    safety = {
        "READ_ONLY_SOURCE_AUDIT": True,
        "SOURCE_MUTATION": False,
        "RETIRED_REPAIR_TREE_READ": False,
        "SAFE_TO_REMOVE_SOURCE": safe,
    }
    return {
        "08-OBJECT-TYPE-NORMALIZATION.json": {
            "summary": {"input_rows": 10, "tree_rows": 4, "blob_rows": 6},
            "safety": safety,
        },
        "09-STATIC-BEHAVIOR-SIGNATURES.json": {
            "behavior_equivalence_proven": False,
            "rows": [],
            "safety": safety,
        },
        "10-STRUCTURED-DATA-COVERAGE.json": {
            "rows": [],
            "safety": safety,
        },
        "11-RECOVERY-REACHABILITY-PROOF.json": {
            "object_recovery_proven": True,
            "full_runtime_rollback_proven": False,
            "missing_objects": [],
            "unreachable_objects": [],
            "safety": safety,
        },
        "12-HIGH-VALUE-REVIEW-QUEUE.json": {
            "queue_count": 6,
            "business_commercial_count": 2,
            "queue": [],
            "safety": safety,
        },
        "PHASE3-FORENSIC-EVIDENCE.json": {
            "schema": "raios.deep-legacy-forensic.phase3-evidence.v1",
            "status": "COMPLETE_EVIDENCE_VERIFIED",
            "object_recovery_proven": True,
            "behavior_equivalence_proven": False,
            "full_runtime_rollback_proven": False,
            "remaining_content_value_review_count": 6,
            "full_forensic_audit_complete": False,
            "safe_to_remove_source": safe,
            "next_required_phase": "TARGETED_HIGH_VALUE_BEHAVIOR_VALIDATION_AND_ASSIMILATION",
            "safety": safety,
        },
        "DELETE-ELIGIBILITY-REPORT.json": {
            "decision": "DENY" if not safe else "ALLOW",
            "safe_to_remove_source": safe,
        },
    }


def test_behavior_recovery_runs_read_only_without_seat(tmp_path):
    board, repo = make_behavior_board(tmp_path)
    source = repo / "historical-capability.txt"
    source.write_text("preserve", encoding="utf-8")
    before = source.read_bytes()
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        behavior_collector=lambda task: fake_behavior_package(task, safe=False),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE3")
    assert out["actions_processed"] == 1
    assert task["status"] == "DONE"
    assert task["executed_by"] == "RAIOS-SYSTEM-ACTION:DETERMINISTIC_BEHAVIOR_RECOVERY"
    assert source.read_bytes() == before
    proof = json.loads((repo / task["evidence"]).read_text(encoding="utf-8"))
    assert proof["object_recovery_proven"] is True
    assert proof["behavior_equivalence_proven"] is False
    assert proof["safe_to_remove_source"] is False


def test_behavior_recovery_rejects_safe_to_remove_true(tmp_path):
    board, repo = make_behavior_board(tmp_path)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        behavior_collector=lambda task: fake_behavior_package(task, safe=True),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE3")
    assert out["actions_blocked"] == 1
    assert task["status"] == "BLOCKED"
    assert "FORENSIC_PHASE3_FAIL_CLOSED_VIOLATION" in task["blocker"]


def test_behavior_recovery_waits_for_phase2_dependency(tmp_path):
    board, repo = make_behavior_board(tmp_path, phase2_done=False)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        behavior_collector=lambda task: fake_behavior_package(task, safe=False),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE3")
    assert out["actions_processed"] == 0
    assert task["status"] == "READY"


def make_commercial_board(tmp_path: Path, phase3_done: bool = True):
    repo = tmp_path / "Greeny-Life"
    (repo / ".ai-os/state").mkdir(parents=True)
    phase3 = {
        "id": "FORENSIC-PHASE3",
        "status": "DONE" if phase3_done else "READY",
        "dependencies": [],
    }
    phase4 = {
        "id": "FORENSIC-PHASE4",
        "title": "commercial revalidation",
        "status": "READY",
        "dependencies": ["FORENSIC-PHASE3"],
        "automation_action": "DEEP_LEGACY_COMMERCIAL_REVALIDATION",
        "dispatch_authorized_by": "C1",
        "destructive_action_requested": False,
    }
    (repo / ".ai-os/state/TASKS.json").write_text(
        json.dumps({"tasks": [phase3, phase4]}), encoding="utf-8"
    )
    return CouncilBoard(repo, tmp_path / "presence.json"), repo


def fake_commercial_package(_task, safe=False, promoted=False):
    safety = {
        "READ_ONLY_SOURCE_AUDIT": True,
        "DATABASE_WRITE": False,
        "CANONICAL_BUSINESS_DATA_MUTATION": False,
        "SOURCE_MUTATION": False,
        "RETIRED_REPAIR_TREE_READ": False,
        "SAFE_TO_REMOVE_SOURCE": safe,
    }
    return {
        "13-BUSINESS-COMMERCIAL-REVALIDATION.json": {
            "raw_business_commercial_rows": 83,
            "substantive_review_count": 29,
            "category_counts": {
                "PROVENANCE_OR_INVENTORY_EVIDENCE": 27,
                "STALE_SALVAGE_EVIDENCE_REQUIRES_REVALIDATION": 21,
                "CURRENT_CODE_SURFACE_PRESENT_STATIC_ONLY": 6,
            },
            "safety": safety,
        },
        "14-COMMERCIAL-DATA-RECOVERY-CANDIDATES.json": {
            "supplier_candidates": [{"historical_name": "Old Supplier"}],
            "customer_candidates": [{"historical_name": "Old Customer"}],
            "market_taxonomy_candidates": [{"historical_market_count": 7}],
            "database_write": False,
            "canonical_promotion_complete": promoted,
            "safety": safety,
        },
        "15-STALE-BUSINESS-SALVAGE-CERTIFICATION-AUDIT.json": {
            "certification": {
                "current_trust_classification": "STALE_NON_CANONICAL_EVIDENCE",
                "accepted_as_current_zero_gap_proof": False,
            },
            "safety": safety,
        },
        "16-COMMERCIAL-CAPABILITY-REVIEW-QUEUE.json": {
            "runtime_equivalence_proven": False,
            "knowledge_assimilation_complete": False,
            "safety": safety,
        },
        "PHASE4-FORENSIC-EVIDENCE.json": {
            "schema": "raios.deep-legacy-forensic.phase4-evidence.v1",
            "status": "COMPLETE_EVIDENCE_VERIFIED",
            "substantive_business_value_review_count": 29,
            "stale_zero_gap_certification_rejected": True,
            "canonical_promotion_complete": promoted,
            "business_value_zero_gap_proven": False,
            "full_forensic_audit_complete": False,
            "safe_to_remove_source": safe,
            "next_required_phase": "FOUNDER_GATED_COMMERCIAL_RECOVERY_VALIDATION_AND_PROMOTION",
            "safety": safety,
        },
        "DELETE-ELIGIBILITY-REPORT.json": {
            "decision": "DENY" if not safe else "ALLOW",
            "safe_to_remove_source": safe,
        },
    }


def test_commercial_revalidation_runs_read_only_without_seat(tmp_path):
    board, repo = make_commercial_board(tmp_path)
    source = repo / "commercial-source.txt"
    source.write_text("preserve", encoding="utf-8")
    before = source.read_bytes()
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        commercial_collector=lambda task: fake_commercial_package(
            task, safe=False, promoted=False
        ),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE4")
    assert out["actions_processed"] == 1, task.get("blocker")
    assert task["status"] == "DONE"
    assert task["executed_by"] == "RAIOS-SYSTEM-ACTION:DETERMINISTIC_COMMERCIAL_REVALIDATION"
    assert source.read_bytes() == before
    proof = json.loads((repo / task["evidence"]).read_text(encoding="utf-8"))
    assert proof["safe_to_remove_source"] is False
    assert proof["canonical_promotion_complete"] is False
    assert proof["stale_zero_gap_certification_rejected"] is True


def test_commercial_revalidation_rejects_delete_or_promotion_boundary_violation(tmp_path):
    board, repo = make_commercial_board(tmp_path)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        commercial_collector=lambda task: fake_commercial_package(
            task, safe=True, promoted=False
        ),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE4")
    assert out["actions_blocked"] == 1
    assert task["status"] == "BLOCKED"
    assert "FORENSIC_PHASE4_FAIL_CLOSED_VIOLATION" in task["blocker"]

    board2, repo2 = make_commercial_board(tmp_path / "promote")
    board2.actions = TaskActionExecutor(
        repo2,
        collector=lambda: {},
        prober=lambda world: [],
        commercial_collector=lambda task: fake_commercial_package(
            task, safe=False, promoted=True
        ),
    )
    out2 = board2.run_cycle(Worker())
    tasks2 = json.loads(board2.tasks.read_text(encoding="utf-8"))["tasks"]
    task2 = next(x for x in tasks2 if x["id"] == "FORENSIC-PHASE4")
    assert out2["actions_blocked"] == 1
    assert task2["status"] == "BLOCKED"
    assert "FORENSIC_PHASE4_PROMOTION_BOUNDARY_VIOLATION" in task2["blocker"]


def test_commercial_revalidation_waits_for_phase3_dependency(tmp_path):
    board, repo = make_commercial_board(tmp_path, phase3_done=False)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        commercial_collector=lambda task: fake_commercial_package(
            task, safe=False, promoted=False
        ),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE4")
    assert out["actions_processed"] == 0
    assert task["status"] == "READY"


def make_commercial_validation_board(tmp_path: Path, phase4_done: bool = True):
    repo = tmp_path / "Greeny-Life"
    (repo / ".ai-os/state").mkdir(parents=True)
    phase4 = {
        "id": "FORENSIC-PHASE4",
        "status": "DONE" if phase4_done else "READY",
        "dependencies": [],
    }
    phase5 = {
        "id": "FORENSIC-PHASE5",
        "status": "READY",
        "dependencies": ["FORENSIC-PHASE4"],
        "automation_action": "DEEP_LEGACY_COMMERCIAL_RECOVERY_VALIDATION",
        "dispatch_authorized_by": "C1",
        "destructive_action_requested": False,
    }
    (repo / ".ai-os/state/TASKS.json").write_text(
        json.dumps({"tasks": [phase4, phase5]}), encoding="utf-8"
    )
    return CouncilBoard(repo, tmp_path / "presence.json"), repo


def fake_commercial_validation_package(_task, safe=False, promoted=False, ready=0):
    safety = {
        "READ_ONLY_SOURCE_AUDIT": True,
        "DATABASE_WRITE": False,
        "CANONICAL_BUSINESS_DATA_MUTATION": False,
        "KNOWLEDGE_CANONICAL_PROMOTION": False,
        "SOURCE_MUTATION": False,
        "SAFE_TO_REMOVE_SOURCE": safe,
    }
    return {
        "17-COMMERCIAL-RECOVERY-PROVENANCE.json": {
            "path_lineage": [],
            "safety": safety,
        },
        "18-COMMERCIAL-DATA-VALIDATION-DECISIONS.json": {
            "supplier_decisions": [],
            "customer_decisions": [],
            "market_taxonomy_decisions": [],
            "promotion_ready_count": ready,
            "canonical_write_executed": False,
            "safety": safety,
        },
        "19-COMMERCIAL-KNOWLEDGE-LINEAGE.json": {
            "knowledge_lineages": [],
            "knowledge_assimilation_executed": False,
            "safety": safety,
        },
        "20-COMMERCIAL-CAPABILITY-VALIDATION-PLAN.json": {
            "executable_behavior_validation_required": [],
            "reference_not_executable_gap": [],
            "runtime_equivalence_proven": False,
            "safety": safety,
        },
        "PHASE5-FORENSIC-EVIDENCE.json": {
            "schema": "raios.deep-legacy-forensic.phase5-evidence.v1",
            "status": "COMPLETE_EVIDENCE_VERIFIED",
            "promotion_ready_count": ready,
            "canonical_promotion_complete": promoted,
            "business_value_zero_gap_proven": False,
            "full_forensic_audit_complete": False,
            "safe_to_remove_source": safe,
            "next_required_phase":
                "EXTERNAL_SOURCE_ENTITY_VALIDATION_AND_EXECUTABLE_BEHAVIOR_PROOF",
            "safety": safety,
        },
        "DELETE-ELIGIBILITY-REPORT.json": {
            "decision": "DENY",
            "safe_to_remove_source": safe,
        },
    }


def test_commercial_recovery_validation_runs_read_only_without_seat(tmp_path):
    board, repo = make_commercial_validation_board(tmp_path)
    source = repo / "historical-commercial.txt"
    source.write_text("preserve", encoding="utf-8")
    before = source.read_bytes()
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        commercial_validation_collector=lambda task:
            fake_commercial_validation_package(task),
    )
    out = board.run_cycle(Worker())
    tasks = json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
    task = next(x for x in tasks if x["id"] == "FORENSIC-PHASE5")
    assert out["actions_processed"] == 1, task.get("blocker")
    assert task["status"] == "DONE"
    assert task["executed_by"] == (
        "RAIOS-SYSTEM-ACTION:DETERMINISTIC_COMMERCIAL_RECOVERY_VALIDATION"
    )
    assert source.read_bytes() == before
    proof = json.loads((repo / task["evidence"]).read_text(encoding="utf-8"))
    assert proof["promotion_ready_count"] == 0
    assert proof["canonical_promotion_complete"] is False
    assert proof["safe_to_remove_source"] is False


def test_commercial_recovery_validation_fails_closed_on_unvalidated_promotion(tmp_path):
    board, repo = make_commercial_validation_board(tmp_path)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        commercial_validation_collector=lambda task:
            fake_commercial_validation_package(task, ready=1),
    )
    out = board.run_cycle(Worker())
    task = next(
        x for x in json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
        if x["id"] == "FORENSIC-PHASE5"
    )
    assert out["actions_blocked"] == 1
    assert task["status"] == "BLOCKED"
    assert "FORENSIC_PHASE5_UNVALIDATED_PROMOTION_CANDIDATE" in task["blocker"]


def test_commercial_recovery_validation_waits_for_phase4(tmp_path):
    board, repo = make_commercial_validation_board(tmp_path, phase4_done=False)
    board.actions = TaskActionExecutor(
        repo,
        collector=lambda: {},
        prober=lambda world: [],
        commercial_validation_collector=lambda task:
            fake_commercial_validation_package(task),
    )
    out = board.run_cycle(Worker())
    task = next(
        x for x in json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]
        if x["id"] == "FORENSIC-PHASE5"
    )
    assert out["actions_processed"] == 0
    assert task["status"] == "READY"
