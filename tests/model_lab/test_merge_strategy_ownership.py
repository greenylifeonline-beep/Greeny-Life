from RAIOS.V9.evolution.model_lab.merge_strategy import declarations, owner_for


def test_merge_strategy_ownership_is_single_and_explicit():
    data = declarations()

    assert owner_for("LINEAR") == "LinearStrategy"
    assert owner_for("TIES") == "MergeKitStrategy"
    assert owner_for("SLERP") == "MergeKitStrategy"

    wiring = data["registry_wiring"]
    assert wiring["product_registry"] == "StrategyRegistry.default"
    assert wiring["build_default_registry"] == "StrategyRegistry.default"
    assert wiring["backend_absent"] == "NOT_IMPLEMENTED"
    assert wiring["false_success_forbidden"] is True
    assert wiring["duplicate_product_registry"] is False

    assert data["execution"] == "FORBIDDEN_HERE"
