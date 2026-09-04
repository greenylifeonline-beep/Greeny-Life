from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts" / "ai-os" / "raios_c5_maintenance_guard.py"


def load_guard():
    spec = importlib.util.spec_from_file_location("raios_c5_maintenance_guard_test", GUARD)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_c5_maintenance_guard_passes_current_canonical_source():
    guard = load_guard()
    assert guard.maintenance_issues(ROOT) == []
    snap = guard.snapshot()
    assert snap["ok"] is True
    assert snap["wal_written"] is False


def test_c5_maintenance_guard_detects_known_regression(tmp_path):
    guard = load_guard()
    root = tmp_path / "repo"
    (root / ".ai-os" / "mcp").mkdir(parents=True)
    (root / ".ai-os" / "mcp" / "C5-MAINTENANCE-LAWS.json").write_text("{}", encoding="utf-8")
    for rel in [
        "src/raios/manager/live_manager.py", "src/raios/command_center/app.py",
        "src/raios/command_center/message_worker.py", "scripts/runtime/Deploy-RAIOS-C5.ps1",
        "scripts/ai-os/raios_change_gate.py", "src/raios/council_ops/operations.py",
        "src/raios/command_center/actor_routing.py", "src/raios/c5_gateway/ollama_client.py",
        "src/raios/ai_gateway/router.py",
    ]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("REGRESSION", encoding="utf-8")
    issues = guard.maintenance_issues(root)
    assert issues
    assert any(row["id"].endswith("_REGRESSION") for row in issues)
