import importlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi.testclient import TestClient
cc=importlib.import_module("raios.command_center.app")
client=TestClient(cc.app)

def test_professional_bilingual_working_surface_is_local_and_complete():
 text=(cc.HERE/"index.html").read_text(encoding="utf-8")
 for value in ("RAIOS COMMAND","محادثة RAIOS","البحث والتحقق","التعلم والاستيعاب","العمل والأدلة","التشخيص","setInterval","العمل الآن","الهدف والبرنامج"):
  assert value in text
 assert "https://" not in text and "<script src=" not in text
 assert "التنفيذ يحتاج إيصالًا" in text
 assert "Search Cortex" in text
 assert text.count('data-view="work"')>=2
 assert text.count('data-view="council"')>=2
 assert "slice(-6)" not in text
 assert "عرض الدفتر كاملاً" in text
 assert "من متاح ومن غير متاح" in text
 assert "تواصل المجلس عبر RAIOS" in text
 assert 'data-target="ALL"' in text
 assert "targets=new Set(['ALL'])" in text
 assert "محركات التنظيف والدمج والتصنيف" in text
 assert "/api/engines" in text
 assert "/api/mcp" in text

def test_health_and_bootstrap_bind_canonical_head(monkeypatch):
 monkeypatch.setattr(cc,"CANONICAL_HEAD","a"*40)
 monkeypatch.setattr(cc,"git",lambda *a:"a"*40)
 monkeypatch.setattr(cc,"overview",lambda:{"canonical_head":"a"*40,"maintenance":{"health":"HEALTHY"}})
 monkeypatch.setattr(cc.MESSAGE_WORKER,"status",lambda:{"healthy":True,"workflow_enabled":True})
 monkeypatch.setattr(cc,"tcp",lambda port:False)
 monkeypatch.setattr(cc,"mcp_bind",lambda:{"schema":"raios.command-center.mcp-bind.v1","live":False,"ninth_tool":False,"second_gateway":False})
 out=client.get("/api/bootstrap").json()
 assert out["ui"]=="CANONICAL_COMMAND_CENTER" and out["direct_mutation"] is False
 assert out["boot_mode"]=="FAST_PLANE_THEN_OVERVIEW" and out["overview"] is None
 assert "plane" in out and "council_lite" in out and "mcp" in out
 assert len(out["csrf"])>=32
 csrf=client.get("/api/csrf").json()
 assert csrf["csrf"]==cc.CSRF and csrf["service"]=="RAIOS_COMMAND_CENTER"
 assert csrf["direct_mutation"] is False
 health=client.get("/health").json()
 assert health["status"]=="ONLINE" and health["canonical_head"]=="a"*40

def test_mutating_routes_require_same_origin_csrf():
 assert client.post("/api/chat",json={"text":"hi"}).status_code==403
 assert client.post("/api/command",json={"text":"x","targets":["ALL"]}).status_code==403
 assert client.post("/api/maintenance/diagnose").status_code==403

def test_chat_preserves_arabic_and_uses_canonical_c5(monkeypatch):
 monkeypatch.setattr(cc,"http_json",lambda *a,**k:(200,{"response":"نعم، أنا جاهز.","status":"OK"}))
 out=client.post("/api/chat",headers={"X-RAIOS-CSRF":cc.CSRF},json={"text":"هل أنت جاهز؟"})
 assert out.status_code==200 and "جاهز" in out.json()["response"]

