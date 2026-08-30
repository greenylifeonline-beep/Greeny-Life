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
    accepted=board.accept_task("NEXT","C2",out["dispatch_id"])
    task=json.loads((board.tasks).read_text(encoding="utf-8"))["tasks"][1]
    assert accepted["status"]=="ACCEPTED"
    assert task["status"]=="IN_PROGRESS" and task["claimed_by"]=="C2"

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
    assert task["dispatch_status"]=="RETURNED_ABSENT_WITH_CHECKPOINT"
    assert task["resume_checkpoint"]["phase"]=="INTERRUPTED"

def test_automatic_cycle_dispatches_only_to_present_eligible_seat(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","lease_expires_at":future},
                                                 "C3":{"presence":"ABSENT"}}}),encoding="utf-8")
    out=board.run_cycle(worker)
    task=json.loads((repo/".ai-os/state/TASKS.json").read_text(encoding="utf-8"))["tasks"][1]
    assert out["tasks_dispatched"]==1
    assert task["assigned_to"]=="C2" and task["dispatch_status"]=="PENDING_ACCEPTANCE"

def test_completion_report_requires_existing_evidence_and_closes_task(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","lease_expires_at":future}}}),encoding="utf-8")
    board.run_cycle(worker)
    task=json.loads((repo/".ai-os/state/TASKS.json").read_text(encoding="utf-8"))["tasks"][1]
    board.accept_task("NEXT","C2",task["dispatch_id"])
    evidence=repo/"proof.json";evidence.write_text('{"pass":true}',encoding="utf-8")
    queued=board.submit_report("NEXT","C2","COMPLETE","implemented and verified",
        ["proof.json"],["implementation complete"],["src/feature.py"],["pytest PASS"],
        "Council review and release the next dependent task.")
    out=board.run_cycle(worker)
    task=json.loads((repo/".ai-os/state/TASKS.json").read_text(encoding="utf-8"))["tasks"][1]
    assert queued["status"]=="REPORT_QUEUED" and out["reports_processed"]==1
    assert task["status"]=="DONE" and task["dispatch_status"]=="COMPLETE_EVIDENCE_VERIFIED"

def test_completion_report_with_missing_evidence_is_rejected(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","lease_expires_at":future}}}),encoding="utf-8")
    board.run_cycle(worker)
    task=json.loads((board.tasks).read_text(encoding="utf-8"))["tasks"][1]
    board.accept_task("NEXT","C2",task["dispatch_id"])
    board.submit_report("NEXT","C2","COMPLETE","unsupported",["missing.json"],
        ["claimed completion"],[],[],"Council review.")
    out=board.run_cycle(worker)
    assert out["reports_rejected"]==1
    rejected=list(board.report_rejected.glob("RPT-*.json"))
    assert len(rejected)==1 and "EVIDENCE_NOT_FOUND" in rejected[0].read_text(encoding="utf-8")


def test_checkpoint_is_embedded_in_task_and_resumable(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT",
        "lease_expires_at":future,"capabilities":["PYTHON"]}}}),encoding="utf-8")
    dispatched=board.dispatch("NEXT","C2",worker)
    board.accept_task("NEXT","C2",dispatched["dispatch_id"])
    evidence=repo/"checkpoint-proof.json"
    evidence.write_text('{"checkpoint":true}',encoding="utf-8")
    saved=board.submit_checkpoint("NEXT","C2","IN_PROGRESS","worker continuity fixed",
        ["atomic writer implemented"],["src/raios/command_center/message_worker.py"],
        ["targeted test PASS"],["checkpoint-proof.json"],
        "Restart the service and execute a live delivery probe.")
    resumed=board.resume_checkpoint("NEXT")
    task=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert saved["status"]=="SAVED"
    assert resumed["resume_checkpoint"]["checkpoint_id"]==saved["checkpoint_id"]
    assert task["resume_checkpoint"]["next_step"].startswith("Restart")
    assert resumed["single_task_ledger"] is True


def test_absent_executor_is_reassigned_by_capability_from_checkpoint(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    tasks=json.loads(board.tasks.read_text(encoding="utf-8"))
    tasks["tasks"][1]["allowed_agents"]=["C2","C3"]
    tasks["tasks"][1]["required_capabilities"]=["PYTHON"]
    board.tasks.write_text(json.dumps(tasks),encoding="utf-8")
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{
        "C2":{"presence":"PRESENT","lease_expires_at":future,"capabilities":["PYTHON"]},
        "C3":{"presence":"PRESENT","lease_expires_at":future,"capabilities":["PYTHON"]}}}),
        encoding="utf-8")
    first=board.run_cycle(worker)
    task=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    board.accept_task("NEXT","C2",task["dispatch_id"])
    saved=board.submit_checkpoint("NEXT","C2","IN_PROGRESS","partial progress",
        ["step one"],["src/one.py"],["unit test PASS"],[],
        "Continue with step two.")
    past=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    presence.write_text(json.dumps({"seats":{
        "C2":{"presence":"PRESENT","lease_expires_at":past,"capabilities":["PYTHON"]},
        "C3":{"presence":"PRESENT","lease_expires_at":future,"capabilities":["PYTHON"]}}}),
        encoding="utf-8")
    second=board.run_cycle(worker)
    task=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert first["tasks_dispatched"]==1 and second["tasks_returned_absent"]==1
    assert second["tasks_dispatched"]==1 and task["assigned_to"]=="C3"
    assert task["resume_checkpoint"]["checkpoint_id"]==saved["checkpoint_id"]
    assert "NEXT_STEP=Continue with step two." in worker.call[2]
