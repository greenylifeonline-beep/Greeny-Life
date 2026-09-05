import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from src.raios.command_center import council_board
from src.raios.command_center.council_board import CouncilBoard

class Worker:
    def enqueue(self,sender,targets,text,task_id):
        self.call=(sender,targets,text,task_id)
        return {"message_id":"MSG-test"}

def setup(tmp_path):
    repo=tmp_path/"Greeny-Life";(repo/".ai-os/state").mkdir(parents=True)
    tasks={"tasks":[{"id":"DONE","title":"done","status":"DONE","dependencies":[]},
      {"id":"NEXT","title":"next","status":"READY","dependencies":["DONE"],
       "allowed_agents":["C2"],"claimed_by":None,"scope":["src"],
       "automatic_dispatch":True,"dispatch_authorized_by":"C1"}]}
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
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":expiry}}}),encoding="utf-8")
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
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":expiry}}}),encoding="utf-8")
    with pytest.raises(ValueError,match="TARGET_PRESENCE_EXPIRED"):
        board.dispatch("NEXT","C2",worker)

def test_pending_assignment_returns_when_presence_expires(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    board.dispatch("NEXT","C2",worker)
    past=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":past}}}),encoding="utf-8")
    out=board.snapshot()
    task=json.loads((repo/".ai-os/state/TASKS.json").read_text(encoding="utf-8"))["tasks"][1]
    assert out["returned_absent_assignments"]==1
    assert task["status"]=="READY" and "assigned_to" not in task
    assert task["dispatch_status"]=="RETURNED_ABSENT_WITH_CHECKPOINT"
    assert task["resume_checkpoint"]["phase"]=="INTERRUPTED"

def test_legacy_stale_claim_returns_to_ready_with_recovery_checkpoint(tmp_path):
    board,presence,repo=setup(tmp_path)
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    task=data["tasks"][1]
    task.update(status="IN_PROGRESS",claimed_by="C3")
    task.pop("automatic_dispatch",None);task.pop("dispatch_authorized_by",None)
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    presence.write_text(json.dumps({"seats":{}}),encoding="utf-8")
    out=board.snapshot()
    task=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert out["returned_absent_assignments"]==1
    assert task["status"]=="READY" and task["legacy_claim_reconciled"] is True
    assert task["dispatch_status"]=="RETURNED_ABSENT_WITH_CHECKPOINT"
    assert task["resume_checkpoint"]["blocker"]=="EXECUTOR_NOT_LIVE_BOUND_CONSUMER"


def test_automatic_cycle_dispatches_only_to_present_eligible_seat(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future},
                                                 "C3":{"presence":"ABSENT"}}}),encoding="utf-8")
    out=board.run_cycle(worker)
    task=json.loads((repo/".ai-os/state/TASKS.json").read_text(encoding="utf-8"))["tasks"][1]
    assert out["tasks_dispatched"]==1
    assert task["assigned_to"]=="C2" and task["dispatch_status"]=="PENDING_ACCEPTANCE"

