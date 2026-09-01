import importlib
from pathlib import Path
from fastapi.testclient import TestClient
cc=importlib.import_module("raios.command_center.app")
client=TestClient(cc.app)

def test_professional_bilingual_working_surface_is_local_and_complete():
 text=(cc.HERE/"index.html").read_text(encoding="utf-8")
 for value in ("RAIOS COMMAND","محادثة RAIOS","المجلس والعملاء","المصانع والنماذج","الصيانة والتحديث","setInterval"):
  assert value in text
 assert "https://" not in text and "<script src=" not in text
 assert "Auto canonical mutation</span><b class=\"badge bad\">OFF" in text

def test_health_and_bootstrap_bind_canonical_head(monkeypatch):
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
 monkeypatch.setattr(cc,"overview",lambda:{"maintenance":{"health":"HEALTHY","auto_canonical_mutation":False}})
 out=client.post("/api/maintenance/diagnose",headers={"X-RAIOS-CSRF":cc.CSRF}).json()
 assert out["actions_executed"]==[] and out["canonical_mutation"] is False

def test_deployer_writes_launcher_as_real_lines():
 script=(Path(__file__).parents[2]/"scripts/runtime/Deploy-RAIOS-Command-Center.ps1").read_text(encoding="utf-8")
 assert "[IO.File]::WriteAllText" in script
 assert '$launcher=@"' in script
 assert 'explorer.exe" "http://127.0.0.1:' in script
