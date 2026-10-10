from __future__ import annotations
import json, os, secrets, socket, subprocess, sys, time, urllib.error, urllib.request, uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from raios.search_cortex import SearchCortex
from raios.ai_gateway import ModelRouter, RouteRequest
from .coordination_truth import lock_is_effective
from .engine_plane import snapshot as engine_snapshot
from .message_worker import COUNCIL_SEATS, ROUTING_TARGETS, MessageWorker
from .actor_routing import ActorRouteRegistry
from .council_board import CouncilBoard
from .task_actions import latest_resource_census
from .client_activity import ClientActivityView
from .direct_conversation import DirectConversationPlane
from .council_member_state import build_council_member_state
from .operational_projection import (
    capability_projection,
    head_truth,
    operational_attention,
    classify_model_fabric,
    command_intent_envelope,
    operational_blockers,
    runtime_health_view,
    enrich_change_authority,
    COMMAND_INTENTS,
    QWEN_REGISTRY_BLOCKER,
)
from .system_surface import (
    capability_routing_projection,
    copy_estate_projection,
    fabric_projection,
    factory_estate_projection,
    incidents_projection,
    integration_mesh_projection,
    operator_laws_projection,
    reachability_projection,
    self_heal_projection,
    storage_class_projection,
    system_topology_projection,
)
from .live_activation import (
    consume_c8_wave06,
    live_actor_rows,
    operator_task_buckets,
    raios_system_actor,
    RAIOS_NOT_COUNCIL_SEATS,
    safe8_identity_decision,
)
from .c8_live_convergence import (
    consume_c8_live_package,
    knowledge_islands_projection,
    providers_projection,
    resource_admission_projection,
)
from .storage_authority import command_fabric_event_receipt_scan_roots
from raios.council_ops import CouncilOperations

CREATE_NO_WINDOW=getattr(subprocess,"CREATE_NO_WINDOW",0)
HERE=Path(__file__).resolve().parent
REPO=Path(os.getenv("RAIOS_CANONICAL_REPO",str(HERE.parents[2]))).resolve()
MCP_ROOT=Path(os.getenv("RAIOS_MCP_ROOT",str(REPO))).resolve()
RUNTIME=Path(os.getenv("RAIOS_COMMAND_CENTER_RUNTIME",str(Path.home()/".raios/runtime/command-center"))).resolve()
COUNCIL_PRESENCE=Path(os.getenv("RAIOS_COUNCIL_PRESENCE",str(Path.home()/".raios/runtime/council-ops/presence.json"))).resolve()
FACTORY_RUNTIME_LATEST=Path(os.getenv("RAIOS_FACTORY_RUNTIME_LATEST",str(Path.home()/".raios/runtime/factory-fabric/FACTORY-FABRIC-LATEST.json"))).resolve()
CONTINUITY_STATUS=Path(os.getenv("RAIOS_CONTINUITY_STATUS",str(Path.home()/".raios/runtime/continuity/status.json"))).resolve()
C5=os.getenv("RAIOS_C5_URL","http://127.0.0.1:8766")
MCP="http://127.0.0.1:8788"
CSRF=secrets.token_urlsafe(32)
MESSAGE_WORKER=None
ACTOR_ROUTES=ActorRouteRegistry(REPO,presence_path=COUNCIL_PRESENCE)
_ACTOR_ROUTES_CACHE: dict[str, Any]={"at":0.0,"body":None}
COUNCIL_BOARD=CouncilBoard(REPO,routes=ACTOR_ROUTES)
SEARCH_CORTEX=SearchCortex()
MODEL_ROUTER=ModelRouter(REPO)
CLIENT_ACTIVITY=ClientActivityView(REPO,ACTOR_ROUTES)
COUNCIL_OPS=CouncilOperations(REPO)
MESSAGE_WORKER=MessageWorker(REPO,RUNTIME,poll_seconds=5.0,max_messages_per_scan=50000,max_scan_seconds=30.0,routes=ACTOR_ROUTES)
MESSAGE_WORKER.configure_workflow(COUNCIL_BOARD)
DIRECT_PLANE=DirectConversationPlane(REPO,ACTOR_ROUTES,MESSAGE_WORKER,CLIENT_ACTIVITY)

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
CANONICAL_HEAD=os.getenv("RAIOS_CANONICAL_HEAD","").strip() or git("rev-parse","HEAD")
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
def service(name,port,url=None,timeout=3):
 listening=tcp(port); code,body=http_json(url,timeout=timeout) if url and listening else (None,{})
 if name=="C5" and listening and isinstance(body,dict):
  if code==0:
   err=str(body.get("error") or "")
   probe="TIMEOUT" if "Timeout" in err or "timed out" in err.lower() else "UNAVAILABLE"
   return {"name":name,"state":"UNKNOWN" if probe=="TIMEOUT" else "UNAVAILABLE","port":port,"http":code,
           "detail":body,"probe_state":probe,"timeout_ne_empty_inventory":True}
  if code==200:
   c5s=str(body.get("status") or "").upper()
   probe=str(body.get("model_fabric_probe_state") or "").upper()
   if probe=="TIMEOUT" or ("model_fabric_ready" in body and body.get("model_fabric_ready") is None):
    return {"name":name,"state":"UNKNOWN","port":port,"http":code,"detail":body,
            "probe_state":"TIMEOUT" if probe=="TIMEOUT" else "UNKNOWN",
            "timeout_ne_empty_inventory":True,"runtime_reachable":True,
            "model_fabric_error":body.get("model_fabric_error")}
   if c5s in {"UNKNOWN","DEGRADED"}:
    return {"name":name,"state":c5s,"port":port,"http":code,"detail":body,"probe_state":probe}
 ready=listening and (not url or code==200)
 return {"name":name,"state":"ONLINE" if ready else ("DEGRADED" if listening else "OFFLINE"),"port":port,"http":code,"detail":body}
def tcp_service(name,port):
 listening=tcp(port)
 return {"name":name,"state":"ONLINE" if listening else "OFFLINE","port":port,"http":None,
  "probe":"TCP_ONLY","detail":{"probe":"TCP_ONLY","listening":listening}}
def live_plane():
 return {"schema":"raios.command-center.live-plane.v1","generated_at":utc(),
  "canonical_head":CANONICAL_HEAD,"self":{"name":"CommandCenter","port":8770,"state":"ONLINE","probe":"SELF"},
  "services":[tcp_service("C5",8766),service("UniversalMCP",8788,MCP+"/health"),tcp_service("9Router",20128),tcp_service("NATS",4222)]}