def test_completion_report_requires_existing_evidence_and_closes_task(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
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
    locks=json.loads((repo/".ai-os/state/LOCKS.json").read_text(encoding="utf-8"))["locks"]
    owned=[x for x in locks if x.get("task_id")=="NEXT" and x.get("lock_kind")=="COUNCIL_TASK_SCOPE"]
    assert owned and all(x.get("status")=="RELEASED" for x in owned)

def test_completion_report_with_missing_evidence_is_rejected(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    board.run_cycle(worker)
    task=json.loads((board.tasks).read_text(encoding="utf-8"))["tasks"][1]
    board.accept_task("NEXT","C2",task["dispatch_id"])
    with pytest.raises(ValueError,match="EVIDENCE_NOT_FOUND"):
        board.submit_report("NEXT","C2","COMPLETE","unsupported",["missing.json"],
            ["claimed completion"],[],["validation claimed"],"Council review.")
    task=json.loads((board.tasks).read_text(encoding="utf-8"))["tasks"][1]
    assert task["status"]=="IN_PROGRESS"


def test_checkpoint_is_embedded_in_task_and_resumable(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,
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
        "C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future,"capabilities":["PYTHON"]},
        "C3":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future,"capabilities":["PYTHON"]}}}),
        encoding="utf-8")
    first=board.run_cycle(worker)
    task=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    board.accept_task("NEXT","C2",task["dispatch_id"])
    saved=board.submit_checkpoint("NEXT","C2","IN_PROGRESS","partial progress",
        ["step one"],["src/one.py"],["unit test PASS"],[],
        "Continue with step two.")
    past=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    presence.write_text(json.dumps({"seats":{
        "C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":past,"capabilities":["PYTHON"]},
        "C3":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future,"capabilities":["PYTHON"]}}}),
        encoding="utf-8")
    second=board.run_cycle(worker)
    task=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert first["tasks_dispatched"]==1 and second["tasks_returned_absent"]==1
    assert second["tasks_dispatched"]==1 and task["assigned_to"]=="C3"
    assert task["resume_checkpoint"]["checkpoint_id"]==saved["checkpoint_id"]
    assert "NEXT_STEP=Continue with step two." in worker.call[2]


def test_automatic_dispatch_requires_explicit_c1_authorization(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    tasks=json.loads(board.tasks.read_text(encoding="utf-8"))
    tasks["tasks"][1].pop("dispatch_authorized_by")
    board.tasks.write_text(json.dumps(tasks),encoding="utf-8")
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,
        "lease_expires_at":future}}}),encoding="utf-8")
    out=board.run_cycle(worker)
    task=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert out["tasks_dispatched"]==0
    assert task["status"]=="READY" and "assigned_to" not in task


def test_founder_gated_task_is_prepared_but_not_dispatched_without_c1_decision(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    data["tasks"][1]["requires_c1_decision"]=True
    data["tasks"][1]["founder_question"]="Approve governed execution?"
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT",
        "signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    out=board.run_cycle(worker)
    assert out["tasks_dispatched"]==0
    receipt=json.loads((board.receipts/"COORDINATION-LATEST.receipt.json").read_text(encoding="utf-8"))
    assert receipt["founder_brief"]["decision_count"]==1
    with pytest.raises(ValueError,match="FOUNDER_DECISION_REQUIRED"):
        board.dispatch("NEXT","C2",worker)
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    data["tasks"][1].update(founder_decision_status="APPROVED",founder_decision_by="C1")
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    assert board.dispatch("NEXT","C2",worker)["status"]=="DISPATCHED_PENDING_ACCEPTANCE"


def test_dispatch_rejects_unsigned_presence(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT",
        "signature_valid":False,"lease_expires_at":future}}}),encoding="utf-8")
    with pytest.raises(ValueError,match="TARGET_SIGNATURE_UNVERIFIED"):
        board.dispatch("NEXT","C2",worker)


def test_second_task_for_same_seat_is_rejected_as_busy(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    data["tasks"].append({"id":"SECOND","title":"second","status":"READY","dependencies":[],
        "allowed_agents":["C2"],"claimed_by":None,"scope":["docs"]})
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT",
        "signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    board.dispatch("NEXT","C2",worker)
    with pytest.raises(ValueError,match="TARGET_BUSY"):
        board.dispatch("SECOND","C2",worker)


def test_overlapping_active_scope_is_rejected_for_other_seat(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    data["tasks"].append({"id":"OVERLAP","title":"overlap","status":"READY","dependencies":[],
        "allowed_agents":["C3"],"claimed_by":None,"scope":["src/feature"]})
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{
        "C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future},
        "C3":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    board.dispatch("NEXT","C2",worker)
    with pytest.raises(ValueError,match="ACTIVE_SCOPE_CONFLICT"):
        board.dispatch("OVERLAP","C3",worker)


def test_active_canonical_lock_blocks_overlapping_dispatch(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT",
        "signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    (repo/".ai-os/state/LOCKS.json").write_text(json.dumps({"locks":[{
        "id":"LEGACY-ACTIVE","task_id":"OTHER","agent":"C9","scope":"src/core","status":"ACTIVE"
    }]}),encoding="utf-8")
    with pytest.raises(ValueError,match="ACTIVE_CANONICAL_LOCK_CONFLICT"):
        board.dispatch("NEXT","C2",worker)


