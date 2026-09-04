import importlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi.testclient import TestClient
cc=importlib.import_module("raios.command_center.app")
client=TestClient(cc.app)

def test_professional_bilingual_working_surface_is_local_and_complete():
 text=(cc.HERE/"index.html").read_text(encoding="utf-8")
 for value in ("RAIOS COMMAND","محادثة RAIOS","البحث والتحقق","التعلم والاستيعاب","العمل والأدلة","التشخيص","setInterval"):
  assert value in text
 assert "https://" not in text and "<script src=" not in text
 assert "التنفيذ يحتاج إيصالًا" in text
 assert "Search Cortex" in text

def test_health_and_bootstrap_bind_canonical_head(monkeypatch):
 monkeypatch.setattr(cc,"CANONICAL_HEAD","a"*40)
 monkeypatch.setattr(cc,"git",lambda *a:"a"*40)
 monkeypatch.setattr(cc,"overview",lambda:{"canonical_head":"a"*40,"maintenance":{"health":"HEALTHY"}})
 monkeypatch.setattr(cc.MESSAGE_WORKER,"status",lambda:{"healthy":True,"workflow_enabled":True})
 out=client.get("/api/bootstrap").json()
 assert out["ui"]=="CANONICAL_COMMAND_CENTER" and out["direct_mutation"] is False
 assert len(out["csrf"])>=32
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


def test_council_identity_is_not_conflated_with_live_presence(tmp_path,monkeypatch):
 root=tmp_path/"root";seatmap=root/".ai-os/mcp/SEAT-MAP.json"
 seatmap.parent.mkdir(parents=True)
 seatmap.write_text(json.dumps({"seats":{
  "C3":{"name_ar":"ChatGPT","actor_role":"CONSULTANT_PEER","mail":True},
  "C5":{"name_ar":"RAIOS","actor_role":"RAIOS_LIVE_BRAIN","mail":True}}}),encoding="utf-8")
 monkeypatch.setattr(cc,"MCP_ROOT",root)
 monkeypatch.setattr(cc.CLIENT_ACTIVITY,"snapshot",lambda:{
  "schema":"raios.client-activity.v3",
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
