from __future__ import annotations
import hashlib
import heapq
import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .coordination_truth import (
    aliases_for_seat, build_founder_brief, build_work_lifecycle,
    canonical_seat, destructive_task_requested, dispatch_priority_score,
    executor_backend_allows_seat, executor_backend_for_seat,
    founder_gate_satisfied, global_legacy_delete_gate_satisfied,
    legacy_delete_gate_satisfied, lock_is_effective, task_claim_is_current, task_work_proof,
)
from .task_actions import TaskActionExecutor
from .coordination_nervous_system import CoordinationNervousSystem
from raios.council_ops.presence_challenge import PresenceChallengeStore
from raios.command_fabric.lease import CommandLeaseAdapter

SEATS=tuple(f"C{i}" for i in range(1,13))
TASK_ACCEPTANCE_TIMEOUT_SECONDS=60
FIRST_WORK_PROOF_TIMEOUT_SECONDS=300
ATTENTION_BACKOFF_SECONDS=(10,30,60,120,300)
ATTENTION_PROGRESS_STALE_SECONDS=max(30,int(os.getenv("RAIOS_PROGRESS_STALE_SECONDS","300")))
ATTENTION_MAX_ITEMS=max(1,int(os.getenv("RAIOS_ATTENTION_MAX_ITEMS","128")))
ATTENTION_MAX_SECONDS=max(.05,float(os.getenv("RAIOS_ATTENTION_MAX_SECONDS","0.35")))
ATTENTION_LOW_FREQUENCY_SECONDS=max(300,int(os.getenv("RAIOS_ATTENTION_LOW_FREQUENCY_SECONDS","900")))
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
        self.command_leases=CommandLeaseAdapter(self.fabric/"leases")
        self.report_inbox=self.fabric/"task-reports/inbox"
        self.report_processed=self.fabric/"task-reports/processed"
        self.report_rejected=self.fabric/"task-reports/rejected"
        self.receipts=self.repo/".ai-os/receipts/command-fabric"
        attention_default=(self.presence.parent/"command-center/attention" if presence is not None else Path.home()/".raios/runtime/command-center/attention")
        self.attention_runtime=Path(os.getenv("RAIOS_ATTENTION_RUNTIME",str(attention_default))).resolve()
        self.attention_cursor=self.attention_runtime/"cursor.json"
        self.actions=TaskActionExecutor(self.repo)
        self.coordination=CoordinationNervousSystem(self.repo,self.presence)
        self.routes=routes
        self.lock=threading.RLock()
        for p in (self.report_inbox,self.report_processed,self.report_rejected,self.receipts,self.attention_runtime):
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
            if not row or row.get("auto_routable") is not True:
                return False
            for left,right in (("actor_id","consumer_actor_id"),("session_id","consumer_session_id"),("device_id","consumer_device_id")):
                if right in row and (not row.get(left) or row.get(left)!=row.get(right)):
                    return False
            return True
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
        nervous=self.coordination.evaluate(routes,tasks)
        nervous={k:v for k,v in nervous.items() if k!="generated_at"}
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
            "coordination_nervous_system":nervous,
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
        # Structured peer coordination travels through the existing Command Fabric.
        # No second transport/scheduler is created.
        for intent in nervous.get("peer_intents",[]):
            event=self.coordination.event(intent.get("type","DEPENDENCY_REQUEST"),
                str(intent.get("from") or "RAIOS-WORKER"),str(intent.get("task_id") or "") or None,
                targets=intent.get("to",[]),dependency_task_id=intent.get("dependency_task_id"),
                proof=intent.get("proof"),reason=intent.get("reason"))
            self.coordination.persist_event(event)
            peer_targets=[x for x in intent.get("to",[]) if x in coordination_available]
            if peer_targets:
                worker.enqueue("RAIOS-WORKER",peer_targets,
                    "COORDINATION_EVENT\nWORK_AUTHORITY=false\n"+
                    json.dumps(event,ensure_ascii=False,separators=(",",":")),intent.get("task_id"))
        for breach in nervous.get("sla_breaches",[]):
            task_id=str(breach.get("task_id") or "")
            task=task_index.get(task_id,{})
            owner=str(task.get("claimed_by") or task.get("assigned_to") or "").upper()
            review=[str(x).upper() for x in (task.get("review_by") or [])]
            escalation_targets=[x for x in dict.fromkeys(([owner] if owner else [])+review)
                                if x in coordination_available]
            event=self.coordination.event("SLA_BREACH","RAIOS-WORKER",task_id or None,
                breach=breach,targets=escalation_targets)
            self.coordination.persist_event(event)
            if escalation_targets:
                worker.enqueue("RAIOS-WORKER",escalation_targets,
                    "COORDINATION_EVENT\nWORK_AUTHORITY=false\n"+
                    json.dumps(event,ensure_ascii=False,separators=(",",":")),task_id or None)
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
            if not lock_is_effective(lock) or lock.get("task_id")==task.get("id"):continue
            for wanted in self._scopes(task):
                if self._scope_overlap(wanted,lock.get("scope","")):
                    conflicts.append({"type":"ACTIVE_CANONICAL_LOCK_CONFLICT",
                                      "lock_id":lock.get("id"),"task_id":lock.get("task_id"),
                                      "holder":lock.get("lease_holder") or lock.get("agent"),
                                      "scope_a":wanted,"scope_b":lock.get("scope")})
        return conflicts
    def _acquire_task_locks(self,task:dict[str,Any],target:str,dispatch_id:str)->list[str]:
        acquired=[]
        for scope in self._scopes(task):
            rec=self.command_leases.acquire(
                owner=target,scope=scope,task_id=str(task.get("id") or ""),
                correlation_id=dispatch_id,capability="task.scope.write",
                resource_or_target=scope,idempotency_key=f"{dispatch_id}:{scope}",
                provenance_ref="COUNCIL_BOARD_DISPATCH",ttl_seconds=1800)
            if not rec.get("ok"):
                for lease_id in acquired:self.command_leases.release(lease_id,owner=target)
                raise ValueError("COMMAND_FABRIC_SCOPE_LEASE_CONFLICT")
            acquired.append(str(rec["lease_id"]))
        return acquired
    def _release_task_locks(self,task_id:str,reason:str,*,all_kinds:bool=False)->int:
        count=0
        for rec in self.command_leases._all():
            if rec.get("state")=="ACTIVE" and str(rec.get("task_id") or "")==str(task_id):
                released=self.command_leases.release(str(rec.get("lease_id")),owner=str(rec.get("owner") or ""))
                if released.get("ok"):count+=1
        data=load(self.locks,{"schema_version":"1.0","locks":[]})
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
    def _reconcile_pending_acceptances(self,data:dict[str,Any])->int:
        returned=0;release_after=[];now_dt=datetime.now(timezone.utc)
        for task in data.get("tasks",[]):
            if str(task.get("dispatch_status") or "").upper()!="PENDING_ACCEPTANCE":continue
            target=str(task.get("assigned_to") or "").upper()
            if not target:continue
            raw=task.get("dispatched_at")
            if not raw:
                task["acceptance_reconcile_state"]="MISSING_DISPATCHED_AT";task["acceptance_reconcile_reason"]="FAIL_CLOSED_NO_RELEASE";continue
            try: dispatched_dt=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
            except (TypeError,ValueError):
                task["acceptance_reconcile_state"]="INVALID_DISPATCHED_AT";task["acceptance_reconcile_reason"]="FAIL_CLOSED_NO_RELEASE";continue
            timeout=max(30,int(task.get("acceptance_timeout_seconds") or TASK_ACCEPTANCE_TIMEOUT_SECONDS))
            if (now_dt-dispatched_dt).total_seconds()<timeout:continue
            did=task.get("dispatch_id");task["last_dispatch_target"]=target;task["last_dispatch_id"]=did;task["last_dispatched_at"]=raw
            task["dispatch_status"]="RETURNED_NO_ACCEPTANCE";task["status"]="READY";task["returned_at"]=utc();task["return_reason"]="ACCEPTANCE_TIMEOUT";task["acceptance_timeout_seconds_applied"]=timeout
            checkpoint={"schema":"raios.task-checkpoint.v1","checkpoint_id":"CHK-"+uuid.uuid4().hex[:16],"task_id":task.get("id"),"actor":"RAIOS-WORKER","phase":"PENDING_ACCEPTANCE_TIMEOUT","summary":"Task dispatch was not accepted within the bounded acceptance window; assignment returned to READY.","completed_steps":[],"changed_files":[],"validation":[],"evidence_refs":[],"next_step":"Redispatch only to a current eligible live-bound seat.","blocker":"ACCEPTANCE_TIMEOUT","created_at":utc(),"previous_dispatch_id":did,"previous_target":target,"dispatched_at":raw,"timeout_seconds":timeout}
            task["last_system_recovery_checkpoint"]=checkpoint
            if not task.get("resume_checkpoint"):
                task["resume_checkpoint"]=checkpoint;task["last_checkpoint_id"]=checkpoint["checkpoint_id"];task["checkpoint_updated_at"]=checkpoint["created_at"]
            atomic(self.receipts/f"{checkpoint['checkpoint_id']}.checkpoint.receipt.json",{**checkpoint,"status":"SYSTEM_RECOVERY_SAVED","single_task_ledger":True})
            release_after.append(str(task.get("id") or ""))
            for key in ("assigned_to","assigned_by","dispatched_by","dispatch_id","dispatched_at","claimed_by","accepted_at","acceptance_fingerprint","acceptance_signature_mode"):task.pop(key,None)
            returned+=1
        if returned:
            atomic(self.tasks,data)
            for task_id in release_after:self._release_task_locks(task_id,"ACCEPTANCE_TIMEOUT",all_kinds=True)
        return returned
    def _reconcile_unproven_acceptances(self,data:dict[str,Any])->int:
        returned=0;release_after=[]
        now_dt=datetime.now(timezone.utc)
        for task in data.get("tasks",[]):
            if str(task.get("status") or "").upper()!="IN_PROGRESS":continue
            if str(task.get("dispatch_status") or "").upper()!="ACCEPTED":continue
            if task_work_proof(task).get("proven") is True:continue
            backend=task.get("executor_backend") if isinstance(task.get("executor_backend"),dict) else {}
            backend_state=str(backend.get("state") or task.get("executor_state") or "").upper()
            unavailable=backend_state in {
                "UNAVAILABLE","DISABLED","BLOCKED","NOT_BOUND","NO_EXECUTOR",
                "PRODUCT_GATE_DISABLED","FEATURE_GATE_DISABLED",
            }
            accepted_at=task.get("accepted_at")
            try:
                accepted_dt=datetime.fromisoformat(str(accepted_at).replace("Z","+00:00"))
            except (TypeError,ValueError):
                accepted_dt=None
            timeout=max(30,int(task.get("first_work_proof_timeout_seconds") or
                               FIRST_WORK_PROOF_TIMEOUT_SECONDS))
            timed_out=bool(
                accepted_dt is not None and
                (now_dt-accepted_dt).total_seconds()>=timeout
            )
            if not unavailable and not timed_out:continue
            reason=("EXECUTOR_BACKEND_UNAVAILABLE" if unavailable
                    else "FIRST_WORK_PROOF_TIMEOUT")
            task["last_dispatch_target"]=task.get("assigned_to") or task.get("claimed_by")
            task["last_dispatch_id"]=task.get("dispatch_id")
            task["last_claimed_by"]=task.get("claimed_by")
            task["last_acceptance_fingerprint"]=task.get("acceptance_fingerprint")
            task["last_acceptance_signature_mode"]=task.get("acceptance_signature_mode")
            task["last_accepted_at"]=task.get("accepted_at")
            task["dispatch_status"]="RETURNED_NO_FIRST_WORK_PROOF"
            task["status"]="READY";task["returned_at"]=utc()
            task["return_reason"]=reason
            task["work_proof_state"]="UNPROVEN"
            task["executor_backend_snapshot"]=backend or None
            checkpoint={
                "schema":"raios.task-checkpoint.v1",
                "checkpoint_id":"CHK-"+uuid.uuid4().hex[:16],
                "task_id":task.get("id"),"actor":"RAIOS-WORKER",
                "phase":"ACCEPTED_NO_WORK_PROOF",
                "summary":(
                    "Task acceptance was authenticated, but no post-acceptance "
                    "executor/progress/checkpoint/evidence proof was observed. "
                    "RAIOS returned the task to READY without claiming work occurred."
                ),
                "completed_steps":[],"changed_files":[],"validation":[],
                "evidence_refs":[],
                "previous_checkpoint_id":(
                    (task.get("resume_checkpoint") or {}).get("checkpoint_id")
                    if isinstance(task.get("resume_checkpoint"),dict) else None
                ),
                "next_step":(
                    "Bind a verified execution backend or produce a first signed "
                    "work checkpoint before claiming ACTIVE_VERIFIED."
                ),
                "blocker":reason,"created_at":utc(),
            }
            task["last_system_recovery_checkpoint"]=checkpoint
            if not task.get("resume_checkpoint"):
                task["resume_checkpoint"]=checkpoint
                task["last_checkpoint_id"]=checkpoint["checkpoint_id"]
                task["checkpoint_updated_at"]=checkpoint["created_at"]
            atomic(
                self.receipts/f"{checkpoint['checkpoint_id']}.checkpoint.receipt.json",
                {**checkpoint,"status":"SYSTEM_RECOVERY_SAVED",
                 "single_task_ledger":True},
            )
            release_after.append(str(task.get("id") or ""))
            for key in (
                "assigned_to","assigned_by","dispatched_by","dispatch_id",
                "dispatched_at","claimed_by","accepted_at",
                "acceptance_fingerprint","acceptance_signature_mode",
                "first_work_proof_deadline","executor_backend",
            ):
                task.pop(key,None)
            returned+=1
        if returned:
            atomic(self.tasks,data)
            for task_id in release_after:
                self._release_task_locks(
                    task_id,"NO_FIRST_WORK_PROOF",all_kinds=True)
        return returned
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
    def _projection_row(self,task:dict[str,Any],done:set[str])->dict[str,Any]:
        status=str(task.get("status") or "UNKNOWN").upper()
        deps=list(task.get("dependencies") or [])
        deps_done=all(d in done for d in deps)
        stage=("DONE" if status=="DONE" else "DOING" if status=="IN_PROGRESS" else
               "NEXT" if status=="READY" and deps_done else "WAITING" if status=="READY" else
               "BLOCKED" if status=="BLOCKED" else status)
        checkpoint=task.get("resume_checkpoint") if isinstance(task.get("resume_checkpoint"),dict) else {}
        reviewers=list(task.get("review_by") or task.get("reviewers") or task.get("required_reviewers") or [])
        evidence=task.get("evidence")
        evidence_refs=list(task.get("evidence_refs") or checkpoint.get("evidence_refs") or [])
        checkpoint_id=str(task.get("last_checkpoint_id") or checkpoint.get("checkpoint_id") or "")
        checkpoint_receipt=self.receipts/f"{checkpoint_id}.checkpoint.receipt.json" if checkpoint_id else None
        proof_ref=(str(evidence) if evidence else
                   str(evidence_refs[-1]) if evidence_refs else
                   str(checkpoint_receipt.relative_to(self.repo)) if checkpoint_receipt and checkpoint_receipt.is_file() else None)
        proof_exists=self._evidence_exists(proof_ref) if proof_ref else False
        review_status=str(task.get("review_status") or ("REVIEW_REQUIRED" if reviewers else "NOT_REQUIRED"))
        return {"id":task.get("id"),"title":task.get("title"),"status":status,"stage":stage,
                "owner":task.get("assigned_to") or task.get("claimed_by") or task.get("executed_by"),
                "model":task.get("model") or task.get("model_id") or task.get("active_model") or task.get("selected_model"),
                "start":task.get("started_at") or task.get("accepted_at") or task.get("dispatched_at") or task.get("created_at"),
                "last_proof":proof_ref,"last_proof_exists":proof_exists,
                "last_proof_at":task.get("completed_at") or task.get("checkpoint_updated_at") or task.get("last_accepted_at") or task.get("updated_at"),
                "reviewer":reviewers,"review_status":review_status,
                "next_checkpoint":task.get("next_step") or checkpoint.get("next_step"),
                "blocker":task.get("blocker") or checkpoint.get("blocker") or task.get("return_reason"),
                "claimed_by":task.get("claimed_by"),"assigned_to":task.get("assigned_to"),
                "dispatch_status":task.get("dispatch_status"),"dependencies":deps,"scope":task.get("scope",[]),
                "priority":task.get("scheduler_priority"),"entity":task.get("entity"),
                "evidence":evidence,"resume_checkpoint":checkpoint or None}
    def snapshot(self)->dict[str,Any]:
        data=load(self.tasks,{"tasks":[]})
        returned_unproven=self._reconcile_unproven_acceptances(data)
        data=load(self.tasks,{"tasks":[]}) if returned_unproven else data
        returned=self._reconcile_absent_assignments(data)
        tasks=data.get("tasks",[])
        buckets={"DONE":[],"IN_PROGRESS":[],"READY":[],"BLOCKED":[],"NEXT":[]}
        done={t.get("id") for t in tasks if t.get("status")=="DONE"}
        projected=[]
        for task in tasks:
            row=self._projection_row(task,done);projected.append(row);status=row["status"]
            if status in buckets:buckets[status].append(row)
            if row["stage"]=="NEXT":buckets["NEXT"].append(row)
        presence=load(self.presence,{"seats":{}}).get("seats",{})
        from .board_now import now_from_projected
        now=now_from_projected(projected,tasks)
        return {"schema":"raios.council-board.v2","generated_at":utc(),
                "projection_sources":["TASKS","PRESENCE","TASK_CHECKPOINTS","RECEIPTS","EVIDENCE"],
                "legacy_now_md_authoritative":False,"tasks":projected,"now":now,
                "now_ne_full_ledger":True,"ledger_total":len(projected),
                "active_program_id":data.get("active_program_id"),
                "summary":{k:len(v) for k,v in buckets.items()},
                "buckets":buckets,"presence":presence,
                "returned_absent_assignments":returned,
                "returned_unproven_acceptances":returned_unproven,
                "single_task_ledger":True,
                "work_gate":{"signed_presence_required":True,"live_bound_consumer_required":True,
                             "worker_assignment_required":False,
                             "self_claim_allowed":True,
                             "self_claim_mode":"GOVERNED_ATOMIC_SELF_CLAIM",
                             "direct_member_handoff_allowed":False,
                             "one_active_task_per_seat":True,"active_scope_overlap_allowed":False,
                             "completion_evidence_required":True}}
    def _claim_mode(self,task:dict[str,Any])->str:
        mode=str(task.get("claim_mode") or "").upper()
        if mode in {"AUTO_ONLY","SELF_CLAIM_ALLOWED","ASSIGNMENT_ONLY","C1_ONLY"}:return mode
        return "SELF_CLAIM_ALLOWED" if task.get("self_claim_allowed") is True else "AUTO_ONLY"
    def _eligible(self,task:dict[str,Any],seat:str)->bool:
        allowed={str(x).upper() for x in task.get("allowed_agents",[])}
        if allowed and not (allowed & self._seat_aliases(seat)):return False
        required={str(x).upper() for x in task.get("required_capabilities",[]) if str(x).strip()}
        if required:
            row=load(self.presence,{"seats":{}}).get("seats",{}).get(seat,{})
            available={str(x).upper() for x in row.get("capabilities",[]) if str(x).strip()}
            if not required.issubset(available):return False
        return executor_backend_allows_seat(task,seat)


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
    def claimable_tasks(self,actor:str)->dict[str,Any]:
        actor=actor.upper()
        if actor not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        if not self._worker_ready(actor):raise ValueError("ACTOR_NOT_EXECUTION_READY")
        with self.lock:
            data=load(self.tasks,{"tasks":[]});tasks=data.get("tasks",[])
            done={t.get("id") for t in tasks if t.get("status")=="DONE"}
            rows=[]
            for task in tasks:
                if task.get("status")!="READY" or task.get("claimed_by") or task.get("assigned_to"):continue
                if self._claim_mode(task)!="SELF_CLAIM_ALLOWED":continue
                if not all(d in done for d in task.get("dependencies",[])):continue
                if not legacy_delete_gate_satisfied(task):continue
                if destructive_task_requested(task) and not self._global_legacy_delete_gate():continue
                if not founder_gate_satisfied(task) or not self._eligible(task,actor):continue
                if self._active_conflicts(task,actor,data) or self._lock_conflicts(task):continue
                rows.append(self._projection_row(task,done))
            rows.sort(key=lambda t:(-dispatch_priority_score(next(x for x in tasks if x.get("id")==t["id"]),tasks)["score"],str(t["id"])))
            return {"schema":"raios.claimable-tasks.v1","actor":actor,"count":len(rows),"tasks":rows,"single_task_ledger":True}
    def claim_task(self,task_id:str,actor:str,actor_proof:dict[str,Any]|None=None)->dict[str,Any]:
        actor=actor.upper()
        if actor not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        if not self._worker_ready(actor):raise ValueError("ACTOR_NOT_EXECUTION_READY")
        with self.lock:
            data=load(self.tasks,{"tasks":[]});tasks=data.get("tasks",[])
            task=next((t for t in tasks if t.get("id")==task_id),None)
            if not task:raise ValueError("TASK_NOT_FOUND")
            if task.get("status")!="READY" or task.get("claimed_by") or task.get("assigned_to"):raise ValueError("TASK_ALREADY_CLAIMED_OR_NOT_READY")
            if self._claim_mode(task)!="SELF_CLAIM_ALLOWED":raise ValueError("SELF_CLAIM_NOT_ALLOWED")
            done={t.get("id") for t in tasks if t.get("status")=="DONE"}
            if not all(d in done for d in task.get("dependencies",[])):raise ValueError("TASK_DEPENDENCIES_NOT_SATISFIED")
            if not legacy_delete_gate_satisfied(task):raise ValueError("DEEP_LEGACY_FORENSIC_AUDIT_REQUIRED")
            if destructive_task_requested(task) and not self._global_legacy_delete_gate():raise ValueError("GLOBAL_LEGACY_DELETE_GATE_CLOSED")
            if not founder_gate_satisfied(task):raise ValueError("FOUNDER_DECISION_REQUIRED")
            if not self._eligible(task,actor):raise ValueError("SEAT_NOT_ALLOWED_FOR_TASK")
            if self._active_conflicts(task,actor,data):raise ValueError("ACTIVE_TASK_OR_SCOPE_CONFLICT")
            if self._lock_conflicts(task):raise ValueError("ACTIVE_CANONICAL_LOCK_CONFLICT")
            signature=self._actor_session_signature(actor,actor_proof,"TASK_SELF_CLAIM",task_id)
            claim_id="CLM-"+uuid.uuid4().hex[:16]
            self._acquire_task_locks(task,actor,claim_id)
            try:
                at=signature.get("signed_at") or utc();task.update(assigned_to=actor,assigned_by=actor,dispatched_by="SELF_CLAIM",dispatch_status="PENDING_ACCEPTANCE",dispatch_id=claim_id,dispatched_at=at,system_owner="RAIOS_SYSTEM",claim_origin="GOVERNED_SELF_CLAIM")
                atomic(self.tasks,data)
            except Exception:
                self._release_task_locks(task_id,"SELF_CLAIM_TASK_WRITE_FAILED");raise
            receipt={"schema":"raios.task-self-claim-receipt.v1","claim_id":claim_id,"task_id":task_id,"actor":actor,"status":"CLAIMED_PENDING_ACCEPTANCE","at":at,"claim_fingerprint":signature["fingerprint"],"signature_mode":signature["signature_mode"],"single_task_ledger":True}
            atomic(self.receipts/f"{claim_id}.{actor}.task-self-claim.receipt.json",receipt)
            return receipt
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
            if task.get("dispatch_status") not in (
                "PENDING_ACCEPTANCE",
                "SELF_CLAIMED_PENDING_ACCEPTANCE",
            ):
                raise ValueError("TASK_NOT_PENDING_ACCEPTANCE")
            if task.get("dispatch_id")!=dispatch_id:raise ValueError("DISPATCH_ID_MISMATCH")
            conflicts=self._active_conflicts(task,actor,data)
            if conflicts:
                kinds={x["type"] for x in conflicts}
                if "TARGET_BUSY" in kinds:raise ValueError("TARGET_BUSY_AT_ACCEPTANCE")
                raise ValueError("ACTIVE_SCOPE_CONFLICT_AT_ACCEPTANCE")
            if self._lock_conflicts(task):raise ValueError("ACTIVE_CANONICAL_LOCK_CONFLICT_AT_ACCEPTANCE")
            lease=self.coordination.lease_write_decision(actor,task_id,self._scopes(task),require_lease=True)
            if lease.get("allowed") is not True:
                raise ValueError("TASK_SCOPE_LEASE_REQUIRED_AT_ACCEPTANCE::"+str(lease.get("decision")))
            signature=self._actor_session_signature(actor,actor_proof,"TASK_ACCEPT",dispatch_id)
            accepted_at=signature.get("signed_at") or utc()
            accepted_dt=datetime.fromisoformat(str(accepted_at).replace("Z","+00:00"))
            timeout=max(30,int(task.get("first_work_proof_timeout_seconds") or
                               FIRST_WORK_PROOF_TIMEOUT_SECONDS))
            deadline=(accepted_dt+timedelta(seconds=timeout)).isoformat()
            selected_backend=executor_backend_for_seat(task,actor)
            task.update(status="IN_PROGRESS",claimed_by=actor,dispatch_status="ACCEPTED",
                        accepted_at=accepted_at,
                        first_work_proof_deadline=deadline,
                        work_proof_state="UNPROVEN",
                        acceptance_fingerprint=signature["fingerprint"],
                        acceptance_signature_mode=signature["signature_mode"])
            if selected_backend is not None:
                task["executor_backend"]=dict(selected_backend)
            else:
                task.pop("executor_backend",None)
            atomic(self.tasks,data)
            receipt={"schema":"raios.task-acceptance-receipt.v3","task_id":task_id,
                     "dispatch_id":dispatch_id,"actor":actor,"status":"ACCEPTED",
                     "at":accepted_at,
                     "first_work_proof_deadline":deadline,
                     "work_proof_state":"UNPROVEN",
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
    @staticmethod
    def _attention_dt(value:Any)->datetime|None:
        if not value:return None
        try:return datetime.fromisoformat(str(value).replace("Z","+00:00"))
        except (TypeError,ValueError):return None
    def _attention_routes(self)->dict[str,dict[str,Any]]:
        if self.routes is None:return {}
        try:rows=self.routes.snapshot().get("seats",[])
        except Exception:return {}
        return {str(r.get("seat") or "").upper():r for r in rows if r.get("seat")}
    def _attention_event(self,mid:str,seat:str,event:str,**extra:Any)->Path:
        suffix=event.lower().replace("_","-")
        n=extra.get("pulse_count")
        key=hashlib.sha256(mid.encode("utf-8")).hexdigest()[:16]
        name=f"ATN-{key}.{seat}.{suffix}{('.'+str(n)) if n is not None else ''}.receipt.json"
        path=self.receipts/name
        if not path.exists():
            atomic(path,{"schema":"raios.command-fabric-attention-event.v1","message_id":mid,
                "target":seat,"event":event,"at":utc(),"head":self._head(),
                "work_authority":False,**extra})
        return path
    def _head(self)->str:
        try:
            head=os.getenv("RAIOS_CANONICAL_HEAD","").strip()
            if head:return head
            git=self.repo/".git/HEAD"
            if git.is_file():return hashlib.sha256(git.read_bytes()).hexdigest()[:40]
        except OSError:pass
        return "UNKNOWN"
    def _attention_message(self,mid:str)->dict[str,Any]:
        return load(self.fabric/"inbox"/f"{mid}.json",{})
    def _attention_pulse_rows(self,mid:str,seat:str,kind:str)->list[dict[str,Any]]:
        key=hashlib.sha256(mid.encode("utf-8")).hexdigest()[:16]
        prefix=f"ATN-{key}.{seat}.{kind.lower().replace('_','-')}."
        rows=[]
        try:
            for path in self.receipts.glob(prefix+"*.receipt.json"):
                row=load(path,{})
                if row.get("event")==kind:rows.append(row)
        except OSError:pass
        return rows
    def _attention_rebuild(self,mid:str,seat:str,tasks:dict[str,dict[str,Any]],
                           routes:dict[str,dict[str,Any]])->dict[str,Any]|None:
        send=load(self.receipts/f"{mid}.send.json",{})
        msg=self._attention_message(mid);payload=msg.get("payload") or {}
        text=str(payload.get("text") or "")
        if text.startswith(("ATTENTION_PULSE\n","PROGRESS_PULSE\n")):return None
        task_id=payload.get("task_id")
        delivery=load(self.receipts/f"{mid}.{seat}.delivery.ack.receipt.json",{})
        actor=load(self.receipts/f"{mid}.{seat}.actor.ack.receipt.json",{})
        if not task_id:task_id=actor.get("task_id")
        task=tasks.get(str(task_id)) if task_id else None
        route=routes.get(seat,{})
        current_session=str(route.get("session_id") or "")
        actor_session=str(actor.get("session_id") or "")
        actor_ok=(actor.get("ack_type")=="ACTOR_ACK" and actor.get("synthetic") is not True and
                  str(actor.get("status") or "").upper() in {"READ","ACKNOWLEDGED","DONE"} and
                  str(actor.get("seat") or actor.get("target") or "").upper()==seat and
                  route.get("consumer_current") is True and bool(current_session) and actor_session==current_session)
        delivery_at=delivery.get("at") if delivery.get("ack_type")=="DELIVERY_ACK" else None
        attention_at=actor.get("at") if actor_ok else None
        response_required=bool(payload.get("response_required",False))
        action_required=bool(payload.get("action_required",False) or task_id)
        lifecycle="SENT";action_at=None;last_progress_at=None;terminal=None;reason=None
        if delivery_at:lifecycle="DELIVERED"
        if attention_at:lifecycle="ATTENTION_ACKNOWLEDGED"
        if task:
            status=str(task.get("status") or "").upper();dispatch=str(task.get("dispatch_status") or "").upper()
            if status=="DONE":terminal="COMPLETED";reason="TASK_DONE";lifecycle="COMPLETED"
            elif status=="BLOCKED":terminal="BLOCKED";reason=str(task.get("blocker") or "TASK_BLOCKED");lifecycle="BLOCKED"
            elif status in {"CANCELLED","CANCELED"}:terminal="CANCELLED_BY_C1";reason="TASK_CANCELLED";lifecycle=terminal
            elif status=="SUPERSEDED":terminal="SUPERSEDED";reason="TASK_SUPERSEDED";lifecycle=terminal
            elif dispatch=="PENDING_ACCEPTANCE":lifecycle="DELIVERED" if delivery_at else "SENT"
            elif status=="IN_PROGRESS":
                action_at=task.get("accepted_at") or task.get("last_accepted_at")
                checkpoint=task.get("resume_checkpoint") if isinstance(task.get("resume_checkpoint"),dict) else {}
                last_progress_at=(task.get("checkpoint_updated_at") or task.get("work_proof_at") or
                                  checkpoint.get("created_at") or action_at)
                lifecycle="WORKING" if (task.get("work_proof_state")=="PROVEN" or checkpoint or dispatch=="CHECKPOINT_SAVED" or task.get("work_proof_at")) else "TASK_ACCEPTED"
        elif attention_at and not response_required and not action_required:
            terminal="ACKNOWLEDGED_NO_ACTION";reason="GENUINE_ACTOR_ACK_NOTICE_ONLY";lifecycle=terminal
        att_rows=self._attention_pulse_rows(mid,seat,"ATTENTION_PULSE")
        prog_rows=self._attention_pulse_rows(mid,seat,"PROGRESS_PULSE")
        pulse_count=len(att_rows)+len(prog_rows)
        next_attention=None
        base=self._attention_dt(delivery_at or send.get("at"))
        if not terminal and not attention_at and delivery_at and base:
            idx=len(att_rows)
            if idx<len(ATTENTION_BACKOFF_SECONDS):due=base+timedelta(seconds=ATTENTION_BACKOFF_SECONDS[idx])
            else:due=base+timedelta(seconds=ATTENTION_BACKOFF_SECONDS[-1]+ATTENTION_LOW_FREQUENCY_SECONDS*(idx-len(ATTENTION_BACKOFF_SECONDS)+1))
            next_attention=due.isoformat()
        return {"schema":"raios.command-fabric-attention-state.v1","message_id":mid,"target":seat,
            "task_id":task_id,"sent_at":send.get("at") or msg.get("created_at"),"delivery_ack_at":delivery_at,
            "attention_ack_at":attention_at,"action_at":action_at,"last_progress_at":last_progress_at,
            "pulse_count":pulse_count,"attention_pulse_count":len(att_rows),"progress_pulse_count":len(prog_rows),
            "next_attention_at":next_attention,"response_required":response_required,"action_required":action_required,
            "lifecycle_state":lifecycle,"terminal_state":terminal,"terminal_at":utc() if terminal else None,
            "terminal_reason":reason,"head":self._head(),"reconciled_from_durable_evidence":True}
    def _attention_persist_events(self,state:dict[str,Any])->None:
        mid=str(state["message_id"]);seat=str(state["target"])
        self._attention_event(mid,seat,"REGISTERED",task_id=state.get("task_id"))
        if state.get("delivery_ack_at"):self._attention_event(mid,seat,"DELIVERED",delivery_ack_at=state["delivery_ack_at"])
        if state.get("attention_ack_at"):self._attention_event(mid,seat,"ATTENTION_ACKNOWLEDGED",attention_ack_at=state["attention_ack_at"])
        if state.get("action_at"):self._attention_event(mid,seat,"TASK_ACCEPTED",action_at=state["action_at"])
        if state.get("lifecycle_state")=="WORKING":self._attention_event(mid,seat,"WORKING",last_progress_at=state.get("last_progress_at"))
        if state.get("terminal_state"):self._attention_event(mid,seat,str(state["terminal_state"]),reason=state.get("terminal_reason"))
    def _attention_maybe_pulse(self,state:dict[str,Any],worker:Any)->str|None:
        if state.get("terminal_state"):return None
        now=datetime.now(timezone.utc);mid=str(state["message_id"]);seat=str(state["target"]);task_id=state.get("task_id")
        due=self._attention_dt(state.get("next_attention_at"))
        if due and now>=due and not state.get("attention_ack_at"):
            count=int(state.get("attention_pulse_count") or 0)+1
            worker.enqueue("RAIOS-WORKER",[seat],f"ATTENTION_PULSE\nWORK_AUTHORITY=false\nMESSAGE_ID={mid}\nPULSE={count}",task_id)
            self._attention_event(mid,seat,"ATTENTION_PULSE",pulse_count=count,reason="DELIVERED_WITHOUT_GENUINE_ACTOR_ATTENTION")
            return "ATTENTION_PULSE"
        if state.get("lifecycle_state") in {"TASK_ACCEPTED","WORKING"}:
            progress=self._attention_dt(state.get("last_progress_at") or state.get("action_at"))
            rows=self._attention_pulse_rows(mid,seat,"PROGRESS_PULSE")
            if rows:
                latest=max((self._attention_dt(r.get("at")) for r in rows),default=None)
                if latest and (progress is None or latest>progress):progress=latest
            if progress and (now-progress).total_seconds()>=ATTENTION_PROGRESS_STALE_SECONDS:
                count=len(rows)+1
                worker.enqueue("RAIOS-WORKER",[seat],f"PROGRESS_PULSE\nWORK_AUTHORITY=false\nMESSAGE_ID={mid}\nPULSE={count}",task_id)
                self._attention_event(mid,seat,"PROGRESS_PULSE",pulse_count=count,reason="WORK_EVIDENCE_STALE")
                return "PROGRESS_PULSE"
        return None
    def _attention_followup_cycle(self,worker:Any)->dict[str,int]:
        started=time.monotonic();processed=0;attention_pulses=0;progress_pulses=0;terminal=0
        head=self._head();cursor=load(self.attention_cursor,{})
        if not isinstance(cursor,dict) or cursor.get("head")!=head:cursor={"head":head,"after":""}
        after=str(cursor.get("after") or "")
        try:
            names=heapq.nsmallest(ATTENTION_MAX_ITEMS,
                (e.name for e in os.scandir(self.receipts) if e.name.endswith('.send.json') and e.name>after))
        except OSError:names=[]
        if not names and after:
            after=""
            try:names=heapq.nsmallest(ATTENTION_MAX_ITEMS,(e.name for e in os.scandir(self.receipts) if e.name.endswith('.send.json')))
            except OSError:names=[]
        tasks={str(t.get("id")):t for t in load(self.tasks,{"tasks":[]}).get("tasks",[]) if t.get("id")}
        routes=self._attention_routes();last=after
        for name in names:
            if processed>0 and (processed>=ATTENTION_MAX_ITEMS or time.monotonic()-started>=ATTENTION_MAX_SECONDS):break
            mid=name[:-10];send=load(self.receipts/name,{})
            for seat in [str(x).upper() for x in send.get("targets",[]) if str(x).upper() in SEATS]:
                if processed>0 and time.monotonic()-started>=ATTENTION_MAX_SECONDS:break
                state=self._attention_rebuild(mid,seat,tasks,routes)
                if state is None:continue
                self._attention_persist_events(state)
                pulse=self._attention_maybe_pulse(state,worker)
                if pulse=="ATTENTION_PULSE":attention_pulses+=1
                elif pulse=="PROGRESS_PULSE":progress_pulses+=1
                if state.get("terminal_state"):terminal+=1
                atomic(self.attention_runtime/f"{mid}.{seat}.json",state)
            last=name;processed+=1
        atomic(self.attention_cursor,{"schema":"raios.attention-cursor.v1","head":head,"after":last,"updated_at":utc(),"non_authoritative":True})
        return {"attention_items_processed":processed,"attention_pulses":attention_pulses,
                "progress_pulses":progress_pulses,"attention_terminal":terminal}
    def attention_snapshot(self,message_id:str|None=None)->dict[str,Any]:
        rows=[]
        pattern=f"{message_id}.*.json" if message_id else "MSG-*.json"
        for path in self.attention_runtime.glob(pattern):
            if path.name=="cursor.json":continue
            row=load(path,{})
            if row:rows.append(row)
        rows.sort(key=lambda r:(str(r.get("message_id")),str(r.get("target"))))
        return {"schema":"raios.command-fabric-attention.v1","generated_at":utc(),
            "message_id":message_id,"count":len(rows),"states":rows,
            "runtime_state_authoritative":False,"durable_receipts_authoritative":True,
            "backoff_seconds":list(ATTENTION_BACKOFF_SECONDS),"progress_stale_seconds":ATTENTION_PROGRESS_STALE_SECONDS}

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
            returned_unaccepted=self._reconcile_pending_acceptances(data)
            data=load(self.tasks,{"tasks":[]}) if returned_unaccepted else data
            returned_unproven=self._reconcile_unproven_acceptances(data)
            data=load(self.tasks,{"tasks":[]}) if returned_unproven else data
            returned=self._reconcile_absent_assignments(data)
            data=load(self.tasks,{"tasks":[]}) if returned else data
            locks_reconciled=self._reconcile_stale_locks(data)
            actions=self.actions.execute_ready(data)
            if actions["actions_processed"] or actions["actions_blocked"]:
                atomic(self.tasks,data)
            dispatched=self._auto_dispatch(worker)
            coordination_changes=self._publish_coordination_change(worker)
            attention=self._attention_followup_cycle(worker)
            return {**reports,**actions,**attention,"presence_prompts":presence_prompts,
                    "tasks_returned_unaccepted":returned_unaccepted,
                    "tasks_returned_unproven":returned_unproven,
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
            scope_lease_ids=self._acquire_task_locks(task,target,dispatch_id)
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
                    "target":target,"dispatch_id":dispatch_id,"message_id":msg["message_id"],
                    "scope_lease_ids":scope_lease_ids}
