from __future__ import annotations
import json, os, secrets, socket, subprocess, sys, urllib.error, urllib.request, uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from raios.search_cortex import SearchCortex
from .message_worker import COUNCIL_SEATS, ROUTING_TARGETS, MessageWorker
from .council_board import CouncilBoard
from .task_actions import latest_resource_census

CREATE_NO_WINDOW=getattr(subprocess,"CREATE_NO_WINDOW",0)
HERE=Path(__file__).resolve().parent
REPO=Path(os.getenv("RAIOS_CANONICAL_REPO",str(HERE.parents[2]))).resolve()
MCP_ROOT=Path(os.getenv("RAIOS_MCP_ROOT",str(REPO))).resolve()
RUNTIME=Path(os.getenv("RAIOS_COMMAND_CENTER_RUNTIME",str(Path.home()/".raios/runtime/command-center"))).resolve()
COUNCIL_PRESENCE=Path(os.getenv("RAIOS_COUNCIL_PRESENCE",str(Path.home()/".raios/runtime/council-ops/presence.json"))).resolve()
C5=os.getenv("RAIOS_C5_URL","http://127.0.0.1:8766")
CSRF=secrets.token_urlsafe(32)
MESSAGE_WORKER=MessageWorker(REPO,RUNTIME,poll_seconds=5.0)
COUNCIL_BOARD=CouncilBoard(REPO)
SEARCH_CORTEX=SearchCortex()
MESSAGE_WORKER.configure_workflow(COUNCIL_BOARD)

@asynccontextmanager
async def lifespan(_: FastAPI):
 MESSAGE_WORKER.start()
 try:
  yield
 finally:
  MESSAGE_WORKER.stop()

app=FastAPI(title="RAIOS Command Center",version="2.0",docs_url=None,redoc_url=None,lifespan=lifespan)

def utc(): return datetime.now(timezone.utc).isoformat()
def load(path,default):
 try:return json.loads(path.read_text(encoding="utf-8-sig"))
 except Exception:return default
def git(*args):
 try:return subprocess.check_output(["git",*args],cwd=REPO,text=True,stderr=subprocess.DEVNULL,timeout=8,creationflags=CREATE_NO_WINDOW).strip()
 except Exception:return "UNKNOWN"
def tcp(port):
 try:
  with socket.create_connection(("127.0.0.1",port),timeout=.8):return True
 except OSError:return False
def http_json(url,method="GET",body=None,timeout=8):
 data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
 req=urllib.request.Request(url,data=data,method=method,headers={"Content-Type":"application/json"})
 try:
  with urllib.request.urlopen(req,timeout=timeout) as r:
   raw=r.read().decode("utf-8-sig",errors="replace")
   try:body=json.loads(raw)
   except json.JSONDecodeError:
    body={"response_type":"NON_JSON","content_type":r.headers.get("Content-Type","").split(";",1)[0]}
   return r.status,body
 except urllib.error.HTTPError as e:
  try:return e.code,json.loads(e.read().decode("utf-8-sig"))
  except Exception:return e.code,{"error":str(e)}
 except Exception as e:return 0,{"error":f"{type(e).__name__}:{e}"}
def require_csrf(value):
 if not value or not secrets.compare_digest(value,CSRF):raise HTTPException(403,"CSRF_REQUIRED")
def service(name,port,url=None):
 listening=tcp(port); code,body=http_json(url,timeout=3) if url and listening else (None,{})
 ready=listening and (not url or code==200)
 return {"name":name,"state":"ONLINE" if ready else ("DEGRADED" if listening else "OFFLINE"),"port":port,"http":code,"detail":body}
def tasks_state():
 tasks=load(REPO/".ai-os/state/TASKS.json",{"tasks":[]})["tasks"]; locks=load(REPO/".ai-os/state/LOCKS.json",{"locks":[]})["locks"]
 return {"total":len(tasks),"ready":sum(t.get("status")=="READY" for t in tasks),"in_progress":sum(t.get("status")=="IN_PROGRESS" for t in tasks),
  "blocked":sum(t.get("status")=="BLOCKED" for t in tasks),"done":sum(t.get("status")=="DONE" for t in tasks),
  "active_locks":sum(x.get("status")=="ACTIVE" for x in locks),"recent":tasks[-12:]}
def _presence_state(row):
 if not row:return "UNPROVEN"
 state=str(row.get("presence") or "UNPROVEN").upper()
 if state!="PRESENT":return state
 expiry=row.get("lease_expires_at")
 if not expiry:return "PRESENT"
 try:
  return "PRESENT" if datetime.fromisoformat(str(expiry).replace("Z","+00:00"))>datetime.now(timezone.utc) else "EXPIRED"
 except (TypeError,ValueError):return "INVALID"
