from raios.neuro_lingua.toc import PASTE_CLAIMS, hunt


def test_toc_uses_canonical_not_invented_minutes():
    rec = hunt()
    assert rec["ok"] is True
    assert rec["simulated"] is False
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert rec["shipments"] == 30
    assert rec["clearances"] == 30
    assert rec["europe_origin_count"] == 0
    assert rec["gulf_warehouse_count"] == 0
    assert rec["duration_fields"] == []
    assert rec["origins"].get("Cairo, Egypt") == 30
    assert rec["wip"]["clearance_uncleared"] == 18
    assert rec["wip"]["in_transit"] == 10
    assert rec["steps"]["identify"]["physical_wip_leader"] == "clearance_uncleared"
    assert rec["steps"]["elevate"]["reason"] == "ELEVATE_REQUIRES_C1"
    assert rec["steps"]["elevate"]["allowed"] is False
    assert rec["steps"]["exploit"]["documents_already_present"] is True
    assert rec["steps"]["subordinate"]["uae_next_route"] is False
    verdicts = {row["verdict"] for row in PASTE_CLAIMS}
    assert "FALSIFIED_EUROPE_ORIGIN_ABSENT" in verdicts
    assert "FALSIFIED_NO_GULF_WAREHOUSE" in verdicts
    assert "FALSIFIED_INVENTED_IMPROVEMENT" in verdicts
    cairo = [row for row in rec["warehouse_load"] if row["id"] == "WH-001"][0]
    assert cairo["over_capacity"] is True