def test_system_first_coordination_receipt_then_single_broadcast(tmp_path):
    repo=tmp_path/"Greeny-Life";(repo/".ai-os/state").mkdir(parents=True)
    (repo/".ai-os/state/TASKS.json").write_text(json.dumps({"tasks":[{
        "id":"SYS-COORD","status":"IN_PROGRESS","claimed_by":"CHATGPT-NORMAL",
        "scope":["src/raios/command_center"],"dispatch_status":"SYSTEM_FIRST_ACTIVE",
        "execution_proof":{"verified":True,"verified_at":datetime.now(timezone.utc).isoformat()}
    }]}),encoding="utf-8")
    (repo/".ai-os/state/LOCKS.json").write_text(json.dumps({"locks":[{
        "id":"L1","task_id":"SYS-COORD","agent":"CHATGPT-NORMAL","lease_holder":"CHATGPT-NORMAL",
        "scope":"src/raios/command_center","status":"ACTIVE"
    }]}),encoding="utf-8")
    presence=tmp_path/"presence.json";presence.write_text(json.dumps({"seats":{}}),encoding="utf-8")
    class Routes:
        def snapshot(self):
            return {"coordination_available":["C2","C6"],"auto_routable":["C6"],"seats":[]}
    class Recorder:
        def __init__(self):self.calls=[]
        def enqueue(self,sender,targets,text,task_id):
            self.calls.append((sender,targets,text,task_id))
            return {"message_id":"MSG-coord"}
    board=CouncilBoard(repo,presence,routes=Routes());worker=Recorder()
    first=board.run_cycle(worker);second=board.run_cycle(worker)
    receipt=json.loads((board.receipts/"COORDINATION-LATEST.receipt.json").read_text(encoding="utf-8"))
    assert first["coordination_changes"]==1 and second["coordination_changes"]==0
    assert receipt["truth_owner"]=="RAIOS_SYSTEM" and receipt["single_coordination_source"] is True
    assert receipt["active_work"][0]["actor"]=="CHATGPT-NORMAL"
    assert worker.calls[0][0]=="RAIOS-WORKER" and worker.calls[0][1]==["C2","C6"]
    assert "WORK_AUTHORITY=false" in worker.calls[0][2]


