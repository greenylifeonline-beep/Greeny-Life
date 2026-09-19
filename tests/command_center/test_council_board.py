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
    leases=[json.loads(x.read_text(encoding="utf-8")) for x in (repo/".ai-os/state/command-fabric/leases").glob("*.json")]
    owned=[x for x in leases if x.get("task_id")=="NEXT"]
    assert owned and all(x.get("state")=="RELEASED" for x in owned)

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


def test_expired_agent_lease_does_not_block_dispatch_and_new_lock_is_system_owned(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    past=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT",
        "signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    (repo/".ai-os/state/LOCKS.json").write_text(json.dumps({"locks":[{
        "id":"EXPIRED-ABSENT","task_id":"OTHER","agent":"C9","scope":"src",
        "status":"ACTIVE","expires_at":past,"owner":"RAIOS_SYSTEM"
    }]}),encoding="utf-8")
    out=board.dispatch("NEXT","C2",worker)
    assert out["status"]=="DISPATCHED_PENDING_ACCEPTANCE"
    locks=json.loads((repo/".ai-os/state/LOCKS.json").read_text(encoding="utf-8"))["locks"]
    assert not [x for x in locks if x.get("lock_kind")=="COUNCIL_TASK_SCOPE"]
    leases=[json.loads(x.read_text(encoding="utf-8")) for x in (repo/".ai-os/state/command-fabric/leases").glob("*.json")]
    acquired=[x for x in leases if x.get("task_id")=="NEXT" and x.get("state")=="ACTIVE"]
    assert acquired and all(x.get("owner")=="C2" and x.get("expires_at") for x in acquired)
    expired=[x for x in locks if x.get("id")=="EXPIRED-ABSENT"][0]
    assert expired["status"]=="ACTIVE"


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


def test_snapshot_v2_projects_live_work_fields_and_rejects_now_md_authority(tmp_path):
    board,_,_=setup(tmp_path)
    data=json.loads(board.tasks.read_text(encoding="utf-8"))
    task=data["tasks"][1]
    task.update(
        model="qwen-test",started_at="2026-09-06T00:00:00+00:00",
        review_by=["C7","C3"],review_status="PENDING_REVIEW",
        next_step="prove runtime",blocker=None,
    )
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    out=board.snapshot();row=next(x for x in out["tasks"] if x["id"]=="NEXT")
    assert out["schema"]=="raios.council-board.v2"
    assert out["legacy_now_md_authoritative"] is False
    assert out["now_ne_full_ledger"] is True
    assert isinstance(out["now"], list)
    assert out["projection_sources"]==["TASKS","PRESENCE","TASK_CHECKPOINTS","RECEIPTS","EVIDENCE"]
    assert row["stage"]=="NEXT" and row["model"]=="qwen-test"
    assert row["reviewer"]==["C7","C3"] and row["review_status"]=="PENDING_REVIEW"
    assert row["next_checkpoint"]=="prove runtime" and row["blocker"] is None