def test_command_all_delivers_to_live_bound_and_lists_unreachable(monkeypatch):
 class Routes:
  def snapshot(self):
   return {"auto_routable":["C2","C8"],"seats":[
    {"seat":"C2","auto_routable":True,"presence_state":"PRESENT","discovery_state":"VERIFIED_EXECUTION_READY","present":True},
    {"seat":"C8","auto_routable":True,"presence_state":"PRESENT","discovery_state":"VERIFIED_EXECUTION_READY","present":True},
    {"seat":"C6","auto_routable":False,"presence_state":"ABSENT","discovery_state":"UNKNOWN","present":False},
    {"seat":"C3","auto_routable":False,"presence_state":"PRESENT","discovery_state":"DISCOVERED_LIVE_UNVERIFIED","present":True},
   ]}
  def resolve(self,requested):
   return {"targets":["C2","C8"],"routing_modes":{"C2":"AUTO_LIVE_BOUND_CONSUMER","C8":"AUTO_LIVE_BOUND_CONSUMER"},
           "owner_selected_unbound":[],"rejected":[],"auto_routable_snapshot":["C2","C8"]}
 class Worker:
  def enqueue(self,*a,**k):
   return {"message_id":"MSG-ALL-1"}
 monkeypatch.setattr(cc,"ACTOR_ROUTES",Routes())
 monkeypatch.setattr(cc,"MESSAGE_WORKER",Worker())
 out=client.post("/api/command",headers={"X-RAIOS-CSRF":cc.CSRF},json={"text":"cooperate","targets":["ALL"]})
 body=out.json()
 assert out.status_code==200
 assert body["delivered_to"]==["C2","C8"]
 seats={x["seat"]:x["reason"] for x in body["unreachable"]}
 assert seats["C6"]=="SIGNED_OUT" and seats["C3"]=="NOT_LIVE_BOUND"
 assert "C2" not in seats and "C8" not in seats
 assert body["lock_owner"]=="RAIOS_SYSTEM"
 assert body["absent_agent_does_not_pin_files"] is True
 assert body["executed"] is False

def test_command_rejects_unseated_target_without_delivery(monkeypatch):
 called=[]
 monkeypatch.setattr(cc,"c1_gateway",lambda:called.append(True))
 out=client.post("/api/command",headers={"X-RAIOS-CSRF":cc.CSRF},json={"text":"test","targets":["C13"]})
 assert out.status_code==400 and not called

def test_availability_endpoint_is_coordination_only_and_c1_authenticated(monkeypatch):
 class Actor: actor_id="C1"
 monkeypatch.setattr(cc,"c1_gateway",lambda:(None,Actor(),None))
 called={}
 def attest(**kwargs):
  called.update(kwargs);return {"status":"ATTESTED","seat":kwargs["seat"],
   "availability":kwargs["state"],"execution_authority":False}
 monkeypatch.setattr(cc.COUNCIL_OPS,"attest_availability",attest)
 out=client.post("/api/availability",headers={"X-RAIOS-CSRF":cc.CSRF},
  json={"seat":"C2","state":"AVAILABLE","reason":"C1 confirms C2 available"})
 assert out.status_code==200 and out.json()["availability"]=="AVAILABLE"
 assert called["attested_by"]=="C1" and called["seat"]=="C2"


def test_self_check_in_rebind_delegates_identity_proof_to_council_ops(monkeypatch):
 seen={}
 def check_in(**kwargs):
  seen.update(kwargs)
  return {"status":"PRESENT","seat":kwargs["seat"],"actor_binding":{"synthetic":False}}
 monkeypatch.setattr(cc.COUNCIL_OPS,"check_in",check_in)
 proof={"seat_id":"C6","SIGNATURE_VALID":True,"ISSUER_IDENTIFIED":True,"ISSUER_TRUSTED":True,
  "PRINCIPAL_BOUND":True,"AUTHORITY_SOURCE_PROVENANCE":"CLIENT_SELF_PROOF",
  "actor_id":"C6-REAL","origin_instance":"CLIENT","device_id":"DEVICE","session_id":"SESSION"}
 out=client.post("/api/council/self-check-in",headers={"X-RAIOS-CSRF":cc.CSRF},
  json={"seat":"C6","auth":proof,"idempotency_key":"rebind-1"})
 assert out.status_code==200
 assert seen=={"seat":"C6","auth":proof,"idem":"rebind-1"}
 assert out.json()["actor_binding"]["synthetic"] is False


def test_self_check_in_rebind_rejects_incomplete_identity_proof():
 out=client.post("/api/council/self-check-in",headers={"X-RAIOS-CSRF":cc.CSRF},
  json={"seat":"C6","auth":{"seat_id":"C6"},"idempotency_key":"rebind-bad"})
 assert out.status_code==409
 assert "AUTHENTICATED_SEAT_PROOF_REQUIRED" in out.json()["detail"]


