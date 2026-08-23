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
    assert rec["c5_bind"]["local_winner"] is False
    assert rec["c5_bind"]["model_agnostic"] is True
    assert rec["c5_bind"]["laptop_is_model_host"] is False
    assert rec["c5_bind"]["duplicate_mcp"] is False
    assert rec["c5_bind"]["interactive_ne_cortex"] is True
    assert rec["c5_bind"]["cursor_session_ne_c5"] is True
    assert rec["c5_bind"]["screen_home"] in {"SESSION_TEMP", "CONTROL_PLANE"}
    assert "LangChain" in rec["engine_now"]["not"]
    assert (ROOT / "scripts" / "ai-os" / "raios_c5_whoami.ps1").is_file()
    assert (ROOT / ".ai-os" / "learning" / "C5-WHOAMI.md").is_file()


def test_p4_connects_existing_council_mcp_registry_without_duplicates():
    import json

    from raios.neuro_lingua.cortex import CORTEX_IDENTITY, ROLE_KEYS, resolve_role
    from raios.neuro_lingua.qwen_runtime import probe
    from raios_c5_screen import BIND_PORTS, C1_PORT, DEFAULT_PORT, screen_health
    from raios_c5_whoami import c5_bind, write_p4_receipt, write_roles_receipt
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
    assert bind["cortex_local_winner"] is False
    assert bind["winners_are_final"] is False
    assert bind["model_agnostic"] is True
    assert bind["laptop_is_model_host"] is False
    assert bind["laptop_role"] == "CONTROL_PLANE_ONLY"
    assert bind["local_ollama_is"] == "DEV_FALLBACK"
    assert bind["source_patch_required"] is False
    assert bind["transport"] == "openai-compatible"
    assert bind["endpoint_kinds"] == [
        "LOCAL_DEV",
        "KAGGLE_WORKER",
        "LIGHTNING_WORKER",
        "HF_ENDPOINT",
        "FRONTIER_PROVIDER",
    ]
    assert "configured" in bind["endpoint"]
    assert bind["arenas"] == ["ROUTER", "CORTEX", "CODE", "REASONING", "EMBEDDING", "RERANKER"]
    assert set(ROLE_KEYS).issubset(bind["roles"])
    assert bind["roles"]["CORTEX_MODEL"]["local_winner"] is False
    assert bind["roles"]["CORTEX_MODEL"]["reason"] == "MEMORY_ALLOCATION_FAILED"
    assert bind["roles"]["CODE_MODEL"]["bridge"] == "opencode"
    assert bind["bridges"]["control"]["id"] == "raios-mcp"
    assert bind["bridges"]["execution"]["id"] == "opencode"
    assert bind["bridges"]["execution"]["install"] is False
    assert bind["bridges"]["execution"]["duplicate_mcp"] is False
    assert bind["mcp_endpoint"] == "http://127.0.0.1:8787/mcp"
    assert bind["mcp_tool_count"] == 8
    assert bind["cursor_session_ne_c5"] is True
    assert bind["screen_home"] in {"SESSION_TEMP", "CONTROL_PLANE"}
    assert bind["duplicate_c5"] is False
    assert bind["council_seat_map_present"] is True
    live = bool(probe(use_cache=False).get("cortex_live"))
    assert bind["main_cortex"] is live
    health = screen_health(port=8876)
    assert health["ok"] is True
    assert health["http"] == 200
    assert health["HEALTH"] == 200
    assert health["MAIN_CORTEX"] is live
    assert health["MODEL"] == CORTEX_IDENTITY
    assert health["LOCAL_WINNER"] is False
    assert health["ROLE"] == "CORTEX_MODEL"
    assert health["LAPTOP_IS_MODEL_HOST"] is False
    assert health["student_substituted"] is False
    receipt = write_p4_receipt(bind)
    assert receipt["ok"] is True
    assert receipt["p4_prep"] is True
    registry = json.loads((ROOT / ".ai-os" / "MODEL-REGISTRY.json").read_text(encoding="utf-8"))
    assert registry["interactive_ne_cortex"] is True
    assert registry["winners_are_final"] is False
    assert registry["local_winner"] is None
    assert registry["laptop_is_model_host"] is False
    assert registry["laptop_role"] == "CONTROL_PLANE_ONLY"
    assert registry["source_patch_required_to_switch_provider"] is False
    assert set(registry["provider_endpoints"]) == {
        "LOCAL_DEV",
        "KAGGLE_WORKER",
        "LIGHTNING_WORKER",
        "HF_ENDPOINT",
        "FRONTIER_PROVIDER",
    }
    assert registry["transport"]["protocol"] == "openai-compatible"
    assert registry["models"]["raios-main-cortex"]["model"] == CORTEX_IDENTITY
    assert registry["models"]["raios-main-cortex"]["local_winner"] is False
    assert registry["models"]["raios-main-cortex"]["availability"] == "MEMORY_ALLOCATION_FAILED"
    assert registry["models"]["raios-main-cortex"]["endpoint"] is None
    assert registry["models"]["raios-main-cortex"]["base_url_env"] == "RAIOS_CORTEX_BASE_URL"
    assert registry["routing"]["cortex"] == "raios-main-cortex"
    assert registry["routing"]["interactive"] != "raios-main-cortex"
    assert registry["roles"]["CORTEX_MODEL"]["local_winner"] is False
    assert registry["bridges"]["control"]["endpoint"] == "http://127.0.0.1:8787/mcp"
    assert registry["bridges"]["execution"]["id"] == "opencode"
    assert registry["bridges"]["execution"]["install"] is False
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
    cortex_role = resolve_role("CORTEX_MODEL")
    assert cortex_role["role"] == "CORTEX_MODEL"
    assert cortex_role["local_winner"] is False
    assert cortex_role["model"] == CORTEX_IDENTITY
    assert cortex_role["winner_final"] is False
    roles_rec = write_roles_receipt(bind)
    assert roles_rec["ok"] is True
    assert roles_rec["code_bridge"] == "opencode"
    assert roles_rec["cortex_reason"] == "MEMORY_ALLOCATION_FAILED"
    assert roles_rec["laptop_is_model_host"] is False
    assert roles_rec["transport"] == "openai-compatible"
    assert roles_rec["bridges"]["execution"]["install"] is False


