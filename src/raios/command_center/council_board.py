from __future__ import annotations
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEATS=tuple(f"C{i}" for i in range(1,13))
EXECUTION_ALIASES={
 "C1":{"C1"},"C2":{"C2","CURSOR","CODEX"},"C3":{"C3","CHATGPT-MAIN-BRAIN","CHATGPT-PEER"},
 "C4":{"C4","DEEPSEEK","DEEPSEEK-LOCAL"},"C5":{"C5","RAIOS","C5-RUNTIME"},
 "C6":{"C6","CODEX","GITHUB-AGENT"},"C7":{"C7"},"C8":{"C8"},"C9":{"C9"},
 "C10":{"C10"},"C11":{"C11"},"C12":{"C12"}}
def utc()->str:return datetime.now(timezone.utc).isoformat()
def load(path:Path,default:Any)->Any:
    try:return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError):return default
def atomic(path:Path,data:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        for attempt in range(6):
            try:os.replace(tmp,path);break
            except PermissionError:
                if attempt==5:raise
                time.sleep(.02*(2**attempt))
    finally:
        try:tmp.unlink(missing_ok=True)
        except OSError:pass

class CouncilBoard:
    def __init__(self,repo:Path,presence:Path|None=None):
        self.repo=repo.resolve();self.tasks=self.repo/".ai-os/state/TASKS.json"
        self.presence=(presence or Path.home()/".raios/runtime/council-ops/presence.json").resolve()
        self.fabric=self.repo/".ai-os/state/command-fabric"
        self.report_inbox=self.fabric/"task-reports/inbox"
        self.report_processed=self.fabric/"task-reports/processed"
        self.report_rejected=self.fabric/"task-reports/rejected"
        self.receipts=self.repo/".ai-os/receipts/command-fabric"
        self.lock=threading.RLock()
        for p in (self.report_inbox,self.report_processed,self.report_rejected,self.receipts):
            p.mkdir(parents=True,exist_ok=True)
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
            target=str(task.get("assigned_to") or task.get("claimed_by") or "").upper()
            governed=(target in SEATS and task.get("dispatch_status") in
                      ("PENDING_ACCEPTANCE","ACCEPTED","CHECKPOINT_SAVED","IN_PROGRESS_REPORTED"))
            if not governed or self._live(target):continue
            task["last_dispatch_target"]=target
            task["last_dispatch_id"]=task.get("dispatch_id")
            task["last_claimed_by"]=task.get("claimed_by")
            task["dispatch_status"]="RETURNED_ABSENT_WITH_CHECKPOINT"
            task["status"]="READY";task["returned_at"]=utc()
            task["return_reason"]="TARGET_PRESENCE_ABSENT_OR_EXPIRED"
            if not task.get("resume_checkpoint"):
                checkpoint={
                    "schema":"raios.task-checkpoint.v1","checkpoint_id":"CHK-"+uuid.uuid4().hex[:16],
                    "task_id":task.get("id"),"actor":"RAIOS-WORKER","phase":"INTERRUPTED",
                    "summary":"Executor presence expired before an explicit checkpoint was received.",
                    "completed_steps":[],"changed_files":[],"validation":[],"evidence_refs":[],
                    "next_step":"Inspect the working tree and latest task evidence before continuing.",
                    "blocker":"EXECUTOR_PRESENCE_EXPIRED","created_at":utc()}
                task["resume_checkpoint"]=checkpoint
                task["last_checkpoint_id"]=checkpoint["checkpoint_id"]
                task["checkpoint_updated_at"]=checkpoint["created_at"]
                atomic(self.receipts/f"{checkpoint['checkpoint_id']}.checkpoint.receipt.json",
                       {**checkpoint,"status":"SYSTEM_RECOVERY_SAVED","single_task_ledger":True})
            for key in ("assigned_to","assigned_by","dispatched_by","dispatch_id",
                        "dispatched_at","claimed_by","accepted_at"):
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
                 "scope":task.get("scope",[]),"evidence":task.get("evidence"),
                 "resume_checkpoint":task.get("resume_checkpoint")}
            if status in buckets:buckets[status].append(row)
            if status=="READY" and all(d in done for d in task.get("dependencies",[])):
                buckets["NEXT"].append(row)
        presence=load(self.presence,{"seats":{}}).get("seats",{})
        return {"schema":"raios.council-board.v1","generated_at":utc(),
                "summary":{k:len(v) for k,v in buckets.items()},
                "buckets":buckets,"presence":presence,"returned_absent_assignments":returned,
                "single_task_ledger":True}
    def _eligible(self,task:dict[str,Any],seat:str)->bool:
        allowed={str(x).upper() for x in task.get("allowed_agents",[])}
        if allowed and not (allowed & EXECUTION_ALIASES.get(seat,{seat})):return False
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
    def accept_task(self,task_id:str,actor:str,dispatch_id:str)->dict[str,Any]:
        actor=actor.upper()
        if actor not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        if not self._live(actor):raise ValueError("TARGET_NOT_PRESENT")
        with self.lock:
            data=load(self.tasks,{"tasks":[]})
            task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
            if not task:raise ValueError("TASK_NOT_FOUND")
            if str(task.get("assigned_to") or "").upper()!=actor:
                raise ValueError("ACCEPTOR_NE_DISPATCH_TARGET")
            if task.get("dispatch_status")!="PENDING_ACCEPTANCE":
                raise ValueError("TASK_NOT_PENDING_ACCEPTANCE")
            if task.get("dispatch_id")!=dispatch_id:raise ValueError("DISPATCH_ID_MISMATCH")
            task.update(status="IN_PROGRESS",claimed_by=actor,dispatch_status="ACCEPTED",
                        accepted_at=utc())
            atomic(self.tasks,data)
            receipt={"schema":"raios.task-acceptance-receipt.v1","task_id":task_id,
                     "dispatch_id":dispatch_id,"actor":actor,"status":"ACCEPTED","at":utc(),
                     "resume_checkpoint":task.get("resume_checkpoint")}
            atomic(self.receipts/f"{dispatch_id}.{actor}.task-accept.receipt.json",receipt)
            return receipt
    def submit_checkpoint(self,task_id:str,actor:str,phase:str,summary:str,
                          completed_steps:list[str],changed_files:list[str],
                          validation:list[str],evidence_refs:list[str],
                          next_step:str,blocker:str|None=None)->dict[str,Any]:
        actor=actor.upper();phase=phase.upper()
        if actor not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        if not self._live(actor):raise ValueError("REPORTER_NOT_PRESENT")
        if phase not in ("IN_PROGRESS","BLOCKED"):raise ValueError("INVALID_CHECKPOINT_PHASE")
        if phase=="BLOCKED" and not (blocker or "").strip():
            raise ValueError("BLOCKER_REQUIRED")
        with self.lock:
            data=load(self.tasks,{"tasks":[]})
            task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
            if not task:raise ValueError("TASK_NOT_FOUND")
            if str(task.get("claimed_by") or "").upper()!=actor:
                raise ValueError("CHECKPOINT_ACTOR_NE_TASK_CLAIM")
            checkpoint=self._build_checkpoint(task,actor,phase,summary,completed_steps,
                changed_files,validation,evidence_refs,next_step,blocker)
            task.update(resume_checkpoint=checkpoint,last_checkpoint_id=checkpoint["checkpoint_id"],
                        checkpoint_updated_at=checkpoint["created_at"],
                        status="BLOCKED" if phase=="BLOCKED" else "IN_PROGRESS",
                        dispatch_status="CHECKPOINT_SAVED")
            if blocker:task["blocker"]=blocker
            atomic(self.tasks,data)
            receipt={**checkpoint,"status":"SAVED","single_task_ledger":True}
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
                      blocker:str|None=None)->dict[str,Any]:
        actor=actor.upper();status=status.upper()
        if actor not in SEATS:raise ValueError("UNKNOWN_COUNCIL_SEAT")
        if not self._live(actor):raise ValueError("REPORTER_NOT_PRESENT")
        if status not in ("IN_PROGRESS","COMPLETE","BLOCKED"):raise ValueError("INVALID_REPORT_STATUS")
        if not next_step.strip():raise ValueError("CHECKPOINT_NEXT_STEP_REQUIRED")
        if status=="BLOCKED" and not (blocker or "").strip():raise ValueError("BLOCKER_REQUIRED")
        data=load(self.tasks,{"tasks":[]})
        task=next((t for t in data.get("tasks",[]) if t.get("id")==task_id),None)
        if not task:raise ValueError("TASK_NOT_FOUND")
        if str(task.get("claimed_by") or "").upper()!=actor:
            raise ValueError("REPORTER_NE_TASK_CLAIM")
        report_id="RPT-"+uuid.uuid4().hex[:16]
        report={"schema":"raios.task-report.v1","report_id":report_id,"task_id":task_id,
                "actor":actor,"status":status,"summary":summary,
                "completed_steps":list(dict.fromkeys(completed_steps)),
                "changed_files":list(dict.fromkeys(changed_files)),
                "validation":list(dict.fromkeys(validation)),
                "evidence_refs":list(dict.fromkeys(evidence_refs)),
                "next_step":next_step,"blocker":blocker,"created_at":utc()}
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
                atomic(self.receipts/f"{checkpoint['checkpoint_id']}.checkpoint.receipt.json",
                       {**checkpoint,"status":"SAVED","source_report_id":path.stem,
                        "single_task_ledger":True})
                receipt={"schema":"raios.task-report-receipt.v1","report_id":path.stem,
                         "task_id":task_id,"actor":actor,"status":"ACCEPTED",
                         "task_status":task["status"],"evidence_refs":refs,
                         "checkpoint_id":checkpoint["checkpoint_id"],"at":utc()}
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
        busy={str(t.get("claimed_by") or t.get("assigned_to")).upper() for t in tasks
              if t.get("status")=="IN_PROGRESS" or t.get("dispatch_status")=="PENDING_ACCEPTANCE"}
        dispatched=0
        for task in tasks:
            if (task.get("automatic_dispatch") is not True or
                task.get("dispatch_authorized_by")!="C1"):continue
            if task.get("status")!="READY" or task.get("claimed_by") or task.get("assigned_to"):continue
            if not all(d in done for d in task.get("dependencies",[])):continue
            candidates=[s for s in SEATS if s!="C1" and s not in busy and
                        self._live(s) and self._eligible(task,s)]
            if not candidates:continue
            target=candidates[0]
            self.dispatch(str(task["id"]),target,worker)
            busy.add(target);dispatched+=1
        return dispatched
    def run_cycle(self,worker:Any)->dict[str,int]:
        with self.lock:
            reports=self._process_reports()
            data=load(self.tasks,{"tasks":[]})
            returned=self._reconcile_absent_assignments(data)
            dispatched=self._auto_dispatch(worker)
            return {**reports,"tasks_returned_absent":returned,"tasks_dispatched":dispatched}
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
        if not self._eligible(task,target):raise ValueError("SEAT_NOT_ALLOWED_FOR_TASK")
        if task.get("claimed_by") not in (None,target):raise ValueError("TASK_ALREADY_CLAIMED")
        dispatch_id="DSP-"+uuid.uuid4().hex[:16]
        task.update(assigned_to=target,assigned_by="C1",dispatched_by="RAIOS-WORKER",
                    dispatch_status="PENDING_ACCEPTANCE",dispatch_id=dispatch_id,
                    dispatched_at=utc(),system_owner="RAIOS_SYSTEM")
        atomic(self.tasks,data)
        checkpoint=task.get("resume_checkpoint") or {}
        resume=(f"\nCHECKPOINT_ID={checkpoint.get('checkpoint_id')}"
                f"\nLAST_PHASE={checkpoint.get('phase')}"
                f"\nNEXT_STEP={checkpoint.get('next_step')}"
                f"\nEVIDENCE_REFS={'|'.join(checkpoint.get('evidence_refs') or [])}"
                if checkpoint else "\nCHECKPOINT_ID=NONE\nNEXT_STEP=START_FROM_TASK_OBJECTIVE")
        text=(f"TASK_ASSIGNMENT\nTASK_ID={task_id}\nTARGET={target}\n"
              f"DISPATCH_ID={dispatch_id}\nAUTHORITY=C1{resume}\n"
              "ACTION=ACCEPT_TASK_THEN_RESUME_FROM_CHECKPOINT")
        msg=worker.enqueue("RAIOS-WORKER",[target],text,task_id)
        return {"status":"DISPATCHED_PENDING_ACCEPTANCE","task_id":task_id,
                "target":target,"dispatch_id":dispatch_id,"message_id":msg["message_id"]}
