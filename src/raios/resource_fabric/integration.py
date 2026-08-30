"""Governed Resource Fabric execution composition.

This module binds existing placement decisions to injected canonical ledger,
lease, router, worker, and receipt adapters.  It deliberately creates none of
those systems and fails closed for paid/GPU/cloud execution without explicit
proof.
"""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from typing import Any, Callable

from .factory import plan_dispatch

def _id(obj: Any) -> str:
    raw=json.dumps(obj,sort_keys=True,ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def unified_resource_registry(world: dict[str,Any], proofs: dict[str,dict[str,Any]]) -> dict[str,Any]:
    """Join compute, model/source registries and storage without inventing capacity."""
    accounts={str(x.get("account_id")):x for x in world.get("accounts") or []}
    def row(pid,kind):
        proof=dict(proofs.get(pid) or {})
        return {"id":pid,"kind":kind,"registered":bool(proof or pid in accounts),
                "auth_proven":proof.get("auth_proven") is True,
                "identity":proof.get("identity","UNOBSERVED"),
                "capacity":proof.get("capacity","UNKNOWN"),
                "dispatch_ready":proof.get("dispatch_ready") is True,
                "evidence":proof.get("evidence",[])}
    return {
      "schema":"raios.unified-resource-registry.v1",
      "compute_pool":[row(x,"COMPUTE") for x in ("LOCAL_AG","KAGGLE_C1","MODAL_01","LIGHTNING_01","ORACLE_01","COLAB_01")],
      "model_registry_pool":[row("HUGGINGFACE","MODEL_REGISTRY"),row("KAGGLE_C1","MODEL_REGISTRY"),row("OLLAMA_LOCAL","MODEL_RUNTIME")],
      "source_pool":[row("GITHUB","SOURCE_RECOVERY")],
      "storage_pool":[row("HUGGINGFACE","MODEL_STORAGE"),row("KAGGLE_C1","DATASET_STORAGE"),row("ORACLE_01","OBJECT_STORAGE"),row("ONEDRIVE","FILE_STORAGE")],
      "unknown_ne_absent":True,"catalog_ne_live_capacity":True,
    }

def execute_governed_local_control(
    decision:dict[str,Any], request:dict[str,Any], *, authority:dict[str,Any],
    ledger:Any, leases:Any, receipt_load:Callable[[str],dict[str,Any]|None],
    receipt_write:Callable[[dict[str,Any]],Any], router:Callable[[],dict[str,Any]],
    worker:Callable[[dict[str,Any]],dict[str,Any]],
) -> dict[str,Any]:
    """Execute the bounded LOCAL_AG/CONTROL path through existing adapters."""
    if not (authority.get("AUTHORIZED") is True and authority.get("PRINCIPAL") and authority.get("AUTHORITY_SOURCE_PROVENANCE")):
        raise PermissionError("C1_AUTHORITY_PROOF_REQUIRED")
    if request.get("workload_class")!="CONTROL" or decision.get("selected_resource")!="LOCAL_AG":
        raise PermissionError("ONLY_LOCAL_CONTROL_LIVE_CLOSED")
    if request.get("gpu_required") or request.get("paid_allowed"):
        raise PermissionError("GPU_OR_PAID_FAIL_CLOSED")
    if not decision.get("dispatch_allowed"):
        raise PermissionError("PLACEMENT_DISPATCH_DENIED")
    plan=plan_dispatch(decision,request,dry_run=True)
    idem=plan["idempotency_key"]
    prior=receipt_load(idem)
    if prior:
        return {"ok":True,"status":"ALREADY_APPLIED","applied":False,"receipt":prior,"RAIOS_IDEMPOTENCY":True}
    scope=f"resource:LOCAL_AG:CONTROL"
    lease=leases.acquire(owner=authority["PRINCIPAL"],scope=scope,task_id=str(request.get("task_id") or request.get("request_id")),
      correlation_id=str(request.get("correlation_id") or request.get("request_id")),capability="resource.control",
      resource_or_target="LOCAL_AG",idempotency_key=idem,provenance_ref=authority["AUTHORITY_SOURCE_PROVENANCE"])
    if not lease.get("ok"): return {"ok":False,"status":"LEASE_CONFLICT","lease":lease}
    job=ledger.enqueue(plan["job"]["job_id"],plan["job"]["op"],{"request":request,"decision":decision})
    try:
        ledger.set_status(job.job_id,"RUNNING","LOCAL_AG")
        route=router()
        result=worker({"request":request,"decision":decision,"route":route})
        status="COMPLETED" if result.get("ok") else "FAILED"
        ledger.set_status(job.job_id,status,"LOCAL_AG")
        receipt={"schema":"raios.resource-dispatch-receipt.v1","IDEMPOTENCY_KEY":idem,
          "task_id":request.get("task_id"),"job_id":job.job_id,"resource":"LOCAL_AG","status":status,
          "route":route,"result":result,"authority":authority["PRINCIPAL"],
          "timestamp":datetime.now(timezone.utc).isoformat(),"GPU_SESSION_STARTED":False,
          "PAID_RESOURCE_CREATED":False,"EXACTLY_ONCE_CLAIMED":False,"RAIOS_IDEMPOTENCY":True}
        path=receipt_write(receipt)
        return {"ok":status=="COMPLETED","status":status,"applied":True,"job":job.as_dict(),
          "lease_id":lease.get("lease_id"),"receipt":receipt,"receipt_path":str(path),
          "NINEROUTER_IS_RESOURCE_AUTHORITY":False,"SECOND_SCHEDULER":False,
          "SECOND_LEDGER":False,"SECOND_LEASE_SYSTEM":False,"SECOND_RECEIPT_SYSTEM":False}
    finally:
        leases.release(str(lease["lease_id"]),owner=authority["PRINCIPAL"])
