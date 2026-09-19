from __future__ import annotations
from raios.command_fabric.lease import CommandLeaseAdapter

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .coordination_truth import lock_is_effective

SEATS=tuple(f"C{i}" for i in range(1,13))
COORDINATION_EVENT_TYPES={
    "TASK_STARTED","BLOCKER_FOUND","SCOPE_LOCKED","NEED_REVIEW","NEED_RESOURCE",
    "DEPENDENCY_REQUEST","HANDOFF_REQUEST","ARTIFACT_READY","MODEL_FAILED","CHECKPOINT",
    "TASK_COMPLETE","DISPATCH_FAILURE","SLA_BREACH","CONFLICT_PREDICTED","RESUME_REQUIRED",
}
SLA_DEFAULTS={
    "delivery_ack_seconds":10,
    "task_accept_seconds":60,
    "first_work_proof_seconds":300,
    "heartbeat_max_age_seconds":15,
    "checkpoint_max_age_seconds":300,
    "blocker_escalation_seconds":0,
}


def utc()->str:
    return datetime.now(timezone.utc).isoformat()


def _parse(value:Any)->datetime|None:
    if not value:return None
    try:return datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except (TypeError,ValueError):return None


def _load(path:Path,default:Any)->Any:
    try:return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError):return default


def _atomic(path:Path,data:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(path)


def _scope_overlap(a:str,b:str)->bool:
    a=str(a or "").replace("\\","/").rstrip("/*/")
    b=str(b or "").replace("\\","/").rstrip("/*/")
    if not a or not b:return False
    return a==b or a.startswith(b+"/") or b.startswith(a+"/")


class CoordinationNervousSystem:
    """Coordination plane over the existing TASKS/locks/presence/Command Fabric.

    It is deliberately transport-agnostic: CouncilBoard remains the only component
    that emits messages through the existing worker. This class derives truth,
    routing intents, SLA breaches, conflict predictions and recovery intents.
    """
    def __init__(self,repo:Path,presence:Path):
        self.repo=repo.resolve()
        self.tasks=self.repo/".ai-os/state/TASKS.json"
        self.locks=self.repo/".ai-os/state/LOCKS.json"
        self.command_leases=CommandLeaseAdapter(self.repo/".ai-os/state/command-fabric/leases")
        self.presence=presence.resolve()
        self.receipts=self.repo/".ai-os/receipts/command-fabric/coordination-events"

    def event(self,event_type:str,actor:str,task_id:str|None=None,**payload:Any)->dict[str,Any]:
        kind=str(event_type or "").upper()
        if kind not in COORDINATION_EVENT_TYPES:raise ValueError("UNKNOWN_COORDINATION_EVENT")
        body={"schema":"raios.coordination-event.v1","event_id":"CEV-"+hashlib.sha256(
            f"{kind}|{actor}|{task_id}|{utc()}|{json.dumps(payload,sort_keys=True,default=str)}".encode()
        ).hexdigest()[:20],"type":kind,"actor":actor,"task_id":task_id,"at":utc(),**payload}
        return body

    def persist_event(self,event:dict[str,Any])->Path:
        if event.get("schema")!="raios.coordination-event.v1":raise ValueError("INVALID_COORDINATION_EVENT")
        path=self.receipts/f"{event['event_id']}.json";_atomic(path,event);return path

    def presence_truth(self,route_snapshot:dict[str,Any])->dict[str,Any]:
        seats={str(r.get("seat") or "").upper():r for r in route_snapshot.get("seats",[])}
        signed=_load(self.presence,{"seats":{}}).get("seats",{})
        tasks=_load(self.tasks,{"tasks":[]}).get("tasks",[])
        locks=_load(self.locks,{"locks":[]}).get("locks",[])
        rows=[]
        for seat in SEATS:
            r=seats.get(seat,{}) ; p=signed.get(seat,{})
            active=next((t for t in tasks if str(t.get("assigned_to") or t.get("claimed_by") or "").upper()==seat and
                         (t.get("status") in ("IN_PROGRESS","BLOCKED") or t.get("dispatch_status")=="PENDING_ACCEPTANCE")),None)
            lock=next((x for x in locks if lock_is_effective(x) and str(x.get("lease_holder") or x.get("agent") or "").upper()==seat),None)
            if p.get("presence")=="PRESENT" and p.get("signature_valid") is True:
                presence_state="PRESENT"
            elif p.get("presence") in ("ABSENT","OFFLINE"):
                presence_state=str(p.get("presence"))
            else:presence_state="UNKNOWN"
            rows.append({
                "seat_id":seat,"assigned_actor":r.get("actor_id") or r.get("actor"),
                "presence_state":presence_state,"reachability_state":r.get("discovery_state") or "UNKNOWN",
                "execution_location":r.get("origin_instance") or r.get("device_id"),
                "work_state":"BUSY" if active else "IDLE",
                "route_state":"READY" if r.get("auto_routable") is True else "NOT_READY",
                "session_state":"CURRENT" if r.get("binding_current") is True else "UNKNOWN",
                "actor_id":r.get("actor_id"),"device_id":r.get("device_id"),"session_id":r.get("session_id"),
                "origin_instance":r.get("origin_instance"),"last_arrival":p.get("arrived_at"),
                "last_heartbeat":p.get("last_heartbeat") or r.get("last_heartbeat"),
                "last_actor_ack":r.get("last_actor_ack"),"current_task":active.get("id") if active else None,
                "current_lock":lock.get("id") if lock else None,"canonical_head":r.get("canonical_head"),
                "evidence_class":"DIRECT_RUNTIME" if r.get("auto_routable") is True else "UNPROVEN",
            })
        return {"schema":"raios.council-presence-truth.v1","seats":rows}

    def lease_write_decision(self,actor:str,task_id:str,scopes:list[str],*,require_lease:bool=True)->dict[str,Any]:
        actor=actor.upper();legacy=_load(self.locks,{"locks":[]}).get("locks",[])
        active=[]
        for rec in self.command_leases._all():
            if self.command_leases.validate(str(rec.get("lease_id") or "")).get("ok"):
                active.append(rec)
        conflicts=[];owned=[];covered=[]
        for scope in scopes:
            overlaps=[x for x in active if _scope_overlap(scope,x.get("scope",""))]
            mine=[x for x in overlaps if str(x.get("owner") or "").upper()==actor and str(x.get("task_id") or "")==str(task_id)]
            owned.extend(str(x.get("lease_id")) for x in mine)
            if mine:covered.append(scope)
            for x in overlaps:
                if x not in mine:conflicts.append({"scope":scope,"lease_id":x.get("lease_id"),"holder":x.get("owner"),"task_id":x.get("task_id")})
            for x in legacy:
                if lock_is_effective(x) and _scope_overlap(scope,x.get("scope","")) and str(x.get("task_id") or "")!=str(task_id):
                    conflicts.append({"scope":scope,"legacy_lock_id":x.get("id"),"holder":x.get("lease_holder") or x.get("agent"),"task_id":x.get("task_id"),"provenance_only":True})
        if conflicts:return {"allowed":False,"decision":"WRITE_DENIED_CONFLICT","conflicts":conflicts,"owned_leases":list(dict.fromkeys(owned))}
        uncovered=[s for s in scopes if s not in covered]
        if require_lease and uncovered:return {"allowed":False,"decision":"WRITE_DENIED_LEASE_REQUIRED","uncovered_scopes":uncovered,"owned_leases":list(dict.fromkeys(owned))}
        return {"allowed":True,"decision":"WRITE_ALLOWED_BY_CURRENT_LEASE","owned_leases":list(dict.fromkeys(owned))}

    def shadow(self,task:dict[str,Any],tasks:list[dict[str,Any]]|None=None)->dict[str,Any]:
        tasks=tasks if tasks is not None else _load(self.tasks,{"tasks":[]}).get("tasks",[])
        locks=_load(self.locks,{"locks":[]}).get("locks",[]);wanted=list(task.get("scope") or [])
        conflicts=[]
        for lock in locks:
            if not lock_is_effective(lock) or str(lock.get("task_id"))==str(task.get("id")):continue
            for a in wanted:
                if _scope_overlap(a,lock.get("scope","")):
                    conflicts.append({"type":"LOCK_CONFLICT","scope":a,"other_scope":lock.get("scope"),"holder":lock.get("lease_holder") or lock.get("agent"),"task_id":lock.get("task_id")})
        for other in tasks:
            if other is task or str(other.get("id"))==str(task.get("id")):continue
            if other.get("status") not in ("IN_PROGRESS","BLOCKED"):continue
            for a in wanted:
                for b in other.get("scope") or []:
                    if _scope_overlap(a,b):conflicts.append({"type":"ACTIVE_TASK_CONFLICT","scope":a,"other_scope":b,"task_id":other.get("id"),"holder":other.get("claimed_by") or other.get("assigned_to")})
        decision="SAFE_PARALLEL" if not conflicts else "SERIALIZE_OR_HANDOFF"
        return {"schema":"raios.coordination-shadow.v1","task_id":task.get("id"),"decision":decision,"conflicts":conflicts}

    def peer_intents(self,tasks:list[dict[str,Any]])->list[dict[str,Any]]:
        by_id={str(t.get("id")):t for t in tasks if t.get("id")};out=[];seen=set()
        for task in tasks:
            tid=str(task.get("id") or "")
            owner=str(task.get("claimed_by") or task.get("assigned_to") or "").upper()
            # Dependency-aware routing.
            for dep in task.get("dependencies") or []:
                d=by_id.get(str(dep));dep_owner=str((d or {}).get("claimed_by") or (d or {}).get("assigned_to") or "").upper()
                if task.get("status") in ("READY","BLOCKED") and d and d.get("status")!="DONE" and dep_owner and dep_owner!=owner:
                    key=("DEPENDENCY_REQUEST",tid,dep_owner,str(dep))
                    if key not in seen:
                        seen.add(key);out.append({"type":"DEPENDENCY_REQUEST","from":owner or "RAIOS-WORKER","to":[dep_owner],"task_id":tid,"dependency_task_id":dep,"reason":"DEPENDENCY_NOT_DONE"})
            # Reviewer auto-subscription after meaningful proof/checkpoint/completion.
            proof=task.get("work_proof_at") or task.get("checkpoint_updated_at") or task.get("completed_at") or task.get("evidence")
            reviewers=[str(x).upper() for x in (task.get("review_by") or task.get("reviewers") or []) if str(x).upper() in SEATS]
            if proof and reviewers:
                key=("NEED_REVIEW",tid,tuple(reviewers),str(proof))
                if key not in seen:
                    seen.add(key);out.append({"type":"NEED_REVIEW","from":owner or "RAIOS-WORKER","to":reviewers,"task_id":tid,"proof":proof})
        return out

    def sla_breaches(self,route_snapshot:dict[str,Any],tasks:list[dict[str,Any]],now:datetime|None=None)->list[dict[str,Any]]:
        now=now or datetime.now(timezone.utc);out=[]
        for task in tasks:
            if task.get("dispatch_status")=="PENDING_ACCEPTANCE":
                at=_parse(task.get("dispatched_at"));limit=max(30,int(task.get("acceptance_timeout_seconds") or SLA_DEFAULTS["task_accept_seconds"]))
                if at and (now-at).total_seconds()>limit:out.append({"type":"TASK_ACCEPTANCE_SLA_BREACH","task_id":task.get("id"),"age_seconds":int((now-at).total_seconds()),"limit_seconds":limit})
            if task.get("dispatch_status")=="ACCEPTED" and not task.get("work_proof_at"):
                at=_parse(task.get("accepted_at"));limit=max(30,int(task.get("first_work_proof_timeout_seconds") or SLA_DEFAULTS["first_work_proof_seconds"]))
                if at and (now-at).total_seconds()>limit:out.append({"type":"FIRST_WORK_PROOF_SLA_BREACH","task_id":task.get("id"),"age_seconds":int((now-at).total_seconds()),"limit_seconds":limit})
            if task.get("status")=="IN_PROGRESS" and task.get("work_proof_at"):
                checkpoint_at=_parse(task.get("checkpoint_updated_at") or task.get("work_proof_at"))
                limit=max(60,int(task.get("checkpoint_max_age_seconds") or SLA_DEFAULTS["checkpoint_max_age_seconds"]))
                if checkpoint_at and (now-checkpoint_at).total_seconds()>limit:
                    out.append({"type":"CHECKPOINT_SLA_BREACH","task_id":task.get("id"),"age_seconds":int((now-checkpoint_at).total_seconds()),"limit_seconds":limit})
            if task.get("status")=="BLOCKED" and task.get("blocker"):
                out.append({"type":"BLOCKER_ESCALATION_REQUIRED","task_id":task.get("id"),"blocker":task.get("blocker")})
        for r in route_snapshot.get("seats",[]):
            if r.get("auto_routable") is True:
                hb=_parse(r.get("last_heartbeat"))
                if hb and (now-hb).total_seconds()>SLA_DEFAULTS["heartbeat_max_age_seconds"]:
                    out.append({"type":"HEARTBEAT_SLA_BREACH","seat":r.get("seat"),"age_seconds":int((now-hb).total_seconds()),"limit_seconds":SLA_DEFAULTS["heartbeat_max_age_seconds"]})
        return out

    def anti_idle(self,route_snapshot:dict[str,Any],tasks:list[dict[str,Any]])->list[dict[str,Any]]:
        done={t.get("id") for t in tasks if t.get("status")=="DONE"};out=[]
        for r in route_snapshot.get("seats",[]):
            seat=str(r.get("seat") or "").upper()
            if seat=="C1" or r.get("auto_routable") is not True:continue
            busy=any(str(t.get("claimed_by") or t.get("assigned_to") or "").upper()==seat and (t.get("status") in ("IN_PROGRESS","BLOCKED") or t.get("dispatch_status")=="PENDING_ACCEPTANCE") for t in tasks)
            if busy:continue
            eligible=[t for t in tasks if t.get("status")=="READY" and t.get("automatic_dispatch") is True and t.get("dispatch_authorized_by")=="C1" and seat in [str(x).upper() for x in (t.get("allowed_agents") or [])] and all(d in done for d in (t.get("dependencies") or [])) and self.shadow(t,tasks)["decision"]=="SAFE_PARALLEL"]
            out.append({"seat":seat,"state":"DISPATCH_EXPECTED" if eligible else "NO_ELIGIBLE_TASK","eligible_tasks":[t.get("id") for t in eligible]})
        return out

    def resume_plan(self,task:dict[str,Any])->dict[str,Any]:
        checkpoint=task.get("resume_checkpoint") if isinstance(task.get("resume_checkpoint"),dict) else None
        if checkpoint:
            return {"mode":"RESUME_FROM_CHECKPOINT","checkpoint_id":checkpoint.get("checkpoint_id"),"phase":checkpoint.get("phase"),"next_step":checkpoint.get("next_step"),"evidence_refs":checkpoint.get("evidence_refs") or []}
        return {"mode":"START_FROM_TASK_OBJECTIVE","checkpoint_id":None,"next_step":None,"evidence_refs":[]}

    def evaluate(self,route_snapshot:dict[str,Any],tasks:list[dict[str,Any]]|None=None)->dict[str,Any]:
        tasks=tasks if tasks is not None else _load(self.tasks,{"tasks":[]}).get("tasks",[])
        intents=self.peer_intents(tasks);breaches=self.sla_breaches(route_snapshot,tasks);anti=self.anti_idle(route_snapshot,tasks)
        shadows=[self.shadow(t,tasks) for t in tasks if t.get("status") in ("READY","IN_PROGRESS","BLOCKED")]
        return {
            "schema":"raios.coordination-nervous-system.v1","generated_at":utc(),
            "presence_truth":self.presence_truth(route_snapshot),"peer_intents":intents,
            "sla":dict(SLA_DEFAULTS),"sla_breaches":breaches,"anti_idle":anti,
            "coordination_shadows":shadows,
            "capabilities":{
                "CF-01":"PRESENCE_TRUTH","CF-02":"LEASE_ENFORCED_WRITE_DECISION","CF-03":"STRUCTURED_EVENTS",
                "CF-04":"DEPENDENCY_AWARE_PEER_ROUTING","CF-05":"REVIEWER_AUTO_SUBSCRIPTION",
                "CF-06":"ACCEPTANCE_TIMEOUT_ANTI_IDLE","CF-07":"BOUNDED_CHECKPOINT_CONTRACT",
                "CF-08":"CRASH_504_RESUME_PLAN","CF-09":"COORDINATION_SHADOW",
                "CF-10":"AUTOMATIC_ESCALATION_INTENTS","CF-11":"COORDINATION_SLA","CF-12":"CHAOS_TEST_CONTRACT",
            },
        }

    @staticmethod
    def chaos_contract()->list[str]:
        return [
            "PENDING_ACCEPTANCE_TIMEOUT","FIRST_WORK_PROOF_TIMEOUT","HEARTBEAT_STALE",
            "504_AFTER_CHECKPOINT","CRASH_BEFORE_CHECKPOINT","DEPENDENCY_BLOCKED",
            "LEASE_CONFLICT","CONCURRENT_WRITE","REVIEWER_UNAVAILABLE","SEAT_RECONNECT",
            "DUPLICATE_DISPATCH","MALFORMED_TIMESTAMP","STALE_CURSOR_WITH_WORKER_P0",
        ]