def council_state():
 seatmap=load(MCP_ROOT/".ai-os/mcp/SEAT-MAP.json",{})
 presence=load(COUNCIL_PRESENCE,{"seats":{}})
 registered=list((seatmap.get("seats") or {}).keys());seats=[];present=0
 for key,row in (seatmap.get("seats") or {}).items():
  proof=(presence.get("seats") or {}).get(key,{})
  state=_presence_state(proof);current=state=="PRESENT";present+=int(current)
  seats.append({"id":key,"name_ar":row.get("name_ar"),"role":row.get("actor_role"),
   "where":row.get("where"),"identity_registered":True,"identity_state":"REGISTERED",
   "presence":state,"presence_current":current,"lease_expires_at":proof.get("lease_expires_at"),
   "mail":row.get("mail",False)})
 return {"seats":seats,"registered_seats":registered,"live_declared":seatmap.get("live",[]),
  "identity_total":len(registered),"present_total":present,
  "no_registered_seats":not registered,"no_present_seats":present==0,
  "identity_ne_presence":True,"attendance_is_proof":True}
def model_state():
 code,body=http_json("http://127.0.0.1:11434/api/tags",timeout=4)
 models=[]
 if code==200:
  for m in body.get("models",[]):models.append({"name":m.get("name"),"size":m.get("size"),"modified_at":m.get("modified_at")})
 return {"ollama_online":code==200,"count":len(models),"models":models,"active_c5":"qwen3:0.6b"}
def receipt_state():
 roots=[MCP_ROOT/".ai-os/mcp/receipts",MCP_ROOT/".ai-os/receipts/command-fabric",REPO/".ai-os/receipts/command-fabric"]
 rows=[]
 for root in roots:
  if root.is_dir():
   for p in root.glob("*.json"):
    try:rows.append({"name":p.name,"path":str(p),"mtime":p.stat().st_mtime,"bytes":p.stat().st_size})
    except OSError:pass
 rows=sorted(rows,key=lambda x:x["mtime"],reverse=True)[:20]
 return {"count":len(rows),"recent":rows}
def factory_state():
 report=REPO/".ai-os/reports/factory-fabric"; names=["RESOURCE","ASSIMILATION","TRAINING","COGNITIVE","C5_EXPERT_FOUNDRY","MODEL"]
 return {"fabric_present":(REPO/"src/raios/factory_fabric").is_dir(),"factories":[{"name":n,"state":"AVAILABLE"} for n in names],"report_root":str(report)}
def resource_state():
 return latest_resource_census(REPO)
def cognitive_state():
 code,loop=http_json(C5+"/v1/cognitive/status",timeout=5)
 manager=load(Path.home()/".raios/runtime/manager/heartbeat.json",{})
 latest=load(Path.home()/".raios/runtime/search-cortex/latest.json",{})
 continuity=load(Path.home()/".raios/runtime/continuity/status.json",{})
 return {"online":code==200,"http":code,"loop":loop if code==200 else {},
  "manager":manager,"search_latest":latest,"continuity":continuity,
  "shared_search_cortex":bool((loop.get("search_cortex") or {}).get("shared")) if isinstance(loop,dict) else False,
  "existing_kae_reused":bool((loop.get("assimilation") or {}).get("existing_kae_reused")) if isinstance(loop,dict) else False}
