from __future__ import annotations
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEATS=tuple(f"C{i}" for i in range(1,13))
def utc()->str:return datetime.now(timezone.utc).isoformat()
def load(path:Path,default:Any)->Any:
    try:return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError):return default
def atomic(path:Path,data:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,path)

class CouncilBoard:
    def __init__(self,repo:Path,presence:Path|None=None):
        self.repo=repo.resolve();self.tasks=self.repo/".ai-os/state/TASKS.json"
        self.presence=(presence or Path.home()/".raios/runtime/council-ops/presence.json").resolve()
    def _live(self,target:str)->bool:
        row=load(self.presence,{"seats":{}}).get("seats",{}).get(target,{})
        if row.get("presence")!="PRESENT":return False
        expiry=row.get("lease_expires_at")
        if not expiry:return True
        try:return datetime.fromisoformat(str(expiry).replace("Z","+00:00"))>datetime.now(timezone.utc)
        except (TypeError,ValueError):return False
    def _reconcile_absent_assignments(self,data:dict[str,Any])->int:
        returned=0
        for task in data.get("tasks",[]):
            target=str(task.get("assigned_to") or "").upper()
            if (task.get("dispatch_status")!="PENDING_ACCEPTANCE" or
                task.get("claimed_by") or not target or self._live(target)):
                continue
            task["last_dispatch_target"]=target
            task["last_dispatch_id"]=task.get("dispatch_id")
            task["dispatch_status"]="RETURNED_ABSENT"
            task["returned_at"]=utc()
            task["return_reason"]="TARGET_PRESENCE_ABSENT_OR_EXPIRED"
            for key in ("assigned_to","assigned_by","dispatched_by","dispatch_id","dispatched_at"):
                task.pop(key,None)
            returned+=1
        if returned:atomic(self.tasks,data)
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
                 "scope":task.get("scope",[]),"evidence":task.get("evidence")}
            if status in buckets:buckets[status].append(row)
            if status=="READY" and all(d in done for d in task.get("dependencies",[])):
                buckets["NEXT"].append(row)
        presence=load(self.presence,{"seats":{}}).get("seats",{})
        return {"schema":"raios.council-board.v1","generated_at":utc(),
                "summary":{k:len(v) for k,v in buckets.items()},
                "buckets":buckets,"presence":presence,"returned_absent_assignments":returned,
                "single_task_ledger":True}
    def dispatch(self,task_id:str,target:str,worker:Any)->dict[str,Any]:
        target=target.upper()
        if target not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        presence=load(self.presence,{"seats":{}}).get("seats",{}).get(target,{})
        if presence.get("presence")!="PRESENT":raise ValueError("TARGET_NOT_PRESENT")
        if not self._live(target):raise ValueError("TARGET_PRESENCE_EXPIRED")
        data=load(self.tasks,{"tasks":[]})
        task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
        if not task:raise ValueError("TASK_NOT_FOUND")
        if task.get("status") not in ("READY","IN_PROGRESS"):raise ValueError("TASK_NOT_DISPATCHABLE")
        allowed=[str(x).upper() for x in task.get("allowed_agents",[])]
        if allowed and target not in allowed:raise ValueError("SEAT_NOT_ALLOWED_FOR_TASK")
        if task.get("claimed_by") not in (None,target):raise ValueError("TASK_ALREADY_CLAIMED")
        dispatch_id="DSP-"+uuid.uuid4().hex[:16]
        task.update(assigned_to=target,assigned_by="C1",dispatched_by="RAIOS-WORKER",
                    dispatch_status="PENDING_ACCEPTANCE",dispatch_id=dispatch_id,
                    dispatched_at=utc(),system_owner="RAIOS_SYSTEM")
        atomic(self.tasks,data)
        text=(f"TASK_ASSIGNMENT\nTASK_ID={task_id}\nTARGET={target}\n"
              f"DISPATCH_ID={dispatch_id}\nAUTHORITY=C1\n"
              "ACTION=CHECK_IN_THEN_CLAIM_OR_RETURN_BLOCKER")
        msg=worker.enqueue("RAIOS-WORKER",[target],text,task_id)
        return {"status":"DISPATCHED_PENDING_ACCEPTANCE","task_id":task_id,
                "target":target,"dispatch_id":dispatch_id,"message_id":msg["message_id"]}
