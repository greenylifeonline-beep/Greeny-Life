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
    def __init__(self,repo:Path,runtime:Path,poll_seconds:float=1.0,max_attempts:int=5):
        self.repo=repo.resolve();self.runtime=runtime.resolve()
        if self.repo.name.casefold()=="greeny-life-repair" or not (self.repo/".git").exists():
            raise RuntimeError(f"NON_CANONICAL_ROOT::{self.repo}")
        self.fabric=self.repo/".ai-os/state/command-fabric"
        self.inbox=self.fabric/"inbox";self.outbox=self.fabric/"outbox"
        self.receipts=self.repo/".ai-os/receipts/command-fabric"
        self.deliveries=self.fabric/"deliveries";self.dead=self.fabric/"dead-letter"
        self.state=self.runtime/"worker";self.poll_seconds=poll_seconds
        self.max_attempts=max_attempts;self.stop_event=threading.Event()
        self.worker_id=f"RAIOS-WORKER@{socket.gethostname()}"
        self.workflow=None;self.thread=None;self.last_error=None;self.consecutive_errors=0
        for p in (self.inbox,self.outbox,self.receipts,self.deliveries,self.dead,self.state):
            p.mkdir(parents=True,exist_ok=True)
    def _targets(self,msg:dict[str,Any])->list[str]:
        payload=msg.get("payload") or {};raw=payload.get("to")
        if isinstance(raw,list):targets=[str(x).upper() for x in raw]
        else:targets=[str(msg.get("target") or "").upper()]
        if "ALL" in targets:targets=list(COUNCIL_SEATS)
        return list(dict.fromkeys(x for x in targets if x in ROUTING_TARGETS))
    def _record(self,mid:str,target:str,status:str,attempt:int,detail:str|None=None)->dict[str,Any]:
        row={"schema":"raios.delivery-ack.v1","receipt_id":f"{mid}.{target}.delivery",
             "message_id":mid,"actor":self.worker_id,"target":target,"status":status,
             "ack_type":"DELIVERY_ACK","attempt":attempt,"at":utc(),
             "head":self._head(),"detail":detail}
        atomic(self.outbox/f"{mid}.{target}.delivery.ack.json",row)
        atomic(self.receipts/f"{mid}.{target}.delivery.ack.receipt.json",row)
        return row
    def _head(self)->str:
        try:
            import subprocess
            return subprocess.check_output(
                ["git","rev-parse","HEAD"],cwd=self.repo,text=True,
                stderr=subprocess.DEVNULL,timeout=5,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
            ).strip()
        except Exception:return "UNKNOWN"
    def _attempts(self,mid:str)->dict[str,Any]:
        return read_json(self.state/f"{mid}.json",{"message_id":mid,"attempts":0}) or {"message_id":mid,"attempts":0}
    def _validate(self,msg:Any,path:Path)->tuple[str,list[str]]:
        if not isinstance(msg,dict) or msg.get("schema")!="raios.message.v1":
            raise ValueError("INVALID_MESSAGE_SCHEMA")
        mid=str(msg.get("message_id") or "")
        if not mid or path.stem!=mid:raise ValueError("MESSAGE_ID_PATH_MISMATCH")
        targets=self._targets(msg)
        if not targets:raise ValueError("NO_CANONICAL_TARGET")
        return mid,targets
    def enqueue(self,sender:str,targets:list[str],text:str,task_id:str|None=None)->dict[str,Any]:
        import uuid
        mid=f"MSG-{int(time.time()*1_000_000)}-{uuid.uuid4().hex[:8]}"
        clean=list(dict.fromkeys(str(x).upper() for x in targets if str(x).upper() in ROUTING_TARGETS))
        if not clean:raise ValueError("NO_CANONICAL_TARGET")
        msg={"schema":"raios.message.v1","message_id":mid,"correlation_id":f"cc-{uuid.uuid4().hex[:12]}",
             "sender":sender,"target":"ALL" if len(clean)>1 else clean[0],"kind":"COMMAND",
             "channel":"INTERNAL_BUS","payload":{"text":text,"to":clean,"task_id":task_id,
             "ack_requested":True},"created_at":utc(),"head":self._head(),"ack_required":True}
        digest=atomic(self.inbox/f"{mid}.json",msg)
        atomic(self.receipts/f"{mid}.send.json",{"receipt_id":mid,"message_id":mid,
          "RECEIPT_ID_EQUALS_MESSAGE_ID":True,"sha256":digest,"event":"SENT","at":utc(),
          "targets":clean,"route":"CANONICAL_LOCAL_FABRIC"})
        return msg

    def process(self,path:Path)->dict[str,Any]:
        msg=read_json(path);mid=path.stem;state=self._attempts(mid)
        try:
            mid,targets=self._validate(msg,path)
            delivered=[]
            for target in targets:
                dst=self.deliveries/target/f"{mid}.json"
                if not dst.exists():atomic(dst,msg)
                self._record(mid,target,"QUEUED_FOR_SEAT",int(state["attempts"])+1)
                delivered.append(target)
            state.update(attempts=int(state["attempts"])+1,status="DELIVERED",
                         targets=delivered,updated_at=utc(),last_error=None)
            atomic(self.state/f"{mid}.json",state);return state
        except Exception as exc:
            state.update(attempts=int(state.get("attempts",0))+1,status="RETRY",
                         updated_at=utc(),last_error=f"{type(exc).__name__}:{exc}")
            if state["attempts"]>=self.max_attempts:
                state["status"]="DEAD_LETTER"
                if path.exists():atomic(self.dead/path.name,read_json(path,{"raw_path":str(path)}))
                self._record(mid,"COMMAND_CENTER","DEAD_LETTER",state["attempts"],state["last_error"])
            atomic(self.state/f"{mid}.json",state);return state
    def configure_workflow(self,workflow:Any)->None:self.workflow=workflow
    def scan_once(self)->dict[str,int]:
        result={"seen":0,"delivered":0,"retried":0,"dead_letter":0}
        for path in sorted(self.inbox.glob("MSG-*.json")):
            result["seen"]+=1;state=self._attempts(path.stem)
            if state.get("status")=="DELIVERED":continue
            if state.get("status")=="RETRY":
                delay=min(60,2**max(0,int(state.get("attempts",0))-1))
                try:
                    changed=datetime.fromisoformat(str(state["updated_at"]).replace("Z","+00:00"))
                    if (datetime.now(timezone.utc)-changed).total_seconds()<delay:continue
                except Exception:pass
            state=self.process(path)
            key={"DELIVERED":"delivered","RETRY":"retried","DEAD_LETTER":"dead_letter"}[state["status"]]
            result[key]+=1
        if self.workflow is not None:result.update(self.workflow.run_cycle(self))
        self.heartbeat(result);return result
    def heartbeat(self,last:dict[str,int]|None=None)->None:
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
    def run(self)->None:
        while not self.stop_event.is_set():
            try:
                self.scan_once();self.last_error=None;self.consecutive_errors=0
            except Exception as exc:
                self.consecutive_errors+=1
                self.last_error=f"{type(exc).__name__}:{exc}"
                try:atomic(self.state/"last-error.json",{"worker_id":self.worker_id,"at":utc(),
                    "error":self.last_error,"consecutive_errors":self.consecutive_errors})
                except Exception:pass
            self.stop_event.wait(self.poll_seconds)
    def start(self)->threading.Thread:
        if self.thread and self.thread.is_alive():return self.thread
        self.stop_event.clear()
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
                   workflow_enabled=self.workflow is not None)
        return row
    def stop(self)->None:self.stop_event.set()
