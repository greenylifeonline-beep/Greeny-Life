from pathlib import Path

MAINTAIN = Path(__file__).resolve().parents[2] / "scripts" / "runtime" / "Maintain-RAIOS-Online.ps1"


def test_operational_degraded_is_not_a_c5_deploy_trigger():
    text = MAINTAIN.read_text(encoding="utf-8")
    assert "OLLAMA_INVENTORY_PROBE_TIMEOUT" in text
    assert '$health.status -eq "DEGRADED"' in text
    assert "model_fabric_ready=false stays visible" in text
    assert "New-C5-Deployer" not in text
    assert "LOCK-W08-ENGINE" not in text
    assert "HttpWebRequest" in text
    assert "System32\\curl.exe" not in text
    assert "Poll HasExited" in text
    assert ".WaitForExit(" not in text


def test_runtime_authority_and_recovery_contracts_are_single_owner_and_bounded():
    root = MAINTAIN.parents[1]
    maintain = MAINTAIN.read_text(encoding="utf-8")
    service = (root / "RAIOS.C5.ServiceHost.cs").read_text(encoding="utf-8")
    native = (root / "Start-RAIOS-Native-MCP-System.ps1").read_text(encoding="utf-8")
    user_lane = (root / "c5-service" / "Invoke-RAIOS-C5-UserLane.ps1").read_text(encoding="utf-8")
    manager = (MAINTAIN.parents[2] / "src" / "raios" / "manager" / "live_manager.py").read_text(encoding="utf-8")

    assert "COGNITIVE_PRIORITY0_CHECK" in maintain
    assert "Get-FreshManagerHeartbeat" in maintain
    assert "[IO.Directory]::EnumerateFiles" in maintain
    assert "NATS_LOG_RETENTION_DEFERRED_BOUNDED" in maintain
    assert "DCR_OWNED_PID_REFRESH" in service
    assert 'native_tunnel_owned_by_service' in service
    assert 'control_authority"] = "RAIOS-C5-SCM"' in service
    assert "-and -not $childAlive" in native
    assert "INTERACTIVE_SESSION_ADAPTER" in user_lane
    assert "can_start_dcr_supervisor" in user_lane
    assert "can_start_native_tunnel" in user_lane
    assert "os.scandir(HEARTBEAT.parent)" in manager
    assert "len(versions) >= 32" in manager