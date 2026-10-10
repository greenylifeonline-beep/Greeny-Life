from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))

from raios_mcp.gateway import read_generation_handoff  # noqa: E402

ENSURE = ROOT / "scripts" / "ai-os" / "raios_mcp_local_ensure.ps1"
SERVER = ROOT / "scripts" / "ai-os" / "raios_mcp" / "server.py"
GATEWAY = ROOT / "scripts" / "ai-os" / "raios_mcp" / "gateway.py"


def _projection(profile: Path, *, active_pid: int = 111) -> Path:
    path = profile / ".raios" / "runtime" / "mcp" / "generation-handoff.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "raios.mcp-generation-handoff.v1",
                "observed_at": "2026-10-10T03:00:00+00:00",
                "authority": "RAIOS-C5-SCM",
                "canonical_head": "a" * 40,
                "transition_reason": "REJECT_SUPERSEDED_GENERATION",
                "previous_pid": 90,
                "previous_generation_id": "old",
                "previous_state": "RETIRED",
                "candidate_pid": 100,
                "candidate_generation_id": "candidate",
                "candidate_state": "SUPERSEDED",
                "active_pid": active_pid,
                "active_generation_id": "active",
                "active_state": "ACTIVE",
                "active_listener_count": 1,
                "active_listener_match": True,
                "duplicate_mcp": False,
                "orphan_generation_count": 0,
                "orphan_pids": [],
                "owner_head_match": True,
                "service_generation": "svc",
                "service_generation_match": True,
                "handoff_complete": True,
                "singleton_verdict": "PASS",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_generation_handoff_explains_lineage_without_pid_guessing(tmp_path):
    profile = tmp_path / "profile"
    _projection(profile, active_pid=111)
    view = read_generation_handoff(profile=profile, current_pid=111)

    assert view["status"] == "ACTIVE"
    assert view["handoff_complete"] is True
    assert view["previous_pid"] == 90
    assert view["previous_state"] == "RETIRED"
    assert view["candidate_pid"] == 100
    assert view["candidate_state"] == "SUPERSEDED"
    assert view["active_pid"] == 111
    assert view["active_state"] == "ACTIVE"
    assert view["active_listener_count"] == 1
    assert view["duplicate_mcp"] is False
    assert view["orphan_generation_count"] == 0
    assert view["singleton_verdict"] == "PASS"
    assert view["lineage"] == [
        {"role": "PREVIOUS", "pid": 90, "state": "RETIRED"},
        {"role": "CANDIDATE", "pid": 100, "state": "SUPERSEDED"},
        {"role": "ACTIVE", "pid": 111, "state": "ACTIVE"},
    ]
    assert "previous PID 90 is RETIRED" in view["explanation"]
    assert "candidate PID 100 is SUPERSEDED" in view["explanation"]
    assert "active PID 111 is ACTIVE" in view["explanation"]


def test_generation_handoff_fails_closed_when_projection_points_to_other_process(tmp_path):
    profile = tmp_path / "profile"
    _projection(profile, active_pid=111)
    view = read_generation_handoff(profile=profile, current_pid=222)

    assert view["status"] == "STALE_OR_INCOMPLETE"
    assert view["projection_consistent_with_process"] is False
    assert view["recorded_handoff_complete"] is True
    assert view["handoff_complete"] is False


def test_generation_handoff_missing_is_explicit_unknown(tmp_path):
    view = read_generation_handoff(profile=tmp_path / "profile", current_pid=333)

    assert view["status"] == "UNKNOWN"
    assert view["projection_present"] is False
    assert view["handoff_complete"] is False
    assert view["singleton_verdict"] == "UNKNOWN"


def test_ensure_writes_bounded_generation_lifecycle_and_steady_state():
    text = ENSURE.read_text(encoding="utf-8")

    assert 'generation-handoff.json' in text
    assert 'generation-lifecycle.jsonl' in text
    assert 'function Write-RaiosGenerationHandoff' in text
    assert 'function Write-RaiosBoundedLifecycle' in text
    assert '[int]$Limit=128' in text
    assert 'previous_state = $previousState' in text
    assert 'candidate_state = $candidateState' in text
    assert 'active_state = "ACTIVE"' in text
    assert 'orphan_generation_count = $orphanPids.Count' in text
    assert 'handoff_complete = $handoffComplete' in text
    assert 'singleton_verdict =' in text
    assert '"STEADY_STATE_VERIFY"' in text


def test_get_head_and_health_expose_same_generation_verdict():
    gateway = GATEWAY.read_text(encoding="utf-8")
    server = SERVER.read_text(encoding="utf-8")

    assert '"generation_handoff": generation_handoff' in gateway
    assert '"generation_summary": generation_handoff.get("explanation")' in gateway
    assert '"generation_lineage": generation_handoff.get("lineage", [])' in gateway
    assert '"generation_handoff_complete": generation_handoff.get("handoff_complete", False)' in gateway
    assert '"generation_singleton_verdict": generation_handoff.get("singleton_verdict", "UNKNOWN")' in gateway
    assert '"generation_orphan_count": generation_handoff.get("orphan_generation_count")' in gateway
    assert '"generation_duplicate_mcp": generation_handoff.get("duplicate_mcp")' in gateway

    assert '"generation_handoff": generation_handoff' in server
    assert '"generation_handoff_complete": generation_handoff.get("handoff_complete", False)' in server
    assert '"generation_singleton_verdict": generation_handoff.get("singleton_verdict", "UNKNOWN")' in server
    assert '"generation_orphan_count": generation_handoff.get("orphan_generation_count")' in server
    assert '"generation_active_pid": generation_handoff.get("active_pid")' in server


def test_health_duplicate_mcp_is_not_hardcoded_false_anymore():
    text = SERVER.read_text(encoding="utf-8")
    assert '"duplicate_mcp": False' not in text
    assert '"duplicate_mcp": bool(generation_handoff.get("duplicate_mcp") is True)' in text


def test_mcp_ensure_powershell_parses_on_available_windows_shell():
    shell = shutil.which("pwsh") or shutil.which("powershell.exe") or shutil.which("powershell")
    if not shell:
        return
    command = (
        "$tokens=$null;$errors=$null;"
        "[Management.Automation.Language.Parser]::ParseFile("
        "'" + str(ENSURE).replace("'", "''") + "',[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count){$errors|ForEach-Object{Write-Error $_.Message};exit 1};exit 0"
    )
    proc = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