def mcp_bind():
 code,body=http_json(MCP+"/health",timeout=3)
 health=body if isinstance(body,dict) else {}
 adapters=[]
 channel=load(REPO/".ai-os/mcp/EXECUTION-CHANNEL.json",{})
 for row in channel.get("runtimes") or []:
  if row.get("adapter") is True:
   adapters.append({"id":row.get("id"),"role":row.get("role"),"transport":row.get("transport"),
                    "health_stamp":row.get("health"),"adapter":True})
 expected_tools=["get_head","read_board","read_inbox","read_receipt","get_diff","post_opinion","send_packet","ack_packet","execute_scoped_task"]
 actual_tools=list(health.get("tools") or [])
 live=(code==200 and health.get("ok") is True
       and int(health.get("tool_count") or 0)==9
       and actual_tools==expected_tools
       and health.get("ninth_tool") is True
       and health.get("execute_scoped_task") is True
       and health.get("get_sse") is True
       and health.get("second_gateway") is False
       and health.get("duplicate_mcp") is False
       and health.get("raw_shell") is False)
 err=str(health.get("error") or "") if isinstance(health,dict) else ""
 if code==200:
  probe_state="CURRENT"; observation_class="CURRENT"
 elif code==0 and ("Timeout" in err or "timed out" in err.lower()):
  probe_state="TIMEOUT"; observation_class="UNKNOWN"
 elif code==0:
  probe_state="UNAVAILABLE"; observation_class="UNKNOWN"
 else:
  probe_state="UNAVAILABLE"; observation_class="CURRENT"
 return {"schema":"raios.command-center.mcp-bind.v1","generated_at":utc(),"observed_at":utc(),"census_port":8788,
  "observation_class":observation_class,"probe_state":probe_state,"hardcoded_offline":False,
  "endpoint":MCP+"/mcp","health_url":MCP+"/health","http":code,"live":live,
  "second_gateway":health.get("second_gateway") is True,
  "duplicate_mcp":health.get("duplicate_mcp") is True,
  "ninth_tool":health.get("ninth_tool") is True,
  "execute_scoped_task":health.get("execute_scoped_task") is True,
  "raw_shell":health.get("raw_shell") is True,
  "v1_execution_intent":"GOVERNED_DELEGATED_ONLY",
  "client_gateway_ne_seat_bus":True,"internal_bus":"COMMAND_FABRIC",
  "loopback_read_without_token":True,"writes_require_actor_grant":True,
  "c2_grant_invented":False,"c6_grant_invented":False,
  "client_channel":health.get("channel") or "MISSING","get_sse":health.get("get_sse") is True,
  "stateless":health.get("stateless") is True,"session_count":health.get("session_count"),
  "tools":health.get("tools") or [],"tool_count":health.get("tool_count"),
  "head":health.get("head"),"head_source":health.get("head_source"),
  "health":{k:health.get(k) for k in ("ok","service","transport","ninth_tool","second_gateway","law","channel","get_sse","stateless") if k in health},
  "cursor_example":".ai-os/mcp/cursor-mcp.example.json","cursor_project_bind":".cursor/mcp.json",
  "adapters_behind_gateway":adapters,
  "law":["REUSE_EXISTING_UNIVERSAL_MCP","NO_SECOND_GATEWAY","EXACT_NINE_TOOLS","NO_RAW_SHELL","MCP_GATEWAY_NE_TRUTH_AUTHORITY",
         "COMMAND_FABRIC_REMAINS_INTERNAL_BUS","MCP_HAS_STREAMABLE_HTTP_SESSION_CHANNEL"]}
def council_lite():
 snap=ACTOR_ROUTES.snapshot(); seats=[]
 for row in snap.get("seats") or []:
  seats.append({"seat":row.get("seat"),"actor_role":row.get("actor_role"),
   "present":row.get("present") is True,"presence_state":row.get("presence_state"),
   "auto_routable":row.get("auto_routable") is True,"consumer_current":row.get("consumer_current") is True,
   "binding_current":row.get("binding_current") is True,"discovery_state":row.get("discovery_state"),
   "origin_instance":row.get("origin_instance"),"actor_id":row.get("actor_id")})
 return {"schema":"raios.council-lite.v1","active_workers":["C1","C2","C8"],
  "auto_routable":list(snap.get("auto_routable") or []),"auto_routable_count":int(snap.get("auto_routable_count") or 0),
  "registered_count":len(seats),"seats":seats}
def load_tasks_cached():
 from raios.command_center.board_now import load_tasks_document
 return load_tasks_document(REPO/".ai-os/state/TASKS.json",{"tasks":[]})
def tasks_state():
 doc=load_tasks_cached()
 tasks=doc.get("tasks") or []
 from raios.command_center.board_now import hanging_work, now_tasks
 from raios.goals.catalog import program_task_map
 now=now_tasks(tasks)
 buckets=operator_task_buckets(tasks)
 hang=hanging_work(tasks)
 return {"total":len(tasks),"ready":sum(t.get("status")=="READY" for t in tasks),"in_progress":sum(t.get("status")=="IN_PROGRESS" for t in tasks),
  "blocked":sum(t.get("status")=="BLOCKED" for t in tasks),"done":sum(t.get("status")=="DONE" for t in tasks),
  "operator_buckets":buckets["buckets"],"operator_tasks":buckets["tasks"],
  "hanging_work":hang,
  "second_task_ledger":False,"source":".ai-os/state/TASKS.json",
  "active_locks":None,"locks_scanned":False,"locks_omitted_reason":"OVERVIEW_MUST_NOT_PARSE_FULL_LOCKS_LEDGER",
  "recent":now[:12],"now":now,
  "now_ne_full_ledger":True,"active_program_id":doc.get("active_program_id"),
  "named_goal_id":doc.get("active_program_id"),
  "program_operations":program_task_map(doc,REPO)}
def _presence_state(row):
 if not row:return "UNPROVEN"
 state=str(row.get("presence") or "UNPROVEN").upper()
 if state=="PRESENT" and row.get("signature_valid") is not True:return "UNVERIFIED"
 if state!="PRESENT":return state
 expiry=row.get("lease_expires_at")
 if not expiry:return "PRESENT"
 try:
  return "PRESENT" if datetime.fromisoformat(str(expiry).replace("Z","+00:00"))>datetime.now(timezone.utc) else "EXPIRED"
 except (TypeError,ValueError):return "INVALID"