def test_successful_non_json_service_probe_is_online_without_body_exposure(monkeypatch):
 class Response:
  status=200
  headers={"Content-Type":"text/html; charset=utf-8"}
  def read(self):return b"<html>dashboard-secret</html>"
  def __enter__(self):return self
  def __exit__(self,*args):return False
 monkeypatch.setattr(cc.urllib.request,"urlopen",lambda *a,**k:Response())
 code,body=cc.http_json("http://127.0.0.1:20128/dashboard")
 assert code==200 and body=={"response_type":"NON_JSON","content_type":"text/html"}
 assert "dashboard-secret" not in str(body)
 monkeypatch.setattr(cc,"tcp",lambda port:True)
 monkeypatch.setattr(cc,"http_json",lambda *a,**k:(code,body))
 assert cc.service("9Router",20128,"http://127.0.0.1:20128/dashboard")["state"]=="ONLINE"


def test_9router_plane_is_tcp_only_and_does_not_fetch_dashboard(monkeypatch):
 called=[]
 monkeypatch.setattr(cc,"tcp",lambda port: called.append(port) or True)
 monkeypatch.setattr(cc,"http_json",lambda *a,**k:(_ for _ in ()).throw(AssertionError("9Router must not HTTP-probe dashboard")))
 row=cc.tcp_service("9Router",20128)
 assert row["state"]=="ONLINE" and row["probe"]=="TCP_ONLY" and called==[20128]


def test_live_plane_mcp_uses_http_health_not_tcp_only(monkeypatch):
 probed=[]
 def fake_service(name,port,url=None,**_k):
  probed.append((name,port,url))
  return {"name":name,"port":port,"state":"ONLINE","http":200}
 monkeypatch.setattr(cc,"service",fake_service)
 monkeypatch.setattr(cc,"tcp_service",lambda name,port:{"name":name,"port":port,"state":"ONLINE","probe":"TCP_ONLY"})
 plane=cc.live_plane()
 names=[x["name"] for x in plane["services"]]
 assert names==["C5","UniversalMCP","9Router","NATS"]
 assert ("UniversalMCP",8788,"http://127.0.0.1:8788/health") in probed
 mcp=next(x for x in plane["services"] if x["name"]=="UniversalMCP")
 assert mcp.get("probe")!="TCP_ONLY"
 assert next(x for x in plane["services"] if x["name"]=="9Router")["probe"]=="TCP_ONLY"

def test_mcp_bind_surface_forbids_ninth_tool_and_second_gateway(monkeypatch):
 monkeypatch.setattr(cc,"http_json",lambda *a,**k:(200,{"ok":True,"tool_count":8,"tools":["get_head","read_board","read_inbox","read_receipt","get_diff","post_opinion","send_packet","ack_packet"],"ninth_tool":False,"second_gateway":False,"head":"abc","head_source":"env","service":"raios-universal-mcp","transport":"streamable-http","law":"MCP_GATEWAY_NE_TRUTH_AUTHORITY","channel":"streamable-http-session","get_sse":True,"stateless":False}))
 monkeypatch.setattr(cc,"load",lambda *a,**k:{"runtimes":[{"id":"c5-runtime","adapter":True,"role":"live brain","transport":"HTTP :8766","health":"ONLINE"}]})
 out=cc.mcp_bind()
 assert out["schema"]=="raios.command-center.mcp-bind.v1"
 assert out["live"] is True and out["ninth_tool"] is False and out["second_gateway"] is False
 assert out["census_port"]==8788 and out["endpoint"].endswith("/mcp")
 assert out["v1_execution_intent"]=="DENIED"
 assert out["client_gateway_ne_seat_bus"] is True
 assert out["c2_grant_invented"] is False
 assert out["get_sse"] is True and out["client_channel"]=="streamable-http-session"
 assert "c5-runtime" in {x["id"] for x in out["adapters_behind_gateway"]}

def test_maintenance_is_diagnostic_not_autonomous(monkeypatch):
 monkeypatch.setattr(cc,"diagnostic_state",lambda:{"health":"HEALTHY","score":100,"root_causes":[],"actions_executed":[],"canonical_mutation":False})
 out=client.post("/api/maintenance/diagnose",headers={"X-RAIOS-CSRF":cc.CSRF}).json()
 assert out["actions_executed"]==[] and out["canonical_mutation"] is False
 assert out["diagnosis"]["score"]==100


