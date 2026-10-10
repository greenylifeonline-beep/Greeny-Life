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
POLICY = ROOT / ".ai-os" / "mcp" / "POLICY.json"


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
                "candidate_relationship": "EXITED",
                "candidate_retirement_attempted": False,
                "candidate_retirement_proven": True,
                "candidate_retirement_reason": "PROCESS_EXITED",
                "repair_applied": False,
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
    assert view["candidate_relationship"] == "EXITED"
    assert view["candidate_retirement_attempted"] is False
    assert view["candidate_retirement_proven"] is True
    assert view["candidate_retirement_reason"] == "PROCESS_EXITED"
    assert view["repair_applied"] is False
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
    assert 'candidate_relationship = [string]$candidateResolution.relationship' in text
    assert 'candidate_retirement_attempted = [bool]$candidateResolution.retirement_attempted' in text
    assert 'candidate_retirement_proven = [bool]$candidateResolution.retirement_proven' in text
    assert 'repair_applied = [bool]$candidateResolution.retirement_attempted' in text
    assert 'active_state = $activeState' in text
    assert 'orphan_generation_count = $orphanPids.Count' in text
    assert 'handoff_complete = $handoffComplete' in text
    assert 'singleton_verdict =' in text
    assert '"STEADY_STATE_VERIFY"' in text
    assert '$preserveTransition' in text
    assert 'verification_reason = $verificationReason' in text
    assert '$priorProjection.transition_reason' in text
    assert 'function Resolve-RaiosCandidateLifecycle' in text
    assert 'function Test-RaiosOwnedLaunchCandidate' in text
    assert 'function Get-RaiosParentLineageProof' in text
    assert "ACTIVE_LINEAGE_PARENT" in text
    assert "AUTO_RETIRED_PROVEN_ORPHAN" in text
    assert "FAIL_CLOSED_LINEAGE_UNPROVEN" not in text
    assert "FAIL_CLOSED_LINEAGE_AND_OWNERSHIP_UNPROVEN" in text
    assert '$ownedCandidate = [bool](Test-RaiosOwnedLaunchCandidate $owner $CandidatePid $ActivePid)' in text
    assert "ACTIVE_LISTENER_PROOF_FAILED_BEFORE_RETIREMENT" in text
    assert "RETIRED_ACTIVE_REVERIFY_FAILED" in text
    assert "OWNED_NON_LISTENER_RETIRED_WITH_INCOMPLETE_LINEAGE" in text
    assert 'candidate_active_reverified = [bool]$candidateResolution.active_reverified' in text
    assert 'candidate_handoff_safe = [bool]$candidateResolution.handoff_safe' in text
    assert '$candidateHandoffSafe = [bool]$candidateResolution.handoff_safe' in text
    assert '$effectiveCandidatePid = [int]$priorProjection.candidate_pid' in text
    assert '$reportedCandidateState = [string]$priorProjection.candidate_state' not in text


def test_owned_candidate_proof_precedes_incomplete_lineage_fail_closed():
    text = ENSURE.read_text(encoding="utf-8")
    resolve_start = text.index("function Resolve-RaiosCandidateLifecycle")
    resolve_end = text.index("function Write-RaiosGenerationHandoff", resolve_start)
    block = text[resolve_start:resolve_end]

    ownership = block.index(
        "$ownedCandidate = [bool](Test-RaiosOwnedLaunchCandidate $owner $CandidatePid $ActivePid)"
    )
    incomplete = block.index("FAIL_CLOSED_LINEAGE_AND_OWNERSHIP_UNPROVEN")
    retire = block.index("Stop-Process -Id $CandidatePid -Force -ErrorAction Stop")
    reverify = block.index("RETIRED_ACTIVE_REVERIFY_FAILED")

    assert ownership < incomplete
    assert ownership < retire < reverify
    assert "if (-not $ownedCandidate)" in block
    assert "Test-RaiosMcpHealthy $healthBefore" in block
    assert "Test-RaiosMcpHealthy $healthAfter" in block
    assert "$listenersBefore.Count -eq 1" in block
    assert "$listenersAfter.Count -eq 1" in block


