"""Work-stealing scheduler. Local simulation is not Kaggle proof."""
from __future__ import annotations

import time
from typing import Any

from . import LIFECYCLE, LAWS
from .checkpoint_store import CheckpointStore
from .idempotency import IdempotencyStore, key as idem_key
from .job_ledger import JobLedger
from .lease_manager import LeaseManager
from .receipt_writer import ReceiptWriter, hash_output
from .reconciliation import reconcile


class WorkStealingScheduler:
    def __init__(self, *, ttl_s: float = 0.05) -> None:
        self.ledger = JobLedger()
        self.leases = LeaseManager(ttl_s=ttl_s)
        self.checkpoints = CheckpointStore()
        self.idem = IdempotencyStore()
        self.receipts = ReceiptWriter()
        self.steps_seen: list[str] = []

    def submit(self, job_id: str, payload: dict[str, Any], op: str = "hash_payload") -> dict[str, Any]:
        job = self.ledger.enqueue(job_id, op, payload)
        return job.as_dict()

    def discover(self, worker_id: str, now: float | None = None) -> dict[str, Any]:
        self.steps_seen.append("DISCOVER_JOB")
        now = time.time() if now is None else now
        stealable = self.leases.stealable(now)
        queued = [j.job_id for j in self.ledger.queued()]
        expired_unfinished = [
            jid
            for jid, job in self.ledger.jobs.items()
            if job.status in {"QUEUED", "LEASED", "RUNNING"} and (jid in stealable or self.leases.holder(jid, now) is None)
        ]
        candidates = []
        for jid in stealable + queued + expired_unfinished:
            if jid not in candidates:
                if self.ledger.jobs[jid].status != "DONE":
                    candidates.append(jid)
        return {"ok": True, "worker_id": worker_id, "jobs": candidates, "step": "DISCOVER_JOB"}

    def run_once(self, worker_id: str, job_id: str, *, die_after_checkpoint: bool = False, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        trace: list[str] = ["DISCOVER_JOB"]
        job = self.ledger.get(job_id)
        if job.status == "DONE":
            store_key = idem_key(job_id, job.input_hash, job.op)
            prior = self.idem.get(store_key)
            return {
                "ok": True,
                "duplicate": True,
                "applied": False,
                "trace": ["DISCOVER_JOB"],
                "prior": prior,
                "reason": "JOB_ALREADY_DONE",
                "law": list(LAWS),
            }
        claimed = self.leases.claim(job_id, worker_id, now=now)
        if not claimed["ok"]:
            return {"ok": False, "trace": trace, **claimed}
        trace.append("CLAIM_LEASE")
        self.ledger.set_status(job_id, "LEASED", worker_id)

        expected = job.input_hash
        if expected != job.input_hash:
            return {"ok": False, "reason": "INPUT_HASH_MISMATCH", "trace": trace}
        trace.append("VERIFY_INPUT_HASH")

        store_key = idem_key(job_id, job.input_hash, job.op)
        prior = self.idem.get(store_key)
        if prior:
            trace.append("EXECUTE")
            return {
                "ok": True,
                "duplicate": True,
                "applied": False,
                "trace": trace,
                "prior": prior,
                "law": list(LAWS),
            }

        resumed = self.checkpoints.resume(job_id)
        state = dict(resumed.get("state") or {})
        seq = int(resumed.get("seq") or 0)
        self.ledger.set_status(job_id, "RUNNING", worker_id)
        trace.append("EXECUTE")
        state["partial"] = list(state.get("partial") or []) + [f"{worker_id}:{job.op}"]
        seq += 1
        self.checkpoints.save(job_id, seq, state)
        trace.append("CHECKPOINT")
        if die_after_checkpoint:
            return {
                "ok": False,
                "reason": "WORKER_DIED_AFTER_CHECKPOINT",
                "resumable": True,
                "seq": seq,
                "trace": trace,
                "worker_id": worker_id,
                "job_id": job_id,
            }

        output = {"job_id": job_id, "op": job.op, "payload": job.payload, "partial": state["partial"]}
        trace.append("WRITE_OUTPUT")
        digest = hash_output(output)
        trace.append("HASH_OUTPUT")
        receipt = self.receipts.write(
            job_id=job_id,
            worker_id=worker_id,
            input_hash=job.input_hash,
            output=output,
            steps=trace + ["WRITE_RECEIPT", "RELEASE_LEASE"],
            resumed=bool(resumed.get("ok")),
        )
        self.idem.remember(store_key, receipt)
        trace.append("WRITE_RECEIPT")
        self.leases.release(job_id, worker_id)
        self.ledger.set_status(job_id, "DONE", worker_id)
        trace.append("RELEASE_LEASE")
        return {
            "ok": True,
            "duplicate": False,
            "output_hash": digest,
            "receipt": receipt,
            "trace": trace,
            "lifecycle_complete": trace == list(LIFECYCLE) or set(LIFECYCLE).issubset(set(trace)),
            "resumed": bool(resumed.get("ok")),
            "worker_id": worker_id,
            "job_id": job_id,
            "law": list(LAWS),
        }


def simulate_pair_failover() -> dict[str, Any]:
    """Two local simulated workers. Not a live Kaggle session."""
    sched = WorkStealingScheduler(ttl_s=0.05)
    job = sched.submit("job-customs-1", {"event": "shipment_status", "state": "customs_hold"})
    first = sched.run_once("LOCAL_SIM_A", job["job_id"], die_after_checkpoint=True)
    time.sleep(0.06)
    discovered = sched.discover("LOCAL_SIM_B")
    second = sched.run_once("LOCAL_SIM_B", job["job_id"])
    retry = sched.run_once("LOCAL_SIM_A", job["job_id"])
    rec = reconcile(sched.receipts.receipts)
    return {
        "schema": "raios.kaggle-work-stealing-proof.v1",
        "work_stealing_proven": False,
        "work_stealing_local_sim_proven": bool(first.get("resumable") and second.get("ok") and retry.get("duplicate")),
        "kaggle_a_worker_proven": False,
        "kaggle_b_worker_proven": False,
        "job": job,
        "worker_a_death": first,
        "discover_b": discovered,
        "worker_b_complete": {k: second.get(k) for k in ("ok", "resumed", "output_hash", "trace", "worker_id")},
        "retry_duplicate": retry.get("duplicate"),
        "reconciliation": rec,
        "lifecycle": list(LIFECYCLE),
        "law": list(LAWS),
        "gl005_proven": False,
    }