def diagnostic_state():
 data=overview(); worker=MESSAGE_WORKER.status(); cognition=data.get("cognitive") or {}; loop=cognition.get("loop") or {}
 causes=[]
 for item in data["services"]:
  if item["state"]!="ONLINE":causes.append({"code":item["name"].upper()+"_NOT_ONLINE","severity":"CRITICAL","evidence":item,"recommended_action":"RESTORE_EXISTING_RUNTIME"})
 if worker.get("healthy") is not True:causes.append({"code":"MESSAGE_WORKER_UNHEALTHY","severity":"CRITICAL","evidence":worker,"recommended_action":"REDEPLOY_COMMAND_CENTER"})
 manager=(loop.get("manager") or {})
 if manager.get("alive") is not True:causes.append({"code":"CONTINUOUS_MANAGER_"+str(manager.get("reason") or "UNPROVEN"),"severity":"HIGH","evidence":manager,"recommended_action":"RESTART_EXISTING_MANAGER"})
 c5=next((x for x in data["services"] if x["name"]=="C5"),{})
 env=((c5.get("detail") or {}).get("environment") or {})
 if env.get("dependency_audit")!="PASS" or env.get("pytest_available") is not True:causes.append({"code":"C5_ENVIRONMENT_INCOMPLETE","severity":"HIGH","evidence":env,"recommended_action":"DEPLOY_CANONICAL_C5_REQUIREMENTS"})
 if data.get("canonical_head")!=data.get("remote_head"):causes.append({"code":"HEAD_REMOTE_DRIFT","severity":"MEDIUM","evidence":{"local":data.get("canonical_head"),"remote":data.get("remote_head")},"recommended_action":"REVIEW_FAST_FORWARD_POLICY"})
 score=max(0,100-sum(30 if x["severity"]=="CRITICAL" else 15 if x["severity"]=="HIGH" else 5 for x in causes))
 return {"schema":"raios.command-center.diagnosis.v2","generated_at":utc(),"health":"HEALTHY" if not causes else "DEGRADED",
  "score":score,"root_causes":causes,"services":data["services"],"worker":worker,"cognitive":cognition,
  "actions_executed":[],"canonical_mutation":False,"existing_first":True}
def overview():
 services=[service("C5",8766,C5+"/health"),service("9Router",20128,"http://127.0.0.1:20128/dashboard"),service("NATS",4222)]
 task=tasks_state(); degraded=[x["name"] for x in services if x["state"]!="ONLINE"]
 return {"generated_at":utc(),"canonical_head":git("rev-parse","HEAD"),"remote_head":git("rev-parse","origin/ai-evolution-202608051809"),
  "services":services,"tasks":task,"models":model_state(),"factories":factory_state(),"resources":resource_state(),"council":council_state(),"cognitive":cognitive_state(),
  "maintenance":{"health":"HEALTHY" if not degraded else "ATTENTION","degraded":degraded,"auto_refresh":True,
   "auto_canonical_mutation":False,"self_update_policy":"LOCAL_RUNTIME_FROM_FAST_FORWARD_CANONICAL_ONLY_WITH_C1_CONFIRMATION"}}

class ChatIn(BaseModel):text:str=Field(min_length=1,max_length=200000); conversation_id:str|None=None
class SearchIn(BaseModel):
 query:str=Field(min_length=2,max_length=4000)
 public_query:str|None=Field(default=None,max_length=400)
 allow_public:bool=False
 deep:bool=True
 limit:int=Field(default=20,ge=1,le=50)
class CommandIn(BaseModel):text:str=Field(min_length=1,max_length=50000);targets:list[str];task_id:str|None=None
class DispatchIn(BaseModel):task_id:str=Field(min_length=1,max_length=200);target:str=Field(min_length=2,max_length=20)
class TaskAcceptIn(BaseModel):
 task_id:str=Field(min_length=1,max_length=200)
 actor:str=Field(min_length=2,max_length=20)
 dispatch_id:str=Field(min_length=4,max_length=200)
class TaskCheckpointIn(BaseModel):
 task_id:str=Field(min_length=1,max_length=200)
 actor:str=Field(min_length=2,max_length=20)
 phase:str=Field(min_length=4,max_length=20)
 summary:str=Field(min_length=1,max_length=50000)
 completed_steps:list[str]=Field(default_factory=list,max_length=200)
 changed_files:list[str]=Field(default_factory=list,max_length=500)
 validation:list[str]=Field(default_factory=list,max_length=200)
 evidence_refs:list[str]=Field(default_factory=list,max_length=100)
 next_step:str=Field(min_length=1,max_length=50000)
 blocker:str|None=Field(default=None,max_length=50000)
class TaskReportIn(BaseModel):
 task_id:str=Field(min_length=1,max_length=200)
 actor:str=Field(min_length=2,max_length=20)
 status:str=Field(min_length=4,max_length=20)
 summary:str=Field(min_length=1,max_length=50000)
 completed_steps:list[str]=Field(default_factory=list,max_length=200)
 changed_files:list[str]=Field(default_factory=list,max_length=500)
 validation:list[str]=Field(default_factory=list,max_length=200)
 evidence_refs:list[str]=Field(default_factory=list,max_length=100)
 next_step:str=Field(min_length=1,max_length=50000)
 blocker:str|None=Field(default=None,max_length=50000)

def c1_gateway():
 sys.path.insert(0,str(REPO/"scripts/ai-os"))
 from raios_mcp.gateway import Gateway,write_envelope
 data=load(MCP_ROOT/".ai-os/mcp/tokens.local.json",{})
 grant=next((x for x in data.get("actors",[]) if x.get("actor_id")=="C1"),None)
 if not grant or not grant.get("token"):raise HTTPException(503,"C1_MCP_GRANT_UNAVAILABLE")
 gw=Gateway.from_root(MCP_ROOT); actor=gw.authenticate(grant["token"]); return gw,actor,write_envelope

