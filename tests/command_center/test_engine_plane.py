from pathlib import Path
from raios.command_center.engine_plane import snapshot


def test_engine_plane_reuses_inventory_and_forbids_second_merge_stack(tmp_path):
    repo = tmp_path / "Greeny-Life"
    reports = repo / ".ai-os" / "reports"
    reports.mkdir(parents=True)
    (reports / "RAIOS-MERGE-ENGINES-INVENTORY.json").write_text(
        '{"live_ids":["mind-fill","kae"],"engines":['
        '{"id":"mind-fill","name_ar":"حقن العقل","status":"LIVE","path":"scripts/ai-os/raios_c5_mind_fill.py","execute_here":true},'
        '{"id":"kae","name_ar":"توريق","status":"LIVE","path":"src/raios/neuro_lingua/kae.py","execute_here":true},'
        '{"id":"brain-discover-merge","name_ar":"brain","status":"DO_NOT_RUN","path":"brain.py","execute_here":false}'
        "]}",
        encoding="utf-8",
    )
    (repo / "scripts/ai-os").mkdir(parents=True)
    (repo / "scripts/ai-os/raios_c5_mind_fill.py").write_text("#", encoding="utf-8")
    (repo / "src/raios/neuro_lingua").mkdir(parents=True)
    (repo / "src/raios/neuro_lingua/kae.py").write_text("#", encoding="utf-8")
    (repo / "brain.py").write_text("#", encoding="utf-8")
    out = snapshot(repo, home=tmp_path)
    assert out["schema"] == "raios.live-engine-plane.v1"
    assert out["automatic_merge"] is False
    assert out["langchain"] is False
    assert out["second_search_bus"] is False
    assert out["merged_now"] is False
    ids = {r["id"]: r for r in out["engines"]}
    assert ids["mind-fill"]["live_keeper"] is True and ids["mind-fill"]["path_exists"] is True
    assert ids["brain-discover-merge"]["live_keeper"] is False
    assert "datasketch" in {c["id"] for c in out["oss_upgrade_candidates"]}
    assert "RapidFuzz" in out["oss_in_use"]
