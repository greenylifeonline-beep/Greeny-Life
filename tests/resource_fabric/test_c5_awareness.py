"""C5 resource-awareness seam tests. Dry-run factory only; no GPU/paid mutation."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("NO_LLM_CALLS", "true")
os.environ["RAIOS_RESOURCE_LIVE"] = "0"

from raios.resource_fabric.c5_awareness import (
    classify_accounts,
    naive_reason,
    reason,
    resource_context,
    run_shadow,
)
from raios.resource_fabric.c5_growth_loop import fixture_world, run_wave
from raios.resource_fabric.secrets import assert_no_secrets


class C5ResourceAwareness(unittest.TestCase):
    def setUp(self):
        self.world = fixture_world()

    def test_no_second_registry_flags(self):
        ctx = resource_context(self.world)
        self.assertFalse(ctx["SECOND_RESOURCE_REGISTRY"])
        self.assertFalse(ctx["SECOND_C5"])
        self.assertFalse(ctx["NINEROUTER_IS_RESOURCE_AUTHORITY"])
        self.assertFalse(ctx["PAID_RESOURCE_ALLOWED"])
        self.assertFalse(ctx["GPU_SESSION_STARTED"])
        assert_no_secrets(ctx)

    def test_accounts_have_knowledge_states(self):
        rows = classify_accounts(self.world)
        by = {r["account_id"]: r for r in rows}
        self.assertEqual(by["KAGGLE_C1"]["auth"], "PROVEN")
        self.assertEqual(by["KAGGLE_C1"]["gpu_eligibility"], "PROVEN")
        self.assertEqual(by["KAGGLE_C1"]["gpu_sku"], "UNOBSERVED")
        self.assertEqual(by["KAGGLE_C1"]["gpu_vram"], "UNOBSERVED")
        self.assertEqual(by["KAGGLE_PARTNER"]["auth"], "AUTH_REQUIRED")
        self.assertEqual(by["ORACLE_01"]["auth"], "AUTH_REQUIRED")
        self.assertEqual(by["COLAB_01"]["auth"], "AUTH_REQUIRED")
        self.assertEqual(by["LOCAL_AG"]["gpu_eligibility"], "NOT_SUPPORTED")
        self.assertNotEqual(by["KAGGLE_C1"]["quota_account"], by["KAGGLE_PARTNER"]["quota_account"])

    def test_reason_reuses_factory_dry_run(self):
        rec = reason("CONTROL", self.world, request_id="T-CTRL")
        self.assertEqual(rec["selected_resource"], "LOCAL_AG")
        self.assertEqual(rec["result_class"], "PLACED")
        self.assertTrue(rec["plan"]["DRY_RUN"])
        self.assertFalse(rec["plan"]["job"]["enqueued"])
        self.assertFalse(rec["PAID_RESOURCE_CREATED"])
        self.assertFalse(rec["GPU_SESSION_STARTED"])
        self.assertFalse(rec["CANONICAL_PROMOTION"])

    def test_gpu_burst_and_vram_abstention(self):
        gpu = reason("GPU_BURST", self.world, request_id="T-GPU", paid_allowed=False)
        self.assertEqual(gpu["selected_resource"], "KAGGLE_C1")
        self.assertTrue(gpu["dispatch_allowed"])
        vram = reason("GPU_BURST", self.world, request_id="T-VRAM", gpu_vram_min_gb=24, paid_allowed=False)
        self.assertEqual(vram["result_class"], "CAPACITY_PROBE_REQUIRED")
        self.assertTrue(vram["abstain"])
        self.assertEqual(vram["knowledge_state"], "UNOBSERVED")
        self.assertFalse(vram["dispatch_allowed"])

    def test_paid_requires_c1(self):
        rec = reason(
            "GPU_BURST",
            self.world,
            request_id="T-PAID",
            paid_allowed=True,
            authority_context="C2",
            preferred_resources=["MODAL_01"],
            prohibited_resources=["KAGGLE_C1", "LOCAL_AG"],
        )
        self.assertEqual(rec["result_class"], "C1_AUTH_REQUIRED")
        self.assertTrue(rec["abstain"])
        self.assertFalse(rec["dispatch_allowed"])
        self.assertFalse(rec["PAID_RESOURCE_CREATED"])

    def test_model_storage_not_local(self):
        rec = reason("MODEL_STORAGE", self.world, request_id="T-STORE")
        self.assertEqual(rec["selected_resource"], "KAGGLE_C1")
        self.assertNotEqual(rec["selected_resource"], "LOCAL_AG")

    def test_shadow_improves_on_naive(self):
        shadow = run_shadow(self.world)
        self.assertGreater(shadow["after_accuracy"], shadow["before_accuracy"])
        self.assertGreaterEqual(shadow["after_accuracy"], 0.99)
        self.assertLess(shadow["before_accuracy"], 0.75)
        self.assertFalse(naive_reason("GPU_BURST")["abstain"])

    def test_failover_unproven_is_none(self):
        ctx = resource_context(self.world)
        self.assertEqual(ctx["gpu_primary"], "KAGGLE_C1")
        self.assertEqual(ctx["gpu_failover"], "NONE_PROVEN")
        self.assertFalse(ctx["gpu_failover_proven"])
        self.assertIn("KAGGLE_PARTNER", ctx["pending_auth"])
        self.assertIn("ORACLE_01", ctx["pending_auth"])

    def test_growth_wave_no_self_promotion_flags(self):
        payload = run_wave(self.world, live_c5=False)
        self.assertTrue(payload["regression_pass"])
        self.assertGreaterEqual(payload["counts"]["VALIDATED"], 8)
        self.assertEqual(payload["counts"]["REJECTED"], 0)
        self.assertFalse(payload["baseline"]["CANONICAL_HIGH_RISK_SELF_PROMOTION"])
        ids = [i["id"] for i in payload["queue"]]
        self.assertEqual(len(ids), len(set(ids)))
        assert_no_secrets(payload)


if __name__ == "__main__":
    unittest.main()