def test_pending_acceptance_times_out_and_returns_to_ready(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    out=board.dispatch("NEXT","C2",worker)
    data=json.loads(board.tasks.read_text(encoding="utf-8"));task=data["tasks"][1]
    task["dispatched_at"]=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat();task["acceptance_timeout_seconds"]=60
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    assert board._reconcile_pending_acceptances(data)==1
    saved=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert saved["status"]=="READY" and saved["dispatch_status"]=="RETURNED_NO_ACCEPTANCE"
    assert saved["return_reason"]=="ACCEPTANCE_TIMEOUT" and "assigned_to" not in saved
    assert saved["last_dispatch_id"]==out["dispatch_id"]
    assert saved["last_system_recovery_checkpoint"]["phase"]=="PENDING_ACCEPTANCE_TIMEOUT"

def test_pending_acceptance_younger_than_timeout_is_unchanged(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    board.dispatch("NEXT","C2",worker);data=json.loads(board.tasks.read_text(encoding="utf-8"))
    assert board._reconcile_pending_acceptances(data)==0
    saved=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert saved["dispatch_status"]=="PENDING_ACCEPTANCE" and saved["assigned_to"]=="C2"

def test_pending_acceptance_missing_timestamp_fails_closed(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    board.dispatch("NEXT","C2",worker);data=json.loads(board.tasks.read_text(encoding="utf-8"));task=data["tasks"][1];task.pop("dispatched_at",None)
    assert board._reconcile_pending_acceptances(data)==0
    assert task["acceptance_reconcile_state"]=="MISSING_DISPATCHED_AT" and task["assigned_to"]=="C2"

def test_expired_pending_assignment_redispatches_same_cycle(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    board.dispatch("NEXT","C2",worker);data=json.loads(board.tasks.read_text(encoding="utf-8"));task=data["tasks"][1]
    task["dispatched_at"]=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat();task["acceptance_timeout_seconds"]=60
    board.tasks.write_text(json.dumps(data),encoding="utf-8")
    out=board.run_cycle(worker);saved=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert out["tasks_returned_unaccepted"]==1 and out["tasks_dispatched"]==1
    assert saved["dispatch_status"]=="PENDING_ACCEPTANCE" and saved["assigned_to"]=="C2"

def test_acceptance_timeout_override_has_30_second_floor(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    board.dispatch("NEXT","C2",worker);data=json.loads(board.tasks.read_text(encoding="utf-8"));task=data["tasks"][1]
    task["acceptance_timeout_seconds"]=1;task["dispatched_at"]=(datetime.now(timezone.utc)-timedelta(seconds=20)).isoformat()
    assert board._reconcile_pending_acceptances(data)==0
    task["dispatched_at"]=(datetime.now(timezone.utc)-timedelta(seconds=31)).isoformat()
    assert board._reconcile_pending_acceptances(data)==1
    saved=json.loads(board.tasks.read_text(encoding="utf-8"))["tasks"][1]
    assert saved["acceptance_timeout_seconds_applied"]==30


class AttentionRoutes:
    def __init__(self,session="S1",current=True):self.session=session;self.current=current
    def snapshot(self):
        return {"seats":[{"seat":"C2","session_id":self.session,"consumer_current":self.current,"auto_routable":self.current}]}

class PulseWorker:
    def __init__(self):self.calls=[]
    def enqueue(self,sender,targets,text,task_id=None,*args,**kwargs):
        self.calls.append((sender,targets,text,task_id));return {"message_id":f"MSG-pulse-{len(self.calls)}"}

def attention_evidence(board,repo,mid="MSG-1000000000000000-abcdef01",*,task_id=None,
                       actor=False,synthetic=False,session="S1",action_required=False,
                       response_required=False,age=20):
    now=datetime.now(timezone.utc);sent=(now-timedelta(seconds=age+1)).isoformat();delivered=(now-timedelta(seconds=age)).isoformat()
    payload={"text":"NOTICE","to":["C2"],"task_id":task_id,"action_required":action_required,"response_required":response_required}
    inbox=repo/".ai-os/state/command-fabric/inbox";inbox.mkdir(parents=True,exist_ok=True)
    (inbox/f"{mid}.json").write_text(json.dumps({"schema":"raios.message.v1","message_id":mid,"payload":payload,"created_at":sent}),encoding="utf-8")
    board.receipts.mkdir(parents=True,exist_ok=True)
    (board.receipts/f"{mid}.send.json").write_text(json.dumps({"message_id":mid,"event":"SENT","at":sent,"targets":["C2"]}),encoding="utf-8")
    (board.receipts/f"{mid}.C2.delivery.ack.receipt.json").write_text(json.dumps({"message_id":mid,"ack_type":"DELIVERY_ACK","at":delivered}),encoding="utf-8")
    if actor:
        (board.receipts/f"{mid}.C2.actor.ack.receipt.json").write_text(json.dumps({"schema":"raios.actor-ack.v1","message_id":mid,"seat":"C2","target":"C2","ack_type":"ACTOR_ACK","status":"READ","at":now.isoformat(),"synthetic":synthetic,"session_id":session,"task_id":task_id}),encoding="utf-8")
    return mid

def test_attention_delivery_without_actor_ack_remains_open_and_pulses(tmp_path):
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker()
    mid=attention_evidence(board,repo,age=20)
    out=board._attention_followup_cycle(worker);state=board.attention_snapshot(mid)["states"][0]
    assert state["lifecycle_state"]=="DELIVERED" and state["terminal_state"] is None
    assert out["attention_pulses"]==1 and "ATTENTION_PULSE" in worker.calls[-1][2]
    assert len(board._attention_pulse_rows(mid,"C2","ATTENTION_PULSE"))==1

def test_genuine_current_session_actor_ack_closes_notice_only(tmp_path):
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker()
    mid=attention_evidence(board,repo,actor=True)
    board._attention_followup_cycle(worker);state=board.attention_snapshot(mid)["states"][0]
    assert state["attention_ack_at"] and state["terminal_state"]=="ACKNOWLEDGED_NO_ACTION"
    assert not worker.calls

def test_synthetic_or_stale_session_ack_never_closes_attention(tmp_path):
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker()
    mid=attention_evidence(board,repo,actor=True,synthetic=True,age=20)
    board._attention_followup_cycle(worker);state=board.attention_snapshot(mid)["states"][0]
    assert state["attention_ack_at"] is None and state["terminal_state"] is None
    mid2=attention_evidence(board,repo,mid="MSG-1000000000000001-abcdef02",actor=True,session="OLD",age=20)
    board._attention_followup_cycle(worker);state2=board.attention_snapshot(mid2)["states"][0]
    assert state2["attention_ack_at"] is None

def test_action_required_message_remains_open_after_read(tmp_path):
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker()
    mid=attention_evidence(board,repo,actor=True,action_required=True)
    board._attention_followup_cycle(worker);state=board.attention_snapshot(mid)["states"][0]
    assert state["lifecycle_state"]=="ATTENTION_ACKNOWLEDGED" and state["terminal_state"] is None

def test_task_attention_transitions_accept_work_checkpoint_done_blocked(tmp_path):
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker();mid=attention_evidence(board,repo,task_id="NEXT",actor=True)
    data=json.loads(board.tasks.read_text(encoding="utf-8"));task=data["tasks"][1]
    task.update(status="IN_PROGRESS",dispatch_status="ACCEPTED",assigned_to="C2",claimed_by="C2",accepted_at=datetime.now(timezone.utc).isoformat())
    board.tasks.write_text(json.dumps(data),encoding="utf-8");board._attention_followup_cycle(worker)
    assert board.attention_snapshot(mid)["states"][0]["lifecycle_state"]=="TASK_ACCEPTED"
    data=json.loads(board.tasks.read_text(encoding="utf-8"));task=data["tasks"][1];task.update(dispatch_status="CHECKPOINT_SAVED",checkpoint_updated_at=datetime.now(timezone.utc).isoformat(),resume_checkpoint={"checkpoint_id":"CHK-x","created_at":datetime.now(timezone.utc).isoformat()});board.tasks.write_text(json.dumps(data),encoding="utf-8")
    board.attention_cursor.write_text(json.dumps({"head":board._head(),"after":""}),encoding="utf-8");board._attention_followup_cycle(worker)
    assert board.attention_snapshot(mid)["states"][0]["lifecycle_state"]=="WORKING"
    data=json.loads(board.tasks.read_text(encoding="utf-8"));data["tasks"][1]["status"]="DONE";board.tasks.write_text(json.dumps(data),encoding="utf-8");board.attention_cursor.write_text(json.dumps({"head":board._head(),"after":""}),encoding="utf-8");board._attention_followup_cycle(worker)
    assert board.attention_snapshot(mid)["states"][0]["terminal_state"]=="COMPLETED"
    data=json.loads(board.tasks.read_text(encoding="utf-8"));data["tasks"][1]["status"]="BLOCKED";data["tasks"][1]["blocker"]="X";board.tasks.write_text(json.dumps(data),encoding="utf-8");board.attention_cursor.write_text(json.dumps({"head":board._head(),"after":""}),encoding="utf-8");board._attention_followup_cycle(worker)
    assert board.attention_snapshot(mid)["states"][0]["terminal_state"]=="BLOCKED"

def test_attention_backoff_and_no_pulse_before_due_or_after_terminal(tmp_path):
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker();mid=attention_evidence(board,repo,age=5)
    board._attention_followup_cycle(worker);assert not worker.calls
    state=board.attention_snapshot(mid)["states"][0];base=board._attention_dt(state["delivery_ack_at"]);due=board._attention_dt(state["next_attention_at"])
    assert int((due-base).total_seconds())==10
    for i,sec in enumerate((10,30,60,120),1):
        board._attention_event(mid,"C2","ATTENTION_PULSE",pulse_count=i,reason="test")
        rebuilt=board._attention_rebuild(mid,"C2",{},board._attention_routes());delta=int((board._attention_dt(rebuilt["next_attention_at"])-base).total_seconds())
        assert delta==(30,60,120,300)[i-1]
    board.routes=AttentionRoutes();attention_evidence(board,repo,mid=mid,actor=True)
    rebuilt=board._attention_rebuild(mid,"C2",{},board._attention_routes());assert rebuilt["terminal_state"]=="ACKNOWLEDGED_NO_ACTION"
    assert board._attention_maybe_pulse(rebuilt,worker) is None

def test_progress_pulse_only_when_stale_and_recent_checkpoint_suppresses(tmp_path,monkeypatch):
    monkeypatch.setattr(council_board,"ATTENTION_PROGRESS_STALE_SECONDS",30)
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker();mid=attention_evidence(board,repo,task_id="NEXT",actor=True)
    data=json.loads(board.tasks.read_text(encoding="utf-8"));task=data["tasks"][1];old=(datetime.now(timezone.utc)-timedelta(seconds=40)).isoformat();task.update(status="IN_PROGRESS",dispatch_status="CHECKPOINT_SAVED",assigned_to="C2",claimed_by="C2",accepted_at=old,checkpoint_updated_at=old,resume_checkpoint={"checkpoint_id":"CHK-old","created_at":old});board.tasks.write_text(json.dumps(data),encoding="utf-8")
    board._attention_followup_cycle(worker);assert any("PROGRESS_PULSE" in c[2] for c in worker.calls)
    worker.calls.clear();data=json.loads(board.tasks.read_text(encoding="utf-8"));now=datetime.now(timezone.utc).isoformat();data["tasks"][1]["checkpoint_updated_at"]=now;data["tasks"][1]["resume_checkpoint"]["created_at"]=now;board.tasks.write_text(json.dumps(data),encoding="utf-8");board.attention_cursor.write_text(json.dumps({"head":board._head(),"after":""}),encoding="utf-8");board._attention_followup_cycle(worker)
    assert not any("PROGRESS_PULSE" in c[2] for c in worker.calls)

def test_runtime_state_missing_corrupt_or_head_mismatch_reconciles_from_receipts(tmp_path):
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker();mid=attention_evidence(board,repo,actor=True)
    board.attention_cursor.write_text('{bad',encoding='utf-8');board._attention_followup_cycle(worker)
    state=board.attention_snapshot(mid)["states"][0];assert state["reconciled_from_durable_evidence"] is True
    path=board.attention_runtime/f"{mid}.C2.json";path.unlink();board.attention_cursor.write_text(json.dumps({"head":"WRONG","after":"ZZZ"}),encoding="utf-8");board._attention_followup_cycle(worker)
    assert board.attention_snapshot(mid)["states"][0]["terminal_state"]=="ACKNOWLEDGED_NO_ACTION"

def test_duplicate_cycles_and_duplicate_actor_ack_are_idempotent(tmp_path):
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker();mid=attention_evidence(board,repo,actor=True)
    for _ in range(2):board.attention_cursor.write_text(json.dumps({"head":board._head(),"after":""}),encoding="utf-8");board._attention_followup_cycle(worker)
    events=[load for load in board.receipts.glob("ATN-*.C2.attention-acknowledged.receipt.json") if json.loads(load.read_text(encoding="utf-8")).get("message_id")==mid]
    assert len(events)==1 and board.attention_snapshot(mid)["count"]==1

def test_attention_cycle_is_bounded_and_never_tracks_its_own_pulse(tmp_path,monkeypatch):
    monkeypatch.setattr(council_board,"ATTENTION_MAX_ITEMS",3);monkeypatch.setattr(council_board,"ATTENTION_MAX_SECONDS",1.0)
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker()
    for i in range(8):attention_evidence(board,repo,mid=f"MSG-10000000000000{i:02d}-abcdef{i:02d}",age=1)
    out=board._attention_followup_cycle(worker);assert out["attention_items_processed"]<=3
    mid="MSG-1999999999999999-pulse000";attention_evidence(board,repo,mid=mid,age=30)
    msg=repo/".ai-os/state/command-fabric/inbox"/f"{mid}.json";d=json.loads(msg.read_text(encoding="utf-8"));d["payload"]["text"]="ATTENTION_PULSE\nWORK_AUTHORITY=false";msg.write_text(json.dumps(d),encoding="utf-8")
    assert board._attention_rebuild(mid,"C2",{},board._attention_routes()) is None

def test_attention_budget_never_starves_first_durable_message(tmp_path,monkeypatch):
    monkeypatch.setattr(council_board,"ATTENTION_MAX_SECONDS",0.05)
    board,_,repo=setup(tmp_path);board.routes=AttentionRoutes();worker=PulseWorker()
    mid=attention_evidence(board,repo,age=20)
    real=board._attention_routes
    def slow_routes():
        import time as _time
        _time.sleep(0.08)
        return real()
    monkeypatch.setattr(board,"_attention_routes",slow_routes)
    out=board._attention_followup_cycle(worker)
    assert out["attention_items_processed"]>=1
    state=board.attention_snapshot(mid)["states"][0]
    assert state["lifecycle_state"]=="DELIVERED"

def test_attention_contract_creates_no_second_worker_or_transport(tmp_path):
    board,_,_=setup(tmp_path)
    assert board.attention_runtime.name=="attention"
    assert not hasattr(board,"attention_worker") and not hasattr(board,"attention_transport")
    assert board.fabric==board.repo/".ai-os/state/command-fabric"


def test_new_dispatch_uses_command_fabric_lease_not_new_council_task_scope_lock(tmp_path):
    board,presence,repo=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    before=json.loads(board.locks.read_text(encoding="utf-8")).get("locks",[]) if board.locks.exists() else []
    out=board.dispatch("NEXT","C2",worker)
    after=json.loads(board.locks.read_text(encoding="utf-8")).get("locks",[]) if board.locks.exists() else []
    assert after==before
    lease_files=list((repo/".ai-os/state/command-fabric/leases").glob("*.json"))
    assert lease_files
    leases=[json.loads(x.read_text(encoding="utf-8")) for x in lease_files]
    owned=[x for x in leases if x.get("task_id")=="NEXT" and x.get("state")=="ACTIVE"]
    assert owned and all(x.get("owner")=="C2" for x in owned)
    assert out.get("scope_lease_ids")==[x["lease_id"] for x in owned]


def test_task3_dispatch_rejects_route_identity_session_substitution(tmp_path):
    board,presence,_=setup(tmp_path);worker=Worker()
    future=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
    presence.write_text(json.dumps({"seats":{"C2":{"presence":"PRESENT","signature_valid":True,"lease_expires_at":future}}}),encoding="utf-8")
    class SubstitutedRoutes:
        def snapshot(self):
            return {"seats":[{"seat":"C2","auto_routable":True,"binding_current":True,"consumer_current":True,
                "actor_id":"ACTOR-A","session_id":"SESSION-A","device_id":"AG",
                "consumer_actor_id":"ACTOR-B","consumer_session_id":"SESSION-B","consumer_device_id":"AG"}],
                "auto_routable":["C2"],"coordination_available":["C2"]}
    board.routes=SubstitutedRoutes()
    with pytest.raises(ValueError,match="TARGET_NOT_LIVE_BOUND_CONSUMER"):
        board.dispatch("NEXT","C2",worker)
