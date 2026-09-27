from pathlib import Path

from raios.command_center.system_surface import copy_estate_projection, factory_estate_projection

REPO = Path(__file__).resolve().parents[2]


def test_copy_estate_classifies_existing_inventory_without_delete_or_merge():
    out = copy_estate_projection(REPO)
    assert out["schema"] == "raios.copy-estate.v1"
    assert out["SAFE_TO_REMOVE_SOURCE"] is False
    assert out["cutover"] is False
    assert out["git_scan"] is False
    assert out["fold_tip_checked_out"] is False
    assert out["merge_executed"] is False
    assert out["delete_executed"] is False
    assert out["second_ccee_runtime"] is False
    assert out["second_mcp"] is False
    assert out["false_pass_library"] == "src/raios/learning_evidence/false_pass.py"
    assert out["unique_value_unwired_count"] >= 1
    assert "src/raios/factory_fabric/model_ecology.py" in out["models_merged_via"]
    assert "ONE_CANONICAL_TREE" in out["law"]
    assert out["copies_total"] >= 1
    assert out["copy_pass2"]["UNIQUE_VALUE_CANDIDATE"] == 1
    assert out["classification_authority"].endswith("pass2_primary")
    assert out["row_class_is_pass1_auto"] is True
    assert sum(out["symbol_counts"].values()) >= 100
    wired_ids = {row["id"] for row in out["capabilities_wired"]}
    assert {"SYM-001", "SYM-002", "SYM-003", "SYM-041"} <= wired_ids
    assert all(row["canonical_location"].endswith("false_pass.py") for row in out["capabilities_wired"])
    assert all(row["SAFE_TO_REMOVE_SOURCE"] is False for row in out["copies"])
    assert (REPO / "src/raios/learning_evidence/false_pass.py").is_file()


def test_factory_estate_attaches_copy_estate(tmp_path):
    estate = factory_estate_projection(tmp_path)
    assert estate["copy_estate"]["SAFE_TO_REMOVE_SOURCE"] is False
    assert estate["copy_estate"]["cutover"] is False
    live = factory_estate_projection(REPO)
    assert live["copy_estate"]["copies_total"] >= 1
    assert live["copy_estate"]["schema"] == "raios.copy-estate.v1"
