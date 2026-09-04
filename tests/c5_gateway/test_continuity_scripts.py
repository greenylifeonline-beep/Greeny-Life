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
    assert "$PythonWindowless" in deploy
    assert "Start-Process -FilePath $PythonWindowless" in deploy


def test_existing_continuity_task_is_reused_with_periodic_self_healing():
    script = (RUNTIME / "Maintain-RAIOS-Online.ps1").read_text(encoding="utf-8")
    launcher = (RUNTIME / "Run-RAIOS-Continuity-Hidden.vbs").read_text(encoding="utf-8")
    assert '$TaskName = "RAIOS-C5-Permanent"' in script
    assert "Register-ScheduledTask" in script
    assert "RepetitionInterval" in script
    assert "$env:SystemRoot\\System32\\wscript.exe" in script
    assert "Run-RAIOS-Continuity-Hidden.vbs" in script
    assert "-NonInteractive -WindowStyle Hidden" in launcher
    assert "shell.Run(command, 0, True)" in launcher
    assert "New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -Hidden" in script
    assert "$routerOnline = Test-Tcp 20128" in script
    assert "node_modules\\9router\\cli.js" in script
    assert "Start-Process -FilePath $node.Source" in script
    assert '"--tray","--host","127.0.0.1"' in script
    assert "Start-Process -FilePath $router.Source" not in script
    assert "Invoke-WebRequest -UseBasicParsing -Uri \"http://127.0.0.1:20128/dashboard\"" not in script
    for service in ("C5", "MANAGER", "EVOLUTION", "COMMAND_CENTER", "ROUTER_9", "NATS", "OLLAMA"):
        assert service in script
    assert "auto_canonical_mutation = $false" in script


def test_network_reconnect_resumes_only_safe_observers_windowlessly():
    script = (RUNTIME / "Maintain-RAIOS-Online.ps1").read_text(encoding="utf-8")
    assert "$NetworkStatePath" in script
    assert "$NetworkRequiredSuccesses = 2" in script
    assert "$NetworkResumeCooldownSeconds = 300" in script
    assert "$resumePending = $reconnected -or [bool]$networkPrevious.resume_pending" in script
    assert "$internetOnline -and $resumePending -and $cooldownElapsed" in script
    assert "Start-Process -FilePath $PythonWindowless" in script
    assert 'safe_jobs = @("RESOURCES")' in script
    assert "$resumeEligible -and $localReady" in script
    assert "local_services_required = $true" in script
    assert "NETWORK_RESUME_MAIL" not in script
    assert "NETWORK_RESUME_SEARCH_INDEX" not in script
    assert "paid_resource_created = $false" in script
    assert "gpu_session_started = $false" in script
    assert "model_download_executed = $false" in script
    assert "canonical_mutation = $false" in script
    assert "NETWORK_RESUME_OFFICIAL" not in script
    assert "NETWORK_RESUME_FACTORY" not in script


def test_manager_guard_checks_liveness_not_lock_file_existence():
    script = (RUNTIME / "Ensure-RAIOS-Cognitive-Loop.ps1").read_text(encoding="utf-8")
    manager = (ROOT / "src" / "raios" / "manager" / "live_manager.py").read_text(encoding="utf-8")
    assert "loop.manager.alive" in script
    assert "STOP_STALE_MANAGER_PID_" in script
    assert "if (Test-Path $lock)" not in script
    assert '"state": "STARTING"' in manager
    assert "write_heartbeat(" in manager
    assert "heartbeat.live-" in manager
    assert "RAIOS-Manager-Liveness-Pulse" in manager
    assert '"tick_inflight": pulse_state["tick_inflight"]' in manager
    assert '"single_cognitive_wal": str(WAL_FILE)' in manager
    assert "SEARCH_REFRESH_SECONDS = 300.0" in manager
    assert "self._refresh_processes.get(name)" in manager
    assert "existing is not None and existing.poll() is None" in manager
    assert "self._search_refresh_process = process" in manager
    assert "RAIOS_COGNITIVE_STORE_ROOT" in script
    assert "RAIOS_LEARNING_ROOT" in script
    assert "evolution_daemon.py" in script
    assert "Get-EvolutionStatus" in script


def test_c5_deploy_binds_the_durable_cognitive_store():
    deploy = (RUNTIME / "Deploy-RAIOS-C5.ps1").read_text(encoding="utf-8")
    assert "RAIOS_COGNITIVE_STORE_ROOT" in deploy
    assert "RAIOS_LEARNING_ROOT" in deploy
    assert '[Environment]::GetFolderPath("UserProfile")' in deploy
    assert "$StableUserProfile" in deploy
    assert "cognitive_store_root" in deploy
    assert "$RuntimeBase = Split-Path -Parent $RuntimeRoot" in deploy
    assert 'Join-Path $RuntimeBase "cognitive-store\\v9"' in deploy