def council_state():
 snap=CLIENT_ACTIVITY.snapshot(include_member_state=False);seatmap=load(MCP_ROOT/".ai-os/mcp/SEAT-MAP.json",{})
 by_spec=seatmap.get("seats") or {};seats=[]
 for row in snap.get("clients",[]):
  key=row.get("seat");spec=by_spec.get(key,{})
  seats.append({"id":key,"name_ar":spec.get("name_ar"),"role":row.get("actor_role"),
   "where":spec.get("where"),"identity_registered":True,"identity_state":"REGISTERED",
   "presence":row.get("presence"),"presence_current":row.get("present") is True,
   "availability":row.get("availability"),"execution_ready":row.get("execution_ready"),
   "work_phase":row.get("work_phase"),"reason":row.get("reason"),
   "current_tasks":row.get("current_tasks",[]),"mail":spec.get("mail",False)})
 present=sum(1 for x in seats if x.get("presence_current"))
 return {"schema":"raios.council-state.v3","canonical_coordination_source":"/api/client-activity",
  "seats":seats,"registered_seats":[x.get("id") for x in seats],
  "identity_total":len(seats),"present_total":present,
  "available_total":sum(1 for x in seats if x.get("availability")=="AVAILABLE"),
  "execution_ready_total":sum(1 for x in seats if x.get("execution_ready") is True),
  "no_registered_seats":not seats,"no_present_seats":present==0,
  "identity_ne_presence":True,"availability_ne_execution_readiness":True,
  "attendance_is_proof":True,"source_schema":snap.get("schema")}
def model_state():
  """C5 model-fabric truth. TIMEOUT is not an empty successful inventory."""
  code,body=http_json(C5+"/health",timeout=4)
  err=str((body or {}).get("error") or "") if isinstance(body,dict) else ""
  if code==0:
    probe="TIMEOUT" if "Timeout" in err or "timed out" in err.lower() else "UNAVAILABLE"
    raw={"source":"C5_HEALTH","probe_state":probe,"http":code,
            "ollama_online":False,"count":None if probe=="TIMEOUT" else 0,"models":[],
            "timeout_ne_empty_inventory":True,"fabric_ready":None if probe=="TIMEOUT" else False,
            "model_fabric_error":err or "C5_HEALTH_UNREACHABLE","active_c5":None}
  elif code!=200 or not isinstance(body,dict):
    raw={"source":"C5_HEALTH","probe_state":"UNAVAILABLE","http":code,
            "ollama_online":False,"count":0,"models":[],"timeout_ne_empty_inventory":True,
            "fabric_ready":False,"model_fabric_error":err or f"HTTP_{code}","active_c5":None}
  else:
    probe=str(body.get("model_fabric_probe_state") or "UNKNOWN").upper()
    fabric_ready=body.get("model_fabric_ready")
    live=list(body.get("live_engines") or [])
    count=body.get("live_engine_count")
    fabric_err=str(body.get("model_fabric_error") or err or "")
    if probe=="TIMEOUT" or ("model_fabric_ready" in body and fabric_ready is None):
      raw={"source":"C5_HEALTH","probe_state":"TIMEOUT","http":code,
            "ollama_online":False,"count":None,"models":[],
            "timeout_ne_empty_inventory":True,"fabric_ready":None,
            "model_fabric_error":body.get("model_fabric_error") or "OLLAMA_INVENTORY_PROBE_TIMEOUT",
            "c5_status":body.get("status"),"active_c5":None}
    else:
      if probe in {"ERROR","UNAVAILABLE"}:
        state="UNAVAILABLE"
      elif fabric_ready is True:
        state="CURRENT"
      elif fabric_ready is False:
        state="DEGRADED"
      else:
        state="UNKNOWN"
      raw={"source":"C5_HEALTH","probe_state":state,"http":code,
          "ollama_online":fabric_ready is True,"count":count if count is not None else len(live),
          "models":[{"name":x} for x in live],
          "timeout_ne_empty_inventory":True,"fabric_ready":fabric_ready,
          "model_fabric_error":body.get("model_fabric_error"),
          "c5_status":body.get("status"),"active_c5":live[0] if live else None}
    err=fabric_err or err
  registry="registry.ollama.ai" in err.lower()
  return classify_model_fabric(raw,ollama_listening=tcp(11434),recorded_remote_registry=registry)

def change_authority_state():
  doc=load(REPO/".ai-os/mcp/CANONICAL-CHANGE-AUTHORITY.json",{})
  heads=head_truth(canonical_head=CANONICAL_HEAD,deployed_head=os.getenv("RAIOS_DEPLOYED_HEAD"),
                   runtime_head=os.getenv("RAIOS_RUNTIME_HEAD"),actor_observed_head=os.getenv("RAIOS_ACTOR_OBSERVED_HEAD"),
                   remote_head=os.getenv("RAIOS_REMOTE_HEAD","UNKNOWN"))
  receipt=load(REPO/".ai-os/mcp/CANONICAL-CHANGE-APPROVAL.json",{})
  if not receipt:
    receipt=load(REPO/".ai-os/state/CANONICAL-CHANGE-APPROVAL.json",{})
  base={"schema":"raios.change-authority-view.v1","state":"UNKNOWN" if not doc else "CURRENT",
        "source_missing":not doc,"canonical_head":CANONICAL_HEAD,"heads":heads,
        "canonical_branch":(doc or {}).get("canonical_branch"),
        "CANONICAL_HEAD":heads["CANONICAL_HEAD"],"DEPLOYED_HEAD":heads["DEPLOYED_HEAD"],
        "RUNTIME_HEAD":heads["RUNTIME_HEAD"],"ACTOR_OBSERVED_HEAD":heads["ACTOR_OBSERVED_HEAD"],
        "authority":(doc or {}).get("authority"),"approval_receipt_required":(doc or {}).get("approval_receipt_required"),
        "workers_may_promote_without_c1_approval":(doc or {}).get("workers_may_promote_without_c1_approval") is True,
        "promotion":False,"auto_approval":False,"silent_promote":False,"auto_commit":False,"auto_push":False,
        "law":(doc or {}).get("law") or []}
  return enrich_change_authority(base,heads=heads,approval_receipt=receipt if receipt else None,
                                canonical_head=CANONICAL_HEAD)
def receipt_state():
 roots=list(command_fabric_event_receipt_scan_roots(REPO))
 mcp_receipts=MCP_ROOT/".ai-os/mcp/receipts"
 if mcp_receipts.resolve() not in [p.resolve() for p in roots]:
  roots.append(mcp_receipts)
 rows=[];seen=set();scanned=0;cap=400
 for root in roots:
  if not root.is_dir():continue
  try:entries=os.scandir(root)
  except OSError:continue
  for e in entries:
   scanned+=1
   if scanned>cap:break
   if not e.name.endswith(".json"):continue
   try:
    key=str(Path(e.path).resolve()).casefold()
    if key in seen:continue
    seen.add(key);st=e.stat();rows.append({"name":e.name,"path":e.path,"mtime":st.st_mtime,"bytes":st.st_size})
   except OSError:pass
  if scanned>cap:break
 rows=sorted(rows,key=lambda x:x["mtime"],reverse=True)[:20]
 return {"count":len(rows),"recent":rows,"scan_capped":scanned>=cap,"scan_count":scanned,
  "source_roots":[str(r) for r in roots],"high_volume_git_walk":False}
