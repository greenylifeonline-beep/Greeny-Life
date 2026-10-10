from __future__ import annotations
import hashlib
import json
import os
import socket
import uuid
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

COUNCIL_SEATS=tuple(f"C{i}" for i in range(1,13))
ROUTING_TARGETS=COUNCIL_SEATS+("C6-LOCAL","COMMAND_CENTER")
DEFAULT_SEATS=COUNCIL_SEATS
def utc()->str:return datetime.now(timezone.utc).isoformat()
def read_json(path:Path,default:Any=None)->Any:
    try:return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError):return default
def atomic(path:Path,data:Any)->str:
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode()
    tmp=path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_bytes(raw)
        for attempt in range(6):
            try:os.replace(tmp,path);break
            except PermissionError:
                if attempt==5:raise
                time.sleep(.02*(2**attempt))
    finally:
        try:tmp.unlink(missing_ok=True)
        except OSError:pass
    return hashlib.sha256(raw).hexdigest()
class MessageWorker:
    def __init__(self,repo:Path,runtime:Path,poll_seconds:float=1.0,max_attempts:int=5,
                 max_messages_per_scan:int=1000,max_scan_seconds:float=3.0,
                 ack_redelivery_seconds:float=30.0,max_ack_redeliveries:int=5,
                 routes:Any=None,presence_path:Path|None=None,
                 bindings_path:Path|None=None,consumers_path:Path|None=None):
        self.repo=repo.resolve();self.runtime=runtime.resolve()
        if self.repo.name.casefold()=="greeny-life-repair" or not (self.repo/".git").exists():
            raise RuntimeError(f"NON_CANONICAL_ROOT::{self.repo}")
        self.fabric=self.repo/".ai-os/state/command-fabric"
        self.inbox=self.fabric/"inbox";self.outbox=self.fabric/"outbox"
        self.receipts=self.repo/".ai-os/receipts/command-fabric"
        self.deliveries=self.fabric/"deliveries";self.dead=self.fabric/"dead-letter"
        self.state=self.runtime/"worker";self.poll_seconds=poll_seconds
        self.max_attempts=max_attempts;self.max_messages_per_scan=max(1,int(max_messages_per_scan))
        self.max_scan_seconds=max(.05,float(max_scan_seconds))
        self.ack_redelivery_seconds=max(1.0,float(ack_redelivery_seconds))
        self.max_ack_redeliveries=max(0,int(max_ack_redeliveries));self.stop_event=threading.Event()
        self.worker_id=f"RAIOS-WORKER@{socket.gethostname()}"
        self.canonical_head=os.getenv("RAIOS_CANONICAL_HEAD","").strip() or self._read_head_once()
        self.workflow=None;self.thread=None;self.heartbeat_thread=None
        self.last_error=None;self.consecutive_errors=0
        self.heartbeat_interval_seconds=5.0
        self._last_heartbeat_monotonic=0.0
        self._progress_lock=threading.Lock();self._heartbeat_write_lock=threading.Lock()
        self._progress_snapshot:dict[str,Any]={}
        self.scan_cursor=self.state/"inbox-scan-cursor.json"
        self.terminal_index=self.state/"delivered-terminal-index.json"
        self._delivered_terminal:set[str]=set()
        self._terminal_dirty=False
        for p in (self.inbox,self.outbox,self.receipts,self.deliveries,self.dead,self.state):
            p.mkdir(parents=True,exist_ok=True)
        index=read_json(self.terminal_index,{}) or {}
        terminal_index_current=(
            index.get("schema")=="raios.message-worker-terminal-index.v2"
            and index.get("terminality_source")=="ACTOR_ACK_OR_COMPLETION"
        )
        self._delivered_terminal={
            str(x) for x in (index.get("message_ids") or []) if terminal_index_current and str(x).startswith("MSG-")
        }
        self._routes=routes
        self._presence_path=presence_path
        self._bindings_path=bindings_path
        self._consumers_path=consumers_path
    def _targets(self,msg:dict[str,Any])->list[str]:
        payload=msg.get("payload") or {};raw=payload.get("to")
        if isinstance(raw,list):targets=[str(x).upper() for x in raw]
        else:targets=[str(msg.get("target") or "").upper()]
        # ALL must be resolved by the authority-aware command layer against live
        # actor/session bindings. The transport worker never expands ALL itself.
        targets=[x for x in targets if x!="ALL"]
        return list(dict.fromkeys(x for x in targets if x in ROUTING_TARGETS))
    def _constitution_live_bound(self,seat:str)->bool:
        if seat not in {"C6","C6-LOCAL"}:
            return True
        if self._routes is not None:
            return bool(self._routes.is_live_bound("C6"))
        from .actor_routing import ActorRouteRegistry
        routes=ActorRouteRegistry(self.repo,presence_path=self._presence_path,
                                  bindings_path=self._bindings_path,consumers_path=self._consumers_path)
        return bool(routes.is_live_bound("C6"))
    def _record(self,mid:str,target:str,status:str,attempt:int,detail:str|None=None)->dict[str,Any]:
        row={"schema":"raios.delivery-ack.v1","receipt_id":f"{mid}.{target}.delivery",
             "message_id":mid,"actor":self.worker_id,"target":target,"status":status,
             "ack_type":"DELIVERY_ACK","attempt":attempt,"at":utc(),
             "head":self._head(),"detail":detail}
        atomic(self.outbox/f"{mid}.{target}.delivery.ack.json",row)
        atomic(self.receipts/f"{mid}.{target}.delivery.ack.receipt.json",row)
        return row
    def _read_head_once(self)->str:
        try:
            import subprocess
            return subprocess.check_output(
                ["git","rev-parse","HEAD"],cwd=self.repo,text=True,
                stderr=subprocess.DEVNULL,timeout=5,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
            ).strip()
        except Exception:return "UNKNOWN"
    def _head(self)->str:return self.canonical_head
    def _attempts(self,mid:str)->dict[str,Any]:
        return read_json(self.state/f"{mid}.json",{"message_id":mid,"attempts":0}) or {"message_id":mid,"attempts":0}
    def _actor_ack_status(self,mid:str,targets:list[str])->dict[str,Any]:
        expected={str(x).upper() for x in targets if str(x).strip()}
        acked:dict[str,dict[str,Any]]={}
        evidence:list[dict[str,Any]]=[]
        for path in self.receipts.glob(f"{mid}.*.ack.receipt.json"):
            row=read_json(path,{}) or {}
            if row.get("schema") not in {"raios.message-ack.v1","raios.actor-ack.v1"}:
                continue
            if str(row.get("status") or "").upper() not in {"ACKNOWLEDGED","READ","DONE","COMPLETED"}:
                continue
            actor=str(row.get("actor") or row.get("actor_id") or "").upper()
            if not actor or actor.startswith("RAIOS-WORKER@"):
                continue
            declared=str(row.get("target") or row.get("seat") or actor).upper()
            item={"path":str(path),"actor":actor,"target":declared,
                  "status":row.get("status"),"at":row.get("at") or row.get("observed_at")}
            evidence.append(item)
            if declared in expected:
                acked[declared]=item
        if not expected and evidence:
            recovered_targets=sorted({str(x.get("target") or x.get("actor") or "").upper()
                                      for x in evidence if str(x.get("target") or x.get("actor") or "").strip()})
            return {"complete":True,"acked":acked,"acked_targets":recovered_targets,
                    "missing_targets":[],"evidence":evidence,
                    "historical_unroutable_recovery":True}
        missing=sorted(expected-set(acked))
        return {"complete":bool(expected) and not missing,"acked":acked,
                "acked_targets":sorted(acked),"missing_targets":missing,
                "evidence":evidence,"historical_unroutable_recovery":False}

    def _publish_actor_ack_terminal(self,mid:str,state:dict[str,Any],ack:dict[str,Any])->dict[str,Any]:
        state.update(status="ACTOR_ACK",lifecycle_state="ACTOR_ACK",
                     actor_ack=True,actor_ack_targets=ack.get("acked_targets") or [],
                     actor_ack_evidence=ack.get("evidence") or [],
                     actor_ack_at=utc(),updated_at=utc(),last_error=None)
        atomic(self.state/f"{mid}.json",state)
        atomic(self.receipts/f"{mid}.actor-ack.lifecycle.receipt.json",{
            "schema":"raios.message-lifecycle-receipt.v1","message_id":mid,
            "lifecycle_state":"ACTOR_ACK","terminal":True,
            "actor_ack_targets":ack.get("acked_targets") or [],
            "actor_ack_evidence":ack.get("evidence") or [],
            "at":state["actor_ack_at"],"head":self._head(),
            "delivery_ack_ne_actor_ack":True,
        })
        self._remember_terminal(mid)
        return state
    def _validate(self,msg:Any,path:Path)->tuple[str,list[str]]:
        if not isinstance(msg,dict) or msg.get("schema")!="raios.message.v1":
            raise ValueError("INVALID_MESSAGE_SCHEMA")
        mid=str(msg.get("message_id") or "")
        if not mid or path.stem!=mid:raise ValueError("MESSAGE_ID_PATH_MISMATCH")
        targets=self._targets(msg)
        if not targets:raise ValueError("NO_CANONICAL_TARGET")
        return mid,targets
    def enqueue(self,sender:str,targets:list[str],text:str,task_id:str|None=None,routing_modes:dict[str,str]|None=None)->dict[str,Any]:
        import uuid
        mid=f"MSG-{int(time.time()*1_000_000)}-{uuid.uuid4().hex[:8]}"
        clean=list(dict.fromkeys(str(x).upper() for x in targets if str(x).upper() in ROUTING_TARGETS))
        if not clean:raise ValueError("NO_CANONICAL_TARGET")
        msg={"schema":"raios.message.v1","message_id":mid,"correlation_id":f"cc-{uuid.uuid4().hex[:12]}",
             "sender":sender,"target":"ALL" if len(clean)>1 else clean[0],"kind":"COMMAND",
             "channel":"INTERNAL_BUS","payload":{"text":text,"to":clean,"task_id":task_id,
             "routing_modes":routing_modes or {},"ack_requested":True,"actor_ack_required":True,
             "actor_ack_synthesized":False},"created_at":utc(),"head":self._head(),"ack_required":True}
        digest=atomic(self.inbox/f"{mid}.json",msg)
        atomic(self.receipts/f"{mid}.send.json",{"receipt_id":mid,"message_id":mid,
          "RECEIPT_ID_EQUALS_MESSAGE_ID":True,"sha256":digest,"event":"SENT","at":utc(),
          "targets":clean,"routing_modes":routing_modes or {},"route":"CANONICAL_LOCAL_FABRIC",
          "actor_ack_synthesized":False})
        return msg

    def process(self,path:Path)->dict[str,Any]:
        msg=read_json(path);mid=path.stem;state=self._attempts(mid)
        try:
            mid,targets=self._validate(msg,path)
            delivered=[];gated=[]
            for target in targets:
                if target in {"C6","C6-LOCAL"} and not self._constitution_live_bound(target):
                    self._record(mid,target,"C6_NOT_LIVE_BOUND_CONSUMER",int(state["attempts"])+1,
                                 "FAIL_CLOSED_NO_C6_IMPERSONATION")
                    gated.append(target)
                    continue
                dst=self.deliveries/target/f"{mid}.json"
                if not dst.exists():atomic(dst,msg)
                self._record(mid,target,"QUEUED_FOR_SEAT",int(state["attempts"])+1)
                delivered.append(target)
            if delivered:
                delivered_at=state.get("delivered_at") or utc()
                state.update(attempts=int(state["attempts"])+1,
                             status="DELIVERED_PENDING_ACTOR_ACK",
                             lifecycle_state="DELIVERED_PENDING_ACTOR_ACK",
                             targets=delivered,c6_gated=gated,delivered_at=delivered_at,
                             last_delivery_at=utc(),actor_ack=False,
                             updated_at=utc(),last_error=None)
            else:
                state.update(attempts=int(state["attempts"])+1,status="C6_NOT_LIVE_BOUND",
                             targets=[],c6_gated=gated,updated_at=utc(),
                             last_error="C6_NOT_LIVE_BOUND_CONSUMER")
            atomic(self.state/f"{mid}.json",state);return state
        except Exception as exc:
            state.update(attempts=int(state.get("attempts",0))+1,status="RETRY",
                         updated_at=utc(),last_error=f"{type(exc).__name__}:{exc}")
            if state["attempts"]>=self.max_attempts:
                state["status"]="DEAD_LETTER"
                if path.exists():atomic(self.dead/path.name,read_json(path,{"raw_path":str(path)}))
                self._record(mid,"COMMAND_CENTER","DEAD_LETTER",state["attempts"],state["last_error"])
            atomic(self.state/f"{mid}.json",state);return state
    def _redeliver_pending_actor_ack(self,path:Path,msg:dict[str,Any],
                                     state:dict[str,Any],targets:list[str])->dict[str,Any]:
        count=int(state.get("ack_redelivery_count") or 0)
        if count>=self.max_ack_redeliveries:
            state.update(status="BLOCKED_ACTOR_ACK",lifecycle_state="BLOCKED_ACTOR_ACK",
                         actor_ack=False,actor_ack_blocked=True,
                         updated_at=utc(),last_error="ACTOR_ACK_NOT_OBSERVED")
            atomic(self.state/f"{path.stem}.json",state)
            return state
        stamp=state.get("last_delivery_at") or state.get("updated_at")
        if stamp:
            try:
                changed=datetime.fromisoformat(str(stamp).replace("Z","+00:00"))
                if (datetime.now(timezone.utc)-changed).total_seconds()<self.ack_redelivery_seconds:
                    return state
            except Exception:
                pass
        delivered=[]
        for target in targets:
            if target in {"C6","C6-LOCAL"} and not self._constitution_live_bound(target):
                continue
            dst=self.deliveries/target/f"{path.stem}.json"
            atomic(dst,msg)
            self._record(path.stem,target,"REDELIVERED_PENDING_ACTOR_ACK",
                         int(state.get("attempts") or 0),
                         "DELIVERY_ACK_NE_ACTOR_ACK")
            delivered.append(target)
        if delivered:
            state.update(status="DELIVERED_PENDING_ACTOR_ACK",
                         lifecycle_state="DELIVERED_PENDING_ACTOR_ACK",
                         ack_redelivery_count=count+1,last_delivery_at=utc(),
                         updated_at=utc(),last_error=None)
            atomic(self.state/f"{path.stem}.json",state)
        return state

    def configure_workflow(self,workflow:Any)->None:self.workflow=workflow
    def _remember_terminal(self,mid:str)->None:
        if mid not in self._delivered_terminal:
            self._delivered_terminal.add(mid);self._terminal_dirty=True
    def _flush_terminal_index(self)->None:
        if not self._terminal_dirty:return
        atomic(self.terminal_index,{
            "schema":"raios.message-worker-terminal-index.v2",
            "generated_at":utc(),"head":self._head(),
            "terminality_source":"ACTOR_ACK_OR_COMPLETION",
            "delivery_ack_ne_actor_ack":True,
            "count":len(self._delivered_terminal),
            "message_ids":sorted(self._delivered_terminal),
        })
        self._terminal_dirty=False
    def _progress_snapshot_copy(self)->dict[str,Any]:
        with self._progress_lock:return dict(self._progress_snapshot)
    def _progress_heartbeat(self,result:dict[str,Any],phase:str,*,force:bool=False)->None:
        snapshot=dict(result)
        snapshot.update(scan_phase=phase,scan_in_progress=phase!="SCAN_COMPLETE",
                        delivered_terminal_cache=len(self._delivered_terminal),
                        terminality_source="ACTOR_ACK_OR_COMPLETION",
                        delivery_ack_ne_actor_ack=True)
        with self._progress_lock:self._progress_snapshot=snapshot
        ticker_alive=bool(self.heartbeat_thread and self.heartbeat_thread.is_alive())
        if force:
            self.heartbeat(snapshot)
            return
        if not ticker_alive:
            now=time.monotonic()
            if now-self._last_heartbeat_monotonic>=self.heartbeat_interval_seconds:
                self.heartbeat(snapshot)
    def _heartbeat_loop(self)->None:
        while not self.stop_event.is_set():
            try:self.heartbeat(self._progress_snapshot_copy())
            except Exception:pass
            self.stop_event.wait(self.heartbeat_interval_seconds)
    def _load_scan_cursor(self)->dict[str,Any]:
        if not self.scan_cursor.exists():
            return {"valid":False,"reason":"MISSING","last_name":None}
        row=read_json(self.scan_cursor)
        if not isinstance(row,dict) or row.get("schema")!="raios.message-worker-scan-cursor.v1":
            return {"valid":False,"reason":"CORRUPT","last_name":None}
        if row.get("head")!=self._head():
            return {"valid":False,"reason":"HEAD_MISMATCH","last_name":None}
        name=row.get("last_name")
        if name is not None and (not isinstance(name,str) or not name.startswith("MSG-") or not name.endswith(".json")):
            return {"valid":False,"reason":"CORRUPT","last_name":None}
        return {"valid":True,"reason":"CURRENT","last_name":name}
    def _commit_scan_cursor(self,last_name:str|None,reason:str)->None:
        atomic(self.scan_cursor,{"schema":"raios.message-worker-scan-cursor.v1",
            "head":self._head(),"updated_at":utc(),"last_name":last_name,
            "reason":reason,"non_authoritative":True,
            "terminality_source":"DURABLE_MESSAGE_TASK_RECEIPT_STATE"})
    def _run_workflow_with_heartbeat(self,result:dict[str,Any])->dict[str,int]:
        if self.workflow is None:return {}
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self._progress_heartbeat(result,"WORKFLOW_RUNNING")
            return self.workflow.run_cycle(self)
        done=threading.Event()
        def pulse()->None:
            while not done.wait(self.heartbeat_interval_seconds):
                try:self._progress_heartbeat(result,"WORKFLOW_RUNNING",force=True)
                except Exception:pass
        ticker=threading.Thread(target=pulse,name="raios-message-worker-workflow-heartbeat",daemon=True)
        ticker.start()
        try:return self.workflow.run_cycle(self)
        finally:
            done.set();ticker.join(timeout=max(1.0,self.heartbeat_interval_seconds+0.5))
    def scan_once(self)->dict[str,Any]:
        result={"seen":0,"delivered":0,"retried":0,"dead_letter":0,"c6_gated":0,
                "actor_ack":0,"pending_actor_ack":0,"redelivered":0,"actor_ack_blocked":0,
                "legacy_delivery_state_migrated":0,
                "terminal_cache_hits":0,"terminal_cache_warmed":0,
                "historical_ack_recovered":0,"scan_budget_exhausted":False}
        deadline=time.monotonic()+self.max_scan_seconds
        cursor=self._load_scan_cursor();after=cursor.get("last_name") if cursor.get("valid") else None
        result["cursor_state"]=cursor.get("reason")
        self._progress_heartbeat(result,"SCAN_START",force=True)
        def handle(path:Path)->None:
            mid=path.stem
            if mid in self._delivered_terminal:
                result["terminal_cache_hits"]+=1;return
            msg=read_json(path,{}) or {}
            targets=self._targets(msg) if isinstance(msg,dict) else []
            state=self._attempts(mid);status=str(state.get("status") or "").upper()
            ack=self._actor_ack_status(mid,targets)
            if ack["complete"]:
                self._publish_actor_ack_terminal(mid,state,ack)
                result["actor_ack"]+=1
                if status in {"DEAD_LETTER","DELIVERED","DELIVERED_PENDING_ACTOR_ACK","BLOCKED_ACTOR_ACK"}:
                    result["historical_ack_recovered"]+=1
                return
            if status in {"ACTOR_ACK","COMPLETED","SUPERSEDED","ARCHIVED"}:
                self._remember_terminal(mid);result["terminal_cache_warmed"]+=1;return
            if status=="DELIVERED":
                # v1 migration: a delivery-only state was incorrectly terminal.
                state.update(status="DELIVERED_PENDING_ACTOR_ACK",
                             lifecycle_state="DELIVERED_PENDING_ACTOR_ACK",
                             actor_ack=False,updated_at=utc(),
                             last_error="LEGACY_DELIVERY_ACK_NE_ACTOR_ACK")
                atomic(self.state/f"{mid}.json",state)
                status="DELIVERED_PENDING_ACTOR_ACK"
                result["legacy_delivery_state_migrated"]+=1
            if status in {"DELIVERED_PENDING_ACTOR_ACK","BLOCKED_ACTOR_ACK"}:
                if status=="BLOCKED_ACTOR_ACK":
                    result["actor_ack_blocked"]+=1
                    return
                before=int(state.get("ack_redelivery_count") or 0)
                state=self._redeliver_pending_actor_ack(path,msg,state,targets)
                after=int(state.get("ack_redelivery_count") or 0)
                if after>before:result["redelivered"]+=1
                if str(state.get("status") or "").upper()=="BLOCKED_ACTOR_ACK":
                    result["actor_ack_blocked"]+=1
                else:
                    result["pending_actor_ack"]+=1
                return
            if status=="DEAD_LETTER":
                return
            if status=="RETRY":
                delay=min(60,2**max(0,int(state.get("attempts",0))-1))
                try:
                    changed=datetime.fromisoformat(str(state["updated_at"]).replace("Z","+00:00"))
                    if (datetime.now(timezone.utc)-changed).total_seconds()<delay:return
                except Exception:pass
            state=self.process(path)
            key={"DELIVERED_PENDING_ACTOR_ACK":"delivered","RETRY":"retried","DEAD_LETTER":"dead_letter",
                 "C6_NOT_LIVE_BOUND":"c6_gated"}[state["status"]]
            result[key]+=1
            if state["status"]=="DELIVERED_PENDING_ACTOR_ACK":result["pending_actor_ack"]+=1
        def consume(after_name:str|None)->tuple[bool,str|None,bool]:
            found=after_name is None;last_done=None;reached_end=True;entries_scanned=0
            with os.scandir(self.inbox) as it:
                for entry in it:
                    entries_scanned+=1
                    if (time.monotonic()>=deadline or result["seen"]>=self.max_messages_per_scan
                            or entries_scanned>self.max_messages_per_scan):
                        result["scan_budget_exhausted"]=True;reached_end=False;break
                    name=entry.name
                    if not (name.startswith("MSG-") and name.endswith(".json")):continue
                    if not found:
                        if name==after_name:found=True
                        continue
                    if after_name is not None and name==after_name:continue
                    path=Path(entry.path);result["seen"]+=1
                    handle(path);last_done=name
                    self._progress_heartbeat(result,"SCANNING")
            return found,last_done,reached_end
        found,last_done,reached_end=consume(after)
        if after is not None and not found:
            result["cursor_state"]="STALE_RECONCILE"
            if time.monotonic()<deadline and result["seen"]<self.max_messages_per_scan:
                _,last_done,reached_end=consume(None)
            elif last_done is None:
                self._commit_scan_cursor(None,"STALE_CURSOR_RESET")
        elif after is not None and found and reached_end and last_done is None:
            result["cursor_state"]="WRAP_RECONCILE"
            if time.monotonic()<deadline and result["seen"]<self.max_messages_per_scan:
                _,last_done,reached_end=consume(None)
            elif last_done is None:
                self._commit_scan_cursor(None,"WRAP_RESET")
        if last_done is not None:
            self._commit_scan_cursor(last_done,"BOUNDED_SCAN_PROGRESS")
        self._flush_terminal_index()
        if self.workflow is not None:
            self._progress_heartbeat(result,"WORKFLOW_START",force=True)
            result.update(self._run_workflow_with_heartbeat(result))
        self._progress_heartbeat(result,"SCAN_COMPLETE",force=True)
        return result
    def heartbeat(self,last:dict[str,Any]|None=None)->None:
        with self._heartbeat_write_lock:
            stamp=utc();expires=(datetime.now(timezone.utc)+timedelta(seconds=30)).isoformat();head=self._head()
            row={"schema":"raios.message-worker-heartbeat.v1","worker_id":self.worker_id,
                 "at":stamp,"lease_expires_at":expires,"head":head,"last_scan":last or {},
                 "consecutive_errors":self.consecutive_errors}
            atomic(self.state/"heartbeat.json",row)
            registry_path=self.fabric/"WORKER-REGISTRY.json"
            registry=read_json(registry_path,{"schema":"raios.worker-registry.v2","workers":[]})
            workers=[w for w in registry.get("workers",[]) if w.get("worker_id")!=self.worker_id]
            workers.append({"worker_id":self.worker_id,"kind":"MESSAGE_PICKUP","liveness":"LIVE",
                            "heartbeat":stamp,"lease_expires_at":expires,"head":head,
                            "owner":"RAIOS_SYSTEM","permanent_lock":False})
            registry.update(workers=workers,generated_at=stamp,head=head)
            atomic(registry_path,registry)
            self._last_heartbeat_monotonic=time.monotonic()
    def run(self)->None:
        while not self.stop_event.is_set():
            try:
                self.scan_once();self.last_error=None;self.consecutive_errors=0
            except Exception as exc:
                self.consecutive_errors+=1
                self.last_error=f"{type(exc).__name__}:{exc}"
                self._progress_heartbeat({"error":self.last_error},"SCAN_ERROR")
                try:atomic(self.state/"last-error.json",{"worker_id":self.worker_id,"at":utc(),
                    "error":self.last_error,"consecutive_errors":self.consecutive_errors})
                except Exception:pass
            self.stop_event.wait(self.poll_seconds)
    def start(self)->threading.Thread:
        if self.thread and self.thread.is_alive():return self.thread
        self.stop_event.clear()
        self._progress_heartbeat({},"STARTING")
        self.heartbeat_thread=threading.Thread(
            target=self._heartbeat_loop,name="raios-message-worker-heartbeat",daemon=True)
        self.heartbeat_thread.start()
        self.thread=threading.Thread(target=self.run,name="raios-message-worker",daemon=True)
        self.thread.start();return self.thread
    def status(self)->dict[str,Any]:
        row=read_json(self.state/"heartbeat.json",{}) or {}
        thread_alive=bool(self.thread and self.thread.is_alive());heartbeat_current=False
        try:
            expiry=datetime.fromisoformat(str(row.get("lease_expires_at") or "").replace("Z","+00:00"))
            heartbeat_current=expiry>datetime.now(timezone.utc)
        except (TypeError,ValueError):pass
        healthy=thread_alive and heartbeat_current and self.last_error is None
        row.update(worker_id=self.worker_id,thread_alive=thread_alive,heartbeat_current=heartbeat_current,
                   healthy=healthy,state="ONLINE" if healthy else ("STARTING" if thread_alive and not row else "DEGRADED"),
                   last_error=self.last_error,consecutive_errors=self.consecutive_errors,
                   workflow_enabled=self.workflow is not None,
                   heartbeat_thread_alive=bool(self.heartbeat_thread and self.heartbeat_thread.is_alive()))
        return row
    def stop(self)->None:self.stop_event.set()
