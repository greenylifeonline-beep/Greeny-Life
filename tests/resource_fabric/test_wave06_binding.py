"""Wave-06 live-binding expansion tests. Dry-run only; no GPU/paid mutation."""

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
from raios.resource_fabric.factory import c1_action_queue, place, reservoir_view, resource_request
from raios.resource_fabric.live import apply_live_overlay, discover_auth, run_live_probes
from raios.resource_fabric.schema import UNOBSERVED
from raios.resource_fabric.secrets import assert_no_secrets


def _reasons(decision: dict, account_id: str) -> list[str]:
    for row in decision.get("rejected_resources") or []:
        if row.get("account_id") == account_id:
            return list(row.get("reasons") or [])
    for row in decision.get("evaluations") or []:
        if row.get("account_id") == account_id:
            return list(row.get("reasons") or []) + list(row.get("conditional_reasons") or [])
    return []


def _wave05_world() -> dict:
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


def _overlay(**probe_updates: dict) -> dict:
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
                "accelerator_types": ["GPU", "TPU"],
                "account_eligible_gpu": True,
                "active_session_gpu": False,
                "gpu_sku": UNOBSERVED,
                "gpu_vram": UNOBSERVED,
            },
            "MODAL_01": {
                "account_id": "MODAL_01",
                "status": "REACHABLE_CREDENTIAL_PRESENT",
                "token_fields_present": True,
                "NO_RESOURCE_CREATED": True,
                "NO_GPU_STARTED": True,
                "gpu_entitlement": UNOBSERVED,
            },
            "KAGGLE_PARTNER": {
                "account_id": "KAGGLE_PARTNER",
                "status": "SEPARATE_PROFILE_CANDIDATE_PRESENT",
                "live_auth_proven": False,
                "distinct_from_c1": False,
                "copied_from_c1": False,
                "isolated_from": "KAGGLE_C1",
            },
            "ORACLE_01": {"account_id": "ORACLE_01", "status": "AUTH_REQUIRED"},
            "COLAB_01": {
                "account_id": "COLAB_01",
                "status": "AUTH_REQUIRED",
                "GOOGLE_AUTH": "ABSENT",
                "COLAB_ACCESS": UNOBSERVED,
            },
            "LIGHTNING_01": {
                "account_id": "LIGHTNING_01",
                "status": "REACHABLE",
                "credits_remaining": 30,
                "storage_used_bytes": 62589,
                "free_storage_bytes": 10737418240,
                "studio_count": 2,
                "account_eligible_gpu": False,
                "gpu_sku": UNOBSERVED,
                "gpu_vram": UNOBSERVED,
            },
            "NINEROUTER": {"provider_type": "MODEL_ROUTING_GATEWAY", "RESOURCE_AUTHORITY": False},
        },
        "observed_at": "2026-08-28T12:36:24+00:00",
        "PAID_RESOURCE_CREATED": False,
        "GPU_SESSION_STARTED": False,
    }
    for aid, rec in probe_updates.items():
        state["probes"][aid] = {**state["probes"][aid], **rec}
    apply_live_overlay(world, state)
    world["live_state"] = state
    return world


