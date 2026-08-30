from __future__ import annotations
import json, os, secrets, socket, subprocess, sys, urllib.error, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .message_worker import COUNCIL_SEATS, ROUTING_TARGETS, MessageWorker
from .council_board import CouncilBoard

HERE=Path(__file__).resolve().parent
REPO=Path(os.getenv("RAIOS_CANONICAL_REPO",str(HERE.parents[2]))).resolve()
MCP_ROOT=Path(os.getenv("RAIOS_MCP_ROOT",str(REPO))).resolve()
RUNTIME=Path(os.getenv("RAIOS_COMMAND_CENTER_RUNTIME",str(Path.home()/".raios/runtime/command-center"))).resolve()
C5=os.getenv("RAIOS_C5_URL","http://127.0.0.1:8766")
CSRF=secrets.token_urlsafe(32)
app=FastAPI(title="RAIOS Command Center",version="1.1",docs_url=None,redoc_url=None)
MESSAGE_WORKER=MessageWorker(REPO,RUNTIME)
COUNCIL_BOARD=CouncilBoard(REPO)

@app.on_event("startup")
def start_message_worker():MESSAGE_WORKER.start()
@app.on_event("shutdown")
def stop_message_worker():MESSAGE_WORKER.stop()

def utc(): return datetime.now(timezone.utc).isoformat()
def load(path,default):
 try:return json.loads(path.read_text(encoding="utf-8-sig"))
 except Exception:return default
def git(*args):
 try:return subprocess.check_output(["git",*args],cwd=REPO,text=True,stderr=subprocess.DEVNULL,timeout=8).strip()
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
   raw=r.read().decode("utf-8-sig",errors="replace"); return r.status,json.loads(raw)
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
def council_state():
 seatmap=load(MCP_ROOT/".ai-os/mcp/SEAT-MAP.json",{}); presence=load(Path.home()/".raios/runtime/council-ops/presence.json",{"seats":{}})
 seats=[]
 for key,row in (seatmap.get("seats") or {}).items():
  p=(presence.get("seats") or {}).get(key,{})
  seats.append({"id":key,"name_ar":row.get("name_ar"),"role":row.get("actor_role"),"where":row.get("where"),"presence":p.get("presence","UNPROVEN"),"mail":row.get("mail",False)})
 return {"seats":seats,"live_declared":seatmap.get("live",[]),"attendance_is_proof":True}
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
def overview():
 services=[service("C5",8766,C5+"/health"),service("9Router",20128,"http://127.0.0.1:20128/dashboard"),service("NATS",4222)]
 task=tasks_state(); degraded=[x["name"] for x in services if x["state"]!="ONLINE"]
 return {"generated_at":utc(),"canonical_head":git("rev-parse","HEAD"),"remote_head":git("rev-parse","origin/ai-evolution-202608051809"),
  "services":services,"tasks":task,"models":model_state(),"factories":factory_state(),"council":council_state(),
  "maintenance":{"health":"HEALTHY" if not degraded else "ATTENTION","degraded":degraded,"auto_refresh":True,
   "auto_canonical_mutation":False,"self_update_policy":"LOCAL_RUNTIME_FROM_FAST_FORWARD_CANONICAL_ONLY_WITH_C1_CONFIRMATION"}}

class ChatIn(BaseModel):text:str=Field(min_length=1,max_length=200000); conversation_id:str|None=None
class CommandIn(BaseModel):text:str=Field(min_length=1,max_length=50000);targets:list[str];task_id:str|None=None
class DispatchIn(BaseModel):task_id:str=Field(min_length=1,max_length=200);target:str=Field(min_length=2,max_length=20)

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
@app.get("/api/models")
def api_models():return model_state()
@app.get("/api/receipts")
def api_receipts():return receipt_state()
@app.get("/api/message-worker")
def api_message_worker():
 return load(MESSAGE_WORKER.state/"heartbeat.json",{"worker_id":MESSAGE_WORKER.worker_id,"status":"STARTING"})
@app.get("/api/factories")
def api_factories():return factory_state()
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
 require_csrf(x_raios_csrf); data=overview(); return {"ok":True,"diagnosis":data["maintenance"],"actions_executed":[],"canonical_mutation":False}
@app.get("/health")
def health():return {"status":"ONLINE","service":"RAIOS_COMMAND_CENTER","canonical_head":git("rev-parse","HEAD"),"timestamp":utc()}