def test_search_endpoint_uses_shared_cortex_and_requires_csrf(monkeypatch):
 assert client.post("/api/search",json={"query":"current status"}).status_code==403
 monkeypatch.setattr(cc.SEARCH_CORTEX,"search",lambda *a,**k:{"schema":"raios.search-cortex.result.v2","count":1,"results":[{"evidence_id":"E001"}],"verification":{"status":"PASS"}})
 out=client.post("/api/search",headers={"X-RAIOS-CSRF":cc.CSRF},json={"query":"current status"})
 assert out.status_code==200
 assert out.json()["results"][0]["evidence_id"]=="E001"

def test_deployer_writes_launcher_as_real_lines():
 script=(Path(__file__).parents[2]/"scripts/runtime/Deploy-RAIOS-Command-Center.ps1").read_text(encoding="utf-8")
 assert "[IO.File]::WriteAllText" in script
 assert '$launcher=@"' in script
 assert 'explorer.exe" "http://127.0.0.1:' in script
 assert "C1AuthorizeWorkingTree" in script


def test_council_identity_is_not_conflated_with_live_presence(tmp_path,monkeypatch):
 root=tmp_path/"root";seatmap=root/".ai-os/mcp/SEAT-MAP.json"
 seatmap.parent.mkdir(parents=True)
 seatmap.write_text(json.dumps({"seats":{
  "C3":{"name_ar":"ChatGPT","actor_role":"CONSULTANT_PEER","mail":True},
  "C5":{"name_ar":"RAIOS","actor_role":"RAIOS_LIVE_BRAIN","mail":True}}}),encoding="utf-8")
 monkeypatch.setattr(cc,"MCP_ROOT",root)
 monkeypatch.setattr(cc.CLIENT_ACTIVITY,"snapshot",lambda **k:{
  "schema":"raios.client-activity.v4",
  "clients":[
   {"seat":"C3","actor_role":"CONSULTANT_PEER","presence":"PRESENT","present":True,
    "availability":"AVAILABLE","execution_ready":True,"work_phase":"WAITING_FOR_ASSIGNMENT",
    "reason":"SIGNED_PRESENT_IDLE_AND_ELIGIBLE","current_tasks":[]},
   {"seat":"C5","actor_role":"RAIOS_LIVE_BRAIN","presence":"AWAY","present":False,
    "availability":"UNKNOWN","execution_ready":False,"work_phase":"SIGN_IN_REQUIRED",
    "reason":"NO_CURRENT_SIGNED_BOUND_CONSUMER_PROOF","current_tasks":[]}]})
 out=cc.council_state();rows={x["id"]:x for x in out["seats"]}
 assert out["identity_total"]==2 and out["present_total"]==1
 assert out["available_total"]==1 and out["execution_ready_total"]==1
 assert out["canonical_coordination_source"]=="/api/client-activity"
 assert rows["C3"]["presence_current"] is True
 assert rows["C5"]["identity_registered"] is True and rows["C5"]["availability"]=="UNKNOWN"


def test_health_uses_cached_head_without_spawning_git(monkeypatch):
 monkeypatch.setattr(cc,"CANONICAL_HEAD","b"*40)
 monkeypatch.setattr(cc.MESSAGE_WORKER,"status",lambda:{"healthy":True,"workflow_enabled":True})
 monkeypatch.setattr(cc,"git",lambda *a:(_ for _ in ()).throw(AssertionError("health must not call git")))
 health=client.get("/health").json()
 assert health["canonical_head"]=="b"*40 and health["status"]=="ONLINE"


def test_command_center_deployer_copies_internal_a2a_receipt_dependency():
 deploy=(cc.HERE.parents[2]/"scripts/runtime/Deploy-RAIOS-Command-Center.ps1").read_text(encoding="utf-8")
 assert "src\\raios\\a2a\\*" in deploy
 assert "$A2APkg" in deploy
 assert "src\\raios\\command_fabric\\*" in deploy
 assert "$FabricPkg" in deploy


