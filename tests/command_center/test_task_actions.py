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