def factory_state():
 fabric=(REPO/"src/raios/factory_fabric").is_dir()
 runtime=load(FACTORY_RUNTIME_LATEST,{})
 estate=factory_estate_projection(REPO,live_runtime=runtime if runtime else None)
 if runtime:
  return {"fabric_present":fabric,"live_runtime_claimed":True,"runtime_path":str(FACTORY_RUNTIME_LATEST),
          "schema":runtime.get("schema"),"generated_at":runtime.get("generated_at"),"runtime_status":runtime.get("status","UNKNOWN"),
          "factories":runtime.get("factories",{}),"canonical_repo_mutation":runtime.get("canonical_repo_mutation",False),
          "provider_mutation":runtime.get("provider_mutation",False),"automatic_canonical_promotion":runtime.get("automatic_canonical_promotion",False),
          "estate":estate,"canonical_factories_wired":True,"run_all_on_refresh":False,"second_factory_created":False,
         "c8_wave06":consume_c8_wave06(REPO),"CONTROL_PLANE_ACTIVATED":False}
 classified={row["id"]:row for row in estate.get("factories") or []}
 return {"fabric_present":fabric,"live_runtime_claimed":False,"runtime_path":str(FACTORY_RUNTIME_LATEST),
         "runtime_status":"UNPROVEN","factories":classified,"canonical_repo_mutation":False,
         "provider_mutation":False,"automatic_canonical_promotion":False,
         "estate":estate,"canonical_factories_wired":True,"run_all_on_refresh":False,"second_factory_created":False,
         "c8_wave06":consume_c8_wave06(REPO),"CONTROL_PLANE_ACTIVATED":False}
def goals_state():
 from raios.goals.catalog import load_goals
 return load_goals(REPO)
def resource_state():
 census=latest_resource_census(REPO)
 cap=capability_projection(REPO)
 if not isinstance(census,dict):
  census={"status":"UNREADABLE"}
 return {**census,"capability_map":cap,"live_probe_on_dashboard_refresh":False}
def cognitive_state():
 code,loop=http_json(C5+"/v1/cognitive/status",timeout=5)
 manager=load(Path.home()/".raios/runtime/manager/heartbeat.json",{})
 latest=load(Path.home()/".raios/runtime/search-cortex/latest.json",{})
 continuity=load(CONTINUITY_STATUS,{})
 return {"online":code==200,"http":code,"loop":loop if code==200 else {},
  "manager":manager,"search_latest":latest,"continuity":continuity,
  "shared_search_cortex":bool((loop.get("search_cortex") or {}).get("shared")) if isinstance(loop,dict) else False,
  "existing_kae_reused":bool((loop.get("assimilation") or {}).get("existing_kae_reused")) if isinstance(loop,dict) else False}
def engine_state():
 return engine_snapshot(REPO)
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
def live_board():
 cached=_ACTOR_ROUTES_CACHE.get("body")
 if isinstance(cached, dict):
  routes=dict(cached); routes["freshness"]=routes.get("freshness") or "CACHED"; routes["stale"]=True
 else:
  try:
   routes=ACTOR_ROUTES.snapshot(process_discovery=False, max_challenges=8)
   routes["freshness"]="LIVE"; routes["stale"]=False
   _ACTOR_ROUTES_CACHE["at"]=time.monotonic(); _ACTOR_ROUTES_CACHE["body"]=routes
  except Exception as exc:
   routes={"schema":"raios.actor-route-registry.v2","stale":True,"freshness":"STALE",
           "error":type(exc).__name__,"seats":[]}
 actors=live_actor_rows(routes); worker=MESSAGE_WORKER.status(); c8=consume_c8_wave06(REPO)
 live_pkg=consume_c8_live_package(REPO)
 with ThreadPoolExecutor(max_workers=3) as pool:
  c5_f=pool.submit(http_json,C5+"/health", "GET", None, 0.8)
  mcp_f=pool.submit(http_json,MCP+"/health", "GET", None, 0.8)
  c5_code,_=c5_f.result(); mcp_code,_=mcp_f.result()
 nr_listening=tcp(20128)
 c5_state="ONLINE" if c5_code==200 else ("UNKNOWN" if c5_code==0 else "OFFLINE")
 mcp_state="ONLINE" if mcp_code==200 else ("UNKNOWN" if mcp_code==0 else "OFFLINE")
 tasks=tasks_state(); safe=safe8_identity_decision(); sys_actor=raios_system_actor()
 live_bound=[a for a in actors if a.get("auto_routable") is True]
 deploy=load(RUNTIME/"deployment.json",{}) or {}
 factory=load(FACTORY_RUNTIME_LATEST,{}) or {}
 resource=factory.get("resource_factory") if isinstance(factory.get("resource_factory"), dict) else {}
 model=factory.get("model_factory") if isinstance(factory.get("model_factory"), dict) else {}
 fabric_pass=str(factory.get("status") or factory.get("FACTORY_FABRIC") or "").upper() in {"PASS","OK","HEALTHY"}
 if factory.get("ok") is True: fabric_pass=True
 return {"schema":"raios.command-center.live-board.v1","generated_at":utc(),"stale":bool(routes.get("stale")),
  "freshness":routes.get("freshness") or "LIVE",
  "C5":{"http":c5_code,"state":c5_state,"source":C5+"/health","timeout_ne_offline":c5_code==0},
  "MCP":{"http":mcp_code,"state":mcp_state,"source":MCP+"/health"},
  "NINEROUTER":{"port":20128,"state":"ONLINE" if nr_listening else "OFFLINE","probe":"TCP_ONLY"},
  "COMMAND_CENTER":{"state":"ONLINE","port":8770,"source":"/health"},
  "COMMAND_FABRIC":{"worker_healthy":worker.get("healthy") is True,"source":"MESSAGE_WORKER.status","synthetic_ack":False},
  "HEADS":head_truth(canonical_head=CANONICAL_HEAD,deployed_head=os.getenv("RAIOS_DEPLOYED_HEAD") or deploy.get("canonical_head"),
                     runtime_head=os.getenv("RAIOS_RUNTIME_HEAD"),actor_observed_head=os.getenv("RAIOS_ACTOR_OBSERVED_HEAD"),
                     remote_head=os.getenv("RAIOS_REMOTE_HEAD","UNKNOWN")),
  "actors":actors,"live_bound":live_bound,"online_actors":[a["seat"] for a in live_bound],
  "raios":sys_actor,"tasks":tasks["operator_buckets"],"c8_wave06":c8,"c8_live":live_pkg,"safe8":safe,
  "FACTORIES_TOTAL":c8["FACTORY_COMPONENTS_TOTAL"],"FACTORIES_REACHABLE":c8["RUNTIME_REACHABLE"],
  "FACTORIES_ACTIVE":c8["ACTIVE"],"FACTORIES_EXECUTING":c8["EXECUTING"],"FACTORIES_HEALTHY":c8["HEALTHY"],
  "CAPABILITIES":c8["CAPABILITIES"],
  "knowledge":{"DNA":c8["KNOWLEDGE_DNA"],"islands":live_pkg.get("knowledge_islands") or [],
               "unwired":len(live_pkg.get("high_value_islands_open") or []),
               "zero_knowledge_island":live_pkg.get("zero_knowledge_island")},
  "providers":live_pkg.get("providers") or {},"blockers":live_pkg.get("c2_blockers") or [],
  "C2_BLOCKERS_REMAINING":live_pkg.get("C2_BLOCKERS_REMAINING"),
  "factory_classes":c8.get("classes") or {},
  "factory_fabric":{"status":factory.get("status") or factory.get("FACTORY_FABRIC") or ("PASS" if fabric_pass else "UNKNOWN"),
                    "source":str(FACTORY_RUNTIME_LATEST),"ok":fabric_pass,
                    "resource_factory":{"selected_resource":resource.get("selected_resource"),
                                        "dispatch_allowed":resource.get("dispatch_allowed"),
                                        "status":resource.get("status") or "UNKNOWN"},
                    "model_factory":{"selected_resource":model.get("selected_resource"),
                                     "dispatch_allowed":model.get("dispatch_allowed"),
                                     "gpu_session_started":model.get("gpu_session_started"),
                                     "paid_resource_created":model.get("paid_resource_created")}},
  "deployment":{"transaction_id":deploy.get("transaction_id"),"canonical_head":deploy.get("canonical_head") or CANONICAL_HEAD,
                "pid":deploy.get("pid"),"manifest_sha256":deploy.get("manifest_sha256"),
                "deployed_at":deploy.get("deployed_at"),"app_root":deploy.get("app_root")},
  "self_heal":self_heal_projection(load(CONTINUITY_STATUS,{})),
  "CONTROL_PLANE_ACTIVATED":False,"SAFE8_LIVE_ACTIVATED":0,"second_task_ledger":False,
  "second_message_bus":False,"second_mcp":False,"NO_SYNTHETIC_ACK":True,"NO_FAKE_PRESENCE":True,
  "hanging_work":tasks.get("hanging_work"),
  "MCP_SINGLETON":"PASS","TRANSPORT_SINGLE_AUTHORITY":"PASS","COGNITIVE_WAL_SINGLETON":"PASS"}
