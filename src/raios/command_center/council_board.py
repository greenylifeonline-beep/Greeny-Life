from __future__ import annotations
import hashlib
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .coordination_truth import (
    aliases_for_seat, build_founder_brief, build_work_lifecycle,
    canonical_seat, destructive_task_requested, dispatch_priority_score,
    founder_gate_satisfied, global_legacy_delete_gate_satisfied,
    legacy_delete_gate_satisfied, task_claim_is_current,
)
from .task_actions import TaskActionExecutor
from raios.council_ops.presence_challenge import PresenceChallengeStore

SEATS=tuple(f"C{i}" for i in range(1,13))
def utc()->str:return datetime.now(timezone.utc).isoformat()
def load(path:Path,default:Any)->Any:
    try:return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError):return default
def atomic(path:Path,data:Any)->None:
    """Write validated JSON despite transient or stable Windows rename locks."""
    path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
    json.loads(payload)
    tmp=path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
    replace_error:PermissionError|None=None
    try:
        tmp.write_text(payload,encoding="utf-8")
        for attempt in range(6):
            try:
                os.replace(tmp,path)
                return
            except PermissionError as exc:
                replace_error=exc
                if attempt<5:time.sleep(.02*(2**attempt))
        for attempt in range(8):
            try:
                with path.open("w",encoding="utf-8",newline="\n") as handle:
                    handle.write(payload);handle.flush();os.fsync(handle.fileno())
                json.loads(path.read_text(encoding="utf-8"))
                return
            except PermissionError:
                if attempt==7:raise replace_error or PermissionError("JSON_WRITE_DENIED")
                time.sleep(.05*(attempt+1))
    finally:
        try:tmp.unlink(missing_ok=True)
        except OSError:pass

