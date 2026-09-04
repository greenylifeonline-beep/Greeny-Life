import json
from pathlib import Path
import pytest
from raios.council_ops import CouncilConflict, CouncilOperations, CouncilValidationError
from raios.council_ops import operations as council_operations

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

def test_c1_can_attest_coordination_availability_without_execution_signature(tmp_path):
 op,_=setup(tmp_path)
 out=op.attest_availability(seat="C2",state="AVAILABLE",attested_by="C1",
  auth=auth("C1"),idem="avail-c2",reason="C1 confirmed C2 available now")
 assert out["status"]=="ATTESTED" and out["availability"]=="AVAILABLE"
 state=json.loads(op.presence_path.read_text(encoding="utf-8"))
 row=state["seats"]["C2"]
 assert row["presence"] if "presence" in row else True
 assert row["availability_source"]=="C1_ATTESTATION"
 assert row.get("signature_valid") is not True


def test_non_owner_cannot_attest_other_seat_availability(tmp_path):
 op,_=setup(tmp_path)
 with pytest.raises(CouncilConflict,match="AVAILABILITY_ATTESTATION_REQUIRES_C1_OR_SELF"):
  op.attest_availability(seat="C2",state="AVAILABLE",attested_by="C3",
   auth=auth("C3"),idem="bad-attest",reason="not owner")


def test_idempotency_key_cannot_change_meaning(tmp_path):
 op,_=setup(tmp_path); op.check_in(seat="C1",auth=auth("C1"),idem="same")
 with pytest.raises(CouncilConflict,match="IDEMPOTENCY_CONFLICT"):
  op.message(from_seat="C1",to_seat="ALL",task_id="T1",text="x",auth=auth("C1"),idem="same")

def test_self_claim_is_disabled_even_when_signed_present(tmp_path):
 op,_=setup(tmp_path); op.check_in(seat="C1",auth=auth("C1"),idem="in")
 with pytest.raises(CouncilConflict,match="SELF_CLAIM_DISABLED_USE_RAIOS_WORKER_DISPATCH"):
  op.claim(seat="C1",task_id="T1",auth=auth("C1"),idem="claim")

def test_direct_handoff_is_disabled(tmp_path):
 op,_=setup(tmp_path)
 op.check_in(seat="C1",auth=auth("C1"),idem="i1")
 op.check_in(seat="C2",auth=auth("C2"),idem="i2")
 with pytest.raises(CouncilConflict,match="DIRECT_HANDOFF_DISABLED"):
  op.handoff(from_seat="C1",to_seat="C2",task_id="T1",auth=auth("C1"),idem="h1",evidence=[])

def test_checkout_requires_handoff_for_active_task(tmp_path):
 op,repo=setup(tmp_path); op.check_in(seat="C1",auth=auth("C1"),idem="i")
 data=json.loads((repo/".ai-os/state/TASKS.json").read_text())
 data["tasks"][0].update(status="IN_PROGRESS",claimed_by="C1")
 (repo/".ai-os/state/TASKS.json").write_text(json.dumps(data),encoding="utf-8")
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
 with pytest.raises(CouncilConflict,match="SELF_CLAIM_DISABLED_USE_RAIOS_WORKER_DISPATCH"):
  op.claim(seat="C1",task_id="T1",auth=auth("C1"),idem="claim-expired")
 with pytest.raises(CouncilConflict,match="CHECK_IN_REQUIRED"):
  op.prove_presence(seat="C1",auth=auth("C1"),idem="proof-expired")
 second=op.check_in(seat="C1",auth=auth("C1"),idem="recheck")
 proof=op.prove_presence(seat="C1",auth=auth("C1"),idem="proof-live")
 assert first["seat"]==second["seat"]==proof["seat"]=="C1"
 assert proof["presence"]=="PRESENT" and proof["lease_expires_at"]>=second["lease_expires_at"]


def test_presence_atomic_falls_back_when_stable_name_is_pinned(tmp_path,monkeypatch):
 target=tmp_path/"presence.json"
 target.write_text('{"seats":{}}',encoding="utf-8")
 monkeypatch.setattr(council_operations.os,"replace",
  lambda *args: (_ for _ in ()).throw(PermissionError("stable name pinned")))
 monkeypatch.setattr(council_operations.time,"sleep",lambda *_:None)
 council_operations._atomic(target,{"seats":{"C3":{"presence":"PRESENT"}}})
 data=json.loads(target.read_text(encoding="utf-8"))
 assert data["seats"]["C3"]["presence"]=="PRESENT"
 assert list(tmp_path.glob("presence.json.*.tmp"))==[]