def test_screen_home_is_control_plane_not_cursor_session():
    from raios_c5_whoami import control_plane_runtime, whoami, write_screen_home_receipt

    whoami()

    home = control_plane_runtime()
    assert home["cursor_session_ne_c5"] is True
    assert home["duplicate_c5"] is False
    assert home["gl005_proven"] is False
    assert "raios_c5_screen.ps1 -Install" in home["install_windows"]
    assert "raios_c5_screen.ps1 -Ensure" in home["ensure_windows"]
    assert home["ensure_linux"].endswith("raios_c5_screen_ensure.sh")
    if home["this_host_is_cursor_cloud"]:
        assert home["screen_home"] == "SESSION_TEMP"
        assert home["durable"] is False
    else:
        assert home["screen_home"] == "CONTROL_PLANE"
    rec = write_screen_home_receipt()
    assert rec["ok"] is True
    assert rec["cursor_session_ne_c5"] is True
    assert rec["duplicate_c5"] is False
    assert rec["new_mcp_tools"] is False
    assert rec["wal_written"] is False
    assert rec["gl005_proven"] is False
    assert rec["screen_home"] == home["screen_home"]
    assert (ROOT / ".ai-os" / "receipts" / "c5-p4" / "SCREEN-HOME.json").is_file()
    md = (ROOT / ".ai-os" / "learning" / "C5-WHOAMI.md").read_text(encoding="utf-8")
    assert "SCREEN_HOME" in md
    assert "CURSOR_SESSION_NE_C5" in md
