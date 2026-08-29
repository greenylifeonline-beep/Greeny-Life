from raios.factory_fabric.model_ecology import classify_records


def test_model_estate_separates_weight_runtime_and_assimilation():
    records = [
        {"name": "qwen3:0.6b", "size_bytes": 522 * 1024**2},
        {"name": "qwen3-embedding:0.6b", "size_bytes": 639 * 1024**2},
        {"name": "qwen3.6:35b-a3b", "size_bytes": 23 * 1024**3},
    ]
    rows = {
        row["model_id"]: row
        for row in classify_records(records, runtime_model="qwen3:0.6b")
    }

    assert rows["qwen3:0.6b"]["currently_bound"] is True
    assert rows["qwen3:0.6b"]["local_execution_class"] == "LOCAL_SAFE"
    assert rows["qwen3-embedding:0.6b"]["kind"] == "EMBEDDING"
    assert rows["qwen3.6:35b-a3b"]["local_execution_class"] == "REMOTE_EXECUTION_REQUIRED"
    assert rows["qwen3.6:35b-a3b"]["remote_migration_required"] is True
    assert rows["qwen3.6:35b-a3b"]["source_removable"] is False
    assert all(row["weight_present"] for row in rows.values())
    assert all(
        row["assimilation_state"] == "WEIGHT_PRESENT_NOT_ASSIMILATED"
        for row in rows.values()
    )