def test_worker_releases_stale_and_orphan_locks_but_keeps_current_verified_lock(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    data["tasks"].append({"id":"SYS","status":"IN_PROGRESS","claimed_by":"CHATGPT-NORMAL",
                          "dispatch_status":"SYSTEM_FIRST_ACTIVE","scope":["src/current"]})
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    (repo/".ai-os/state/LOCKS.json").write_text(json.dumps({"locks":[
        {"id":"L-CURRENT","task_id":"SYS","agent":"CHATGPT-NORMAL","scope":"src/current","status":"ACTIVE"},
        {"id":"L-STALE","task_id":"NEXT","agent":"C2","scope":"src","status":"ACTIVE"},
        {"id":"L-ORPHAN","task_id":"MISSING","agent":"C9","scope":"docs","status":"ACTIVE"}
    ]}),encoding="utf-8")
    out=board.run_cycle(worker)
    locks=json.loads((repo/".ai-os/state/LOCKS.json").read_text(encoding="utf-8"))["locks"]
    by={x["id"]:x for x in locks}
    assert out["locks_reconciled"]==2
    assert by["L-CURRENT"]["status"]=="ACTIVE"
    assert by["L-STALE"]["status"]=="RELEASED"
    assert by["L-ORPHAN"]["status"]=="RELEASED"
    receipt=json.loads((board.receipts/"LOCK-RECONCILIATION-LATEST.receipt.json").read_text(encoding="utf-8"))
    assert receipt["released_count"]==2


def test_auto_dispatch_uses_dependency_impact_priority(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    data["tasks"][1]["automatic_dispatch"]=False
    data["tasks"].extend([
        {"id":"HIGH","title":"unblocks child","status":"READY","dependencies":["DONE"],
         "allowed_agents":["C2"],"scope":["high"],"automatic_dispatch":True,
         "dispatch_authorized_by":"C1"},
        {"id":"LOW","title":"independent","status":"READY","dependencies":["DONE"],
         "allowed_agents":["C2"],"scope":["low"],"automatic_dispatch":True,
         "dispatch_authorized_by":"C1"},
        {"id":"CHILD","title":"child","status":"READY","dependencies":["HIGH"],
         "allowed_agents":["C2"],"scope":["child"]}
    ])
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT",
        "signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    out=board.run_cycle(worker)
    tasks={x["id"]:x for x in json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"]}
    assert out["tasks_dispatched"]==1
    assert tasks["HIGH"]["dispatch_status"]=="PENDING_ACCEPTANCE"
    assert "assigned_to" not in tasks["LOW"]


def test_atomic_falls_back_when_windows_pins_stable_task_name(tmp_path,monkeypatch):
 target=tmp_path/"TASKS.json"
 target.write_text('{"tasks":[]}',encoding="utf-8")
 monkeypatch.setattr(council_board.os,"replace",
  lambda *args: (_ for _ in ()).throw(PermissionError("stable name pinned")))
 monkeypatch.setattr(council_board.time,"sleep",lambda *_:None)
 council_board.atomic(target,{"tasks":[{"id":"T1"}]})
 assert json.loads(target.read_text(encoding="utf-8"))["tasks"][0]["id"]=="T1"
 assert list(tmp_path.glob("TASKS.json.*.tmp"))==[]


def test_manual_dispatch_blocks_destructive_task_until_deep_legacy_gate(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    task=data["tasks"][1]
    task.update(title="Delete old duplicate source",destructive_action_requested=True)
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT",
        "signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    with pytest.raises(ValueError,match="DEEP_LEGACY_FORENSIC_AUDIT_REQUIRED"):
        board.dispatch("NEXT","C2",worker)
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    data["tasks"][1]["deep_legacy_forensic_gate"]={
        "status":"PASS",
        "authorized_surface_census_complete":True,
        "hash_and_lineage_complete":True,
        "semantic_capability_extraction_complete":True,
        "data_schema_knowledge_extraction_complete":True,
        "current_vs_legacy_coverage_complete":True,
        "unique_value_extracted_merged_migrated_or_retained":True,
        "behavior_equivalence_or_superior_replacement_proven":True,
        "provenance_preserved":True,
        "recovery_or_rollback_proven":True,
        "safe_to_remove_source":True,
        "unknown_unclassified_unresolved_unique_value":0,
        "exact_redundancy":True,
        "standing_c1_duplicate_authority":True,
    }
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError,match="GLOBAL_LEGACY_DELETE_GATE_CLOSED"):
        board.dispatch("NEXT","C2",worker)
    board.foundation.write_text(json.dumps({"facts":{
        "DEEP_LEGACY_FORENSIC_AUDIT_PASS":True,
        "LEGACY_DELETE_ALLOWED":True,
        "SAFE_TO_REMOVE_SOURCE":True,
        "LEGACY_UNIQUE_VALUE_UNRESOLVED":0
    }}),encoding="utf-8")
    assert board.dispatch("NEXT","C2",worker)["status"]=="DISPATCHED_PENDING_ACCEPTANCE"


def test_accepted_task_returns_to_ready_when_first_work_proof_times_out(tmp_path):
    board,_,_=setup(tmp_path)
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    task=data["tasks"][1]
    accepted=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
    task.update(
        status="IN_PROGRESS",dispatch_status="ACCEPTED",
        assigned_to="C2",claimed_by="C2",dispatch_id="DSP-old",
        accepted_at=accepted,acceptance_fingerprint="ACC-old",
        acceptance_signature_mode="SESSION_BOUND_ATTENDANCE_FINGERPRINT",
        first_work_proof_timeout_seconds=60,
    )
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    board.locks.write_text(json.dumps({"locks":[{
        "id":"L1","task_id":"NEXT","status":"ACTIVE","scope":"src",
        "agent":"C2","lease_holder":"C2"
    }]}),encoding="utf-8")
    returned=board._reconcile_unproven_acceptances(data)
    assert returned==1
    saved=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert saved["status"]=="READY"
    assert saved["dispatch_status"]=="RETURNED_NO_FIRST_WORK_PROOF"
    assert saved["return_reason"]=="FIRST_WORK_PROOF_TIMEOUT"
    assert saved["last_acceptance_fingerprint"]=="ACC-old"
    assert "claimed_by" not in saved and "assigned_to" not in saved
    assert saved["last_system_recovery_checkpoint"]["phase"]=="ACCEPTED_NO_WORK_PROOF"
    locks=json.loads(board.locks.read_text(encoding="utf-8"))["locks"]
    assert locks[0]["status"]=="RELEASED"


def test_post_acceptance_work_proof_prevents_first_proof_return(tmp_path):
    board,_,_=setup(tmp_path)
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    task=data["tasks"][1]
    accepted=datetime.now(timezone.utc)-timedelta(minutes=10)
    task.update(
        status="IN_PROGRESS",dispatch_status="ACCEPTED",
        assigned_to="C2",claimed_by="C2",dispatch_id="DSP-proof",
        accepted_at=accepted.isoformat(),
        first_work_proof_timeout_seconds=60,
        work_proof_at=(accepted+timedelta(seconds=30)).isoformat(),
    )
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    assert board._reconcile_unproven_acceptances(data)==0
    saved=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert saved["status"]=="IN_PROGRESS"
    assert saved["dispatch_status"]=="ACCEPTED"


def test_unavailable_executor_returns_accepted_task_immediately(tmp_path):
    board,_,_=setup(tmp_path)
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    task=data["tasks"][1]
    task.update(
        status="IN_PROGRESS",dispatch_status="ACCEPTED",
        assigned_to="C2",claimed_by="C2",dispatch_id="DSP-no-executor",
        accepted_at=datetime.now(timezone.utc).isoformat(),
        acceptance_fingerprint="ACC-no-executor",
        executor_backend={
            "kind":"CURSOR_DESKTOP_BRIDGE",
            "state":"FEATURE_GATE_DISABLED",
            "verified":True,
            "reason":"CURSOR_PRODUCT_GATE_FALSE_AND_USER_SETTING_FALSE",
        },
    )
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    assert board._reconcile_unproven_acceptances(data)==1
    saved=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert saved["status"]=="READY"
    assert saved["return_reason"]=="EXECUTOR_BACKEND_UNAVAILABLE"
    assert saved["executor_backend_snapshot"]["state"]=="FEATURE_GATE_DISABLED"


def test_verified_unavailable_executor_backend_blocks_only_that_seat(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    task=data["tasks"][1]
    task["allowed_agents"]=["C2","C6"]
    task["executor_backends"]={
        "C2":{
            "kind":"CURSOR_DESKTOP_BRIDGE",
            "state":"FEATURE_GATE_DISABLED",
            "verified":True,
        }
    }
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    expiry=(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()
    presence.write_text(json.dumps({"seats":{
        "C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":expiry},
        "C6":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":expiry},
    }}),encoding="utf-8")
    with pytest.raises(ValueError,match="SEAT_NOT_ALLOWED_FOR_TASK"):
        board.dispatch("NEXT","C2",worker)
    out=board.dispatch("NEXT","C6",worker)
    assert out["status"]=="DISPATCHED_PENDING_ACCEPTANCE"
    assert out["target"]=="C6"