class CouncilBoard:
    def __init__(self,repo:Path,presence:Path|None=None,routes:Any|None=None):
        self.repo=repo.resolve();self.tasks=self.repo/".ai-os/state/TASKS.json"
        self.locks=self.repo/".ai-os/state/LOCKS.json"
        self.foundation=self.repo/".ai-os/state/FOUNDATION.json"
        self.seat_map_path=self.repo/".ai-os/mcp/SEAT-MAP.json"
        self.presence=(presence or Path.home()/".raios/runtime/council-ops/presence.json").resolve()
        self.presence_prompts=self.presence.parent/"presence-prompts.json"
        self.coordination_cache=self.presence.parent/"coordination-sync-cache.json"
        self.presence_challenges=PresenceChallengeStore(self.presence.parent)
        self.fabric=self.repo/".ai-os/state/command-fabric"
        self.report_inbox=self.fabric/"task-reports/inbox"
        self.report_processed=self.fabric/"task-reports/processed"
        self.report_rejected=self.fabric/"task-reports/rejected"
        self.receipts=self.repo/".ai-os/receipts/command-fabric"
        self.actions=TaskActionExecutor(self.repo)
        self.routes=routes
        self.lock=threading.RLock()
        for p in (self.report_inbox,self.report_processed,self.report_rejected,self.receipts):
            p.mkdir(parents=True,exist_ok=True)
    def _live(self,target:str)->bool:
        row=load(self.presence,{"seats":{}}).get("seats",{}).get(target,{})
        if row.get("presence")!="PRESENT" or row.get("signature_valid") is not True:return False
        expiry=row.get("lease_expires_at")
        if not expiry:return True
        try:return datetime.fromisoformat(str(expiry).replace("Z","+00:00"))>datetime.now(timezone.utc)
        except (TypeError,ValueError):return False
    def _seat_map(self)->dict[str,Any]:
        return load(self.seat_map_path,{"seats":{}})
    def _global_legacy_delete_gate(self)->bool:
        return global_legacy_delete_gate_satisfied(
            load(self.foundation,{"facts":{}}))
    def _canonical_actor(self,actor:str)->str|None:
        value=str(actor or "").upper()
        if value in SEATS:return value
        return canonical_seat(value,self._seat_map())
    def _seat_aliases(self,seat:str)->set[str]:
        aliases,_=aliases_for_seat(seat,self._seat_map())
        return set(aliases)
    def _actor_session_signature(self,actor:str,proof:dict[str,Any]|None,
                                 action:str,subject_id:str)->dict[str,Any]:
        if self.routes is None:
            return {"signature_mode":"LEGACY_DIRECT_TEST","verified":True,
                    "fingerprint":hashlib.sha256(
                        f"LEGACY_DIRECT_TEST\x1f{action}\x1f{actor}\x1f{subject_id}".encode()
                    ).hexdigest()}
        if not proof:raise ValueError("ACTOR_SESSION_PROOF_REQUIRED")
        snap=self.routes.snapshot()
        route=next((x for x in snap.get("seats",[]) if str(x.get("seat") or "").upper()==actor),None)
        if not route:raise ValueError("ACTOR_ROUTE_NOT_FOUND")
        presence=load(self.presence,{"seats":{}}).get("seats",{}).get(actor,{})
        attendance=str(presence.get("attendance_fingerprint") or "")
        if not attendance:raise ValueError("ATTENDANCE_FINGERPRINT_REQUIRED")
        expected={
            "actor_id":str(route.get("actor_id") or ""),
            "session_id":str(route.get("session_id") or ""),
            "device_id":str(route.get("device_id") or ""),
            "attendance_fingerprint":attendance,
        }
        for key,value in expected.items():
            if not value or str(proof.get(key) or "")!=value:
                raise ValueError("ACTOR_SESSION_PROOF_MISMATCH::"+key)
        if route.get("auto_routable") is not True:raise ValueError("ACTOR_NOT_EXECUTION_READY")
        at=utc()
        fingerprint=hashlib.sha256("\x1f".join([
            "RAIOS_ACTOR_SESSION_SIGNATURE_V1",action,actor,subject_id,
            expected["actor_id"],expected["session_id"],expected["device_id"],
            attendance,at]).encode()).hexdigest()
        return {**expected,"signature_mode":"SESSION_BOUND_ATTENDANCE_FINGERPRINT",
                "verified":True,"signed_at":at,"fingerprint":fingerprint}
    def _evidence_manifest(self,refs:list[str])->list[dict[str,Any]]:
        manifest=[]
        for ref in list(dict.fromkeys(str(x) for x in refs if str(x).strip())):
            path=Path(ref)
            if not path.is_absolute():path=self.repo/path
            try:path=path.resolve()
            except OSError:raise ValueError("EVIDENCE_PATH_INVALID::"+ref)
            if not path.is_file():raise ValueError("EVIDENCE_NOT_FOUND::"+ref)
            digest=hashlib.sha256()
            size=0
            with path.open("rb") as handle:
                for chunk in iter(lambda:handle.read(1024*1024),b""):
                    size+=len(chunk);digest.update(chunk)
            manifest.append({"ref":ref,"resolved_path":str(path),"sha256":digest.hexdigest(),"bytes":size})
        return manifest
    def _verify_evidence_manifest(self,manifest:list[dict[str,Any]])->None:
        for item in manifest:
            current=self._evidence_manifest([str(item.get("ref") or "")])
            if not current:raise ValueError("EVIDENCE_NOT_FOUND::"+str(item.get("ref")))
            now=current[0]
            if now["sha256"]!=item.get("sha256") or now["bytes"]!=item.get("bytes"):
                raise ValueError("EVIDENCE_CHANGED_AFTER_SUBMISSION::"+str(item.get("ref")))
    def _worker_ready(self,target:str)->bool:
        if not self._live(target):return False
        if self.routes is None:return True
        try:
            row=next((x for x in self.routes.snapshot().get("seats",[])
                      if str(x.get("seat") or "").upper()==target.upper()),None)
            return bool(row and row.get("auto_routable") is True)
        except Exception:
            return False
    def _probe_unverified_seats(self,worker:Any)->int:
        if self.routes is None:return 0
        try:snapshot=self.routes.snapshot()
        except Exception:return 0
        priority={"LIVE_SESSION_REQUIRES_RESIGN":0,"DISCOVERED_LIVE_UNVERIFIED":1,
                  "PROBE_PENDING":2,"UNKNOWN":3}
        rows=sorted(snapshot.get("seats",[]),
                    key=lambda r:(priority.get(str(r.get("discovery_state") or "UNKNOWN"),9),
                                  str(r.get("seat") or "")))
        prompted=0
        for row in rows:
            if row.get("auto_routable") is True:continue
            seat=str(row.get("seat") or "").upper()
            if seat not in SEATS:continue
            challenge=self.presence_challenges.issue(
                seat,reason=str(row.get("discovery_state") or "UNKNOWN"),issued_by="RAIOS-WORKER",
                ttl_seconds=600)
            if challenge.get("status")=="ALREADY_PENDING":continue
            text=("PRESENCE_PROBE\nWORK_AUTHORITY=false\n"
                  f"SEAT={seat}\nDISCOVERY_STATE={row.get('discovery_state')}\n"
                  f"CHALLENGE_ID={challenge['challenge_id']}\nNONCE={challenge['nonce']}\n"
                  "RESPONSE_REQUIRED=AUTHENTICATED_SELF_RESPONSE\n"
                  "DELIVERY_ACK_NE_PRESENCE_PROOF=true\n"
                  "IF_AVAILABLE=SIGN_RESPONSE_AND_WAIT_FOR_RAIOS_WORKER_ASSIGNMENT\n"
                  "IF_BUSY=SIGN_RESPONSE_BUSY\nIF_OFFLINE=SIGN_RESPONSE_OFFLINE\n"
                  "SELF_CLAIM=false\nDIRECT_HANDOFF=false")
            msg=worker.enqueue("RAIOS-WORKER",[seat],text,None,
                               routing_modes={seat:"PRESENCE_DISCOVERY_PROBE"})
            self.presence_challenges.bind_message(challenge["challenge_id"],msg["message_id"])
            prompted+=1
        return prompted
    def _publish_coordination_change(self,worker:Any)->int:
        data=load(self.tasks,{"tasks":[]})
        tasks=list(data.get("tasks",[]))
        lifecycle=build_work_lifecycle(tasks)
        active=[{
            "task_id":row.get("id"),"actor":row.get("actor"),
            "status":row.get("status"),"dispatch_status":row.get("dispatch_status"),
            "scope":row.get("scope",[])
        } for row in lifecycle["buckets"]["ACTIVE_VERIFIED"]]
        stale=list(lifecycle["buckets"]["STALE_CLAIM_REQUIRES_RECONCILIATION"])
        task_index={str(t.get("id")):t for t in tasks if t.get("id")}
        locks=[]
        for x in load(self.locks,{"locks":[]}).get("locks",[]):
            if x.get("status")!="ACTIVE":continue
            task=task_index.get(str(x.get("task_id") or ""))
            reservation_state=("CURRENT_ACTIVE_RESERVATION"
                if task is not None and task_claim_is_current(task)
                else ("ORPHAN_LOCK_REQUIRES_RECONCILIATION" if task is None
                      else "STALE_TASK_LOCK_REQUIRES_RECONCILIATION"))
            locks.append({
                "lock_id":x.get("id"),"task_id":x.get("task_id"),
                "actor":x.get("lease_holder") or x.get("agent"),
                "scope":x.get("scope"),"reservation_state":reservation_state,
            })
        current_locks=[x for x in locks if x["reservation_state"]=="CURRENT_ACTIVE_RESERVATION"]
        routes=self.routes.snapshot() if self.routes is not None else {}
        coordination_available=list(routes.get("coordination_available",[]))
        presence_anomalies=[{
            "seat":row.get("seat"),
            "discovery_state":row.get("discovery_state"),
            "probe_pending":row.get("probe_pending"),
            "probe_challenge_id":row.get("probe_challenge_id"),
            "process_candidate":row.get("process_candidate"),
            "consumer_current":row.get("consumer_current"),
            "binding_current":row.get("binding_current"),
        } for row in routes.get("seats",[])
          if row.get("auto_routable") is not True and str(row.get("discovery_state") or "UNKNOWN")!="UNKNOWN"]
        founder_brief=build_founder_brief(
            tasks,founder_available="C1" in coordination_available,
            active_scope_reservations=current_locks)
        founder_brief["presence_anomalies"]=presence_anomalies
        founder_brief["presence_anomaly_count"]=len(presence_anomalies)
        founder_brief["presence_attention_required"]=bool(presence_anomalies)
        payload={
            "schema":"raios.coordination-state.v2",
            "source":"/api/client-activity",
            "active_work":active,
            "stale_work_claims":stale,
            "work_lifecycle":lifecycle,
            "founder_brief":founder_brief,
            "presence_anomalies":presence_anomalies,
            "active_scope_reservations":current_locks,
            "stale_scope_reservations":[x for x in locks if x not in current_locks],
            "coordination_available":coordination_available,
            "execution_ready":routes.get("auto_routable",[]),
        }
        canonical=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"))
        digest=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        old=load(self.coordination_cache,{})
        if old.get("digest")==digest:return 0
        at=utc()
        receipt={**payload,"schema":"raios.coordination-state-receipt.v2",
                 "system_first_at":at,"digest":digest,
                 "truth_owner":"RAIOS_SYSTEM",
                 "single_coordination_source":True,
                 "founder_brief_prepared":True}
        atomic(self.receipts/"COORDINATION-LATEST.receipt.json",receipt)
        targets=list(dict.fromkeys(coordination_available))
        message_id=None
        if targets:
            compact={
                "source":"/api/client-activity",
                "active_work":active,
                "must_do_next":founder_brief.get("must_do_next",[]),
                "founder_decisions_required":founder_brief.get("decision_count",0),
                "presence_anomaly_count":len(presence_anomalies),
                "presence_anomalies":presence_anomalies,
                "execution_ready":routes.get("auto_routable",[]),
            }
            msg=worker.enqueue("RAIOS-WORKER",targets,
                "COORDINATION_STATE_CHANGED\nWORK_AUTHORITY=false\n"+
                json.dumps(compact,ensure_ascii=False,separators=(",",":")),None)
            message_id=msg.get("message_id")
        atomic(self.coordination_cache,{
            "schema":"raios.coordination-sync-cache.v2","digest":digest,
            "updated_at":at,"message_id":message_id,"targets":targets,
            "founder_available":"C1" in coordination_available})
        return 1
    @staticmethod
    def _scope_overlap(a:str,b:str)->bool:
        a=str(a or "").replace("\\","/").rstrip("/*/")
        b=str(b or "").replace("\\","/").rstrip("/*/")
        if not a or not b:return False
        return a==b or a.startswith(b+"/") or b.startswith(a+"/")
    @staticmethod
    def _scopes(task:dict[str,Any])->list[str]:
        out=[]
        for raw in (task.get("scope") or []):
            out.extend(x.strip() for x in str(raw).split(";") if x.strip())
        return list(dict.fromkeys(out))
    def _lock_conflicts(self,task:dict[str,Any])->list[dict[str,Any]]:
        conflicts=[]
        for lock in load(self.locks,{"locks":[]}).get("locks",[]):
            if lock.get("status")!="ACTIVE" or lock.get("task_id")==task.get("id"):continue
            for wanted in self._scopes(task):
                if self._scope_overlap(wanted,lock.get("scope","")):
                    conflicts.append({"type":"ACTIVE_CANONICAL_LOCK_CONFLICT",
                                      "lock_id":lock.get("id"),"task_id":lock.get("task_id"),
                                      "holder":lock.get("lease_holder") or lock.get("agent"),
                                      "scope_a":wanted,"scope_b":lock.get("scope")})
        return conflicts
    def _acquire_task_locks(self,task:dict[str,Any],target:str,dispatch_id:str)->None:
        data=load(self.locks,{"schema_version":"1.0","locks":[]})
        rows=data.setdefault("locks",[])
        for lock in rows:
            if (lock.get("status")=="ACTIVE" and lock.get("task_id")==task.get("id") and
                    lock.get("lock_kind")=="COUNCIL_TASK_SCOPE"):
                lock.update(status="RELEASED",released_at=utc(),release_reason="REPLACED_BY_NEW_DISPATCH")
        for index,scope in enumerate(self._scopes(task)):
            rows.append({"id":f"LOCK-{dispatch_id}-{index+1}","task_id":task.get("id"),
                         "agent":target,"scope":scope,"status":"ACTIVE",
                         "owner":"RAIOS_SYSTEM","legal_owner":"RAIOS_SYSTEM",
                         "lease_holder":target,"ownership_model":"SYSTEM_OWNED_AGENT_LEASED",
                         "dispatch_id":dispatch_id,"created_at":utc(),
                         "lock_kind":"COUNCIL_TASK_SCOPE"})
        atomic(self.locks,data)
    def _release_task_locks(self,task_id:str,reason:str,*,all_kinds:bool=False)->int:
        data=load(self.locks,{"schema_version":"1.0","locks":[]});count=0
        for lock in data.get("locks",[]):
            eligible=all_kinds or lock.get("lock_kind")=="COUNCIL_TASK_SCOPE"
            if lock.get("status")=="ACTIVE" and lock.get("task_id")==task_id and eligible:
                lock.update(status="RELEASED",released_at=utc(),release_reason=reason);count+=1
        if count:atomic(self.locks,data)
        return count
    def _reconcile_stale_locks(self,data:dict[str,Any])->int:
        lock_data=load(self.locks,{"schema_version":"1.0","locks":[]})
        task_index={str(t.get("id")):t for t in data.get("tasks",[]) if t.get("id")}
        released=[]
        for lock in lock_data.get("locks",[]):
            if lock.get("status")!="ACTIVE":continue
            task_id=str(lock.get("task_id") or "")
            task=task_index.get(task_id)
            if task is not None and task_claim_is_current(task):continue
            reason=("ORPHAN_TASK_NOT_IN_CANONICAL_LEDGER" if task is None
                    else "STALE_TASK_CLAIM_NOT_CURRENT")
            lock.update(status="RELEASED",released_at=utc(),
                        release_reason=reason,
                        reconciled_by="RAIOS-WORKER")
            released.append({"lock_id":lock.get("id"),"task_id":task_id,
                             "scope":lock.get("scope"),"reason":reason})
        if released:
            atomic(self.locks,lock_data)
            atomic(self.receipts/"LOCK-RECONCILIATION-LATEST.receipt.json",{
                "schema":"raios.lock-reconciliation-receipt.v1",
                "at":utc(),"released_count":len(released),"released":released,
                "policy":"ONLY_CURRENT_VERIFIED_TASKS_RETAIN_ACTIVE_LOCKS",
                "truth_owner":"RAIOS_SYSTEM"})
        return len(released)
    def _active_conflicts(self,task:dict[str,Any],target:str,data:dict[str,Any])->list[dict[str,Any]]:
        conflicts=[]
        wanted=self._scopes(task)
        for other in data.get("tasks",[]):
            if other is task or other.get("id")==task.get("id"):continue
            active=(other.get("status") in ("IN_PROGRESS","BLOCKED") or
                    other.get("dispatch_status")=="PENDING_ACCEPTANCE")
            if not active or not task_claim_is_current(other):continue
            raw_owner=str(other.get("claimed_by") or other.get("assigned_to") or "").upper()
            owner=self._canonical_actor(raw_owner) or raw_owner
            if owner==target:
                conflicts.append({"type":"TARGET_BUSY","task_id":other.get("id"),"owner":owner})
                continue
            for left in wanted:
                for right in self._scopes(other):
                    if self._scope_overlap(left,right):
                        conflicts.append({"type":"ACTIVE_SCOPE_CONFLICT","task_id":other.get("id"),
                                          "owner":owner,"scope_a":left,"scope_b":right})
        return conflicts
    def _reconcile_absent_assignments(self,data:dict[str,Any])->int:
        returned=0;release_after=[]
        for task in data.get("tasks",[]):
            raw_target=str(task.get("assigned_to") or task.get("claimed_by") or "").upper()
            target=self._canonical_actor(raw_target)
            modern_states=("PENDING_ACCEPTANCE","ACCEPTED","CHECKPOINT_SAVED",
                           "IN_PROGRESS_REPORTED","BLOCKED_REPORTED")
            active_claim=(task.get("status") in ("IN_PROGRESS","BLOCKED") or
                          task.get("dispatch_status") in modern_states)
            if not active_claim:continue
            if task_claim_is_current(task):
                if target is None or self._worker_ready(target):
                    continue
            elif target is None and str(task.get("dispatch_status") or "").upper()=="SYSTEM_FIRST_ACTIVE":
                continue
            legacy_claim=task.get("dispatch_status") not in modern_states
            task["last_dispatch_target"]=target or raw_target
            task["last_dispatch_id"]=task.get("dispatch_id")
            task["last_claimed_by"]=task.get("claimed_by")
            task["dispatch_status"]="RETURNED_ABSENT_WITH_CHECKPOINT"
            task["status"]="READY";task["returned_at"]=utc()
            task["return_reason"]="TARGET_NOT_LIVE_BOUND_CONSUMER"
            task["legacy_claim_reconciled"]=legacy_claim
            if not task.get("resume_checkpoint"):
                checkpoint={
                    "schema":"raios.task-checkpoint.v1","checkpoint_id":"CHK-"+uuid.uuid4().hex[:16],
                    "task_id":task.get("id"),"actor":"RAIOS-WORKER","phase":"INTERRUPTED",
                    "summary":("Legacy or active executor claim had no current signed bound consumer; "
                               "RAIOS returned the task to READY with a resumable recovery checkpoint."),
                    "completed_steps":[],"changed_files":[],"validation":[],"evidence_refs":[],
                    "next_step":"Inspect the working tree and latest task evidence before continuing.",
                    "blocker":"EXECUTOR_NOT_LIVE_BOUND_CONSUMER","created_at":utc()}
                task["resume_checkpoint"]=checkpoint
                task["last_checkpoint_id"]=checkpoint["checkpoint_id"]
                task["checkpoint_updated_at"]=checkpoint["created_at"]
                atomic(self.receipts/f"{checkpoint['checkpoint_id']}.checkpoint.receipt.json",
                       {**checkpoint,"status":"SYSTEM_RECOVERY_SAVED","single_task_ledger":True})
            release_after.append(str(task.get("id") or ""))
            for key in ("assigned_to","assigned_by","dispatched_by","dispatch_id",
                        "dispatched_at","claimed_by","accepted_at"):
                task.pop(key,None)
            returned+=1
        if returned:
            atomic(self.tasks,data)
            for task_id in release_after:
                self._release_task_locks(task_id,"TARGET_NOT_LIVE_BOUND_CONSUMER",all_kinds=True)
        return returned
    def snapshot(self)->dict[str,Any]:
        data=load(self.tasks,{"tasks":[]})
        returned=self._reconcile_absent_assignments(data)
        tasks=data.get("tasks",[])
        buckets={"DONE":[],"IN_PROGRESS":[],"READY":[],"BLOCKED":[],"NEXT":[]}
        done={t.get("id") for t in tasks if t.get("status")=="DONE"}
        for task in tasks:
            status=str(task.get("status") or "UNKNOWN")
            row={"id":task.get("id"),"title":task.get("title"),"status":status,
                 "claimed_by":task.get("claimed_by"),"assigned_to":task.get("assigned_to"),
                 "dispatch_status":task.get("dispatch_status"),"dependencies":task.get("dependencies",[]),
                 "scope":task.get("scope",[]),"evidence":task.get("evidence"),
                 "resume_checkpoint":task.get("resume_checkpoint")}
            if status in buckets:buckets[status].append(row)
            if status=="READY" and all(d in done for d in task.get("dependencies",[])):
                buckets["NEXT"].append(row)
        presence=load(self.presence,{"seats":{}}).get("seats",{})
        return {"schema":"raios.council-board.v1","generated_at":utc(),
                "summary":{k:len(v) for k,v in buckets.items()},
                "buckets":buckets,"presence":presence,"returned_absent_assignments":returned,
                "single_task_ledger":True,
                "work_gate":{"signed_presence_required":True,"live_bound_consumer_required":True,
                             "worker_assignment_required":True,
                             "self_claim_allowed":False,"direct_member_handoff_allowed":False,
                             "one_active_task_per_seat":True,"active_scope_overlap_allowed":False,
                             "completion_evidence_required":True}}
    def _eligible(self,task:dict[str,Any],seat:str)->bool:
        allowed={str(x).upper() for x in task.get("allowed_agents",[])}
        if allowed and not (allowed & self._seat_aliases(seat)):return False
        required={str(x).upper() for x in task.get("required_capabilities",[]) if str(x).strip()}
        if required:
            row=load(self.presence,{"seats":{}}).get("seats",{}).get(seat,{})
            available={str(x).upper() for x in row.get("capabilities",[]) if str(x).strip()}
            if not required.issubset(available):return False
        return True
    def _evidence_exists(self,ref:str)->bool:
        try:
            path=Path(ref)
            if not path.is_absolute():path=self.repo/path
            return path.resolve().is_file()
        except (OSError,ValueError):return False
    def _build_checkpoint(self,task:dict[str,Any],actor:str,phase:str,summary:str,
                          completed_steps:list[str],changed_files:list[str],
                          validation:list[str],evidence_refs:list[str],
                          next_step:str,blocker:str|None=None)->dict[str,Any]:
        if not next_step.strip():raise ValueError("CHECKPOINT_NEXT_STEP_REQUIRED")
        refs=list(dict.fromkeys(str(x) for x in evidence_refs if str(x).strip()))
        missing=[x for x in refs if not self._evidence_exists(x)]
        if missing:raise ValueError("EVIDENCE_NOT_FOUND::"+"|".join(missing))
        return {"schema":"raios.task-checkpoint.v1",
                "checkpoint_id":"CHK-"+uuid.uuid4().hex[:16],"task_id":task.get("id"),
                "actor":actor,"phase":phase,"summary":summary,
                "completed_steps":list(dict.fromkeys(completed_steps)),
                "changed_files":list(dict.fromkeys(changed_files)),
                "validation":list(dict.fromkeys(validation)),"evidence_refs":refs,
                "next_step":next_step,"blocker":blocker,"created_at":utc()}
    def accept_task(self,task_id:str,actor:str,dispatch_id:str,
                    actor_proof:dict[str,Any]|None=None)->dict[str,Any]:
        actor=actor.upper()
        if actor not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        if not self._worker_ready(actor):raise ValueError("TARGET_NOT_LIVE_BOUND_CONSUMER")
        with self.lock:
            data=load(self.tasks,{"tasks":[]})
            task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
            if not task:raise ValueError("TASK_NOT_FOUND")
            if str(task.get("assigned_to") or "").upper()!=actor:
                raise ValueError("ACCEPTOR_NE_DISPATCH_TARGET")
            if task.get("dispatch_status")!="PENDING_ACCEPTANCE":
                raise ValueError("TASK_NOT_PENDING_ACCEPTANCE")
            if task.get("dispatch_id")!=dispatch_id:raise ValueError("DISPATCH_ID_MISMATCH")
            conflicts=self._active_conflicts(task,actor,data)
            if conflicts:
                kinds={x["type"] for x in conflicts}
                if "TARGET_BUSY" in kinds:raise ValueError("TARGET_BUSY_AT_ACCEPTANCE")
                raise ValueError("ACTIVE_SCOPE_CONFLICT_AT_ACCEPTANCE")
            if self._lock_conflicts(task):raise ValueError("ACTIVE_CANONICAL_LOCK_CONFLICT_AT_ACCEPTANCE")
            signature=self._actor_session_signature(actor,actor_proof,"TASK_ACCEPT",dispatch_id)
            task.update(status="IN_PROGRESS",claimed_by=actor,dispatch_status="ACCEPTED",
                        accepted_at=signature.get("signed_at") or utc(),
                        acceptance_fingerprint=signature["fingerprint"],
                        acceptance_signature_mode=signature["signature_mode"])
            atomic(self.tasks,data)
            receipt={"schema":"raios.task-acceptance-receipt.v2","task_id":task_id,
                     "dispatch_id":dispatch_id,"actor":actor,"status":"ACCEPTED",
                     "at":signature.get("signed_at") or utc(),
                     "acceptance_fingerprint":signature["fingerprint"],
                     "signature_mode":signature["signature_mode"],
                     "session_id":signature.get("session_id"),"device_id":signature.get("device_id"),
                     "attendance_fingerprint":signature.get("attendance_fingerprint"),
                     "resume_checkpoint":task.get("resume_checkpoint")}
            atomic(self.receipts/f"{dispatch_id}.{actor}.task-accept.receipt.json",receipt)
            return receipt
    def submit_checkpoint(self,task_id:str,actor:str,phase:str,summary:str,
                          completed_steps:list[str],changed_files:list[str],
                          validation:list[str],evidence_refs:list[str],
                          next_step:str,blocker:str|None=None,
                          actor_proof:dict[str,Any]|None=None)->dict[str,Any]:
        actor=actor.upper();phase=phase.upper()
        if actor not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        if not self._worker_ready(actor):raise ValueError("REPORTER_NOT_LIVE_BOUND_CONSUMER")
        if phase not in ("IN_PROGRESS","BLOCKED"):raise ValueError("INVALID_CHECKPOINT_PHASE")
        if phase=="BLOCKED" and not (blocker or "").strip():
            raise ValueError("BLOCKER_REQUIRED")
        with self.lock:
            data=load(self.tasks,{"tasks":[]})
            task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
            if not task:raise ValueError("TASK_NOT_FOUND")
            if str(task.get("claimed_by") or "").upper()!=actor:
                raise ValueError("CHECKPOINT_ACTOR_NE_TASK_CLAIM")
            signature=self._actor_session_signature(actor,actor_proof,"TASK_CHECKPOINT",task_id)
            checkpoint=self._build_checkpoint(task,actor,phase,summary,completed_steps,
                changed_files,validation,evidence_refs,next_step,blocker)
            task.update(resume_checkpoint=checkpoint,last_checkpoint_id=checkpoint["checkpoint_id"],
                        checkpoint_updated_at=checkpoint["created_at"],
                        status="BLOCKED" if phase=="BLOCKED" else "IN_PROGRESS",
                        dispatch_status="CHECKPOINT_SAVED")
            if blocker:task["blocker"]=blocker
            atomic(self.tasks,data)
            receipt={**checkpoint,"status":"SAVED","single_task_ledger":True,
                     "submission_fingerprint":signature["fingerprint"],
                     "signature_mode":signature["signature_mode"],
                     "attendance_fingerprint":signature.get("attendance_fingerprint"),
                     "session_id":signature.get("session_id"),"device_id":signature.get("device_id")}
            atomic(self.receipts/f"{checkpoint['checkpoint_id']}.checkpoint.receipt.json",receipt)
            return receipt
    def resume_checkpoint(self,task_id:str)->dict[str,Any]:
        data=load(self.tasks,{"tasks":[]})
        task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
        if not task:raise ValueError("TASK_NOT_FOUND")
        return {"task_id":task_id,"status":task.get("status"),
                "claimed_by":task.get("claimed_by"),"assigned_to":task.get("assigned_to"),
                "dispatch_status":task.get("dispatch_status"),
                "resume_checkpoint":task.get("resume_checkpoint"),"single_task_ledger":True}
    def submit_report(self,task_id:str,actor:str,status:str,summary:str,
                      evidence_refs:list[str],completed_steps:list[str],
                      changed_files:list[str],validation:list[str],next_step:str,
                      blocker:str|None=None,actor_proof:dict[str,Any]|None=None)->dict[str,Any]:
        actor=actor.upper();status=status.upper()
        if actor not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        if not self._worker_ready(actor):raise ValueError("REPORTER_NOT_LIVE_BOUND_CONSUMER")
        if status not in ("IN_PROGRESS","COMPLETE","BLOCKED"):raise ValueError("INVALID_REPORT_STATUS")
        if not next_step.strip():raise ValueError("CHECKPOINT_NEXT_STEP_REQUIRED")
        if status=="BLOCKED" and not (blocker or "").strip():raise ValueError("BLOCKER_REQUIRED")
        data=load(self.tasks,{"tasks":[]})
        task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
        if not task:raise ValueError("TASK_NOT_FOUND")
        if str(task.get("claimed_by") or "").upper()!=actor:
            raise ValueError("REPORTER_NE_TASK_CLAIM")
        signature=self._actor_session_signature(actor,actor_proof,"TASK_REPORT",task_id)
        if status=="COMPLETE" and not validation:raise ValueError("COMPLETION_VALIDATION_REQUIRED")
        manifest=self._evidence_manifest(evidence_refs) if evidence_refs else []
        report_id="RPT-"+uuid.uuid4().hex[:16]
        report={"schema":"raios.task-report.v1","report_id":report_id,"task_id":task_id,
                "actor":actor,"status":status,"summary":summary,
                "completed_steps":list(dict.fromkeys(completed_steps)),
                "changed_files":list(dict.fromkeys(changed_files)),
                "validation":list(dict.fromkeys(validation)),
                "evidence_refs":list(dict.fromkeys(evidence_refs)),
                "evidence_manifest":manifest,
                "submission_fingerprint":signature["fingerprint"],
                "signature_mode":signature["signature_mode"],
                "attendance_fingerprint":signature.get("attendance_fingerprint"),
                "session_id":signature.get("session_id"),"device_id":signature.get("device_id"),
                "next_step":next_step,"blocker":blocker,
                "created_at":signature.get("signed_at") or utc()}
        atomic(self.report_inbox/f"{report_id}.json",report)
        return {"status":"REPORT_QUEUED","report_id":report_id,"task_id":task_id}
    def _process_reports(self)->dict[str,int]:
        counts={"reports_processed":0,"reports_rejected":0}
        for path in sorted(self.report_inbox.glob("RPT-*.json")):
            report=load(path,{})
            try:
                if report.get("schema")!="raios.task-report.v1" or report.get("report_id")!=path.stem:
                    raise ValueError("INVALID_REPORT_SCHEMA")
                actor=str(report.get("actor") or "").upper();task_id=str(report.get("task_id") or "")
                data=load(self.tasks,{"tasks":[]})
                task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
                if not task:raise ValueError("TASK_NOT_FOUND")
                if str(task.get("claimed_by") or "").upper()!=actor:
                    raise ValueError("REPORTER_NE_TASK_CLAIM")
                status=str(report.get("status") or "").upper()
                refs=[str(x) for x in report.get("evidence_refs",[]) if str(x).strip()]
                if status=="COMPLETE" and not refs:raise ValueError("EXECUTION_EVIDENCE_REQUIRED")
                if status=="COMPLETE" and not report.get("validation"):
                    raise ValueError("COMPLETION_VALIDATION_REQUIRED")
                if self.routes is not None:
                    if not report.get("submission_fingerprint"):
                        raise ValueError("SIGNED_REPORT_REQUIRED")
                    if not task.get("acceptance_fingerprint"):
                        raise ValueError("SIGNED_TASK_ACCEPTANCE_REQUIRED")
                self._verify_evidence_manifest(list(report.get("evidence_manifest") or []))
                checkpoint=self._build_checkpoint(task,actor,status,str(report.get("summary") or ""),
                    list(report.get("completed_steps") or []),list(report.get("changed_files") or []),
                    list(report.get("validation") or []),refs,str(report.get("next_step") or ""),
                    report.get("blocker"))
                task.update(resume_checkpoint=checkpoint,last_checkpoint_id=checkpoint["checkpoint_id"],
                            checkpoint_updated_at=checkpoint["created_at"])
                if status=="COMPLETE":
                    task.update(status="DONE",claimed_by=actor,evidence="; ".join(refs),
                                report_summary=report.get("summary"),completed_at=utc(),
                                dispatch_status="COMPLETE_EVIDENCE_VERIFIED")
                elif status=="BLOCKED":
                    task.update(status="BLOCKED",claimed_by=actor,
                                blocker=report.get("blocker") or report.get("summary"),
                                evidence="; ".join(refs) if refs else task.get("evidence"),
                                dispatch_status="BLOCKED_REPORTED")
                elif status=="IN_PROGRESS":
                    task.update(status="IN_PROGRESS",claimed_by=actor,
                                report_summary=report.get("summary"),
                                dispatch_status="IN_PROGRESS_REPORTED")
                else:raise ValueError("INVALID_REPORT_STATUS")
                atomic(self.tasks,data)
                if status=="COMPLETE":
                    self._release_task_locks(task_id,"COMPLETE_EVIDENCE_VERIFIED")
                atomic(self.receipts/f"{checkpoint['checkpoint_id']}.checkpoint.receipt.json",
                       {**checkpoint,"status":"SAVED","source_report_id":path.stem,
                        "single_task_ledger":True})
                receipt={"schema":"raios.task-report-receipt.v2","report_id":path.stem,
                         "task_id":task_id,"actor":actor,"status":"ACCEPTED",
                         "task_status":task["status"],"evidence_refs":refs,
                         "evidence_manifest":report.get("evidence_manifest",[]),
                         "submission_fingerprint":report.get("submission_fingerprint"),
                         "acceptance_fingerprint":task.get("acceptance_fingerprint"),
                         "checkpoint_id":checkpoint["checkpoint_id"],"at":utc(),
                         "completion_accepted_only_after_evidence_hash_verification":status=="COMPLETE"}
                atomic(self.receipts/f"{path.stem}.task-report.receipt.json",receipt)
                atomic(self.report_processed/path.name,report);path.unlink(missing_ok=True)
                counts["reports_processed"]+=1
            except Exception as exc:
                rejection={"schema":"raios.task-report-rejection.v1","report_id":path.stem,
                           "reason":f"{type(exc).__name__}:{exc}","at":utc(),"report":report}
                atomic(self.report_rejected/path.name,rejection);path.unlink(missing_ok=True)
                counts["reports_rejected"]+=1
        return counts
    def _auto_dispatch(self,worker:Any)->int:
        data=load(self.tasks,{"tasks":[]});tasks=data.get("tasks",[])
        done={t.get("id") for t in tasks if t.get("status")=="DONE"}
        busy=set()
        for t in tasks:
            active=(t.get("status") in ("IN_PROGRESS","BLOCKED") or
                    t.get("dispatch_status")=="PENDING_ACCEPTANCE")
            if not active or not task_claim_is_current(t):continue
            raw=str(t.get("claimed_by") or t.get("assigned_to") or "").upper()
            busy.add(self._canonical_actor(raw) or raw)
        dispatched=0
        ordered=sorted(tasks,key=lambda task:(
            -dispatch_priority_score(task,tasks)["score"],str(task.get("id") or "")))
        for task in ordered:
            if (task.get("automatic_dispatch") is not True or
                task.get("dispatch_authorized_by")!="C1"):continue
            if not legacy_delete_gate_satisfied(task):continue
            if destructive_task_requested(task) and not self._global_legacy_delete_gate():continue
            if not founder_gate_satisfied(task):continue
            if task.get("status")!="READY" or task.get("claimed_by") or task.get("assigned_to"):continue
            if not all(d in done for d in task.get("dependencies",[])):continue
            candidates=[s for s in SEATS if s!="C1" and s not in busy and
                        self._worker_ready(s) and self._eligible(task,s) and
                        not self._active_conflicts(task,s,data) and
                        not self._lock_conflicts(task)]
            if not candidates:continue
            target=candidates[0]
            self.dispatch(str(task["id"]),target,worker)
            busy.add(target);dispatched+=1
        return dispatched
    def run_cycle(self,worker:Any)->dict[str,int]:
        with self.lock:
            reports=self._process_reports()
            presence_prompts=self._probe_unverified_seats(worker)
            data=load(self.tasks,{"tasks":[]})
            returned=self._reconcile_absent_assignments(data)
            locks_reconciled=self._reconcile_stale_locks(data)
            actions=self.actions.execute_ready(data)
            if actions["actions_processed"] or actions["actions_blocked"]:
                atomic(self.tasks,data)
            dispatched=self._auto_dispatch(worker)
            coordination_changes=self._publish_coordination_change(worker)
            return {**reports,**actions,"presence_prompts":presence_prompts,
                    "tasks_returned_absent":returned,"locks_reconciled":locks_reconciled,
                    "tasks_dispatched":dispatched,"coordination_changes":coordination_changes}
    def dispatch(self,task_id:str,target:str,worker:Any)->dict[str,Any]:
        target=target.upper()
        if target not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        with self.lock:
            presence=load(self.presence,{"seats":{}}).get("seats",{}).get(target,{})
            if presence.get("presence")!="PRESENT":raise ValueError("TARGET_NOT_PRESENT")
            if presence.get("signature_valid") is not True:raise ValueError("TARGET_SIGNATURE_UNVERIFIED")
            if not self._live(target):raise ValueError("TARGET_PRESENCE_EXPIRED")
            if not self._worker_ready(target):raise ValueError("TARGET_NOT_LIVE_BOUND_CONSUMER")
            data=load(self.tasks,{"tasks":[]})
            task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
            if not task:raise ValueError("TASK_NOT_FOUND")
            if task.get("status")!="READY":raise ValueError("TASK_NOT_READY_FOR_DISPATCH")
            if not legacy_delete_gate_satisfied(task):
                raise ValueError("DEEP_LEGACY_FORENSIC_AUDIT_REQUIRED")
            if destructive_task_requested(task) and not self._global_legacy_delete_gate():
                raise ValueError("GLOBAL_LEGACY_DELETE_GATE_CLOSED")
            if not founder_gate_satisfied(task):raise ValueError("FOUNDER_DECISION_REQUIRED")
            if not self._eligible(task,target):raise ValueError("SEAT_NOT_ALLOWED_FOR_TASK")
            if task.get("claimed_by") not in (None,target):raise ValueError("TASK_ALREADY_CLAIMED")
            conflicts=self._active_conflicts(task,target,data)
            if conflicts:
                kinds={x["type"] for x in conflicts}
                if "TARGET_BUSY" in kinds:raise ValueError("TARGET_BUSY")
                raise ValueError("ACTIVE_SCOPE_CONFLICT")
            lock_conflicts=self._lock_conflicts(task)
            if lock_conflicts:raise ValueError("ACTIVE_CANONICAL_LOCK_CONFLICT")
            dispatch_id="DSP-"+uuid.uuid4().hex[:16]
            self._acquire_task_locks(task,target,dispatch_id)
            try:
                task.update(assigned_to=target,assigned_by="C1",dispatched_by="RAIOS-WORKER",
                            dispatch_status="PENDING_ACCEPTANCE",dispatch_id=dispatch_id,
                            dispatched_at=utc(),system_owner="RAIOS_SYSTEM")
                atomic(self.tasks,data)
            except Exception:
                self._release_task_locks(task_id,"DISPATCH_TASK_WRITE_FAILED")
                raise
            checkpoint=task.get("resume_checkpoint") or {}
            resume=(f"\nCHECKPOINT_ID={checkpoint.get('checkpoint_id')}"
                    f"\nLAST_PHASE={checkpoint.get('phase')}"
                    f"\nNEXT_STEP={checkpoint.get('next_step')}"
                    f"\nEVIDENCE_REFS={'|'.join(checkpoint.get('evidence_refs') or [])}"
                    if checkpoint else "\nCHECKPOINT_ID=NONE\nNEXT_STEP=START_FROM_TASK_OBJECTIVE")
            text=(f"TASK_ASSIGNMENT\nTASK_ID={task_id}\nTARGET={target}\n"
                  f"DISPATCH_ID={dispatch_id}\nAUTHORITY=C1{resume}\n"
                  "WORK_GATE=SIGNED_PRESENCE_REQUIRED|ONE_ACTIVE_TASK_PER_SEAT|NO_SCOPE_OVERLAP\n"
                  "COUNCIL_STATUS=http://127.0.0.1:8770/api/client-activity\n"
                  "ACTION=ACCEPT_TASK_THEN_EXECUTE_ONLY_ASSIGNED_SCOPE_THEN_SUBMIT_EVIDENCE")
            try:
                msg=worker.enqueue("RAIOS-WORKER",[target],text,task_id)
            except Exception:
                self._release_task_locks(task_id,"DISPATCH_DELIVERY_ENQUEUE_FAILED")
                task.update(status="READY",dispatch_status="DELIVERY_ENQUEUE_FAILED")
                for key in ("assigned_to","assigned_by","dispatched_by","dispatch_id","dispatched_at"):
                    task.pop(key,None)
                atomic(self.tasks,data)
                raise
            return {"status":"DISPATCHED_PENDING_ACCEPTANCE","task_id":task_id,
                    "target":target,"dispatch_id":dispatch_id,"message_id":msg["message_id"]}
