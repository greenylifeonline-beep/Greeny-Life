"""PR3b: nested safety.* flags are authoritative.

Historical false-positive: CURRENT_GOAL_OVERWRITE_DETECTED fired because
``exec_receipt.get("current_goal_overwritten") is False`` saw a missing
top-level key (None is False). The receipt stores the flag at
safety.authoritative_current_goal_overwritten.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "_raios-authoritative-certifier" / "src"
sys.path.insert(0, str(SRC))

from raios_authoritative_certifier import (  # noqa: E402
    evaluate_execution_safety,
)

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "true-open-execution-receipt.safety.json"
)


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_historical_top_level_lookup_is_the_false_positive():
    receipt = load_fixture()
    # Original gate: require(receipt.get("current_goal_overwritten") is False, ...)
    # Missing key → None is False → require fails as overwrite.
    condition = receipt.get("current_goal_overwritten") is False
    assert condition is False
    with pytest.raises(RuntimeError, match="CURRENT_GOAL_OVERWRITE_DETECTED"):
        if not condition:
            raise RuntimeError("CURRENT_GOAL_OVERWRITE_DETECTED")


def test_nested_safety_false_flags_pass():
    flags = evaluate_execution_safety(load_fixture())
    assert flags == {
        "stale_locks_reactivated": False,
        "authoritative_current_goal_overwritten": False,
        "authoritative_active_wave_overwritten": False,
        "legacy_provider_binding_restored": False,
    }


def test_explicit_current_goal_overwrite_still_fails():
    receipt = load_fixture()
    receipt["safety"]["authoritative_current_goal_overwritten"] = True
    with pytest.raises(RuntimeError, match="CURRENT_GOAL_OVERWRITE_DETECTED"):
        evaluate_execution_safety(receipt)


def test_explicit_active_wave_overwrite_still_fails():
    receipt = load_fixture()
    receipt["safety"]["authoritative_active_wave_overwritten"] = True
    with pytest.raises(RuntimeError, match="ACTIVE_WAVE_OVERWRITE_DETECTED"):
        evaluate_execution_safety(receipt)


def test_explicit_legacy_binding_restore_still_fails():
    receipt = load_fixture()
    receipt["safety"]["legacy_provider_binding_restored"] = True
    with pytest.raises(RuntimeError, match="LEGACY_PROVIDER_BINDING_RESTORED"):
        evaluate_execution_safety(receipt)


def test_explicit_stale_lock_reactivation_still_fails():
    receipt = load_fixture()
    receipt["safety"]["stale_locks_reactivated"] = True
    with pytest.raises(RuntimeError, match="STALE_LOCK_REACTIVATION_DETECTED"):
        evaluate_execution_safety(receipt)


def test_missing_nested_key_is_schema_not_overwrite():
    receipt = load_fixture()
    del receipt["safety"]["authoritative_current_goal_overwritten"]
    with pytest.raises(RuntimeError, match="SAFETY_SCHEMA_PATH_MISSING"):
        evaluate_execution_safety(receipt)


def test_missing_safety_block_is_schema_not_overwrite():
    receipt = load_fixture()
    del receipt["safety"]
    with pytest.raises(RuntimeError, match="SAFETY_BLOCK_MISSING"):
        evaluate_execution_safety(receipt)


def test_top_level_false_cannot_mask_nested_true():
    receipt = load_fixture()
    receipt["current_goal_overwritten"] = False
    receipt["active_wave_overwritten"] = False
    receipt["legacy_provider_binding_restored"] = False
    receipt["safety"]["authoritative_current_goal_overwritten"] = True
    with pytest.raises(RuntimeError, match="CURRENT_GOAL_OVERWRITE_DETECTED"):
        evaluate_execution_safety(receipt)


def test_top_level_true_cannot_override_nested_false():
    receipt = load_fixture()
    receipt["current_goal_overwritten"] = True
    receipt["active_wave_overwritten"] = True
    receipt["legacy_provider_binding_restored"] = True
    flags = evaluate_execution_safety(receipt)
    assert flags["authoritative_current_goal_overwritten"] is False


def test_fixture_matches_live_receipt_safety_contract():
    receipt = load_fixture()
    safety = receipt["safety"]
    assert "current_goal_overwritten" not in receipt
    assert "current_goal_overwritten" not in safety
    assert "active_wave_overwritten" not in safety
    assert safety["authoritative_current_goal_overwritten"] is False
    assert safety["authoritative_active_wave_overwritten"] is False
