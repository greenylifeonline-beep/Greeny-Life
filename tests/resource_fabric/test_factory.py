"""Wave-05 executable Resource Factory tests. Dry-run only; no GPU/paid mutation."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("NO_LLM_CALLS", "true")
os.environ["RAIOS_RESOURCE_LIVE"] = "0"

from raios.resource_fabric.census import collect_world
from raios.resource_fabric.cli import main
from raios.resource_fabric.factory import (
    DEFAULT_POLICY,
    WORKLOAD_CLASSES,
    evaluate_workload,
    place,
    plan_dispatch,
    reservoir_view,
    resource_request,
)
from raios.resource_fabric.live import apply_live_overlay, discover_auth
from raios.resource_fabric.placement import decide, placement_request
from raios.resource_fabric.schema import (
    EXISTING_JOB_LEDGER,
    EXISTING_LEASE_SYSTEM,
    EXISTING_RECEIPT_ROOT,
    EXISTING_TASK_REGISTRY,
    UNOBSERVED,
)
from raios.resource_fabric.secrets import assert_no_secrets


def _world() -> dict:
    world = collect_world()
    state = {
        "auth": discover_auth(),
        "probes": {
            "LOCAL_AG": {
                "account_id": "LOCAL_AG",
                "status": "REACHABLE",
                "ram_total_gb": 7.8,
                "ram_avail_gb": 0.4,
                "execution_blocked_by_memory": True,
            },
            "KAGGLE_C1": {
                "account_id": "KAGGLE_C1",
                "status": "REACHABLE",
                "gpu_quota": {"limit": 30, "used": 1.06, "remaining": 28.94, "reset_at": "2026-08-29T00:00:00"},
                "tpu_quota": {"limit": 20, "used": 0, "remaining": 20, "reset_at": "2026-08-29T00:00:00"},
                "dataset_used_bytes": 7301477,
                "account_eligible_gpu": True,
                "active_session_gpu": False,
            },
            "MODAL_01": {"account_id": "MODAL_01", "status": "REACHABLE", "NO_RESOURCE_CREATED": True, "NO_GPU_STARTED": True},
            "KAGGLE_PARTNER": {
                "account_id": "KAGGLE_PARTNER",
                "status": "AUTH_REQUIRED",
                "live_auth_proven": False,
                "copied_from_c1": False,
                "isolated_from": "KAGGLE_C1",
            },
            "ORACLE_01": {"account_id": "ORACLE_01", "status": "AUTH_REQUIRED"},
            "COLAB_01": {"account_id": "COLAB_01", "status": "AUTH_REQUIRED"},
            "LIGHTNING_01": {"account_id": "LIGHTNING_01", "status": "PARTIAL"},
            "NINEROUTER": {"provider_type": "MODEL_ROUTING_GATEWAY", "RESOURCE_AUTHORITY": False},
        },
        "observed_at": "2026-08-28T00:00:00+00:00",
        "PAID_RESOURCE_CREATED": False,
        "GPU_SESSION_STARTED": False,
    }
    apply_live_overlay(world, state)
    world["live_state"] = state
    return world


def _reasons(decision: dict, account_id: str) -> list[str]:
    for row in decision.get("rejected_resources") or []:
        if row.get("account_id") == account_id:
            return list(row.get("reasons") or [])
    for row in decision.get("evaluations") or []:
        if row.get("account_id") == account_id:
            return list(row.get("reasons") or []) + list(row.get("conditional_reasons") or [])
    return []


class ResourceFactory(unittest.TestCase):
    def setUp(self):
        self.world = _world()

    def test_workload_classes_supported(self):
        self.assertEqual(set(WORKLOAD_CLASSES), set(DEFAULT_POLICY["workload_classes"]))

    def test_a_control_low_ram_places_local(self):
        req = resource_request(workload_class="CONTROL", request_id="A")
        dec = place(req, self.world)
        self.assertEqual(dec["result_class"], "PLACED")
        self.assertEqual(dec["selected_resource"], "LOCAL_AG")
        self.assertTrue(dec["dispatch_allowed"])
        self.assertFalse(dec["GPU_SESSION_STARTED"])

    def test_b_heavy_local_inference_rejected(self):
        req = resource_request(workload_class="GPU_BURST", heavy_inference=True, request_id="B", preferred_resources=["LOCAL_AG"])
        dec = place(req, self.world)
        self.assertIn("LOCAL_AG_HEAVY_INFERENCE_DENIED", _reasons(dec, "LOCAL_AG"))
        self.assertNotEqual(dec.get("selected_resource"), "LOCAL_AG")

    def test_c_gpu_burst_kaggle_candidate_modal_paid_rejected(self):
        req = resource_request(workload_class="GPU_BURST", paid_allowed=False, request_id="C")
        dec = place(req, self.world)
        self.assertIn(dec["selected_resource"], {"KAGGLE_C1"})
        self.assertIn("KAGGLE_C1", dec["eligible_resources"] + [c["account_id"] for c in dec["conditional_resources"]])
        self.assertIn("PAID_GPU_DENIED", _reasons(dec, "MODAL_01"))
        self.assertNotIn("MODAL_01", dec["eligible_resources"])

    def test_d_exact_vram_unobserved_is_probe_not_fabricated(self):
        req = resource_request(workload_class="GPU_BURST", gpu_vram_min_gb=24, paid_allowed=False, request_id="D")
        dec = place(req, self.world)
        self.assertEqual(dec["result_class"], "CAPACITY_PROBE_REQUIRED")
        self.assertTrue(dec["requires_capacity_probe"])
        self.assertFalse(dec["dispatch_allowed"])
        kag = next(r for r in dec["evaluations"] if r["account_id"] == "KAGGLE_C1")
        self.assertEqual(kag["live_gpu_vram"], UNOBSERVED)
        self.assertIn("CAPACITY_PROBE_REQUIRED", kag["conditional_reasons"])
        self.assertNotEqual(kag["live_gpu_vram"], 16)

    def test_e_model_storage_rejects_local(self):
        req = resource_request(workload_class="MODEL_STORAGE", request_id="E")
        dec = place(req, self.world)
        self.assertIn("LOCAL_MODEL_STORAGE_PROHIBITED", _reasons(dec, "LOCAL_AG"))
        self.assertEqual(dec["selected_resource"], "KAGGLE_C1")
        self.assertTrue(dec["dispatch_allowed"])

    def test_f_kaggle_partner_rejected_unproven(self):
        req = resource_request(workload_class="GPU_BURST", request_id="F")
        dec = place(req, self.world)
        reasons = _reasons(dec, "KAGGLE_PARTNER")
        self.assertTrue(any(x in reasons for x in ("KAGGLE_PARTNER_LIVE_AUTH_UNPROVEN", "UNAUTHENTICATED_RESOURCE")))
        partner = next(r for r in dec["evaluations"] if r["account_id"] == "KAGGLE_PARTNER")
        self.assertFalse(partner["dispatch_allowed"])

    def test_g_oracle_auth_required(self):
        req = resource_request(workload_class="LONG_RUNNING_SERVICE", request_id="G")
        dec = place(req, self.world)
        self.assertIn("AUTH_REQUIRED", _reasons(dec, "ORACLE_01"))

    def test_h_colab_google_auth_setup_required(self):
        req = resource_request(workload_class="GPU_BURST", request_id="H")
        dec = place(req, self.world)
        self.assertIn("GOOGLE_AUTH_SETUP_REQUIRED", _reasons(dec, "COLAB_01"))

    def test_i_modal_cpu_short_job_eligible(self):
        req = resource_request(workload_class="BATCH_CPU", request_id="I")
        dec = place(req, self.world)
        self.assertIn("MODAL_01", dec["eligible_resources"])
        self.assertEqual(dec["selected_resource"], "MODAL_01")
        self.assertEqual(dec["result_class"], "PLACED")
        modal = next(r for r in dec["evaluations"] if r["account_id"] == "MODAL_01")
        self.assertEqual(modal["cost_class"], "SERVERLESS_UNACTIVATED")

    def test_j_paid_without_c1_requires_authority(self):
        req = resource_request(
            workload_class="GPU_BURST",
            paid_allowed=True,
            authority_context="C2",
            preferred_resources=["MODAL_01"],
            prohibited_resources=["KAGGLE_C1", "LOCAL_AG"],
            request_id="J",
        )
        dec = place(req, self.world)
        self.assertEqual(dec["result_class"], "C1_AUTH_REQUIRED")
        self.assertTrue(dec["requires_c1_authorization"])
        self.assertFalse(dec["dispatch_allowed"])

    def test_k_repeat_is_deterministic(self):
        req = resource_request(workload_class="CONTROL", request_id="K")
        first = place(req, self.world)
        second = place(req, self.world)
        self.assertEqual(first["decision_id"], second["decision_id"])
        self.assertEqual(first["selected_resource"], second["selected_resource"])
        self.assertEqual(first["result_class"], second["result_class"])
        self.assertEqual(first["ranking"], second["ranking"])

    def test_dry_run_plan_does_not_mutate(self):
        packed = evaluate_workload("CONTROL", self.world, request_id="DRY")
        plan = packed["plan"]
        self.assertTrue(plan["DRY_RUN"])
        self.assertFalse(plan["PROVIDER_MUTATION"])
        self.assertFalse(plan["GPU_SESSION_STARTED"])
        self.assertFalse(plan["PAID_RESOURCE_CREATED"])
        self.assertFalse(plan["job"]["enqueued"])
        self.assertFalse(plan["lease"]["acquired"])
        self.assertFalse(plan["receipt"]["written"])
        self.assertEqual(plan["job"]["ledger"], EXISTING_JOB_LEDGER)
        self.assertEqual(plan["task_registry"], EXISTING_TASK_REGISTRY)
        self.assertIn("command-fabric/leases", plan["lease_system"])
        self.assertEqual(EXISTING_LEASE_SYSTEM, plan["lease_system"])
        self.assertEqual(plan["receipt"]["root"], EXISTING_RECEIPT_ROOT)
        self.assertFalse(plan["SECOND_SCHEDULER"])
        self.assertFalse(plan["SECOND_LEASE_SYSTEM"])
        self.assertFalse(plan["SECOND_RECEIPT_SYSTEM"])
        self.assertFalse(plan["SECOND_PROVIDER_REGISTRY"])
        self.assertFalse(plan["NINEROUTER_IS_RESOURCE_AUTHORITY"])
        assert_no_secrets(plan)

    def test_live_dispatch_blocked_in_this_wave(self):
        req = resource_request(workload_class="CONTROL", request_id="LIVE")
        dec = place(req, self.world)
        with self.assertRaises(ValueError):
            plan_dispatch(dec, req, dry_run=False)

    def test_existing_decide_still_works(self):
        req = placement_request(requires_gpu=True, min_gpu_vram_gb=24)
        dec = decide(req, self.world)
        self.assertEqual(dec["kind"], "PlacementDecision")
        self.assertFalse(dec["PAID_ACTIVATION"])

    def test_kaggle_quotas_not_merged(self):
        req = resource_request(workload_class="GPU_BURST", request_id="Q")
        dec = place(req, self.world)
        c1 = next(r for r in dec["evaluations"] if r["account_id"] == "KAGGLE_C1")
        partner = next(r for r in dec["evaluations"] if r["account_id"] == "KAGGLE_PARTNER")
        self.assertEqual(c1["quota_account"], "KAGGLE_C1")
        self.assertEqual(partner["quota_account"], "KAGGLE_PARTNER")
        self.assertNotEqual(c1["quota_account"], partner["quota_account"])

    def test_reservoir_derives_from_live_not_static_only(self):
        view = reservoir_view(self.world)
        self.assertTrue(view["STATIC_SNAPSHOT_NE_RUNTIME_AUTHORITY"])
        self.assertIn("LOCAL_AG", view["currently_schedulable"])
        self.assertIn("KAGGLE_C1", view["currently_schedulable"])
        self.assertIn("MODAL_01", view["currently_schedulable"])
        self.assertNotIn("KAGGLE_PARTNER", view["currently_schedulable"])
        self.assertEqual(view["gpu_pool"]["current_primary"], "KAGGLE_C1")
        self.assertEqual(view["gpu_pool"]["failover"], "NONE_PROVEN")
        self.assertEqual(view["gpu_pool"]["live_gpu_sku_known"], [])
        self.assertEqual(view["gpu_pool"]["live_vram_known"], [])
        self.assertFalse(view["kaggle_partner_dispatch_allowed"])
        self.assertFalse(view["control_plane"]["NINEROUTER_IS_RESOURCE_AUTHORITY"])

    def test_discovery_does_not_start_gpu(self):
        packed = evaluate_workload("DISCOVERY", self.world, request_id="DISC")
        self.assertFalse(packed["decision"]["GPU_SESSION_STARTED"])
        self.assertFalse(packed["plan"]["GPU_SESSION_STARTED"])
        self.assertFalse(packed["request"]["gpu_required"])

    def test_cli_reservoir_plan_explain(self):
        import io
        from contextlib import redirect_stdout

        for cmd in ("reservoir", "placement", "plan", "explain"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main([cmd, "--no-probe", "-Workload", "CONTROL"])
            self.assertEqual(code, 0, cmd)
            self.assertTrue(buf.getvalue())

    def test_no_second_scheduler_import_in_factory(self):
        text = Path(__file__).resolve().parents[2].joinpath("src/raios/resource_fabric/factory.py").read_text(encoding="utf-8")
        self.assertNotIn("WorkStealingScheduler(", text)
        self.assertNotIn("JobLedger(", text)
        self.assertNotIn("CommandLeaseAdapter(", text)
        self.assertIn("EXISTING_JOB_LEDGER", text)
        self.assertIn("EXISTING_SCHEDULER", text)


if __name__ == "__main__":
    unittest.main()
