"""Governed attendance and coordination over existing RAIOS control seams.

Not a scheduler, ledger, lock service, bus, WAL, receipt system, or authority system.
Presence is operational runtime state; tasks and locks reuse the canonical files.
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from raios.a2a.receipt_bridge import build_receipt
from .presence_challenge import PresenceChallengeError, PresenceChallengeStore
INTERNAL_SEATS=tuple(f"C{i}" for i in range(1,13))

TASKS=Path(".ai-os/state/TASKS.json"); LOCKS=Path(".ai-os/state/LOCKS.json")
class CouncilValidationError(RuntimeError): pass
class CouncilConflict(RuntimeError): pass

def _now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def _expires(seconds=120): return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
def _live(row):
    if row.get("presence")!="PRESENT" or row.get("signature_valid") is not True: return False
    expiry=row.get("lease_expires_at")
    return not expiry or datetime.fromisoformat(expiry.replace("Z","+00:00"))>datetime.now(timezone.utc)
def _load(path, default):
    try: return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError: return default
def _atomic(path, value):
    """Validated JSON write resilient to transient and stable Windows locks."""
    path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+"\n"
    json.loads(payload)
    tmp=path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    replace_error=None
    try:
        tmp.write_text(payload,encoding="utf-8")
        for attempt in range(6):
            try:
                os.replace(tmp,path);return
            except PermissionError as exc:
                replace_error=exc
                if attempt<5:time.sleep(.02*(2**attempt))
        for attempt in range(8):
            try:
                with path.open("w",encoding="utf-8",newline="\n") as handle:
                    handle.write(payload);handle.flush();os.fsync(handle.fileno())
                json.loads(path.read_text(encoding="utf-8"));return
            except PermissionError:
                if attempt==7:raise replace_error or PermissionError("JSON_WRITE_DENIED")
                time.sleep(.05*(attempt+1))
    finally:
        try:tmp.unlink(missing_ok=True)
        except OSError:pass
def _id(*parts): return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:24]
def _fingerprint(action,seat,auth,at,challenge_fingerprint=""):
    provenance=json.dumps(auth.get("AUTHORITY_SOURCE_PROVENANCE") or {},sort_keys=True,separators=(",",":"))
    actor=auth.get("actor_id") or auth.get("principal") or auth.get("PRINCIPAL") or ""
    origin=auth.get("origin_instance") or auth.get("ORIGIN_INSTANCE") or ""
    device=auth.get("device_id") or auth.get("remote_device_id") or auth.get("DEVICE_ID") or ""
    session=auth.get("session_id") or auth.get("remote_session_id") or auth.get("SESSION_ID") or ""
    return hashlib.sha256("\x1f".join(map(str,(
      "RAIOS_ATTENDANCE_FINGERPRINT_V1",action,seat,actor,origin,device,session,at,provenance,challenge_fingerprint
    ))).encode()).hexdigest()
def _overlap(a,b):
    a,b=a.rstrip("/*/"),b.rstrip("/*/"); return a==b or a.startswith(b+"/") or b.startswith(a+"/")
IDEMPOTENCY_KEEP=256
def prune_idempotency(state, keep=IDEMPOTENCY_KEEP):
    idem=state.get("idempotency") or {}
    extra=len(idem)-keep
    if extra<=0: return 0
    for key in list(idem.keys())[:extra]:
        idem.pop(key, None)
    state["idempotency"]=idem
    return extra
def _commit_presence(path, state):
    prune_idempotency(state)
    _atomic(path, state)

class CouncilOperations:
    def __init__(self, repo:Path, runtime:Path|None=None):
        self.repo=repo.resolve(); self.runtime=(runtime or Path.home()/".raios/runtime/council-ops").resolve()
        self.presence_path=self.runtime/"presence.json"; self.receipt_dir=self.runtime/"receipts"
        self.bindings_path=self.runtime/"actor-bindings.json"
        self.seat_map_path=self.repo/".ai-os/mcp/SEAT-MAP.json"
        self.assignment_path=self.repo/".ai-os/state/a2a/seat-assignments.json"
        self.assignment_receipt_dir=self.repo/".ai-os/receipts/council-ops/seat-assignment"
        self.challenges=PresenceChallengeStore(self.runtime)
    def compact_runtime(self):
        state=self._state(); dropped=prune_idempotency(state)
        _atomic(self.presence_path,state)
        return {"idempotency_dropped":dropped,"idempotency_kept":len(state.get("idempotency") or {}),
                "challenges_dropped":self.challenges.compact()}
    def _auth(self, seat, auth):
        if seat.split("-",1)[0].split("@",1)[0] not in INTERNAL_SEATS: raise CouncilValidationError("UNKNOWN_SEAT")
        if auth.get("seat_id")!=seat: raise CouncilValidationError("SEAT_IDENTITY_MISMATCH")
        if not all(auth.get(k) is True for k in ("SIGNATURE_VALID","ISSUER_IDENTIFIED","ISSUER_TRUSTED","PRINCIPAL_BOUND")):
            raise CouncilValidationError("AUTHENTICATED_SEAT_PROOF_REQUIRED")
        if not auth.get("AUTHORITY_SOURCE_PROVENANCE"): raise CouncilValidationError("AUTHORITY_PROVENANCE_REQUIRED")
        self._require_reserved_assignment(seat,auth)
    def _seat_map(self): return _load(self.seat_map_path,{"schema":"raios.seat-map.v2","seats":{}})
    def _assignments(self): return _load(self.assignment_path,{"schema":"raios.seat-assignments.v1","assignments":{},"history":[]})
    def _reserved_assignment_required(self,seat):
        spec=(self._seat_map().get("seats") or {}).get(seat) or {}
        return str(spec.get("actor_role") or "").startswith("UNASSIGNED_PENDING_")
    def _require_reserved_assignment(self,seat,auth):
        if not self._reserved_assignment_required(seat): return
        actor=auth.get("actor_id") or auth.get("principal") or auth.get("PRINCIPAL")
        row=(self._assignments().get("assignments") or {}).get(seat) or {}
        if row.get("status")!="ASSIGNED": raise CouncilValidationError("C1_SEAT_ASSIGNMENT_REQUIRED")
        if not actor or actor!=row.get("actor_id"): raise CouncilValidationError("ASSIGNED_ACTOR_MISMATCH")
        if row.get("authority")!="C1" or not row.get("authorization_provenance"):
            raise CouncilValidationError("ASSIGNMENT_PROVENANCE_INVALID")
    def _state(self): return _load(self.presence_path,{"schema":"raios.council-presence.v1","seats":{},"idempotency":{}})
    def _bindings(self): return _load(self.bindings_path,{"schema":"raios.actor-bindings.v1","bindings":{}})
    def _bind_from_auth(self,seat,auth,lease_expires_at):
        actor_id=auth.get("actor_id") or auth.get("principal") or auth.get("PRINCIPAL")
        origin=auth.get("origin_instance") or auth.get("ORIGIN_INSTANCE")
        device=auth.get("device_id") or auth.get("remote_device_id") or auth.get("DEVICE_ID")
        session=auth.get("session_id") or auth.get("remote_session_id") or auth.get("SESSION_ID")
        if not all((actor_id,origin,device,session)):
            return None
        data=self._bindings(); row={
          "seat":seat,"actor_id":actor_id,"origin_instance":origin,"device_id":device,
          "session_id":session,"auth_evidence":auth.get("AUTHORITY_SOURCE_PROVENANCE"),
          "bound_at":_now(),"last_seen":_now(),"lease_expires_at":lease_expires_at,
          "signature_valid":True,"synthetic":False}
        data["bindings"][seat]=row;data["generated_at"]=_now();_atomic(self.bindings_path,data);return row
    def _head(self):
        try:
            return subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.repo,text=True,stderr=subprocess.DEVNULL,timeout=5,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)).strip()
        except Exception as exc:
            raise CouncilValidationError("CANONICAL_HEAD_UNAVAILABLE") from exc
    @staticmethod
    def _valid_actor_id(actor_id):
        actor=str(actor_id or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:@/\-]{2,127}",actor): return False
        if actor.upper() in {"RESERVED","UNASSIGNED","UNKNOWN","NONE","NULL","C8","RAIOS-WORKER"}: return False
        return True
    @staticmethod
    def _expiry_current(value):
        if not value: return False
        try: return datetime.fromisoformat(str(value).replace("Z","+00:00"))>datetime.now(timezone.utc)
        except (TypeError,ValueError): return False
    def _active_task_for_seat(self,seat):
        data=_load(self.repo/TASKS,{"tasks":[]})
        active={"ACTIVE","IN_PROGRESS","CLAIMED","DOING","PENDING_ACCEPTANCE","ASSIGNED"}
        fields=("claimed_by","assigned_to","target","dispatch_target","last_dispatch_target","owner")
        for task in data.get("tasks",[]):
            if str(task.get("status") or "").upper() not in active: continue
            if any(str(task.get(k) or "").upper()==seat for k in fields): return task
        return None
    def _active_lock_for_seat(self,seat):
        data=_load(self.repo/LOCKS,{"locks":[]}); active={"ACTIVE","CLAIMED","IN_PROGRESS","HELD"}
        for row in data.get("locks",[]):
            if str(row.get("status") or "").upper() not in active: continue
            identities=(row.get("agent"),row.get("holder"),row.get("lease_holder"))
            if any(str(x or "").upper()==seat for x in identities): return row
        return None
    def authorize_seat_assignment(self,*,seat,actor_id,authority,c1_intent,authorization_provenance,transaction_id=None):
        seat=str(seat or "").upper(); authority=str(authority or "").upper(); actor_id=str(actor_id or "").strip()
        if seat!="C8": raise CouncilValidationError("FIRST_GOVERNED_ASSIGNMENT_C8_ONLY")
        if authority!="C1": raise CouncilValidationError("C1_AUTHORITY_REQUIRED")
        if c1_intent is not True: raise CouncilValidationError("C1_ASSIGNMENT_INTENT_REQUIRED")
        if not self._valid_actor_id(actor_id): raise CouncilValidationError("MALFORMED_ACTOR_IDENTITY")
        prov=authorization_provenance if isinstance(authorization_provenance,dict) else {}
        if prov.get("authority")!="C1" or not prov.get("source") or not prov.get("decision"):
            raise CouncilValidationError("AUTHORIZATION_PROVENANCE_INCOMPLETE")
        seat_map=self._seat_map(); spec=(seat_map.get("seats") or {}).get(seat)
        if not isinstance(spec,dict): raise CouncilValidationError("SEAT_NOT_DEFINED")
        if str(spec.get("actor_role") or "").startswith("UNASSIGNED_PENDING_") is False:
            raise CouncilConflict("SEAT_NOT_LEGALLY_ASSIGNABLE")
        assignments=self._assignments(); current=(assignments.get("assignments") or {}).get(seat)
        for other_seat,other in (assignments.get("assignments") or {}).items():
            if other_seat!=seat and other.get("status")=="ASSIGNED" and other.get("actor_id")==actor_id:
                raise CouncilConflict("ACTOR_ALREADY_ASSIGNED_TO_OTHER_SEAT")
        if current:
            if current.get("actor_id")==actor_id and current.get("status")=="ASSIGNED":
                return {"status":"ALREADY_ASSIGNED","seat":seat,"actor_id":actor_id,"receipt":current.get("receipt"),"transaction_id":current.get("transaction_id")}
            raise CouncilConflict("SEAT_ALREADY_ASSIGNED")
        for historical in assignments.get("history",[]):
            if historical.get("seat")==seat and historical.get("actor_id")!=actor_id:
                raise CouncilConflict("CONFLICTING_HISTORICAL_ASSIGNMENT")
        bindings=self._bindings(); binding=(bindings.get("bindings") or {}).get(seat) or {}
        for other_seat,other in (bindings.get("bindings") or {}).items():
            if other_seat!=seat and other.get("actor_id")==actor_id and self._expiry_current(other.get("lease_expires_at")):
                raise CouncilConflict("ACTOR_ALREADY_BOUND_TO_OTHER_SEAT")
        if binding:
            if binding.get("actor_id")!=actor_id: raise CouncilConflict("INCOMPATIBLE_ACTOR_BINDING")
            if self._expiry_current(binding.get("lease_expires_at")): raise CouncilConflict("ACTIVE_SESSION_EXISTS")
            raise CouncilConflict("CURRENT_ACTOR_BINDING_EXISTS")
        presence=(self._state().get("seats") or {}).get(seat) or {}
        if _live(presence): raise CouncilConflict("SIGNED_PRESENCE_EXISTS")
        consumer=_load(self.runtime/"consumers"/f"{seat}.json",{})
        if str(consumer.get("state") or "").upper()=="ONLINE" and self._expiry_current(consumer.get("lease_expires_at")):
            raise CouncilConflict("LIVE_CONSUMER_EXISTS")
        task=self._active_task_for_seat(seat)
        if task: raise CouncilConflict("ACTIVE_TASK_EXISTS")
        lock=self._active_lock_for_seat(seat)
        if lock: raise CouncilConflict("ACTIVE_LEASE_EXISTS")
        head=self._head(); at=_now(); tx=str(transaction_id or ("C8ASSIGN-"+uuid.uuid4().hex))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}",tx): raise CouncilValidationError("MALFORMED_TRANSACTION_ID")
        previous={"seat_map":spec,"assignment":None,"presence":"ABSENT","binding":None,"consumer":"ABSENT","active_task":None,"active_lease":None}
        new={"assignment_state":"ASSIGNED_PENDING_SESSION_BOOTSTRAP","availability":"INACTIVE","presence":"ABSENT","current_session":None,"live_consumer":False,"active_task":None,"active_lease":None}
        receipt_id="ASG-"+_id(seat,actor_id,tx,head)
        receipt_path=self.assignment_receipt_dir/f"{receipt_id}.json"
        receipt={"schema":"raios.c1-seat-assignment-receipt.v1","receipt_id":receipt_id,"transaction_id":tx,"seat":seat,"actor_id":actor_id,"authority":"C1","authorization_provenance":prov,"previous_seat_state":previous,"new_seat_state":new,"assignment_timestamp":at,"canonical_head":head,"implementation_version":"raios.council-seat-assignment.v1","self_signed_presence_required":True,"live_bound_consumer_required":True,"worker_assignment_required":True,"no_self_claim":True,"no_active_scope_overlap":True,"live_activation_executed":False}
        _atomic(receipt_path,receipt)
        row={"seat":seat,"actor_id":actor_id,"status":"ASSIGNED","authority":"C1","authorization_provenance":prov,"assigned_at":at,"transaction_id":tx,"receipt_id":receipt_id,"receipt":str(receipt_path),"canonical_head":head,"implementation_version":"raios.council-seat-assignment.v1","availability":"INACTIVE","presence":"ABSENT","current_session_id":None,"live_consumer":False,"live_activation_executed":False}
        assignments.setdefault("assignments",{})[seat]=row; assignments.setdefault("history",[]).append(dict(row)); assignments["updated_at"]=at
        _atomic(self.assignment_path,assignments)
        return {**row,"status":"ASSIGNED_PENDING_SESSION_BOOTSTRAP"}
    def _once(self,state,idem,fp):
        old=state["idempotency"].get(idem)
        if old and old["fingerprint"]!=fp: raise CouncilConflict("IDEMPOTENCY_CONFLICT")
        return old
    def _receipt(self,seat,action,task,context,idem,auth,status,evidence):
        intent={"COMMAND_ID":_id(seat,action,task,idem),"CHANGE_ID":task,"CORRELATION_ID":context,
                "ACTOR":seat,"TARGET_SELECTOR":"RAIOS_COUNCIL","INTENT":action}
        receipt=build_receipt(a2a_task_id=task,a2a_context_id=context,intent=intent,
          capability_id="raios.council.operations",semantic_contract_id="raios.council.v1",
          semantic_fingerprint=_id(action,task),auth_result=auth,
          policy_result={"POLICY_RESULT":"ALLOW","RISK_CLASS":"LOW"},status=status,evidence_refs=evidence)
        path=self.receipt_dir/(intent["COMMAND_ID"]+".receipt.json"); _atomic(path,receipt)
        return str(path),receipt
    def check_in(self,*,seat,auth,idem):
        self._auth(seat,auth); state=self._state(); fp=_id("IN",seat); old=self._once(state,idem,fp)
        if old: return {"status":"ALREADY_APPLIED",**old["result"]}
        at=_now(); fingerprint=_fingerprint("CHECK_IN",seat,auth,at)
        path,_=self._receipt(seat,"CHECK_IN","COUNCIL-PRESENCE","presence:"+seat,idem,auth,"PRESENT",[str(self.presence_path)])
        result={"seat":seat,"presence":"PRESENT","checked_in_at":at,"last_seen":at,
                "lease_expires_at":_expires(),"signature_valid":True,"receipt":path,
                "availability":"AVAILABLE","availability_source":"SELF_SIGNED_PRESENCE",
                "availability_attested_at":at,"availability_expires_at":_expires(1800),
                "availability_reason":"SIGNED_PRESENT_AND_AVAILABLE_FOR_COORDINATION",
                "attendance_fingerprint":fingerprint,
                "attendance_proof_type":"AUTHENTICATED_SELF_CHECK_IN",
                "work_state":"WAITING_FOR_ASSIGNMENT",
                "required_action":"WAIT_FOR_RAIOS_WORKER_DISPATCH"}
        state["seats"][seat]=result; state["idempotency"][idem]={"fingerprint":fp,"result":result}; _commit_presence(self.presence_path,state)
        self.challenges.supersede_for_seat(
            seat,reason="AUTHENTICATED_SELF_CHECK_IN",
            attendance_fingerprint=fingerprint)
        binding=self._bind_from_auth(seat,auth,result["lease_expires_at"])
        return {"status":"PRESENT",**result,"actor_binding":binding}
    def prove_presence(self,*,seat,auth,idem):
        self._auth(seat,auth); state=self._state(); current=state["seats"].get(seat,{})
        if not _live(current): raise CouncilConflict("CHECK_IN_REQUIRED")
        fp=_id("PRESENCE",seat,idem); old=self._once(state,idem,fp)
        if old: return {"status":"ALREADY_APPLIED",**old["result"]}
        now=_now();fingerprint=_fingerprint("PROVE_PRESENCE",seat,auth,now,current.get("attendance_fingerprint",""))
        current.update(last_seen=now,lease_expires_at=_expires(),signature_valid=True,
                       availability="AVAILABLE",availability_source="SELF_SIGNED_PRESENCE",
                       availability_attested_at=now,availability_expires_at=_expires(1800),
                       availability_reason="SIGNED_PRESENT_AND_AVAILABLE_FOR_COORDINATION",
                       attendance_fingerprint=fingerprint,
                       attendance_proof_type="AUTHENTICATED_PRESENCE_REFRESH",
                       work_state="WAITING_FOR_ASSIGNMENT",
                       required_action="WAIT_FOR_RAIOS_WORKER_DISPATCH")
        path,_=self._receipt(seat,"PROVE_PRESENCE","COUNCIL-PRESENCE","presence:"+seat,idem,auth,"PRESENT",[str(self.presence_path)])
        current["receipt"]=path;state["seats"][seat]=current
        state["idempotency"][idem]={"fingerprint":fp,"result":current};_commit_presence(self.presence_path,state)
        self.challenges.supersede_for_seat(
            seat,reason="AUTHENTICATED_PRESENCE_REFRESH",
            attendance_fingerprint=fingerprint)
        binding=self._bind_from_auth(seat,auth,current["lease_expires_at"])
        return {"status":"PRESENT",**current,"actor_binding":binding}
    def respond_presence_challenge(self,*,seat,challenge_id,nonce,origin_salt,response_word,
                                  availability,auth,idem):
        seat=str(seat).upper();availability=str(availability).upper()
        self._auth(seat,auth)
        state=self._state();fp=_id("PRESENCE_CHALLENGE",seat,challenge_id,availability)
        old=self._once(state,idem,fp)
        if old:return {"status":"ALREADY_APPLIED",**old["result"]}
        proof=self.challenges.consume(
            seat=seat,challenge_id=challenge_id,nonce=nonce,origin_salt=origin_salt,
            response_word=response_word,auth=auth,state=availability)
        at=_now()
        row=dict(state["seats"].get(seat,{}) or {})
        if availability in ("AVAILABLE","BUSY"):
            row.update(
                seat=seat,presence="PRESENT",signature_valid=True,
                checked_in_at=row.get("checked_in_at") or at,last_seen=at,
                lease_expires_at=_expires(),
                availability=availability,
                availability_source="SELF_CHALLENGE_RESPONSE",
                availability_attested_at=at,availability_expires_at=_expires(1800),
                availability_reason="VERIFIED_CHALLENGE_RESPONSE",
                attendance_fingerprint=proof["response_fingerprint"],
                attendance_proof_type="CHALLENGE_RESPONSE",
                presence_challenge_id=challenge_id,
                work_state="WAITING_FOR_ASSIGNMENT" if availability=="AVAILABLE" else "BUSY_EXTERNAL_OR_UNASSIGNED",
                required_action="WAIT_FOR_RAIOS_WORKER_DISPATCH" if availability=="AVAILABLE" else "REPORT_OR_FINISH_CURRENT_WORK")
            binding=self._bind_from_auth(seat,auth,row["lease_expires_at"])
        else:
            row.update(
                seat=seat,presence="ABSENT",signature_valid=True,checked_out_at=at,
                availability="OFFLINE",availability_source="SELF_CHALLENGE_RESPONSE",
                availability_attested_at=at,availability_expires_at=_expires(1800),
                availability_reason="VERIFIED_CHALLENGE_RESPONSE_OFFLINE",
                departure_fingerprint=proof["response_fingerprint"],
                departure_proof_type="CHALLENGE_RESPONSE",
                presence_challenge_id=challenge_id,
                work_state="SIGNED_OUT",required_action="SIGN_CHECK_IN_BEFORE_ANY_WORK")
            binding=None
            bindings=self._bindings();bindings.get("bindings",{}).pop(seat,None);bindings["generated_at"]=_now();_atomic(self.bindings_path,bindings)
        path,_=self._receipt(
            seat,"RESPOND_PRESENCE_CHALLENGE","COUNCIL-PRESENCE","challenge:"+challenge_id,
            idem,auth,availability,[proof.get("message_id") or challenge_id,proof["response_fingerprint"]])
        row["receipt"]=path;state["seats"][seat]=row
        result={"seat":seat,"availability":row["availability"],"presence":row["presence"],
                "signature_valid":True,"attendance_fingerprint":row.get("attendance_fingerprint"),
                "departure_fingerprint":row.get("departure_fingerprint"),
                "challenge_id":challenge_id,"receipt":path,"actor_binding":binding}
        state["idempotency"][idem]={"fingerprint":fp,"result":result};_commit_presence(self.presence_path,state)
        return {"status":"VERIFIED",**result}
    def attest_availability(self,*,seat,state,attested_by,auth,idem,reason=""):
        seat=str(seat).upper();attested_by=str(attested_by).upper();state=str(state).upper()
        self._auth(attested_by,auth)
        if seat not in INTERNAL_SEATS:raise CouncilValidationError("UNKNOWN_SEAT")
        if attested_by not in ("C1",seat):raise CouncilConflict("AVAILABILITY_ATTESTATION_REQUIRES_C1_OR_SELF")
        if state not in ("AVAILABLE","BUSY","OFFLINE","UNKNOWN"):
            raise CouncilValidationError("INVALID_AVAILABILITY_STATE")
        data=self._state();fp=_id("AVAILABILITY",seat,state,attested_by,reason);old=self._once(data,idem,fp)
        if old:return {"status":"ALREADY_APPLIED",**old["result"]}
        at=_now();row=dict(data["seats"].get(seat,{}) or {})
        row.update(seat=seat,availability=state,
                   availability_source=f"{attested_by}_ATTESTATION",
                   availability_attested_at=at,availability_expires_at=_expires(1800),
                   availability_reason=reason or "EXPLICIT_COORDINATION_AVAILABILITY")
        path,_=self._receipt(attested_by,"ATTEST_AVAILABILITY","COUNCIL-PRESENCE",
                             "availability:"+seat,idem,auth,state,[str(self.presence_path)])
        row["availability_receipt"]=path;data["seats"][seat]=row
        result={"seat":seat,"availability":state,"availability_source":row["availability_source"],
                "availability_attested_at":at,"availability_expires_at":row["availability_expires_at"],
                "availability_reason":row["availability_reason"],"receipt":path}
        data["idempotency"][idem]={"fingerprint":fp,"result":result};_commit_presence(self.presence_path,data)
        return {"status":"ATTESTED",**result}
    def check_out(self,*,seat,auth,idem,handoff_receipt=None):
        self._auth(seat,auth); tasks=_load(self.repo/TASKS,{"tasks":[]})["tasks"]
        active=[t["id"] for t in tasks if
                (t.get("claimed_by")==seat and t.get("status")=="IN_PROGRESS") or
                (t.get("assigned_to")==seat and t.get("dispatch_status")=="PENDING_ACCEPTANCE")]
        if active and not handoff_receipt: raise CouncilConflict("ACTIVE_TASKS_REQUIRE_HANDOFF:"+",".join(active))
        state=self._state(); fp=_id("OUT",seat,",".join(active),handoff_receipt or ""); old=self._once(state,idem,fp)
        if old: return {"status":"ALREADY_APPLIED",**old["result"]}
        ev=[handoff_receipt] if handoff_receipt else []; path,_=self._receipt(seat,"CHECK_OUT","COUNCIL-PRESENCE","presence:"+seat,idem,auth,"ABSENT",ev)
        out_at=_now();departure_fingerprint=_fingerprint("CHECK_OUT",seat,auth,out_at)
        result={"seat":seat,"presence":"ABSENT","checked_out_at":out_at,"active_tasks":active,"receipt":path,
                "signature_valid":True,"availability":"OFFLINE",
                "availability_source":"SELF_SIGNED_CHECK_OUT",
                "availability_attested_at":out_at,"availability_expires_at":_expires(1800),
                "availability_reason":"MEMBER_EXPLICITLY_SIGNED_OUT",
                "departure_fingerprint":departure_fingerprint,
                "departure_proof_type":"AUTHENTICATED_SELF_CHECK_OUT"}
        state["seats"][seat]=result; state["idempotency"][idem]={"fingerprint":fp,"result":result}; _commit_presence(self.presence_path,state)
        self.challenges.supersede_for_seat(
            seat,reason="AUTHENTICATED_SELF_CHECK_OUT",
            attendance_fingerprint=departure_fingerprint)
        bindings=self._bindings();bindings.get("bindings",{}).pop(seat,None);bindings["generated_at"]=_now();_atomic(self.bindings_path,bindings)
        return {"status":"ABSENT",**result}
    def claim(self,*,seat,task_id,auth,idem):
        self._auth(seat,auth)
        raise CouncilConflict("SELF_CLAIM_DISABLED_USE_RAIOS_WORKER_DISPATCH")
    def handoff(self,*,from_seat,to_seat,task_id,auth,idem,evidence):
        self._auth(from_seat,auth)
        raise CouncilConflict("DIRECT_HANDOFF_DISABLED_USE_CHECKPOINT_AND_RAIOS_WORKER_REASSIGNMENT")
    def message(self,*,from_seat,to_seat,task_id,text,auth,idem):
        self._auth(from_seat,auth); state=self._state()
        if not _live(state["seats"].get(from_seat,{})): raise CouncilConflict("CHECK_IN_REQUIRED")
        fp=_id("MESSAGE",from_seat,to_seat,task_id,text); old=self._once(state,idem,fp)
        if old: return {"status":"ALREADY_APPLIED",**old["result"]}
        dests=[s for s,v in state["seats"].items() if _live(v) and s!=from_seat] if to_seat=="ALL" else [to_seat]
        if not dests or any(not _live(state["seats"].get(d,{})) for d in dests): raise CouncilConflict("DESTINATION_NOT_PRESENT")
        context="task:"+task_id; path,receipt=self._receipt(from_seat,"COORDINATION_MESSAGE",task_id,context,idem,auth,"ROUTED",[str(TASKS)])
        roots={d.split("-",1)[0] for d in dests}; origin=from_seat.split("-",1)[0]
        routes=[{"from":origin,"to":dest,"transport":"INTERNAL_BUS","command_fabric_gate":True} for dest in sorted(roots)]
        env={"task_id":task_id,"context_id":context,"message_id":_id("msg",idem),"artifact_id":_id("art",idem),
          "correlation_id":context,"idempotency_key":idem,"provenance":auth["AUTHORITY_SOURCE_PROVENANCE"],"receipt":receipt}
        if any(not env.get(k) for k in ("task_id","context_id","message_id","artifact_id","correlation_id","idempotency_key","provenance","receipt")):
            raise CouncilConflict("INVALID_INTERNAL_MESSAGE_ENVELOPE")
        result={"from":from_seat,"to":dests,"text":text,"routes":routes,"envelope":env,"receipt":path,"direct_mutation":False,"command_fabric_gate":True}
        state["idempotency"][idem]={"fingerprint":fp,"result":result}; _commit_presence(self.presence_path,state)
        return {"status":"ROUTED",**result}
    def audit(self):
        tasks=_load(self.repo/TASKS,{"tasks":[]})["tasks"]; active=[x for x in _load(self.repo/LOCKS,{"locks":[]})["locks"] if x.get("status")=="ACTIVE"]
        conflicts=[]
        for i,a in enumerate(active):
            for b in active[i+1:]:
                if a.get("agent")!=b.get("agent") and _overlap(a.get("scope",""),b.get("scope","")): conflicts.append({"type":"LOCK_SCOPE_OVERLAP","a":a.get("id"),"b":b.get("id")})
        ids={}
        for t in tasks: ids[t.get("id")]=ids.get(t.get("id"),0)+1
        conflicts += [{"type":"DUPLICATE_TASK_ID","task_id":k} for k,v in ids.items() if k and v>1]
        lock_ids={}
        for lock in active: lock_ids.setdefault(lock.get("id"),set()).add((lock.get("task_id"),lock.get("agent")))
        conflicts += [{"type":"DUPLICATE_LOCK_IDENTITY","lock_id":k} for k,v in lock_ids.items() if k and len(v)>1]
        return {"presence":self._state()["seats"],"tasks_total":len(tasks),"active_locks":len(active),"conflicts":conflicts,
          "conflict_total":len(conflicts),"second_task_ledger":False,"second_lock_system":False,"second_bus":False,"second_wal":False,"second_receipt_system":False}
