import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_cloud import ARTIFACTS, gateway_route, refuse_local_model_download, stamp  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORTS = ROOT / ".ai-os" / "reports"


def test_cloud_wave_fail_closed_no_wal_no_pull_no_gl005():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = stamp()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["from"] == "C2"
    assert rec["wave"] == "C5-CLOUD-FIRST-MIGRATION"
    assert rec["wal_written"] is False
    assert rec["wal_moved"] is False
    assert rec["weight_downloaded"] is False
    assert rec["openai"] is False
    assert rec["paid_api"] is False
    assert rec["gl005_proven"] is False
    assert rec["cloud_migration_proven"] is False
    assert rec["remote_work_proven"] is True
    assert rec["stop_new_local_model_downloads"] is True
    assert rec["laptop_is_control_plane"] is True
    assert rec["screen_multilingual"] is True
    assert before == after
    assert [row["name"] for row in rec["artifacts"]] == list(ARTIFACTS)
    for name in ARTIFACTS:
        path = REPORTS / name
        assert path.is_file(), name
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload.get("gl005_proven") is False
    storage = json.loads((REPORTS / "RAIOS-CLOUD-STORAGE-REALITY-AUDIT.json").read_text(encoding="utf-8"))
    assert storage["github_origin"].startswith("https://github.com/")
    assert "x-access-token" not in storage["github_origin"]
    move = json.loads((REPORTS / "RAIOS-CLOUD-MOVE-TRAINING-BOOKS-WAL.json").read_text(encoding="utf-8"))
    assert move["wal"]["moved"] is False
    assert move["wal"]["action"] == "BLOCKED_A15"
    stop = json.loads((REPORTS / "RAIOS-STOP-NEW-LOCAL-MODEL-DOWNLOADS.json").read_text(encoding="utf-8"))
    assert stop["enforced_here"] is True
    remote = json.loads((REPORTS / "RAIOS-REMOTE-WORK-LAPTOP-DISCONNECTED.json").read_text(encoding="utf-8"))
    assert remote["laptop_required_to_run_keepers"] is False
    assert remote["remote_work_while_laptop_client_disconnected"] is True


def test_gateway_forbids_openai_and_refuses_ollama_pull():
    blocked = refuse_local_model_download("ollama pull qwen3.6:35b-a3b")
    assert blocked["allowed"] is False
    assert blocked["stop"] == "STOP_NEW_LOCAL_MODEL_DOWNLOADS"
    openai = gateway_route("gpt-4o")
    assert openai["route"] == "FORBIDDEN"
    assert openai["execute"] is False
    student = gateway_route("qwen2.5:0.5b")
    assert student["route"] in {"LOCAL_OLLAMA", "LOCAL_OLLAMA_DOWN"}


def test_git_remote_userinfo_is_stripped():
    from raios_c5_cloud import strip_userinfo

    assert strip_userinfo("https://github.com/org/repo") == "https://github.com/org/repo"
    assert strip_userinfo("https://x-access-token:example@github.com/org/repo") == "https://github.com/org/repo"