@app.get("/",response_class=HTMLResponse)
def index():return (HERE/"index.html").read_text(encoding="utf-8")
@app.get("/api/bootstrap")
def bootstrap():return {"csrf":CSRF,"overview":overview(),"ui":"CANONICAL_COMMAND_CENTER","direct_mutation":False}
@app.get("/api/overview")
def api_overview():return overview()
@app.get("/api/cognitive")
def api_cognitive():return cognitive_state()
@app.post("/api/search")
def api_search(req:SearchIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 return SEARCH_CORTEX.search(req.query,public_allowed=req.allow_public,public_query=req.public_query,
  official_allowed=True,limit=req.limit,deep=req.deep,trace=True)
@app.get("/api/tasks")
def api_tasks():return tasks_state()
@app.get("/api/council")
def api_council():return council_state()
@app.get("/api/council-board")
def api_council_board():return COUNCIL_BOARD.snapshot()
@app.post("/api/task-dispatch")
def api_task_dispatch(req:DispatchIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:return COUNCIL_BOARD.dispatch(req.task_id,req.target,MESSAGE_WORKER)
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.post("/api/task-accept")
def api_task_accept(req:TaskAcceptIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:return COUNCIL_BOARD.accept_task(req.task_id,req.actor,req.dispatch_id)
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.post("/api/task-checkpoint")
def api_task_checkpoint(req:TaskCheckpointIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:return COUNCIL_BOARD.submit_checkpoint(req.task_id,req.actor,req.phase,req.summary,
  req.completed_steps,req.changed_files,req.validation,req.evidence_refs,
  req.next_step,req.blocker)
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.get("/api/task-resume/{task_id}")
def api_task_resume(task_id:str):
 try:return COUNCIL_BOARD.resume_checkpoint(task_id)
 except ValueError as exc:raise HTTPException(404,str(exc))
@app.post("/api/task-report")
def api_task_report(req:TaskReportIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:return COUNCIL_BOARD.submit_report(req.task_id,req.actor,req.status,req.summary,
  req.evidence_refs,req.completed_steps,req.changed_files,req.validation,
  req.next_step,req.blocker)
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.get("/api/models")
def api_models():return model_state()
@app.get("/api/receipts")
def api_receipts():return receipt_state()
@app.get("/api/message-worker")
def api_message_worker():return MESSAGE_WORKER.status()
@app.get("/api/factories")
def api_factories():return factory_state()
@app.get("/api/resources")
def api_resources():return resource_state()
@app.post("/api/chat")
def chat(req:ChatIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf); code,body=http_json(C5+"/v1/chat","POST",{"text":req.text,"language":"auto","conversation_id":req.conversation_id},130)
 if code!=200:raise HTTPException(502,{"upstream":code,"detail":body})
 return {"ok":True,**body}
@app.post("/api/command")
def command(req:CommandIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf); allowed=set(ROUTING_TARGETS); targets=[]
 for t in req.targets:
  u=t.upper(); targets.extend(COUNCIL_SEATS if u=="ALL" else [u])
 targets=list(dict.fromkeys(targets))
 if not targets or any(t not in allowed for t in targets):raise HTTPException(400,"TARGET_NOT_LIVE_OR_UNKNOWN")
 try:msg=MESSAGE_WORKER.enqueue("C1@COMMAND_CENTER",targets,req.text,req.task_id)
 except ValueError as exc:raise HTTPException(400,str(exc))
 return {"ok":True,"results":[{"targets":targets,"route":"CANONICAL_LOCAL_FABRIC",
  "status":"SENT_PENDING_DELIVERY_ACK","message_id":msg["message_id"]}],
  "executed":False,"promotion":False,"timestamp":utc()}
@app.post("/api/maintenance/diagnose")
def diagnose(x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf); data=diagnostic_state(); return {"ok":True,"diagnosis":data,"actions_executed":[],"canonical_mutation":False}
@app.get("/health")
def health():
 worker=MESSAGE_WORKER.status();online=worker.get("healthy") is True
 return {"status":"ONLINE" if online else "DEGRADED","service":"RAIOS_COMMAND_CENTER",
  "canonical_head":git("rev-parse","HEAD"),"message_worker":worker,
  "workflow_automation":worker.get("workflow_enabled") is True,"timestamp":utc()}
