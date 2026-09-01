"""Wave-02 live account binding tests. Does not require paid activation or model migration."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("NO_LLM_CALLS", "true")
os.environ["RAIOS_RESOURCE_LIVE"] = "0"

from raios.resource_fabric.census import collect_world, status_view
from raios.resource_fabric.cli import main
from raios.resource_fabric.live import (
    apply_live_overlay,
    bind_live_accounts,
    count_unknown_fields,
    discover_auth,
    model_hosting_fit,
    _probe_kaggle_partner,
    qwen35b_placement,
    run_live_probes,
)
from raios.resource_fabric.placement import recompose_v2
from raios.resource_fabric.schema import UNKNOWN
from raios.resource_fabric.secrets import assert_no_secrets


def _state(**probes: dict) -> dict:
    auth = discover_auth()
    merged = {
        "KAGGLE_PARTNER": {"account_id": "KAGGLE_PARTNER", "status": "AUTH_REQUIRED", "copied_from_c1": False, "isolated_from": "KAGGLE_C1"},
        "ORACLE_01": {"account_id": "ORACLE_01", "status": "AUTH_REQUIRED"},
        "COLAB_01": {"account_id": "COLAB_01", "status": "AUTH_REQUIRED"},
        "NINEROUTER": {
            "provider_type": "MODEL_ROUTING_GATEWAY",
            "endpoint": "LOCAL_ONLY",
            "RESOURCE_AUTHORITY": False,
            "health": "ok",
            "accounts_connected": 0,
            "models_visible": 12,
        },
    }
    merged.update(probes)
    return {"auth": auth, "probes": merged, "observed_at": "2026-08-27T22:00:00+00:00", "PAID_RESOURCE_CREATED": False}


class LiveBinding(unittest.TestCase):
    def test_kaggle_json_absent_is_not_account_absent(self):
        c1 = next(x for x in discover_auth() if x["account_id"] == "KAGGLE_C1")
        self.assertTrue(c1["KAGGLE_JSON_ABSENT_NE_ACCOUNT_ABSENT"])
        self.assertNotEqual(c1.get("session_state"), "ABSENT")
        self.assertNotEqual(c1.get("credential_ref"), "")

    def test_kaggle_partner_probe_isolates_c1_oauth_home(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            partner = root / "partner"
            partner.mkdir()
            (partner / "kaggle.json").write_text(
                '{"username":"partner-user","key":"redacted-test-token"}',
                encoding="utf-8",
            )
            calls = []

            def fake_cli(args, *, timeout, env=None):
                calls.append((args, env))
                if args[1:3] == ["config", "view"]:
                    return {"ok": True, "stdout": "- username: partner-user\n- auth_method: LEGACY", "stderr": ""}
                return {"ok": True, "stdout": "[]", "stderr": ""}

            inherited = {
                "KAGGLE_API_TOKEN": "must-not-leak",
                "KAGGLE_USERNAME": "greenylife",
                "KAGGLE_KEY": "must-not-leak",
            }
            with patch("raios.resource_fabric.live._partner_candidate_dirs", return_value=[partner]), \
                 patch("raios.resource_fabric.live.C1_KAGGLE_DIR", root / "c1"), \
                 patch("raios.resource_fabric.live._run_cli", side_effect=fake_cli), \
                 patch.dict(os.environ, inherited, clear=False):
                result = _probe_kaggle_partner(live=True)

            self.assertEqual(result["status"], "REACHABLE")
            self.assertEqual(result["IDENTITY_PROOF"], "partner-user")
            self.assertTrue(result["distinct_from_c1"])
            for _, env in calls:
                self.assertEqual(env["KAGGLE_CONFIG_DIR"], str(partner))
                self.assertEqual(env["HOME"], str(partner / ".isolated-home"))
                self.assertEqual(env["USERPROFILE"], str(partner / ".isolated-home"))
                self.assertNotIn("KAGGLE_API_TOKEN", env)
                self.assertNotIn("KAGGLE_USERNAME", env)
                self.assertNotIn("KAGGLE_KEY", env)

    def test_kaggle_accounts_isolated_on_overlay(self):
        world = collect_world()
        state = _state(
            KAGGLE_C1={
                "account_id": "KAGGLE_C1",
                "status": "REACHABLE",
                "gpu_quota": {"limit": 30, "used": 1.06, "remaining": 28.94, "reset_at": "2026-08-29T00:00:00"},
                "tpu_quota": {"limit": 20, "used": 0, "remaining": 20, "reset_at": "2026-08-29T00:00:00"},
                "dataset_used_bytes": 7301477,
                "account_eligible_gpu": True,
                "active_session_gpu": False,
            }
        )
        apply_live_overlay(world, state)
        c1 = next(a for a in world["accounts"] if a["account_id"] == "KAGGLE_C1")
        partner = next(a for a in world["accounts"] if a["account_id"] == "KAGGLE_PARTNER")
        self.assertEqual(c1["status"], "REACHABLE")
        self.assertEqual(partner["status"], "AUTH_REQUIRED")
        q1 = next(q for q in world["quotas"] if q["account_id"] == "KAGGLE_C1" and q["resource_type"] == "gpu_hours")
        q2 = next(q for q in world["quotas"] if q["account_id"] == "KAGGLE_PARTNER")
        self.assertEqual(q1["remaining"], 28.94)
        self.assertEqual(q2["remaining"], UNKNOWN)
        self.assertNotEqual(q1["quota_id"], q2["quota_id"])

    def test_catalog_gpu_not_claimed_as_live_sku(self):
        world = collect_world()
        apply_live_overlay(world, _state(KAGGLE_C1={"account_id": "KAGGLE_C1", "status": "REACHABLE", "gpu_quota": {"limit": 30, "used": 1, "remaining": 29, "reset_at": "t"}, "account_eligible_gpu": True, "active_session_gpu": False}))
        catalog = [g for g in world["accelerators"] if g.get("gpu_class") == "CATALOG_GPU" and g.get("account_id") == "KAGGLE_C1"]
        live = [g for g in world["accelerators"] if g.get("gpu_class") == "ACCOUNT_ELIGIBLE_GPU"]
        self.assertTrue(catalog)
        self.assertTrue(live)
        self.assertTrue(all(g.get("observation_kind") == "CATALOG" for g in catalog))
        self.assertNotEqual(catalog[0].get("resource_id"), live[0].get("resource_id"))

    def test_unknown_capacity_not_zeroed(self):
        world = collect_world()
        before = count_unknown_fields(world)
        apply_live_overlay(world, _state())
        oracle_store = next(s for s in world["storage"] if s["storage_id"] == "ORACLE_01:object_storage")
        self.assertEqual(oracle_store["capacity_total_gb"], UNKNOWN)
        self.assertNotEqual(oracle_store["capacity_total_gb"], 0)
        self.assertGreaterEqual(before["UNKNOWN_STORAGE_FIELDS"], 1)

    def test_auth_required_ne_absent(self):
        world = collect_world()
        apply_live_overlay(world, _state())
        oracle = next(a for a in world["accounts"] if a["account_id"] == "ORACLE_01")
        self.assertEqual(oracle["status"], "AUTH_REQUIRED")
        self.assertTrue(oracle["AUTH_REQUIRED_NE_ABSENT"])
        self.assertNotEqual(oracle["status"], "ABSENT")

    def test_secret_redaction_on_auth_rows(self):
        rows = discover_auth()
        assert_no_secrets(rows)
        for row in rows:
            self.assertFalse(str(row.get("credential_ref", "")).lower().startswith("token="))

    def test_provider_failure_isolation(self):
        def boom():
            raise RuntimeError("kaggle-down")

        with patch("raios.resource_fabric.live._probe_kaggle_c1", side_effect=boom):
            with patch("raios.resource_fabric.live._probe_lightning", return_value={"account_id": "LIGHTNING_01", "status": "REACHABLE", "credits_remaining": 30}):
                with patch("raios.resource_fabric.live._probe_modal_presence", return_value={"account_id": "MODAL_01", "status": "PARTIAL"}):
                    with patch("raios.resource_fabric.live._probe_local", return_value={"account_id": "LOCAL_AG", "status": "REACHABLE", "c5": "SUCCESS"}):
                        with patch("raios.resource_fabric.live._probe_9router", return_value={"RESOURCE_AUTHORITY": False, "health": "ok"}):
                            state = run_live_probes(live=True)
        self.assertEqual(state["probes"]["KAGGLE_C1"]["status"], "UNAVAILABLE")
        self.assertTrue(state["probes"]["KAGGLE_C1"]["PROBE_FAIL_NE_ABSENT"])
        self.assertEqual(state["probes"]["LIGHTNING_01"]["status"], "REACHABLE")
        self.assertNotEqual(state["probes"]["KAGGLE_C1"]["status"], "ABSENT")

    def test_quota_observation_account_scoped(self):
        world = collect_world()
        apply_live_overlay(
            world,
            _state(
                KAGGLE_C1={
                    "status": "REACHABLE",
                    "gpu_quota": {"limit": 30, "used": 1, "remaining": 29, "reset_at": "2026-08-29T00:00:00"},
                    "tpu_quota": {"limit": 20, "used": 0, "remaining": 20, "reset_at": "2026-08-29T00:00:00"},
                    "account_eligible_gpu": True,
                    "active_session_gpu": False,
                }
            ),
        )
        for q in world["quotas"]:
            if q["account_id"] == "KAGGLE_C1" and q["resource_type"] == "gpu_hours":
                self.assertEqual(q["remaining"], 29)
            if q["account_id"] == "KAGGLE_PARTNER":
                self.assertEqual(q["remaining"], UNKNOWN)

    def test_pricing_time_scoped(self):
        world = collect_world()
        apply_live_overlay(world, _state())
        modal_prices = [p for p in world["pricing"] if p["account_id"] == "MODAL_01" and p["price_kind"] == "CATALOG_PRICE"]
        self.assertTrue(modal_prices)
        self.assertTrue(all(p.get("observed_at") for p in modal_prices))
        self.assertTrue(all(p.get("source") for p in modal_prices))

    def test_credit_expiry_and_credit_ne_cash(self):
        world = collect_world()
        apply_live_overlay(
            world,
            _state(LIGHTNING_01={"status": "REACHABLE", "credits_remaining": 30, "storage_used_bytes": 62589, "free_storage_bytes": 10737418240, "studio_count": 2}),
        )
        cred = next(c for c in world["credits"] if c["account_id"] == "LIGHTNING_01")
        self.assertEqual(cred["remaining_value"], 30)
        self.assertTrue(cred["CREDIT_NE_CASH"])
        self.assertIn("CREDIT_NE_CASH", cred["restrictions"])

    def test_no_paid_activation_flags(self):
        world = collect_world()
        state = _state()
        apply_live_overlay(world, state)
        self.assertFalse(state["PAID_RESOURCE_CREATED"])
        plan = recompose_v2(world)
        self.assertFalse(plan["PAID_RESOURCE_ACTIVATED"])
        self.assertFalse(plan["NINEROUTER_IS_RESOURCE_AUTHORITY"])

    def test_no_model_migration(self):
        world = collect_world()
        state = _state(LOCAL_AG={"status": "REACHABLE", "ram_total_gb": 7.8, "c5": "SUCCESS", "ollama": "SUCCESS"})
        apply_live_overlay(world, state)
        fit = model_hosting_fit(world, state)
        qwen = qwen35b_placement(world, state, fit)
        self.assertFalse(qwen["MODEL_WEIGHT_TRANSFER_EXECUTED"])
        self.assertFalse(qwen["LOCAL_MODEL_DELETE_EXECUTED"])
        self.assertTrue(qwen["LOCAL_RUN_FORBIDDEN"])
        self.assertFalse(fit["LOCAL_AG"]["CAN_STORE_MODEL_WEIGHTS"])

    def test_9router_not_resource_authority(self):
        world = collect_world()
        apply_live_overlay(world, _state())
        gw = (world.get("gateways") or [{}])[0]
        self.assertEqual(gw["provider_type"], "MODEL_ROUTING_GATEWAY")
        self.assertEqual(gw["endpoint"], "LOCAL_ONLY")
        self.assertFalse(gw["RESOURCE_AUTHORITY"])

    def test_bind_without_network_uses_presence_only(self):
        world = collect_world()
        bind_live_accounts(world, live=False)
        st = status_view(world)
        self.assertIn("accounts_auth_required", st)
        self.assertTrue(st["UNOBSERVED_NE_ABSENT"])

    def test_cli_required_commands(self):
        for cmd in ("status", "accounts", "gpu", "storage", "services", "quota", "credits", "pricing", "models", "recomposition"):
            code = main([cmd, "--no-probe"])
            self.assertEqual(code, 0, cmd)


if __name__ == "__main__":
    unittest.main()
