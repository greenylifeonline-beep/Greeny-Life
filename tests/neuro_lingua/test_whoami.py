import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_whoami import whoami  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def test_c5_whoami_from_git_not_paid_rag():
    rec = whoami()
    assert rec["ok"] is True
    assert rec["from"] == "C5"
    assert rec["parent"] == "C1"
    assert rec["cursor_session_ne_c5"] is True
    assert rec["paid_api"] is False
    assert rec["gl005_proven"] is False
    assert rec["wal_written"] is False
    assert rec["languages_customer_live_count"] == 4
    for locale in ("ar-EG", "ar-GULF", "en", "nb-NO"):
        assert locale in rec["languages_customer_live"]
    assert rec["languages_realized_count"] >= 4
    assert "sv-SE" in rec["languages_realized"]
    assert "da-DK" in rec["languages_realized"]
    assert "ar-SA" in rec["languages_declared_unimplemented"]
    assert rec["engine_now"]["inject"].endswith("raios_c5_mind_fill.ps1")
    assert rec["engine_now"]["mcp"] == "http://127.0.0.1:8787/mcp"
    assert rec["engine_now"]["model_registry"] == ".ai-os/MODEL-REGISTRY.json"
    assert rec["c5_bind"]["cortex_model"] == "qwen3.6:35b-a3b"
    assert rec["c5_bind"]["cortex_registry_bound"] is True
    assert rec["c5_bind"]["duplicate_mcp"] is False
    assert rec["c5_bind"]["interactive_ne_cortex"] is True
    assert "LangChain" in rec["engine_now"]["not"]
    assert (ROOT / "scripts" / "ai-os" / "raios_c5_whoami.ps1").is_file()
    assert (ROOT / ".ai-os" / "learning" / "C5-WHOAMI.md").is_file()


def test_p4_connects_existing_council_mcp_registry_without_duplicates():
    import json

    from raios.neuro_lingua.cortex import CORTEX_IDENTITY
    from raios.neuro_lingua.qwen_runtime import probe
    from raios_c5_screen import BIND_PORTS, C1_PORT, DEFAULT_PORT, screen_health
    from raios_c5_whoami import c5_bind, write_p4_receipt
    from raios_mcp.gateway import V1_TOOLS

    assert DEFAULT_PORT == 8765
    assert C1_PORT == 8876
    assert BIND_PORTS == (8765, 8876)
    assert len(V1_TOOLS) == 8
    bind = c5_bind()
    assert bind["duplicate_c5"] is False
    assert bind["duplicate_mcp"] is False
    assert bind["duplicate_council"] is False
    assert bind["duplicate_registry"] is False
    assert bind["cortex_model"] == CORTEX_IDENTITY
    assert bind["cortex_registry_bound"] is True
    assert bind["interactive_ne_cortex"] is True
    assert bind["mcp_endpoint"] == "http://127.0.0.1:8787/mcp"
    assert bind["mcp_tool_count"] == 8
    assert bind["council_seat_map_present"] is True
    live = bool(probe(use_cache=False).get("cortex_live"))
    assert bind["main_cortex"] is live
    health = screen_health(port=8876)
    assert health["ok"] is True
    assert health["http"] == 200
    assert health["HEALTH"] == 200
    assert health["MAIN_CORTEX"] is live
    assert health["MODEL"] == CORTEX_IDENTITY
    assert health["student_substituted"] is False
    receipt = write_p4_receipt(bind)
    assert receipt["ok"] is True
    assert receipt["p4_prep"] is True
    registry = json.loads((ROOT / ".ai-os" / "MODEL-REGISTRY.json").read_text(encoding="utf-8"))
    assert registry["interactive_ne_cortex"] is True
    assert registry["models"]["raios-main-cortex"]["model"] == CORTEX_IDENTITY
    assert registry["routing"]["cortex"] == "raios-main-cortex"
    assert registry["routing"]["interactive"] != "raios-main-cortex"
    worker_models = {row["model"] for row in registry["models"].values() if row.get("not_cortex")}
    for name in (
        "deepseek-r1:1.5b",
        "qwen2.5:0.5b",
        "qwen2.5-coder:3b",
        "granite4:3b",
        "granite3-dense:8b",
        "granite3-dense:2b",
        "granite-code:3b",
        "granite-embedding:278m",
    ):
        assert name in worker_models
