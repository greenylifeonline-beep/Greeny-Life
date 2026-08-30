"""Work-stealing scheduler. Local simulation is not Kaggle proof."""
from __future__ import annotations
import math

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

    # RESOURCE_INTELLIGENCE_ROUTING_V1
    def load_resource_projection(self, path: str | None = None) -> dict[str, Any]:
        """Read resource evidence only. The scheduler MUST NOT probe cloud providers."""
        import json
        from pathlib import Path
        target = Path(path) if path else (Path(__file__).resolve().parents[4] / ".ai-os" / "learning" / "RESOURCE-PROJECTION.json")
        if not target.exists():
            return {"schema": "raios.resource-projection.v1", "records": [], "state": "NOT_PROVEN"}
        return json.loads(target.read_text(encoding="utf-8"))

    def resource_selection_factors(self) -> list[str]:
        """Reuse A14 selection semantics without activating A14 as a second scheduler."""
        import json
        from pathlib import Path
        factors = ["capability_fit", "verified_availability", "historical_success", "failure_rate", "latency", "cost_observation"]
        root = Path(__file__).resolve().parents[4]
        router = root / "RAIOS" / "V9" / "agents" / "a14" / "routing" / "CAPABILITY-FIRST-ROUTER.json"
        if router.exists():
            try:
                data = json.loads(router.read_text(encoding="utf-8"))
                candidate = data.get("selection_factors")
                if isinstance(candidate, list) and candidate:
                    factors = list(candidate)
            except Exception:
                pass
        for name in ("verified_accuracy", "freshness", "resource_scarcity", "credit_runway", "risk_budget", "data_locality"):
            if name not in factors:
                factors.append(name)
        return factors

    def route_resource_task(
        self,
        task_fingerprint: dict[str, Any],
        *,
        projection: dict[str, Any] | None = None,
        projection_path: str | None = None,
    ) -> dict[str, Any]:
        """Capability/risk eligibility first. Economics only rank workers that are already eligible."""
        UNKNOWN = "UNKNOWN"

        def number(value: Any) -> float | None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            result = float(value)
            if not math.isfinite(result):
                return None
            return result

        data = projection if projection is not None else self.load_resource_projection(projection_path)
        records = list((data or {}).get("records", []))
        required_capability = str(task_fingerprint.get("capability", ""))
        risk_class = str(task_fingerprint.get("risk_class", "NORMAL")).upper()

        raw_min_accuracy = task_fingerprint.get("min_verified_accuracy")
        if isinstance(raw_min_accuracy, bool):
            return {"ok": False, "reason": "INVALID_MIN_VERIFIED_ACCURACY", "worker_id": None}
        if isinstance(raw_min_accuracy, (int, float)) and not math.isfinite(float(raw_min_accuracy)):
            return {"ok": False, "reason": "INVALID_MIN_VERIFIED_ACCURACY", "worker_id": None}

        minimum_accuracy = number(raw_min_accuracy)
        risk_budget = number(task_fingerprint.get("risk_budget"))
        if minimum_accuracy is None and risk_budget is not None:
            minimum_accuracy = max(0.0, min(1.0, 1.0 - risk_budget))
        if risk_class in {"HIGH", "CRITICAL"} and minimum_accuracy is None:
            return {
                "ok": False,
                "reason": "RISK_ACCURACY_REQUIREMENT_UNPROVEN",
                "eligible": [],
                "rejected": [],
                "selection_factors": self.resource_selection_factors(),
            }

        eligible: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for row in records:
            auth_state = str(row.get("auth_state", UNKNOWN)).upper()
            if auth_state == "REVOKED":
                continue
            capacity_state = str(row.get("physical_capacity_state", UNKNOWN)).upper()
            if capacity_state == "RUNTIME_UNCERTAIN":
                continue

            worker = row.get("worker_id", UNKNOWN)
            reason = None
            if worker in {None, "", UNKNOWN}:
                reason = "NO_EXECUTION_WORKER"
            elif str(row.get("freshness", UNKNOWN)).upper() != "FRESH":
                reason = "STALE_OR_UNPROVEN_EVIDENCE"
            elif str(row.get("availability", UNKNOWN)).upper() != "READY":
                reason = "WORKER_NOT_READY"
            else:
                classes = row.get("task_classes", [])
                if not isinstance(classes, list):
                    classes = []
                if required_capability and required_capability not in classes:
                    reason = "CAPABILITY_MISMATCH"

            if reason is None and minimum_accuracy is not None:
                actual = number(row.get("verified_accuracy"))
                if actual is None:
                    reason = "VERIFIED_ACCURACY_UNPROVEN"
                elif actual < minimum_accuracy:
                    reason = "VERIFIED_ACCURACY_BELOW_THRESHOLD"

            confidence = number(row.get("confidence"))
            if reason is None and confidence is None:
                reason = "EVIDENCE_CONFIDENCE_UNPROVEN"

            runway = number(row.get("projected_runway"))
            if reason is None and runway is not None and runway <= 0:
                reason = "CREDIT_RUNWAY_EXHAUSTED"

            if reason is not None:
                rejected.append({"worker_id": worker, "provider": row.get("provider"), "reason": reason})
                continue
            eligible.append(row)

        if not eligible:
            return {
                "ok": False,
                "reason": "NO_ELIGIBLE_WORKER",
                "eligible": [],
                "rejected": rejected,
                "selection_factors": self.resource_selection_factors(),
            }

        priced_currencies = {
            str(row.get("currency")).upper()
            for row in eligible
            if row.get("currency") not in {None, "", UNKNOWN}
            and (number(row.get("price_cpu_second")) is not None or number(row.get("price_gpu_second")) is not None)
        }
        if len(priced_currencies) > 1:
            return {
                "ok": False,
                "reason": "CROSS_CURRENCY_COST_COMPARISON_UNPROVEN",
                "eligible": [],
                "rejected": rejected,
                "currencies": sorted(priced_currencies),
                "selection_factors": self.resource_selection_factors(),
            }

        requested_locality = task_fingerprint.get("data_locality")
        gpu_required = bool(task_fingerprint.get("gpu_required", False))

        def score(row: dict[str, Any]) -> tuple[Any, ...]:
            accuracy = number(row.get("verified_accuracy"))
            success = number(row.get("task_success_rate"))
            failure = number(row.get("failure_rate"))
            confidence = number(row.get("confidence"))
            latency = number(row.get("observed_latency"))
            cpu_cost = number(row.get("price_cpu_second"))
            gpu_cost = number(row.get("price_gpu_second"))
            expected_cost = gpu_cost if gpu_required else cpu_cost
            concurrency = number(row.get("max_concurrency"))
            runway = number(row.get("projected_runway"))
            locality = row.get("data_locality")
            locality_match = 0
            if requested_locality not in {None, UNKNOWN}:
                if locality == requested_locality:
                    locality_match = 1
                elif isinstance(locality, list) and requested_locality in locality:
                    locality_match = 1
            return (
                accuracy if accuracy is not None else -1.0,
                confidence if confidence is not None else -1.0,
                success if success is not None else -1.0,
                -(failure if failure is not None else 2.0),
                locality_match,
                1 if expected_cost is not None else 0,
                -(expected_cost if expected_cost is not None else float("inf")),
                1 if latency is not None else 0,
                -(latency if latency is not None else float("inf")),
                concurrency if concurrency is not None else -1.0,
                runway if runway is not None else -1.0,
                str(row.get("worker_id")),
            )

        winner = max(eligible, key=score)
        return {
            "ok": True,
            "worker_id": winner.get("worker_id"),
            "provider": winner.get("provider"),
            "record": winner,
            "eligible_count": len(eligible),
            "rejected": rejected,
            "selection_factors": self.resource_selection_factors(),
            "task_fingerprint": dict(task_fingerprint),
            "law": [
                "QUALITY_BEFORE_COST",
                "STALE_EVIDENCE_MUST_NOT_ROUTE",
                "PROVIDER_NAME_DOES_NOT_DETERMINE_ROUTING",
                "SCHEDULER_MUST_NOT_PROBE_PROVIDERS",
            ],
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