class Wave06LiveBinding(unittest.TestCase):
    def test_baseline_world_still_rejects_unproven_partner(self):
        world = _wave05_world()
        dec = place(resource_request(workload_class="GPU_BURST", request_id="W6-F"), world)
        reasons = _reasons(dec, "KAGGLE_PARTNER")
        self.assertTrue(any(x in reasons for x in ("KAGGLE_PARTNER_LIVE_AUTH_UNPROVEN", "UNAUTHENTICATED_RESOURCE")))
        partner = next(r for r in dec["evaluations"] if r["account_id"] == "KAGGLE_PARTNER")
        self.assertFalse(partner["dispatch_allowed"])
        self.assertTrue(partner["KAGGLE_QUOTA_ISOLATED_FROM_C1"])
        self.assertNotIn("KAGGLE_QUOTA_ISOLATED_FROM_C1", partner["reasons"])

    def test_partner_proven_distinct_enters_reservoir_without_quota_merge(self):
        world = _overlay(
            KAGGLE_PARTNER={
                "status": "REACHABLE",
                "live_auth_proven": True,
                "distinct_from_c1": True,
                "copied_from_c1": False,
                "account_eligible_gpu": True,
                "IDENTITY_PROOF": "partner-user",
            }
        )
        view = reservoir_view(world)
        self.assertIn("KAGGLE_PARTNER", view["currently_schedulable"])
        self.assertTrue(view["kaggle_partner_dispatch_allowed"])
        self.assertEqual(view["gpu_pool"]["current_primary"], "KAGGLE_C1")
        self.assertEqual(view["gpu_pool"]["failover"], ["KAGGLE_PARTNER"])
        self.assertTrue(view["gpu_pool"]["failover_proven"])
        dec = place(resource_request(workload_class="GPU_BURST", paid_allowed=False, request_id="W6-P"), world)
        c1 = next(r for r in dec["evaluations"] if r["account_id"] == "KAGGLE_C1")
        partner = next(r for r in dec["evaluations"] if r["account_id"] == "KAGGLE_PARTNER")
        self.assertEqual(c1["quota_account"], "KAGGLE_C1")
        self.assertEqual(partner["quota_account"], "KAGGLE_PARTNER")
        self.assertNotEqual(c1["quota_account"], partner["quota_account"])
        self.assertTrue(partner["authenticated"])
        self.assertTrue(partner["KAGGLE_QUOTA_ISOLATED_FROM_C1"])

    def test_partner_same_as_c1_is_not_dispatchable(self):
        world = _overlay(
            KAGGLE_PARTNER={
                "status": "NOT_DISTINCT_FROM_C1",
                "live_auth_proven": False,
                "distinct_from_c1": False,
                "copied_from_c1": True,
            }
        )
        view = reservoir_view(world)
        self.assertNotIn("KAGGLE_PARTNER", view["currently_schedulable"])
        dec = place(resource_request(workload_class="GPU_BURST", request_id="W6-SAME"), world)
        self.assertFalse(next(r for r in dec["evaluations"] if r["account_id"] == "KAGGLE_PARTNER")["dispatch_allowed"])

    def test_lightning_reachable_cpu_not_unpaid_gpu_failover(self):
        world = _overlay()
        view = reservoir_view(world)
        self.assertIn("LIGHTNING_01", view["currently_schedulable"])
        self.assertEqual(view["gpu_pool"]["failover"], "NONE_PROVEN")
        self.assertNotIn("LIGHTNING_01", view["gpu_pool"]["currently_schedulable"])
        self.assertEqual(view["persistent_control"]["failover"], "LIGHTNING_01")
        gpu = place(resource_request(workload_class="GPU_BURST", paid_allowed=False, request_id="W6-LGPU"), world)
        self.assertIn("PAID_GPU_DENIED", _reasons(gpu, "LIGHTNING_01"))
        cpu = place(resource_request(workload_class="BATCH_CPU", request_id="W6-LCPU"), world)
        self.assertIn("LIGHTNING_01", cpu["eligible_resources"])
        self.assertEqual(cpu["selected_resource"], "MODAL_01")

    def test_modal_credential_present_is_cpu_dispatchable_not_gpu_entitlement(self):
        world = _overlay()
        view = reservoir_view(world)
        self.assertIn("MODAL_01", view["currently_schedulable"])
        cpu = place(resource_request(workload_class="BATCH_CPU", request_id="W6-MCPU"), world)
        self.assertEqual(cpu["selected_resource"], "MODAL_01")
        gpu = place(resource_request(workload_class="GPU_BURST", paid_allowed=False, request_id="W6-MGPU"), world)
        self.assertIn("PAID_GPU_DENIED", _reasons(gpu, "MODAL_01"))
        modal = next(a for a in world["accounts"] if a["account_id"] == "MODAL_01")
        self.assertEqual(modal["gpu_entitlement"], UNOBSERVED)

    def test_colab_adc_is_not_colab_access(self):
        world = _overlay()
        dec = place(resource_request(workload_class="GPU_BURST", request_id="W6-COLAB"), world)
        reasons = _reasons(dec, "COLAB_01")
        self.assertIn("GOOGLE_AUTH_SETUP_REQUIRED", reasons)
        self.assertIn("BLOCKED_C1_ACTION", reasons)
        colab = next(a for a in world["accounts"] if a["account_id"] == "COLAB_01")
        self.assertEqual(colab["COLAB_ACCESS"], UNOBSERVED)
        self.assertEqual(colab["status"], "AUTH_REQUIRED")

    def test_sku_vram_remain_unobserved(self):
        world = _overlay()
        dec = place(resource_request(workload_class="GPU_BURST", gpu_vram_min_gb=24, paid_allowed=False, request_id="W6-VRAM"), world)
        kag = next(r for r in dec["evaluations"] if r["account_id"] == "KAGGLE_C1")
        self.assertEqual(kag["live_gpu_sku"], UNOBSERVED)
        self.assertEqual(kag["live_gpu_vram"], UNOBSERVED)
        self.assertEqual(dec["result_class"], "CAPACITY_PROBE_REQUIRED")
        view = reservoir_view(world)
        self.assertEqual(view["gpu_pool"]["live_gpu_sku_known"], [])
        self.assertEqual(view["gpu_pool"]["live_vram_known"], [])

    def test_oracle_auth_required_not_absent(self):
        world = _overlay()
        view = reservoir_view(world)
        self.assertIn("ORACLE_01", view["pending_auth"])
        self.assertIn("BLOCKED_C1_ACTION", _reasons(place(resource_request(workload_class="LONG_RUNNING_SERVICE", request_id="W6-ORACLE"), world), "ORACLE_01"))
        oracle = next(a for a in world["accounts"] if a["account_id"] == "ORACLE_01")
        self.assertEqual(oracle["status"], "AUTH_REQUIRED")
        self.assertNotEqual(oracle["status"], "ABSENT")

    def test_c5_grounding_remains_blocked(self):
        world = _overlay()
        view = reservoir_view(world)
        self.assertEqual(view["RF_C5_12"], "BLOCKED_BY_GOVERNED_CHANNEL")
        self.assertFalse(view["control_plane"]["NINEROUTER_IS_RESOURCE_AUTHORITY"])
        assert_no_secrets(view)

    def test_no_second_registry_flags(self):
        world = _overlay()
        packed = place(resource_request(workload_class="CONTROL", request_id="W6-CTRL"), world)
        self.assertFalse(packed["SECOND_PROVIDER_REGISTRY"])
        self.assertFalse(packed["SECOND_SCHEDULER"])
        self.assertFalse(packed["PAID_ACTIVATION"])
        self.assertFalse(packed["GPU_SESSION_STARTED"])

    def test_wave06_closure_proven_reservoir_and_c1_queue(self):
        world = _overlay()
        view = reservoir_view(world)
        self.assertTrue(view["KAGGLE_C1_BOUND"])
        self.assertTrue(view["LIGHTNING_01_BOUND"])
        self.assertFalse(view["UNPROVEN_PROVIDER_ADMITTED"])
        self.assertTrue(view["RESOURCE_FACTORY_REUSED"])
        self.assertFalse(view["SECOND_RESOURCE_REGISTRY_CREATED"])
        self.assertTrue(view["FAILOVER_POLICY_UPDATED_FROM_PROVEN_CAPACITY"])
        self.assertEqual(view["BLOCKED_C1_ACTION_COUNT"], 3)
        self.assertTrue(view["WAVE06_COMPLETE_WITH_BOUNDED_EXTERNAL_ACTION_QUEUE"])
        self.assertEqual(view["gpu_pool"]["current_primary"], "KAGGLE_C1")
        self.assertEqual(view["gpu_pool"]["failover"], "NONE_PROVEN")
        self.assertEqual(view["cpu_pool"]["remote_primary"], "MODAL_01")
        self.assertEqual(view["cpu_pool"]["failover"], "KAGGLE_C1")
        self.assertEqual(view["persistent_control"]["failover"], "LIGHTNING_01")
        self.assertNotIn("KAGGLE_PARTNER", view["currently_schedulable"])
        self.assertNotIn("ORACLE_01", view["currently_schedulable"])
        self.assertNotIn("COLAB_01", view["currently_schedulable"])
        queue = c1_action_queue()
        self.assertEqual(len(queue), 3)
        self.assertEqual({row["account_id"] for row in queue}, {"KAGGLE_PARTNER", "ORACLE_01", "COLAB_01"})
        self.assertTrue(all(row["classification"] == "BLOCKED_C1_ACTION" for row in queue))
        self.assertTrue(all(row["do_not_repeat_probe"] for row in queue))
        gpu = place(resource_request(workload_class="GPU_BURST", paid_allowed=False, request_id="W6-CLOSE"), world)
        self.assertEqual(gpu["selected_resource"], "KAGGLE_C1")
        self.assertFalse(gpu["GPU_SESSION_STARTED"])
        assert_no_secrets(view)
        assert_no_secrets(queue)

    def test_blocked_accounts_are_not_reprobed(self):
        state = run_live_probes(live=False)
        for aid in ("KAGGLE_PARTNER", "ORACLE_01", "COLAB_01"):
            rec = state["probes"][aid]
            self.assertEqual(rec["status"], "BLOCKED_C1_ACTION")
            self.assertTrue(rec["PROBE_SKIPPED"])


if __name__ == "__main__":
    unittest.main()
