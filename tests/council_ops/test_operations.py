import json
from pathlib import Path
import pytest
from raios.council_ops import CouncilConflict, CouncilOperations, CouncilValidationError

def auth(seat):
 return {"seat_id":seat,"SIGNATURE_VALID":True,"ISSUER_IDENTIFIED":True,"ISSUER_TRUSTED":True,
  "PRINCIPAL_BOUND":True,"AUTHORITY_SOURCE_PROVENANCE":{"issuer":"test","principal":seat}}
def setup(tmp_path):
 repo=tmp_path/"repo"; (repo/".ai-os/state").mkdir(parents=True)
 tasks={"tasks":[{"id":"T1","scope":["src/one"],"dependencies":[],"allowed_agents":["C1","C2"],"status":"READY","claimed_by":None}]}
 locks={"locks":[]}
 (repo/".ai-os/state/TASKS.json").write_text(json.dumps(tasks),encoding="utf-8")
 (repo/".ai-os/state/LOCKS.json").write_text(json.dumps(locks),encoding="utf-8")
 return CouncilOperations(repo,tmp_path/"runtime"),repo

def test_check_in_is_authenticated_and_idempotent(tmp_path):
 op,_=setup(tmp_path)
 with pytest.raises(CouncilValidationError): op.check_in(seat="C1",auth={},idem="x")
 first=op.check_in(seat="C1",auth=auth("C1"),idem="in-c1")
 again=op.check_in(seat="C1",auth=auth("C1"),idem="in-c1")
 assert first["presence"]=="PRESENT" and again["status"]=="ALREADY_APPLIED"
 assert Path(first["receipt"]).is_file()

def test_idempotency_key_cannot_change_meaning(tmp_path):
 op,_=setup(tmp_path); op.check_in(seat="C1",auth=auth("C1"),idem="same")
 with pytest.raises(CouncilConflict,match="IDEMPOTENCY_CONFLICT"):
  op.message(from_seat="C1",to_seat="ALL",task_id="T1",text="x",auth=auth("C1"),idem="same")

def test_claim_reuses_tasks_and_blocks_lock_overlap(tmp_path):
 op,repo=setup(tmp_path); op.check_in(seat="C1",auth=auth("C1"),idem="in")
 locks={"locks":[{"id":"L1","agent":"C7","scope":"src","status":"ACTIVE"}]}
 (repo/".ai-os/state/LOCKS.json").write_text(json.dumps(locks),encoding="utf-8")
 with pytest.raises(CouncilConflict,match="LOCK_CONFLICT"): op.claim(seat="C1",task_id="T1",auth=auth("C1"),idem="claim")
 locks["locks"][0]["status"]="RELEASED"; (repo/".ai-os/state/LOCKS.json").write_text(json.dumps(locks),encoding="utf-8")
 assert op.claim(seat="C1",task_id="T1",auth=auth("C1"),idem="claim")["status"]=="CLAIMED"
 assert json.loads((repo/".ai-os/state/TASKS.json").read_text())["tasks"][0]["claimed_by"]=="C1"

def test_handoff_requires_presence_and_owner(tmp_path):
 op,repo=setup(tmp_path); op.check_in(seat="C1",auth=auth("C1"),idem="i1")
 op.claim(seat="C1",task_id="T1",auth=auth("C1"),idem="c1")
 with pytest.raises(CouncilConflict,match="DESTINATION_NOT_PRESENT"):
  op.handoff(from_seat="C1",to_seat="C2",task_id="T1",auth=auth("C1"),idem="h1",evidence=[])
 op.check_in(seat="C2",auth=auth("C2"),idem="i2")
 out=op.handoff(from_seat="C1",to_seat="C2",task_id="T1",auth=auth("C1"),idem="h1",evidence=["proof"])
 assert out["status"]=="HANDED_OFF"
 assert json.loads((repo/".ai-os/state/TASKS.json").read_text())["tasks"][0]["claimed_by"]=="C2"

def test_checkout_requires_handoff_for_active_task(tmp_path):
 op,_=setup(tmp_path); op.check_in(seat="C1",auth=auth("C1"),idem="i"); op.claim(seat="C1",task_id="T1",auth=auth("C1"),idem="c")
 with pytest.raises(CouncilConflict,match="ACTIVE_TASKS_REQUIRE_HANDOFF"):
  op.check_out(seat="C1",auth=auth("C1"),idem="o")
 assert op.check_out(seat="C1",auth=auth("C1"),idem="o",handoff_receipt="proof")["presence"]=="ABSENT"

def test_all_hands_message_has_existing_envelope_and_routes(tmp_path):
 op,_=setup(tmp_path)
 for s in ("C1","C2","C3"): op.check_in(seat=s,auth=auth(s),idem="in-"+s)
 out=op.message(from_seat="C1",to_seat="ALL",task_id="T1",text="coordinate",auth=auth("C1"),idem="m1")
 assert out["to"]==["C2","C3"] and len(out["routes"])==2
 assert set(out["envelope"])=={"task_id","context_id","message_id","artifact_id","correlation_id","idempotency_key","provenance","receipt"}
 assert out["command_fabric_gate"] is True and out["direct_mutation"] is False

def test_audit_detects_cross_owner_overlap_without_second_systems(tmp_path):
 op,repo=setup(tmp_path)
 locks={"locks":[{"id":"A","agent":"C1","scope":"src/x","status":"ACTIVE"},{"id":"B","agent":"C2","scope":"src","status":"ACTIVE"}]}
 (repo/".ai-os/state/LOCKS.json").write_text(json.dumps(locks),encoding="utf-8")
 out=op.audit(); assert out["conflict_total"]==1
 assert all(out[k] is False for k in ("second_task_ledger","second_lock_system","second_bus","second_wal","second_receipt_system"))

def test_presence_proof_refreshes_lease_and_expired_seat_cannot_claim(tmp_path):
 op,_=setup(tmp_path); first=op.check_in(seat="C1",auth=auth("C1"),idem="in")
 state=json.loads(op.presence_path.read_text(encoding="utf-8"))
 state["seats"]["C1"]["lease_expires_at"]="2000-01-01T00:00:00Z"
 op.presence_path.write_text(json.dumps(state),encoding="utf-8")
 with pytest.raises(CouncilConflict,match="CHECK_IN_REQUIRED"):
  op.claim(seat="C1",task_id="T1",auth=auth("C1"),idem="claim-expired")
 with pytest.raises(CouncilConflict,match="CHECK_IN_REQUIRED"):
  op.prove_presence(seat="C1",auth=auth("C1"),idem="proof-expired")
 second=op.check_in(seat="C1",auth=auth("C1"),idem="recheck")
 proof=op.prove_presence(seat="C1",auth=auth("C1"),idem="proof-live")
 assert first["seat"]==second["seat"]==proof["seat"]=="C1"
 assert proof["presence"]=="PRESENT" and proof["lease_expires_at"]>=second["lease_expires_at"]