def test_evolution_loop_is_non_recursive_bounded_and_windowless():
    daemon = (ROOT / "RAIOS" / "V9" / "runtime" / "evolution_daemon.py").read_text(encoding="utf-8")
    brain = (ROOT / "RAIOS" / "V9" / "runtime" / "evolution_brain.py").read_text(encoding="utf-8")
    manager = (ROOT / "src" / "raios" / "manager" / "live_manager.py").read_text(encoding="utf-8")
    manager_init = (ROOT / "src" / "raios" / "manager" / "__init__.py").read_text(encoding="utf-8")
    engine = (ROOT / "src" / "raios" / "search_cortex" / "engine.py").read_text(encoding="utf-8")
    bus = (ROOT / "RAIOS" / "V9" / "runtime" / "cognitive_event_bus.py").read_text(encoding="utf-8")
    history = (ROOT / "RAIOS" / "V9" / "runtime" / "git_history_search.py").read_text(encoding="utf-8")
    script = (RUNTIME / "Ensure-RAIOS-Cognitive-Loop.ps1").read_text(encoding="utf-8")
    center_deploy = (RUNTIME / "Deploy-RAIOS-Command-Center.ps1").read_text(encoding="utf-8")

    assert "trace=False" in daemon
    assert 'write_heartbeat(state="IDLE_COGNITION"' not in daemon
    assert "MAX_FAILURE_BACKOFF_SECONDS = 60.0" in daemon
    assert "safe_write_heartbeat" in daemon
    assert "subprocess.check_output" not in brain
    assert "RAIOS_CANONICAL_REPO" in brain
    assert "CREATE_NO_WINDOW" in manager
    assert "creationflags=CREATE_NO_WINDOW" in manager
    assert "LOCAL_TICK_SECONDS = 15.0" in manager
    assert "REASON_RETRY_SECONDS = 300.0" in manager
    assert "semantic_dict()" in manager
    assert '"phase_latency_ms": phase_latency_ms' in manager
    assert "active_gap_codes" in manager
    assert "def __getattr__" in manager_init
    assert "from .live_manager import LiveManager, run_once" not in manager_init.split(
        "def __getattr__", 1
    )[0]
    assert 'parser.add_argument("--no-refresh-spawn"' in manager
    assert 'parser.add_argument("--no-reasoning"' in manager
    assert "if self.enable_refreshes:" in manager
    assert "if self.enable_reasoning and reason_due and should_reason:" in manager
    assert "JSONL_TAIL_SCAN_BYTES" in bus
    assert "_PROCESSED_ID_CACHE" in bus
    assert "_load_jsonl_snapshot" in bus
    assert "CREATE_NO_WINDOW" in engine
    assert "creationflags=CREATE_NO_WINDOW" in engine
    assert "subprocess.check_output" not in bus.split("def repo_sha", 1)[0]
    assert "_REPO_SHA_CACHE" in bus
    assert "creationflags=CREATE_NO_WINDOW" in bus
    assert "subprocess.check_output" not in history
    assert "creationflags=CREATE_NO_WINDOW" in history
    assert "$PythonWindowless" in script
    assert "C5_PYTHONW_MISSING" in script
    assert "Start-Process -FilePath $PythonWindowless" in script
    assert "$PythonWindowless" in center_deploy
    assert "Start-Process $PythonWindowless" in center_deploy


def test_c5_truth_guard_preserves_c1_canonical_gl005_proof():
    enforcer = (ROOT / "scripts" / "ai-os" / "raios_c5_enforce.py").read_text(encoding="utf-8")
    lawbook = (ROOT / ".ai-os" / "mcp" / "C5-LAWBOOK.json").read_text(encoding="utf-8")
    assert "3ac6a7c886b396eef0225d617cbad3f22a10c846" in enforcer
    assert "git\", \"merge-base\", \"--is-ancestor\"" in enforcer
    assert "authenticated_orchestration_task_proven" in enforcer
    assert "gl005_orchestration_validation_proven" in enforcer
    assert "C1_CANONICAL_LINEAGE" in enforcer
    assert "and not gl005_proven" in enforcer
    assert 'c5["instance_role"] = "c1-assistant"' not in enforcer
    assert "report canonical C5 seat drift; no autonomous seat-map rewrite" in enforcer
    assert "Never overwrite a C1-proven state" in lawbook