def test_command_fabric_package_import_does_not_load_c1c5_pipeline():
 import sys
 text=(cc.HERE.parent/"command_fabric"/"__init__.py").read_text(encoding="utf-8")
 assert "def __getattr__" in text
 assert "from .pipeline import execute, EXISTING_NATS_PROVIDER" not in text.split("def __getattr__",1)[0]
 assert "raios.command_fabric.pipeline" not in sys.modules
 assert "raios.c1c5" not in sys.modules


def test_goals_catalog_is_named_view_over_tasks():
 out=client.get("/api/goals").json()
 assert out["schema"]=="raios.goal-catalog.v1"
 assert out["second_goal_ledger"] is False and out["kernel"] is False
 assert out["active_program_id"]=="RAIOS-CAPABILITY-EVOLUTION-202609-202703"
 ids={g["goal_id"] for g in out["goals"]}
 assert "RAIOS-CAPABILITY-EVOLUTION-202609-202703" in ids
 assert "RAIOS-CANONICAL-CONVERGENCE-001" in ids


def test_overview_exposes_now_slice_and_named_goals(monkeypatch):
 monkeypatch.setattr(cc,"CANONICAL_HEAD","c"*40)
 monkeypatch.setattr(cc,"service",lambda name,port,url=None,**_k:{"name":name,"port":port,"state":"ONLINE","detail":{}})
 monkeypatch.setattr(cc,"tcp_service",lambda name,port:{"name":name,"port":port,"state":"ONLINE","probe":"TCP_ONLY"})
 monkeypatch.setattr(cc,"git",lambda *a:(_ for _ in ()).throw(AssertionError("overview must not call git")))
 monkeypatch.setattr(cc,"model_state",lambda:{"ollama_online":False,"count":0,"models":[]})
 monkeypatch.setattr(cc,"factory_state",lambda:{"fabric_present":True,"live_runtime_claimed":False})
 monkeypatch.setattr(cc,"resource_state",lambda:{})
 monkeypatch.setattr(cc,"council_state",lambda:{"seats":[]})
 monkeypatch.setattr(cc,"cognitive_state",lambda:{"online":False})
 out=cc.overview()
 assert out["canonical_head"]=="c"*40
 assert out["head_source"]=="env_or_cached_ne_subprocess"
 assert out["tasks"]["now_ne_full_ledger"] is True
 assert out["tasks"]["locks_scanned"] is False
 assert isinstance(out["tasks"]["now"],list)
 assert out["tasks"]["recent"]==out["tasks"]["now"][:12]
 assert out["goals"]["schema"]=="raios.goal-catalog.v1"
 assert out["goals"]["kernel"] is False


def test_attention_endpoints_use_existing_council_board(monkeypatch):
 monkeypatch.setattr(cc.COUNCIL_BOARD,"attention_snapshot",lambda message_id=None:{"schema":"raios.command-fabric-attention.v1","message_id":message_id,"states":[]})
 all_rows=client.get("/api/attention")
 one=client.get("/api/attention/MSG-test")
 assert all_rows.status_code==200 and all_rows.json()["schema"]=="raios.command-fabric-attention.v1"
 assert one.status_code==200 and one.json()["message_id"]=="MSG-test"

def test_factory_state_reads_live_runtime_report(tmp_path,monkeypatch):
 runtime=tmp_path/"FACTORY-FABRIC-LATEST.json"
 runtime.write_text(json.dumps({"schema":"raios.factory-fabric.run.v1","generated_at":"2026-09-17T02:00:00+00:00","status":"PASS","factories":{"assimilation_factory":{"factory":"ASSIMILATION_FACTORY","status":"PASS"}},"canonical_repo_mutation":False,"automatic_canonical_promotion":False}),encoding="utf-8")
 monkeypatch.setattr(cc,"FACTORY_RUNTIME_LATEST",runtime,raising=False)
 out=cc.factory_state()
 assert out["live_runtime_claimed"] is True
 assert out["runtime_status"]=="PASS"
 assert out["schema"]=="raios.factory-fabric.run.v1"
 assert out["factories"]["assimilation_factory"]["status"]=="PASS"
 assert out["canonical_repo_mutation"] is False
 assert out["automatic_canonical_promotion"] is False