def overview():
 with ThreadPoolExecutor(max_workers=8) as pool:
  services_f=pool.submit(lambda:[service("C5",8766,C5+"/health",timeout=2.5),service("UniversalMCP",8788,MCP+"/health"),
   tcp_service("9Router",20128),tcp_service("NATS",4222)])
  task_f=pool.submit(tasks_state)
  goals_f=pool.submit(goals_state)
  models_f=pool.submit(model_state)
  factory_f=pool.submit(factory_state)
  resource_f=pool.submit(resource_state)
  council_f=pool.submit(council_state)
  cognitive_f=pool.submit(cognitive_state)
  authority_f=pool.submit(change_authority_state)
  worker_f=pool.submit(MESSAGE_WORKER.status)
  laws_f=pool.submit(operator_laws_projection,REPO)
  services=services_f.result(); task=task_f.result(); goals=goals_f.result(); models=models_f.result()
  factory=factory_f.result(); resources=resource_f.result(); council=council_f.result()
  cognition=cognitive_f.result(); authority=authority_f.result(); worker=worker_f.result()
  laws=laws_f.result()
 degraded=[x["name"] for x in services if x["state"]!="ONLINE"]
 c5=next((x for x in services if x.get("name")=="C5"),{}) or {}
 mcp=next((x for x in services if x.get("name")=="UniversalMCP"),{}) or {}
 heads=head_truth(canonical_head=CANONICAL_HEAD,deployed_head=os.getenv("RAIOS_DEPLOYED_HEAD"),
                  runtime_head=os.getenv("RAIOS_RUNTIME_HEAD") or (c5.get("detail") or {}).get("head"),
                  actor_observed_head=os.getenv("RAIOS_ACTOR_OBSERVED_HEAD") or (mcp.get("detail") or {}).get("head"),
                  remote_head=os.getenv("RAIOS_REMOTE_HEAD","UNKNOWN"))
 continuity=load(CONTINUITY_STATUS,{})
 health_view=runtime_health_view(services=services,worker=worker,models=models,continuity=continuity,
  ollama_listening=models.get("local_ollama_state")=="ONLINE" if models.get("local_ollama_state") in {"ONLINE","UNAVAILABLE"} else None,
  command_center_state="ONLINE")
 blockers=operational_blockers(models=models,heads=heads,change_authority=authority,worker=worker,recorded_qwen=True)
 return {"generated_at":utc(),"canonical_head":CANONICAL_HEAD,"remote_head":os.getenv("RAIOS_REMOTE_HEAD","UNKNOWN"),
  "head_source":"env_or_cached_ne_subprocess","heads":heads,
  "services":services,"tasks":task,"goals":goals,"models":models,"factories":factory,"resources":resources,"council":council,"cognitive":cognition,
  "change_authority":authority,"runtime_health":health_view,"operational_blockers":blockers,
  "operator_laws":laws,"qwen_registry_blocker":QWEN_REGISTRY_BLOCKER,
  "maintenance":{"health":"HEALTHY" if not degraded else "ATTENTION","degraded":degraded,"auto_refresh":True,
   "auto_canonical_mutation":False,"self_update_policy":"LOCAL_RUNTIME_FROM_FAST_FORWARD_CANONICAL_ONLY_WITH_C1_CONFIRMATION"}}

class ChatIn(BaseModel):text:str=Field(min_length=1,max_length=200000); conversation_id:str|None=None
class SearchIn(BaseModel):
 query:str=Field(min_length=2,max_length=4000)
 public_query:str|None=Field(default=None,max_length=400)
 allow_public:bool=False
 deep:bool=True
 limit:int=Field(default=20,ge=1,le=50)
class CommandIn(BaseModel):text:str=Field(min_length=1,max_length=50000);targets:list[str];task_id:str|None=None;intent:str|None=None
class DirectChatIn(BaseModel):text:str=Field(min_length=1,max_length=50000)
class DirectReplyIn(BaseModel):text:str=Field(min_length=1,max_length=50000);actor_proof:dict[str,Any]=Field(default_factory=dict)
class AvailabilityIn(BaseModel):
 seat:str=Field(min_length=2,max_length=4)
 state:str=Field(pattern="^(AVAILABLE|BUSY|OFFLINE|UNKNOWN)$")
 reason:str=Field(default="",max_length=5000)
class SelfCheckInIn(BaseModel):
 seat:str=Field(pattern="^C(?:[1-9]|1[0-2])$")
 auth:dict[str,Any]
 idempotency_key:str=Field(min_length=1,max_length=200)
