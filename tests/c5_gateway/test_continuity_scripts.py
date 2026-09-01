from pathlib import Path

ROOT = Path(__file__).parents[2]
RUNTIME = ROOT / "scripts" / "runtime"


def test_c5_environment_is_manifest_driven_and_complete():
    requirements = (ROOT / "requirements-c5.txt").read_text(encoding="utf-8")
    deploy = (RUNTIME / "Deploy-RAIOS-C5.ps1").read_text(encoding="utf-8")
    for name in ("pytest", "pytest-asyncio", "hypothesis", "ddgs", "fastapi", "uvicorn", "pydantic"):
        assert name in requirements
    assert "C5_DEPENDENCY_AUDIT=" in deploy
    assert 'dependency_audit = "PASS"' in deploy
    assert "requirements_sha256" in deploy
    assert '"c5_gateway","search_cortex","neuro_lingua"' in deploy


def test_existing_continuity_task_is_reused_with_periodic_self_healing():
    script = (RUNTIME / "Maintain-RAIOS-Online.ps1").read_text(encoding="utf-8")
    assert '$TaskName = "RAIOS-C5-Permanent"' in script
    assert "Register-ScheduledTask" in script
    assert "RepetitionInterval" in script
    assert "$routerOnline = Test-Tcp 20128" in script
    assert "Invoke-WebRequest -UseBasicParsing -Uri \"http://127.0.0.1:20128/dashboard\"" not in script
    for service in ("C5", "MANAGER", "COMMAND_CENTER", "ROUTER_9", "NATS", "OLLAMA"):
        assert service in script
    assert "auto_canonical_mutation = $false" in script


def test_manager_guard_checks_liveness_not_lock_file_existence():
    script = (RUNTIME / "Ensure-RAIOS-Cognitive-Loop.ps1").read_text(encoding="utf-8")
    assert "loop.manager.alive" in script
    assert "STOP_STALE_MANAGER_PID_" in script
    assert "if (Test-Path $lock)" not in script
