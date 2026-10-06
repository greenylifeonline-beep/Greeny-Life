"""The local MCP launcher may record identity only for the process it just started."""

from pathlib import Path

ENSURE = Path(__file__).resolve().parents[2] / "scripts" / "ai-os" / "raios_mcp_local_ensure.ps1"


def test_launch_record_is_not_a_retroactive_adoption():
    text = ENSURE.read_text(encoding="utf-8")
    assert "CIM_ADOPTED" not in text
    assert "LEGACY_HEALTH_ADOPTED" not in text
    assert "STARTED_CANONICAL" not in text
    assert "MCP_LIVE_BUT_UNOWNED" in text
    assert "C1_EXPLICIT_QUARANTINE_RETIREMENT" in text
    assert "ownership_proven = $false" in text
    assert "raios.universal-mcp-launch.v1" in text
    assert 'observation = "PROCESS_START"' in text
    for field in (
        "started_at",
        "command_line",
        "c5_generation",
        "launch_source_sha256",
        "launcher",
    ):
        assert field in text


def test_existing_listener_is_not_rewritten_before_the_identity_gate():
    text = ENSURE.read_text(encoding="utf-8")
    gate = text.index("Test-RaiosLaunchIdentity $Info $OwningPid $Port")
    start = text.index("Start-Process -FilePath $Python")
    write = text.index("Write-RaiosLaunchIdentity -Process $Process")
    assert gate < start < write
    assert "Write-RaiosOwnerManifest" not in text
    assert "MCP_LISTENER_PID_NOT_LAUNCH_PID" not in text
    assert "PromoteOwnedGeneration" in text
    assert "CONTRACT_DRIFT" in text
    assert "LOCAL_MCP_PROMOTE_OWNED" in text