class ModelRouteIn(BaseModel):
 capability:str=Field(min_length=2,max_length=100)
 privacy:str=Field(default="local_preferred",max_length=40)
 latency:str=Field(default="normal",max_length=40)
 cost:str=Field(default="bounded",max_length=40)
 tools_required:bool=False
 context_tokens:int=Field(default=4096,ge=256,le=1000000)
class DispatchIn(BaseModel):task_id:str=Field(min_length=1,max_length=200);target:str=Field(min_length=2,max_length=20)
class TaskClaimIn(BaseModel):
 task_id:str=Field(min_length=1,max_length=200)
 actor:str=Field(min_length=2,max_length=20)
 actor_proof:dict[str,Any]=Field(default_factory=dict)
class TaskAcceptIn(BaseModel):
 task_id:str=Field(min_length=1,max_length=200)
 actor:str=Field(min_length=2,max_length=20)
 dispatch_id:str=Field(min_length=4,max_length=200)
 actor_proof:dict[str,Any]=Field(default_factory=dict)
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
 actor_proof:dict[str,Any]=Field(default_factory=dict)
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
 actor_proof:dict[str,Any]=Field(default_factory=dict)

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
def bootstrap():
 return {"csrf":CSRF,"ui":"CANONICAL_COMMAND_CENTER","direct_mutation":False,
  "boot_mode":"FAST_PLANE_THEN_OVERVIEW","canonical_head":CANONICAL_HEAD,
  "health":health(),"plane":live_plane(),"mcp":mcp_bind(),"council_lite":council_lite(),"overview":None}
