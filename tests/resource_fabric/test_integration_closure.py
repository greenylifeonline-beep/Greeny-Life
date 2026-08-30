from pathlib import Path
from RAIOS.V9.cloud.nomadic.job_ledger import JobLedger
from raios.command_fabric.lease import CommandLeaseAdapter
from raios.resource_fabric.integration import execute_governed_local_control, unified_resource_registry

def decision():
 return {"selected_resource":"LOCAL_AG","dispatch_allowed":True,"decision_id":"D1","request_id":"R1","cost_class":"FREE","failover_order":[]}

def request(**extra):
 out={"workload_class":"CONTROL","request_id":"R1","task_id":"T1","correlation_id":"C1","gpu_required":False,"paid_allowed":False,"persistence_required":False}
 out.update(extra); return out

def authority():
 return {"AUTHORIZED":True,"PRINCIPAL":"C1@AG","AUTHORITY_SOURCE_PROVENANCE":"C1_TEST"}

def test_unified_registry_does_not_drop_model_and_source_surfaces():
 world={"accounts":[{"account_id":"LOCAL_AG"},{"account_id":"KAGGLE_C1"}]}
 proofs={
  "HUGGINGFACE":{"auth_proven":True,"identity":"greenylifeonline","capacity":"UNKNOWN","evidence":["HF_AUTH_WHOAMI_PROVEN"]},
  "GITHUB":{"auth_proven":True,"identity":"greenylifeonline-beep","capacity":"GIT","evidence":["GIT_REMOTE_PUSH_PROVEN"]},
  "OLLAMA_LOCAL":{"auth_proven":True,"identity":"AG","capacity":"11_MODELS"},
 }
 reg=unified_resource_registry(world,proofs)
 assert {x["id"] for x in reg["model_registry_pool"]}>={"HUGGINGFACE","OLLAMA_LOCAL"}
 assert reg["source_pool"][0]["id"]=="GITHUB"
 assert reg["unknown_ne_absent"] is True
 assert reg["catalog_ne_live_capacity"] is True

def test_local_control_executes_existing_adapters_and_is_idempotent(tmp_path):
 ledger=JobLedger(tmp_path/"jobs.jsonl")
 leases=CommandLeaseAdapter(tmp_path/"leases")
 receipts={}
 def load(k): return receipts.get(k)
 def write(r): receipts[r["IDEMPOTENCY_KEY"]]=r; return tmp_path/"receipt.json"
 calls=[]
 def worker(env): calls.append(env); return {"ok":True,"C5_HTTP":200,"NINEROUTER_HTTP":200}
 kwargs=dict(authority=authority(),ledger=ledger,leases=leases,receipt_load=load,receipt_write=write,
             router=lambda:{"gateway":"9ROUTER","RESOURCE_AUTHORITY":False,"health":"ok"},worker=worker)
 first=execute_governed_local_control(decision(),request(),**kwargs)
 second=execute_governed_local_control(decision(),request(),**kwargs)
 assert first["status"]=="COMPLETED" and first["applied"] is True
 assert second["status"]=="ALREADY_APPLIED" and second["applied"] is False
 assert len(calls)==1
 assert first["SECOND_LEDGER"] is False and first["SECOND_LEASE_SYSTEM"] is False
 assert all(x["state"]=="RELEASED" for x in leases._all())

def test_live_path_fails_closed_for_gpu_paid_cloud_and_missing_authority(tmp_path):
 base=dict(ledger=JobLedger(tmp_path/"j"),leases=CommandLeaseAdapter(tmp_path/"l"),
  receipt_load=lambda k:None,receipt_write=lambda r:None,router=lambda:{},worker=lambda e:{"ok":True})
 import pytest
 with pytest.raises(PermissionError,match="C1_AUTHORITY"):
  execute_governed_local_control(decision(),request(),authority={},**base)
 with pytest.raises(PermissionError,match="GPU_OR_PAID"):
  execute_governed_local_control(decision(),request(gpu_required=True),authority=authority(),**base)
 cloud=decision();cloud["selected_resource"]="KAGGLE_C1"
 with pytest.raises(PermissionError,match="ONLY_LOCAL"):
  execute_governed_local_control(cloud,request(),authority=authority(),**base)
