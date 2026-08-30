"""Governed attendance and coordination over existing RAIOS control seams.

Not a scheduler, ledger, lock service, bus, WAL, receipt system, or authority system.
Presence is operational runtime state; tasks and locks reuse the canonical files.
"""
from __future__ import annotations
import hashlib, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from raios.a2a.receipt_bridge import build_receipt
from raios.a2a_all_hands.bind import INTERNAL_SEATS, routing_matrix, validate_envelope

TASKS=Path(".ai-os/state/TASKS.json"); LOCKS=Path(".ai-os/state/LOCKS.json")
class CouncilValidationError(RuntimeError): pass
class CouncilConflict(RuntimeError): pass

def _now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def _expires(seconds=120): return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
def _live(row):
    if row.get("presence")!="PRESENT": return False
    expiry=row.get("lease_expires_at")
    return not expiry or datetime.fromisoformat(expiry.replace("Z","+00:00"))>datetime.now(timezone.utc)
def _load(path, default):
    try: return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError: return default
def _atomic(path, value):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8"); os.replace(tmp,path)
def _id(*parts): return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:24]
def _overlap(a,b):
    a,b=a.rstrip("/*/"),b.rstrip("/*/"); return a==b or a.startswith(b+"/") or b.startswith(a+"/")

class CouncilOperations:
    def __init__(self, repo:Path, runtime:Path|None=None):
        self.repo=repo.resolve(); self.runtime=(runtime or Path.home()/".raios/runtime/council-ops").resolve()
        self.presence_path=self.runtime/"presence.json"; self.receipt_dir=self.runtime/"receipts"
    def _auth(self, seat, auth):
        if seat.split("-",1)[0].split("@",1)[0] not in INTERNAL_SEATS: raise CouncilValidationError("UNKNOWN_SEAT")
        if auth.get("seat_id")!=seat: raise CouncilValidationError("SEAT_IDENTITY_MISMATCH")
        if not all(auth.get(k) is True for k in ("SIGNATURE_VALID","ISSUER_IDENTIFIED","ISSUER_TRUSTED","PRINCIPAL_BOUND")):
            raise CouncilValidationError("AUTHENTICATED_SEAT_PROOF_REQUIRED")
        if not auth.get("AUTHORITY_SOURCE_PROVENANCE"): raise CouncilValidationError("AUTHORITY_PROVENANCE_REQUIRED")
    def _state(self): return _load(self.presence_path,{"schema":"raios.council-presence.v1","seats":{},"idempotency":{}})
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
        at=_now(); path,_=self._receipt(seat,"CHECK_IN","COUNCIL-PRESENCE","presence:"+seat,idem,auth,"PRESENT",[str(self.presence_path)])
        result={"seat":seat,"presence":"PRESENT","checked_in_at":at,"last_seen":at,
                "lease_expires_at":_expires(),"signature_valid":True,"receipt":path}
        state["seats"][seat]=result; state["idempotency"][idem]={"fingerprint":fp,"result":result}; _atomic(self.presence_path,state)
        return {"status":"PRESENT",**result}
    def prove_presence(self,*,seat,auth,idem):
        self._auth(seat,auth); state=self._state(); current=state["seats"].get(seat,{})
        if not _live(current): raise CouncilConflict("CHECK_IN_REQUIRED")
        fp=_id("PRESENCE",seat,idem); old=self._once(state,idem,fp)
        if old: return {"status":"ALREADY_APPLIED",**old["result"]}
        current.update(last_seen=_now(),lease_expires_at=_expires(),signature_valid=True)
        path,_=self._receipt(seat,"PROVE_PRESENCE","COUNCIL-PRESENCE","presence:"+seat,idem,auth,"PRESENT",[str(self.presence_path)])
        current["receipt"]=path;state["seats"][seat]=current
        state["idempotency"][idem]={"fingerprint":fp,"result":current};_atomic(self.presence_path,state)
        return {"status":"PRESENT",**current}
    def check_out(self,*,seat,auth,idem,handoff_receipt=None):
        self._auth(seat,auth); tasks=_load(self.repo/TASKS,{"tasks":[]})["tasks"]
        active=[t["id"] for t in tasks if t.get("claimed_by")==seat and t.get("status")=="IN_PROGRESS"]
        if active and not handoff_receipt: raise CouncilConflict("ACTIVE_TASKS_REQUIRE_HANDOFF:"+",".join(active))
        state=self._state(); fp=_id("OUT",seat,",".join(active),handoff_receipt or ""); old=self._once(state,idem,fp)
        if old: return {"status":"ALREADY_APPLIED",**old["result"]}
        ev=[handoff_receipt] if handoff_receipt else []; path,_=self._receipt(seat,"CHECK_OUT","COUNCIL-PRESENCE","presence:"+seat,idem,auth,"ABSENT",ev)
        result={"seat":seat,"presence":"ABSENT","checked_out_at":_now(),"active_tasks":active,"receipt":path}
        state["seats"][seat]=result; state["idempotency"][idem]={"fingerprint":fp,"result":result}; _atomic(self.presence_path,state)
        return {"status":"ABSENT",**result}
    def claim(self,*,seat,task_id,auth,idem):
        self._auth(seat,auth); state=self._state()
        if not _live(state["seats"].get(seat,{})): raise CouncilConflict("CHECK_IN_REQUIRED")
        data=_load(self.repo/TASKS,{"tasks":[]}); task=next((t for t in data["tasks"] if t.get("id")==task_id),None)
        if not task: raise CouncilValidationError("TASK_NOT_FOUND")
        if task.get("allowed_agents") and seat not in task["allowed_agents"]: raise CouncilConflict("SEAT_NOT_ALLOWED")
        if task.get("status") not in ("READY","IN_PROGRESS") or task.get("claimed_by") not in (None,seat): raise CouncilConflict("TASK_NOT_CLAIMABLE")
        for dep in task.get("dependencies",[]):
            d=next((t for t in data["tasks"] if t.get("id")==dep),None)
            if not d or d.get("status")!="DONE": raise CouncilConflict("DEPENDENCY_INCOMPLETE:"+dep)
        for scope in task.get("scope",[]):
            for lock in _load(self.repo/LOCKS,{"locks":[]})["locks"]:
                if lock.get("status")=="ACTIVE" and lock.get("agent")!=seat and _overlap(lock.get("scope",""),scope):
                    raise CouncilConflict("LOCK_CONFLICT:"+str(lock.get("id")))
        fp=_id("CLAIM",seat,task_id); old=self._once(state,idem,fp)
        if old: return {"status":"ALREADY_APPLIED",**old["result"]}
        task["status"]="IN_PROGRESS"; task["claimed_by"]=seat; _atomic(self.repo/TASKS,data)
        path,_=self._receipt(seat,"CLAIM",task_id,"task:"+task_id,idem,auth,"CLAIMED",[str(TASKS),str(LOCKS)])
        result={"task_id":task_id,"claimed_by":seat,"receipt":path}; state["idempotency"][idem]={"fingerprint":fp,"result":result}; _atomic(self.presence_path,state)
        return {"status":"CLAIMED",**result}
    def handoff(self,*,from_seat,to_seat,task_id,auth,idem,evidence):
        self._auth(from_seat,auth); state=self._state()
        if not _live(state["seats"].get(to_seat,{})): raise CouncilConflict("DESTINATION_NOT_PRESENT")
        data=_load(self.repo/TASKS,{"tasks":[]}); task=next((t for t in data["tasks"] if t.get("id")==task_id),None)
        if not task: raise CouncilValidationError("TASK_NOT_FOUND")
        if task.get("claimed_by")!=from_seat or task.get("status")!="IN_PROGRESS": raise CouncilConflict("SOURCE_NOT_TASK_OWNER")
        if task.get("allowed_agents") and to_seat not in task["allowed_agents"]: raise CouncilConflict("DESTINATION_NOT_ALLOWED")
        fp=_id("HANDOFF",from_seat,to_seat,task_id,*sorted(evidence)); old=self._once(state,idem,fp)
        if old: return {"status":"ALREADY_APPLIED",**old["result"]}
        task["claimed_by"]=to_seat; task["handoff_from"]=from_seat; task["handoff_at"]=_now(); _atomic(self.repo/TASKS,data)
        path,_=self._receipt(from_seat,"HANDOFF",task_id,"task:"+task_id,idem,auth,"HANDED_OFF",evidence+[str(TASKS)])
        result={"task_id":task_id,"from":from_seat,"to":to_seat,"receipt":path}; state["idempotency"][idem]={"fingerprint":fp,"result":result}; _atomic(self.presence_path,state)
        return {"status":"HANDED_OFF",**result}
    def message(self,*,from_seat,to_seat,task_id,text,auth,idem):
        self._auth(from_seat,auth); state=self._state()
        if not _live(state["seats"].get(from_seat,{})): raise CouncilConflict("CHECK_IN_REQUIRED")
        fp=_id("MESSAGE",from_seat,to_seat,task_id,text); old=self._once(state,idem,fp)
        if old: return {"status":"ALREADY_APPLIED",**old["result"]}
        dests=[s for s,v in state["seats"].items() if _live(v) and s!=from_seat] if to_seat=="ALL" else [to_seat]
        if not dests or any(not _live(state["seats"].get(d,{})) for d in dests): raise CouncilConflict("DESTINATION_NOT_PRESENT")
        context="task:"+task_id; path,receipt=self._receipt(from_seat,"COORDINATION_MESSAGE",task_id,context,idem,auth,"ROUTED",[str(TASKS)])
        roots={d.split("-",1)[0] for d in dests}; routes=[r for r in routing_matrix(nats_available=False) if r["from"]==from_seat.split("-",1)[0] and r["to"] in roots]
        env=validate_envelope({"task_id":task_id,"context_id":context,"message_id":_id("msg",idem),"artifact_id":_id("art",idem),
          "correlation_id":context,"idempotency_key":idem,"provenance":auth["AUTHORITY_SOURCE_PROVENANCE"],"receipt":receipt})
        result={"from":from_seat,"to":dests,"text":text,"routes":routes,"envelope":env,"receipt":path,"direct_mutation":False,"command_fabric_gate":True}
        state["idempotency"][idem]={"fingerprint":fp,"result":result}; _atomic(self.presence_path,state)
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
