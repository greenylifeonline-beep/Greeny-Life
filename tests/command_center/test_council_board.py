import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from src.raios.command_center.council_board import CouncilBoard

class Worker:
    def enqueue(self,sender,targets,text,task_id):
        self.call=(sender,targets,text,task_id)
        return {"message_id":"MSG-test"}

def setup(tmp_path):
    repo=tmp_path/"Greeny-Life";(repo/".ai-os/state").mkdir(parents=True)
    tasks={"tasks":[{"id":"DONE","title":"done","status":"DONE","dependencies":[]},
      {"id":"NEXT","title":"next","status":"READY","dependencies":["DONE"],
       "allowed_agents":["C2"],"claimed_by":None,"scope":["src"]}]}
    (repo/".ai-os/state/TASKS.json").write_text(json.dumps(tasks),encoding="utf-8")
    presence=tmp_path/"presence.json"
    return CouncilBoard(repo,presence),presence,repo

def test_board_classifies_done_ready_and_next(tmp_path):
    board,_,_=setup(tmp_path);out=board.snapshot()
    assert out["summary"]["DONE"]==1
    assert out["summary"]["READY"]==1
    assert out["summary"]["NEXT"]==1
    assert out["single_task_ledger"] is True

def test_dispatch_requires_live_present_target(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    with pytest.raises(ValueError,match="TARGET_NOT_PRESENT"):
        board.dispatch("NEXT","C2",worker)
    expiry=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","lease_expires_at":expiry}}}),encoding="utf-8")
    out=board.dispatch("NEXT","C2",worker)
    assert out["status"]=="DISPATCHED_PENDING_ACCEPTANCE"
    assert worker.call[0]=="RAIOS-WORKER"
    assert worker.call[1]==["C2"]

def test_dispatch_rejects_expired_presence(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    expiry=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","lease_expires_at":expiry}}}),encoding="utf-8")
    with pytest.raises(ValueError,match="TARGET_PRESENCE_EXPIRED"):
        board.dispatch("NEXT","C2",worker)

def test_pending_assignment_returns_when_presence_expires(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","lease_expires_at":future}}}),encoding="utf-8")
    board.dispatch("NEXT","C2",worker)
    past=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","lease_expires_at":past}}}),encoding="utf-8")
    out=board.snapshot()
    task=json.loads((repo/".ai-os/state/TASKS.json").read_text(encoding="utf-8"))["tasks"][1]
    assert out["returned_absent_assignments"]==1
    assert task["status"]=="READY" and "assigned_to" not in task
    assert task["dispatch_status"]=="RETURNED_ABSENT"
