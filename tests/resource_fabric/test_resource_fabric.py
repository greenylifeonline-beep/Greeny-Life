"""Resource Fabric deterministic tests. Does not replay precanonical suites."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("NO_LLM_CALLS", "true")

from raios.resource_fabric.adapters import ADAPTERS, KaggleAdapter
from raios.resource_fabric.census import collect_world, snapshots, status_view, unused_capabilities
from raios.resource_fabric.cost import SCENARIOS, credit_effective, estimate
from raios.resource_fabric.observations import ObservationStore, observation
from raios.resource_fabric.placement import (
    MODEL_WEIGHTS_LOCAL,
    ModelWarehouse,
    compare_owned_vs_market,
    decide,
    market_offer,
    model_placement,
    model_record,
    placement_request,
    recompose,
)
from raios.resource_fabric.probe import ResourceProbeRunner
from raios.resource_fabric.projection import classify_unused, project_accelerator, scores
from raios.resource_fabric.schema import (
    SERVICE_CATEGORIES,
    STORAGE_TYPES,
    UNKNOWN,
    accelerator_resource,
    account,
    compute_resource,
    credit,
    provider,
    quota,
    resource_lease,
    service,
    storage_resource,
)
from raios.resource_fabric.secrets import assert_no_secrets, is_credential_ref, mask_record


class SchemaAndInvariants(unittest.TestCase):
    def test_provider_ne_account(self):
        p = provider(provider_id="KAGGLE", provider_type="notebook", display_name="Kaggle")
        self.assertTrue(p["PROVIDER_NE_ACCOUNT"])

    def test_two_kaggle_accounts_isolated(self):
        a = KaggleAdapter()
        accs = a.discover_accounts()
        self.assertEqual({x["account_id"] for x in accs}, {"KAGGLE_C1", "KAGGLE_PARTNER"})
        q1 = a.discover_quotas("KAGGLE_C1")
        q2 = a.discover_quotas("KAGGLE_PARTNER")
        self.assertNotEqual(q1[0]["quota_id"], q2[0]["quota_id"])
        self.assertEqual(q1[0]["account_id"], "KAGGLE_C1")
        self.assertEqual(q2[0]["account_id"], "KAGGLE_PARTNER")
        s1 = a.discover_storage("KAGGLE_C1")
        s2 = a.discover_storage("KAGGLE_PARTNER")
        self.assertTrue(all(x["account_id"] == "KAGGLE_C1" for x in s1))
        self.assertTrue(all(x["account_id"] == "KAGGLE_PARTNER" for x in s2))

    def test_zero_quota_service_still_available(self):
        rec = service(
            service_id="s1",
            service_name="functions",
            category="FUNCTIONS",
            provider_id="ORACLE_CLOUD",
            account_id="ORACLE_01",
            available=True,
            enabled=False,
            quota_available=0,
        )
        self.assertTrue(rec["available"])
        self.assertTrue(rec["AVAILABLE_WITH_ZERO_QUOTA"])
        self.assertNotEqual(rec["available"], False)

    def test_ephemeral_ne_persistent_compute(self):
        with self.assertRaises(ValueError):
            compute_resource(
                resource_id="x",
                provider_id="KAGGLE",
                account_id="KAGGLE_C1",
                persistent=True,
                ephemeral=True,
            )

    def test_storage_free_le_total(self):
        with self.assertRaises(ValueError):
            storage_resource(
                storage_id="x",
                provider_id="KAGGLE",
                account_id="KAGGLE_C1",
                storage_type="object_storage",
                capacity_total_gb=10,
                capacity_free_gb=11,
                capacity_used_gb=0,
            )

    def test_storage_unknown_capacity_allowed(self):
        rec = storage_resource(
            storage_id="x",
            provider_id="KAGGLE",
            account_id="KAGGLE_C1",
            storage_type="object_storage",
        )
        self.assertEqual(rec["capacity_total_gb"], UNKNOWN)

    def test_credential_ref_not_secret(self):
        rec = account(
            account_id="A",
            provider_id="KAGGLE",
            account_alias="A",
            owner_alias="C1",
            credential_ref="env:KAGGLE_CONFIG_A",
        )
        self.assertTrue(is_credential_ref(rec["credential_ref"]))
        assert_no_secrets(rec)

    def test_secret_in_credential_ref_rejected(self):
        with self.assertRaises(ValueError):
            account(
                account_id="A",
                provider_id="KAGGLE",
                account_alias="A",
                owner_alias="C1",
                credential_ref="token=supersecretvalue",
            )

    def test_resource_lease_wraps_existing_system(self):
        rec = resource_lease(lease_id="L1", resource_id="r", account_id="A", owner_identity="C1@AG")
        self.assertFalse(rec["SECOND_LEASE_SYSTEM"])
        self.assertTrue(rec["WAVE01_NO_ACQUIRE"])
        self.assertIn("command-fabric/leases", rec["EXISTING_LEASE_SYSTEM"])

    def test_missing_price_is_unknown(self):
        rec = estimate(scenario="GPU_1H", accelerator_rate=UNKNOWN)
        self.assertEqual(rec["accelerator"], UNKNOWN)
        self.assertEqual(rec["gross"], UNKNOWN)
        self.assertNotEqual(rec["accelerator"], 0)

    def test_free_tier_not_unlimited(self):
        rec = estimate(scenario="COST_24_7", compute_rate=1.0, free_tier_hours=10)
        self.assertTrue(rec["FREE_TIER_NE_UNLIMITED"])
        self.assertGreater(rec["compute"], 0)

    def test_credit_ne_cash(self):
        rec = estimate(scenario="GPU_10H", accelerator_rate=2.0, credits=[{"remaining_value": 5, "expires_at": "2099-01-01T00:00:00+00:00"}])
        self.assertTrue(rec["CREDIT_NE_CASH"])
        self.assertEqual(rec["credits_offset"], 5)

    def test_credit_expiry_respected(self):
        expired = credit(
            credit_id="c",
            provider_id="MODAL",
            account_id="MODAL_01",
            remaining_value=100,
            expires_at="2020-01-01T00:00:00+00:00",
        )
        now = datetime(2026, 8, 27, tzinfo=timezone.utc)
        self.assertEqual(credit_effective(expired, now=now), 0.0)

    def test_credit_unexpired_remaining(self):
        live = credit(
            credit_id="c",
            provider_id="MODAL",
            account_id="MODAL_01",
            remaining_value=40,
            expires_at="2099-01-01T00:00:00+00:00",
        )
        now = datetime(2026, 8, 27, tzinfo=timezone.utc)
        self.assertEqual(credit_effective(live, now=now), 40.0)

    def test_mask_never_emits_token(self):
        masked = mask_record({"authorization": "Bearer abcdefghijklmnop", "ok": 1})
        self.assertEqual(masked["authorization"], "***MASKED***")
        assert_no_secrets(masked)

    def test_historical_observation_preserved(self):
        tmp = Path(tempfile.mkdtemp()) / "obs.jsonl"
        store = ObservationStore(tmp)
        first = observation(provider="KAGGLE", account="KAGGLE_C1", resource_or_service="gpu", value="UNOBSERVED", source="t")
        store.append(first)
        second = observation(provider="KAGGLE", account="KAGGLE_C1", resource_or_service="gpu", value="PARTIAL", source="t2")
        store.append(second)
        self.assertEqual(len(store.history), 2)
        self.assertEqual(store.history[0]["observation_id"], first["observation_id"])
        with self.assertRaises(ValueError):
            store.rewrite_forbidden(first["observation_id"], value="ABSENT")

    def test_probe_failure_ne_absent(self):
        runner = ResourceProbeRunner(timeout_seconds=1)

        def boom():
            raise RuntimeError("down")

        rec = runner.run(provider="COLAB", account="COLAB_01", fn=boom, probe_id="x")
        self.assertEqual(rec["status"], "UNAVAILABLE")
        self.assertTrue(rec["PROBE_FAIL_NE_ABSENT"])
        self.assertNotEqual(rec["status"], "ABSENT")

    def test_same_hash_no_duplicate_transfer(self):
        wh = ModelWarehouse()
        rec = model_record(model_id="m1", family="qwen", size_gb=1.2, sha256="abc123")
        self.assertEqual(wh.register(rec)["STATUS"], "REGISTERED")
        again = model_record(model_id="m1-copy", family="qwen", size_gb=1.2, sha256="abc123")
        out = wh.register(again)
        self.assertEqual(out["STATUS"], "ALREADY_STORED")
        self.assertFalse(out["DUPLICATE_TRANSFER"])

    def test_local_model_storage_prohibited(self):
        self.assertFalse(MODEL_WEIGHTS_LOCAL)
        wh = ModelWarehouse()
        rec = model_record(model_id="m1", family="qwen", size_gb=1, sha256="deadbeef")
        wh.register(rec)
        out = wh.add_location("m1", {"kind": "LOCAL", "path": "C:/weights"})
        self.assertEqual(out["code"], "LOCAL_MODEL_STORAGE_PROHIBITED")

    def test_split_control_storage_inference(self):
        model = model_record(model_id="m", family="qwen", size_gb=10, sha256="h", min_vram=24, recommended_vram=40)
        storage = storage_resource(
            storage_id="oci-object",
            provider_id="ORACLE_CLOUD",
            account_id="ORACLE_01",
            storage_type="object_storage",
            persistent=True,
            model_weights_suitable=True,
            capacity_total_gb=200,
            capacity_used_gb=10,
            capacity_free_gb=190,
        )
        inference = accelerator_resource(
            resource_id="kaggle-gpu",
            provider_id="KAGGLE",
            account_id="KAGGLE_C1",
            gpu_vram_gb=32,
        )
        control = {"account_id": "LOCAL_AG"}
        out = model_placement(model, storage, inference, control)
        self.assertEqual(out["CONTROL_LOCATION"], "LOCAL_AG")
        self.assertTrue(out["CAN_STORE"])
        self.assertTrue(out["CAN_RUN"])
        self.assertFalse(out["CAN_RUN_EFFICIENTLY"])
        self.assertTrue(out["SPLIT_CONTROL_STORAGE_INFERENCE"])

    def test_local_storage_cannot_hold_weights(self):
        model = model_record(model_id="m", family="qwen", size_gb=1, sha256="h")
        storage = {"storage_id": "local", "account_id": "LOCAL_AG", "region": "local", "capacity_free_gb": 100}
        inference = {"resource_id": "gpu", "gpu_vram_gb": 48, "persistent": False}
        out = model_placement(model, storage, inference, {"account_id": "LOCAL_AG"})
        self.assertFalse(out["CAN_STORE"])


def _mk_storage_test(st: str):
    def _test(self):
        rec = storage_resource(
            storage_id=f"id-{st}",
            provider_id="ORACLE_CLOUD",
            account_id="ORACLE_01",
            storage_type=st,
            persistent=st != "ephemeral_disk",
        )
        self.assertEqual(rec["type"], st)
        self.assertEqual(rec["ephemeral"], not rec["persistent"])

    return _test


def _mk_service_test(cat: str):
    def _test(self):
        rec = service(
            service_id=f"svc-{cat}",
            service_name=cat,
            category=cat,
            provider_id="ORACLE_CLOUD",
            account_id="ORACLE_01",
            available=True,
            quota_available=UNKNOWN,
        )
        self.assertEqual(rec["category"], cat)
        self.assertTrue(rec["available"])

    return _test


def _mk_cost_test(sc: str):
    def _test(self):
        rec = estimate(scenario=sc, compute_rate=UNKNOWN, accelerator_rate=UNKNOWN, storage_gb_month=UNKNOWN, egress_gb_rate=UNKNOWN)
        self.assertEqual(rec["scenario"], sc)
        self.assertTrue(rec["MISSING_PRICE_IS_UNKNOWN"])
        if sc.startswith("GPU") or sc.startswith("COST") or sc.startswith("STORAGE") or sc.startswith("EGRESS"):
            self.assertTrue("gross" in rec)

    return _test


def _mk_provider_test(pid: str):
    def _test(self):
        ad = ADAPTERS[pid]
        ident = ad.identify()
        self.assertEqual(ident["provider_id"], pid)
        self.assertFalse(getattr(ad, "mutating_forbidden") is False)
        for acc in ad.discover_accounts():
            self.assertEqual(acc["provider_id"], pid)
            assert_no_secrets(acc)

    return _test


for _st in STORAGE_TYPES:
    setattr(SchemaAndInvariants, f"test_storage_type_{_st}", _mk_storage_test(_st))
for _cat in SERVICE_CATEGORIES:
    setattr(SchemaAndInvariants, f"test_service_category_{_cat}", _mk_service_test(_cat))
for _sc in SCENARIOS:
    setattr(SchemaAndInvariants, f"test_cost_scenario_{_sc}", _mk_cost_test(_sc))
for _pid in ADAPTERS:
    setattr(SchemaAndInvariants, f"test_adapter_{_pid}", _mk_provider_test(_pid))


class PlacementCensus(unittest.TestCase):
    def setUp(self):
        self.world = collect_world()

    def test_accounts_include_required_slots(self):
        ids = {a["account_id"] for a in self.world["accounts"]}
        for required in ("ORACLE_01", "KAGGLE_C1", "KAGGLE_PARTNER", "LIGHTNING_01", "COLAB_01", "MODAL_01"):
            self.assertIn(required, ids)

    def test_no_invented_usernames_on_partner(self):
        partner = next(a for a in self.world["accounts"] if a["account_id"] == "KAGGLE_PARTNER")
        self.assertEqual(partner["account_alias"], "KAGGLE_PARTNER")
        self.assertNotIn("@", partner["account_alias"])

    def test_kaggle_c1_reuses_greenylife_provenance(self):
        c1 = next(a for a in self.world["accounts"] if a["account_id"] == "KAGGLE_C1")
        self.assertTrue(any("greenylife" in r or "KAGGLE" in r for r in c1["provenance_refs"]))

    def test_placement_gpu_24gb(self):
        req = placement_request(requires_gpu=True, min_gpu_vram_gb=24)
        dec = decide(req, self.world)
        self.assertEqual(dec["kind"], "PlacementDecision")
        self.assertFalse(dec["PAID_ACTIVATION"])
        self.assertIn("ranked", dec)

    def test_recompose_planning_only(self):
        plan = recompose(self.world)
        self.assertTrue(plan["PLANNING_ONLY"])
        self.assertFalse(plan["PAID_RESOURCE_ACTIVATED"])
        self.assertEqual(plan["CONTROL_NODE"], "AG")

    def test_status_unknowns_not_zeroed(self):
        st = status_view(self.world)
        self.assertEqual(st["cpu_total"], UNKNOWN)
        self.assertNotEqual(st["persistent_storage_total_gb"], 0)

    def test_snapshots_mask(self):
        snaps = snapshots(self.world)
        assert_no_secrets(snaps)
        self.assertIn("RESOURCE-CENSUS.json", snaps)

    def test_unused_classes_known(self):
        rows = unused_capabilities(self.world)
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(row["class"], {"ACTIVE_USED", "ACTIVE_IDLE", "AVAILABLE_UNUSED", "AVAILABLE_ZERO_QUOTA", "CREDIT_BACKED", "FREE_TIER", "PAID_UNUSED", "UNKNOWN"})

    def test_market_compare_unknown(self):
        offer = market_offer(provider="AWS", service="g5", resource_type="gpu", price=UNKNOWN, source="UNINSERTED")
        cmp = compare_owned_vs_market(UNKNOWN, offer["price"])
        self.assertEqual(cmp["DELTA"], UNKNOWN)
        self.assertFalse(cmp["STALE_MARKET_HARDCODED"])

    def test_scores_dimensional(self):
        sc = scores({"persistent": True, "gpu_vram_gb": 40, "price_per_hour": 1.5, "available": True})
        self.assertFalse(sc["OPAQUE_SINGLE_SCORE_ONLY"])
        self.assertIn("gpu_score", sc)
        self.assertIn("RAIOS_VALUE_SCORE", sc)

    def test_zero_quota_class(self):
        self.assertEqual(classify_unused({"available": True, "quota_available": 0}), "AVAILABLE_ZERO_QUOTA")

    def test_project_heavy_inference(self):
        classes = project_accelerator({"gpu_vram_gb": 48, "session_limit": UNKNOWN})
        self.assertIn("HEAVY_INFERENCE", classes)

    def test_quota_record_zero_remaining_not_absent(self):
        q = quota(
            quota_id="q",
            provider_id="KAGGLE",
            account_id="KAGGLE_C1",
            service_id="nb",
            resource_type="gpu_hours",
            remaining=0,
            limit=30,
        )
        self.assertTrue(q["ZERO_REMAINING_NE_SERVICE_ABSENT"])
        self.assertEqual(q["remaining"], 0.0)

    def test_generic_ssh_has_no_fabricated_accounts(self):
        self.assertEqual(ADAPTERS["GENERIC_SSH"].discover_accounts(), [])

    def test_cli_module_importable(self):
        from raios.resource_fabric import cli

        self.assertTrue(callable(cli.main))


if __name__ == "__main__":
    unittest.main()
