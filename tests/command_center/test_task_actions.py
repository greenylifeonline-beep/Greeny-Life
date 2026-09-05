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