def test_get_head_and_health_expose_same_generation_verdict():
    gateway = GATEWAY.read_text(encoding="utf-8")
    server = SERVER.read_text(encoding="utf-8")

    assert '"generation_handoff": generation_handoff' in gateway
    assert '"generation_summary": generation_handoff.get("explanation")' in gateway
    assert '"generation_lineage": generation_handoff.get("lineage", [])' in gateway
    assert '"generation_handoff_complete": generation_handoff.get("handoff_complete", False)' in gateway
    assert '"generation_singleton_verdict": generation_handoff.get("singleton_verdict", "UNKNOWN")' in gateway
    assert '"generation_orphan_count": generation_handoff.get("orphan_generation_count")' in gateway
    assert '"verification_reason": raw.get("verification_reason")' in gateway
    assert '"candidate_relationship": candidate_relationship' in gateway
    assert '"candidate_retirement_attempted": candidate_retirement_attempted' in gateway
    assert '"candidate_retirement_proven": candidate_retirement_proven' in gateway
    assert '"candidate_retirement_reason": candidate_retirement_reason' in gateway
    assert '"repair_applied": repair_applied' in gateway
    assert '"duplicate_mcp": bool(generation_handoff.get("duplicate_mcp") is True)' in gateway
    assert '"generation_duplicate_mcp": bool(generation_handoff.get("duplicate_mcp") is True)' in gateway

    assert '"generation_handoff": generation_handoff' in server
    assert '"generation_handoff_complete": generation_handoff.get("handoff_complete", False)' in server
    assert '"generation_singleton_verdict": generation_handoff.get("singleton_verdict", "UNKNOWN")' in server
    assert '"generation_orphan_count": generation_handoff.get("orphan_generation_count")' in server
    assert '"generation_active_pid": generation_handoff.get("active_pid")' in server
    assert '"generation_candidate_state": generation_handoff.get("candidate_state")' in server
    assert '"generation_candidate_relationship": generation_handoff.get("candidate_relationship")' in server
    assert '"generation_candidate_retirement_attempted": generation_handoff.get("candidate_retirement_attempted", False)' in server
    assert '"generation_candidate_retirement_proven": generation_handoff.get("candidate_retirement_proven", False)' in server
    assert '"generation_candidate_retirement_reason": generation_handoff.get("candidate_retirement_reason")' in server
    assert '"generation_repair_applied": generation_handoff.get("repair_applied", False)' in server
    assert '"duplicate_mcp": bool(generation_handoff.get("duplicate_mcp") is True)' in server
    assert '"generation_duplicate_mcp": bool(generation_handoff.get("duplicate_mcp") is True)' in server


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


def test_runtime_truth_precedence_is_machine_readable():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    precedence = policy["truth_precedence"]

    assert precedence["schema"] == "raios.truth-precedence.v1"
    assert precedence["order"] == [
        "LIVE_RUNTIME_TRUTH",
        "LOCAL_CANONICAL_REPOSITORY",
        "GITHUB_MIRROR_HISTORY",
    ]
    assert precedence["remote_commit_is_live_proof"] is False
    assert precedence["source_side_change_requires_live_verification"] is True
    assert "runtime_health" in precedence["live_verification_requires"]
    assert "owner_identity" in precedence["live_verification_requires"]
    assert "canonical_head_match" in precedence["live_verification_requires"]
    assert "receipt_or_equivalent_live_evidence" in precedence["live_verification_requires"]
    assert "LIVE_RUNTIME_TRUTH_PRECEDES_SOURCE_PROJECTIONS" in policy["law"]
    assert "REMOTE_COMMIT_NE_LIVE_DEPLOYMENT" in policy["law"]
    assert "SOURCE_CHANGE_REQUIRES_LIVE_VERIFICATION" in policy["law"]