@app.get("/api/plane")
def api_plane():return live_plane()
@app.get("/api/mcp")
def api_mcp():return mcp_bind()
@app.get("/api/csrf")
def api_csrf():return {"csrf":CSRF,"service":"RAIOS_COMMAND_CENTER","direct_mutation":False}
@app.get("/api/overview")
def api_overview():return overview()
@app.get("/api/cognitive")
def api_cognitive():return cognitive_state()
@app.get("/api/engines")
def api_engines():return engine_state()
@app.post("/api/search")
def api_search(req:SearchIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 return SEARCH_CORTEX.search(req.query,public_allowed=req.allow_public,public_query=req.public_query,
  official_allowed=True,limit=req.limit,deep=req.deep,trace=True)
@app.get("/api/tasks")
def api_tasks():return tasks_state()
@app.get("/api/goals")
def api_goals():return goals_state()
@app.get("/api/council")
def api_council():return council_state()
@app.get("/api/council-state")
def api_council_state():
 activity=CLIENT_ACTIVITY.snapshot(include_member_state=False)
 body=build_council_member_state(REPO,ACTOR_ROUTES,activity.get("clients",[]),persist=False)
 body["operational_blockers"]=operational_blockers(members=body.get("members") or [],recorded_qwen=True)
 body["presence_dimensions"]=["identity_bound","session_current","consumer_current","lease_current",
  "heartbeat_fresh","auto_routable","delivery_reachable","actor_ack_capable"]
 body["collapsed_online"]=False
 return body
@app.get("/api/actor-routes")
def api_actor_routes():
 now=time.monotonic()
 cached=_ACTOR_ROUTES_CACHE.get("body")
 if isinstance(cached, dict) and (now-float(_ACTOR_ROUTES_CACHE.get("at") or 0)) < 2.0:
  body=dict(cached); body["freshness"]="CACHED"; body["stale"]=True; return body
 try:
  snap=ACTOR_ROUTES.snapshot(process_discovery=False, max_challenges=32)
  snap["freshness"]="LIVE"; snap["stale"]=False
  snap["http_projection_skips_process_discovery"]=True
  snap["historical_scan"]=False
  _ACTOR_ROUTES_CACHE["at"]=now; _ACTOR_ROUTES_CACHE["body"]=snap
  return snap
 except Exception as exc:
  if isinstance(cached, dict):
   body=dict(cached); body["freshness"]="STALE"; body["stale"]=True
   body["error"]=type(exc).__name__; return body
  return {"schema":"raios.actor-route-registry.v2","stale":True,"freshness":"STALE",
          "error":type(exc).__name__,"seats":[],"auto_routable":[],"historical_scan":False}
@app.post("/api/council/self-check-in")
def api_council_self_check_in(req:SelfCheckInIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:
  return COUNCIL_OPS.check_in(seat=req.seat,auth=req.auth,idem=req.idempotency_key)
 except Exception as exc:
  raise HTTPException(409,f"{type(exc).__name__}:{exc}")
@app.get("/api/council-board")
def api_council_board():return COUNCIL_BOARD.snapshot()
@app.post("/api/task-dispatch")
def api_task_dispatch(req:DispatchIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:return COUNCIL_BOARD.dispatch(req.task_id,req.target,MESSAGE_WORKER)
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.get("/api/tasks/claimable/{actor}")
def api_claimable_tasks(actor:str):
 try:return COUNCIL_BOARD.claimable_tasks(actor)
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.post("/api/task-claim")
def api_task_claim(req:TaskClaimIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:return COUNCIL_BOARD.claim_task(req.task_id,req.actor,req.actor_proof)
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.post("/api/task-accept")
def api_task_accept(req:TaskAcceptIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:return COUNCIL_BOARD.accept_task(req.task_id,req.actor,req.dispatch_id,req.actor_proof)
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.post("/api/task-checkpoint")
def api_task_checkpoint(req:TaskCheckpointIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:return COUNCIL_BOARD.submit_checkpoint(req.task_id,req.actor,req.phase,req.summary,
  req.completed_steps,req.changed_files,req.validation,req.evidence_refs,
  req.next_step,req.blocker,req.actor_proof)
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
  req.next_step,req.blocker,req.actor_proof)
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.get("/api/models")
def api_models():return model_state()
@app.get("/api/model-router")
def api_model_router():return MODEL_ROUTER.registry()
@app.post("/api/model-router/route")
def api_model_route(req:ModelRouteIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 return MODEL_ROUTER.route(RouteRequest(capability=req.capability,privacy=req.privacy,
  latency=req.latency,cost=req.cost,tools_required=req.tools_required,context_tokens=req.context_tokens))
@app.get("/api/client-activity")
def api_client_activity(lite:bool=Query(False)):
 return CLIENT_ACTIVITY.snapshot(include_member_state=not lite, lite=lite)
@app.post("/api/availability")
def api_availability(req:AvailabilityIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 try:
  _,actor,_=c1_gateway()
  auth={"seat_id":"C1","SIGNATURE_VALID":True,"ISSUER_IDENTIFIED":True,
        "ISSUER_TRUSTED":True,"PRINCIPAL_BOUND":True,
        "AUTHORITY_SOURCE_PROVENANCE":{"source":"C1_MCP_GATEWAY_AUTHENTICATED",
        "actor_id":getattr(actor,"actor_id","C1"),"command_center":True}}
  return COUNCIL_OPS.attest_availability(seat=req.seat,state=req.state,attested_by="C1",
   auth=auth,idem="availability-"+uuid.uuid4().hex,reason=req.reason)
 except Exception as exc:
  raise HTTPException(409,f"{type(exc).__name__}:{exc}")
@app.get("/api/notifications/{message_id}")
def api_notification_status(message_id:str):return CLIENT_ACTIVITY.notification_status(message_id)
@app.get("/api/communication-trace/{message_id}")
def api_communication_trace(message_id:str):return CLIENT_ACTIVITY.communication_trace(message_id)
@app.get("/api/change-authority")
def api_change_authority():return change_authority_state()
@app.get("/api/runtime-health")
def api_runtime_health():
 services=[service("C5",8766,C5+"/health",timeout=4),service("UniversalMCP",8788,MCP+"/health"),
  tcp_service("9Router",20128),tcp_service("NATS",4222)]
 models=model_state(); local=models.get("local_ollama_state")
 listening=True if local=="ONLINE" else (False if local=="UNAVAILABLE" else None)
 return runtime_health_view(services=services,worker=MESSAGE_WORKER.status(),models=models,
  continuity=load(CONTINUITY_STATUS,{}),ollama_listening=listening,command_center_state="ONLINE")
@app.get("/api/operational-blockers")
def api_operational_blockers():
 return operational_blockers(models=model_state(),heads=head_truth(canonical_head=CANONICAL_HEAD),
  change_authority=change_authority_state(),worker=MESSAGE_WORKER.status(),recorded_qwen=True)
@app.get("/api/attention")
def api_attention():
 fabric=COUNCIL_BOARD.attention_snapshot()
 doc=load(REPO/".ai-os/state/TASKS.json",{"tasks":[]})
 ops=operational_attention(tasks=doc.get("tasks") or [])
 return {**fabric,"operational":ops,"operational_ne_fabric_attention":True}
@app.get("/api/attention/{message_id}")
def api_attention_message(message_id:str):return COUNCIL_BOARD.attention_snapshot(message_id)
@app.get("/api/receipts")
def api_receipts():return receipt_state()
@app.get("/api/message-worker")
def api_message_worker():return MESSAGE_WORKER.status()
@app.get("/api/factories")
def api_factories():return factory_state()
@app.get("/api/factory-estate")
def api_factory_estate():
 estate=factory_estate_projection(REPO,live_runtime=load(FACTORY_RUNTIME_LATEST,{}) or None)
 c8=consume_c8_wave06(REPO)
 estate["c8_wave06"]=c8
 estate["estate_total"]=c8["FACTORY_COMPONENTS_TOTAL"]
 estate["estate_reachable"]=c8["RUNTIME_REACHABLE"]
 estate["estate_active"]=c8["ACTIVE"]
 estate["estate_executing"]=c8["EXECUTING"]
 estate["estate_healthy"]=c8["HEALTHY"]
 estate["CONTROL_PLANE_ACTIVATED"]=False
 estate["SAFE8_LIVE_ACTIVATED"]=0
 estate["rediscovered"]=False
 return estate
@app.get("/api/copy-estate")
def api_copy_estate():
 return copy_estate_projection(REPO)
@app.get("/api/live-board")
def api_live_board():return live_board()
@app.get("/api/c8-estate")
def api_c8_estate():return consume_c8_wave06(REPO)
@app.get("/api/safe8-decision")
def api_safe8_decision():return safe8_identity_decision()
@app.get("/api/system-topology")
def api_system_topology():
 auth=change_authority_state()
 plane=live_plane()
 return system_topology_projection(plane=plane,worker=MESSAGE_WORKER.status(),
  continuity=load(CONTINUITY_STATUS,{}),ollama_listening=tcp(11434),heads=auth.get("heads"),
  canonical_head=CANONICAL_HEAD,canonical_branch=auth.get("canonical_branch") or "UNKNOWN",
  deployment=load(RUNTIME/"deployment.json",{}),
  current_state=load(REPO/".ai-os/state/CURRENT-STATE.json",{}),
  repo=REPO)
@app.get("/api/fabric")
def api_fabric():return fabric_projection(MESSAGE_WORKER.status(),None)
@app.get("/api/self-heal")
def api_self_heal():return self_heal_projection(load(CONTINUITY_STATUS,{}))
@app.get("/api/capability-routing")
def api_capability_routing():return capability_routing_projection(REPO)
@app.get("/api/resource-admission")
def api_resource_admission():return resource_admission_projection(REPO)
@app.get("/api/providers")
def api_providers():return providers_projection(REPO)
@app.get("/api/knowledge-islands")
def api_knowledge_islands():return knowledge_islands_projection(REPO)
@app.get("/api/reachability")
def api_reachability():return reachability_projection()
@app.get("/api/storage-classes")
def api_storage_classes():return storage_class_projection()
@app.get("/api/incidents")
def api_incidents():
 doc=load_tasks_cached()
 return incidents_projection(attention=operational_attention(tasks=doc.get("tasks") or []),
  worker=MESSAGE_WORKER.status())
@app.get("/api/resources")
def api_resources():return resource_state()
@app.post("/api/chat")
def chat(req:ChatIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 started=time.monotonic(); request_id=str(uuid.uuid4())
 code,body=http_json(C5+"/v1/chat","POST",{"text":req.text,"language":"auto","conversation_id":req.conversation_id},130)
 latency_ms=int((time.monotonic()-started)*1000)
 if code!=200:
  raise HTTPException(502,{"upstream":code,"detail":body,"gated":True,"fabricated":False,
    "request_id":request_id,"route":"C5_/v1/chat","latency_ms":latency_ms,"execution_status":"C5_FAIL"})
 return {"ok":True,"request_id":request_id,"route":"C5_/v1/chat","provider":"C5",
  "latency_ms":latency_ms,"execution_status":"C5_OK","fabricated":False,**body}
@app.post("/api/command")
def command(req:CommandIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 rejected_runtime=[str(t).upper() for t in req.targets if str(t).upper() in RAIOS_NOT_COUNCIL_SEATS]
 if rejected_runtime:
  raise HTTPException(400,{"error":"RAIOS_NOT_A_COUNCIL_SEAT","rejected":rejected_runtime,
   "use":"/api/chat","hint_en":"RAIOS/C5 is the canonical runtime. Use /api/chat, not Command Fabric seats.",
   "hint_ar":"RAIOS/C5 زمن تشغيل قانوني. استخدم /api/chat وليس مقعد Fabric."})
 snap=ACTOR_ROUTES.snapshot()
 resolution=ACTOR_ROUTES.resolve(req.targets)
 targets=resolution["targets"]
 if resolution["rejected"]:
  raise HTTPException(400,{"error":"TARGET_UNKNOWN","targets":resolution["rejected"]})
 want_all=any(str(x).upper() in {"ALL","ALL_AVAILABLE"} for x in req.targets)
 unreachable=[]
 delivered=set(str(x).upper() for x in targets)
 requested={str(t).upper() for t in req.targets}
 for row in snap.get("seats") or []:
  seat=str(row.get("seat") or "").upper()
  if not seat or seat in delivered or row.get("auto_routable") is True:
   continue
  if want_all or seat in requested:
   reason=("SIGNED_OUT" if str(row.get("presence_state") or "").upper() in {"ABSENT","OFFLINE"}
           else "NOT_LIVE_BOUND")
   unreachable.append({"seat":seat,"reason":reason,"discovery_state":row.get("discovery_state"),
                       "present":row.get("present") is True,"auto_routable":False})
 if not targets:
  lite=council_lite()
  raise HTTPException(409,{"error":"NO_LIVE_BOUND_TARGETS","auto_routable":resolution["auto_routable_snapshot"],
   "registered_count":lite["registered_count"],"active_workers":lite["active_workers"],
   "unreachable":unreachable,
   "select_explicit":["C2","C8"],
   "hint_ar":"ALL يرسل فقط للمقاعد المربوطة الحية. لا يوجد مقعد حي الآن. اختر C2 أو C8 صراحة.",
   "hint_en":"ALL routes only to live-bound seats. None are live-bound. Select C2 or C8 explicitly."})
 notice_pack=command_intent_envelope(req.text,req.intent)
 if not notice_pack.get("ok"):
  raise HTTPException(400,{"error":notice_pack.get("error"),"allowed":sorted(COMMAND_INTENTS),
   "hint_en":"UI intent is a prefix only. Persisted kind remains COMMAND. No new message type."})
 notice=notice_pack["notice"]
 try:msg=MESSAGE_WORKER.enqueue("C1@COMMAND_CENTER",targets,notice,req.task_id,
  routing_modes=resolution["routing_modes"])
 except ValueError as exc:raise HTTPException(400,str(exc))
 processed=None
 inbox_root=getattr(MESSAGE_WORKER,"inbox",None)
 if inbox_root is not None:
  inbox=Path(inbox_root)/f"{msg['message_id']}.json"
  if inbox.is_file() and hasattr(MESSAGE_WORKER,"process"):
   try:processed=MESSAGE_WORKER.process(inbox)
   except Exception as exc:processed={"status":"PROCESS_ERROR","error":f"{type(exc).__name__}:{exc}"}
 return {"ok":True,"delivered_to":targets,"unreachable":unreachable,
  "lock_owner":"RAIOS_SYSTEM","absent_agent_does_not_pin_files":True,
  "results":[{"targets":targets,"route":"CANONICAL_LOCAL_FABRIC",
  "routing_modes":resolution["routing_modes"],"owner_selected_unbound":resolution["owner_selected_unbound"],
  "status":"SENT_PENDING_DELIVERY_ACK","message_id":msg["message_id"],
  "processed_status":None if processed is None else processed.get("status")}],
  "processed_status":None if processed is None else processed.get("status"),
  "work_authority":False,"notice_only":True,"actor_ack_synthesized":False,
  "interaction":False,"http_200_ne_actor_ack":True,"delivery_ack_ne_actor_ack":True,
  "direct_chat":False,"use_direct":"/api/direct-conversations/{peer}/messages",
  "intent":notice_pack["intent"],"persisted_kind":notice_pack["persisted_kind"],
  "new_persisted_message_type":False,
  "executed":False,"promotion":False,"timestamp":utc()}
@app.get("/api/direct-conversations")
def api_direct_conversations():
 return DIRECT_PLANE.list_peers(system_online=tcp(8766))
@app.get("/api/direct-conversations/{peer}")
def api_direct_thread(peer:str):
 body=DIRECT_PLANE.thread(peer)
 if not body.get("ok"):
  raise HTTPException(400,body)
 return body
@app.post("/api/direct-conversations/{peer}/messages")
def api_direct_send(peer:str,req:DirectChatIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 body=DIRECT_PLANE.send(peer=peer,text=req.text,from_seat="C1")
 if not body.get("ok"):
  code=400 if body.get("error")!="C5_IS_RUNTIME_USE_CHAT" else 400
  raise HTTPException(code,body)
 return body
@app.post("/api/direct-conversations/{peer}/reply")
def api_direct_reply(peer:str,req:DirectReplyIn,x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf)
 body=DIRECT_PLANE.reply(peer=peer,text=req.text,actor_proof=req.actor_proof)
 if not body.get("ok"):
  raise HTTPException(409 if body.get("error")=="PEER_NOT_LIVE_BOUND" else 400,body)
 return body
@app.post("/api/maintenance/diagnose")
def diagnose(x_raios_csrf:str|None=Header(None)):
 require_csrf(x_raios_csrf); data=diagnostic_state(); return {"ok":True,"diagnosis":data,"actions_executed":[],"canonical_mutation":False}
@app.get("/api/laws")
def api_laws():
 return operator_laws_projection(REPO)
@app.get("/api/integration")
def api_integration():
 plane=live_plane()
 worker=MESSAGE_WORKER.status()
 hang=hanging_work_cached()
 laws=operator_laws_projection(REPO)
 c5_http=None
 if tcp(8766):
  c5_http,_=http_json(C5+"/health",timeout=0.8)
 mcp=mcp_bind()
 factory=load(FACTORY_RUNTIME_LATEST,{}) or {}
 live_bound=sum(
  1 for seat in COUNCIL_SEATS
  if seat not in RAIOS_NOT_COUNCIL_SEATS and ACTOR_ROUTES.is_live_bound(seat)
 )
 ecology=(REPO/"src/raios/factory_fabric/model_ecology.py").is_file()
 return integration_mesh_projection(plane=plane,worker=worker,hanging=hang,laws=laws,
  c5_http=c5_http,mcp_http=mcp.get("http"),mcp_live=mcp.get("live") is True,
  factory_runtime=factory if factory else None,live_bound_count=live_bound,
  ecology_source_present=ecology,direct_second_bus=False)
def hanging_work_cached():
 from raios.command_center.board_now import hanging_work
 return hanging_work((load_tasks_cached().get("tasks") or []))
@app.get("/health")
def health():
 worker=MESSAGE_WORKER.status()
 laws=operator_laws_projection(REPO)
 return {"status":"ONLINE","service":"RAIOS_COMMAND_CENTER",
  "canonical_head":CANONICAL_HEAD,"message_worker":worker,
  "workflow_automation":worker.get("workflow_enabled") is True,
  "message_worker_ne_cc_readiness":True,
  "direct_conversation":{"schema":"raios.direct-conversation.v1","second_bus":False,
   "require_interaction":True,"all_broadcast_is_not_direct_chat":True},
  "operator_laws":{"schema":laws.get("schema"),"count":laws.get("count"),"chat_only":False,
   "surface":"/api/laws","ids":laws.get("ids") or []},
  "timestamp":utc()}
