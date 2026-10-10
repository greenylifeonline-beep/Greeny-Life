from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts/runtime/Deploy-RAIOS-C5-Service.ps1"
SERVICE = ROOT / "scripts/runtime/RAIOS.C5.ServiceHost.cs"
USERLANE = ROOT / "scripts/runtime/c5-service/Invoke-RAIOS-C5-UserLane.ps1"
MAINTAIN = ROOT / "scripts/runtime/Maintain-RAIOS-Online.ps1"


def deploy_text() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def service_text() -> str:
    return SERVICE.read_text(encoding="utf-8")


def test_c5_deployer_uses_nine_tool_contract():
    text = deploy_text()
    assert "tool_count -eq 9" in text
    assert "execute_scoped_task -eq $true" in text
    assert "tool_count -eq 8" not in text


def test_c5_service_allows_governed_scm_stop():
    text = service_text()
    assert "CanStop = true;" in text
    assert "CanStop = false;" not in text


def test_c5_deploy_receipt_path_does_not_collide_with_receipt_object():
    text = deploy_text()
    assert "$ReceiptPath=Join-Path $Root 'service-deploy-receipt.json'" in text
    assert "$receipt=[ordered]@{" in text
    assert "$tmp=$ReceiptPath+'.tmp-'" in text
    assert "Move-Item -LiteralPath $tmp -Destination $ReceiptPath -Force" in text

    # PowerShell variable names are case-insensitive. Regressing to $Receipt
    # for the path would alias $receipt and recreate AddHashTableToNonHashTable.
    assert not re.search(
        r"(?im)^\s*\$Receipt\s*=\s*Join-Path\s+\$Root\s+'service-deploy-receipt\.json'",
        text,
    )


def test_c5_bootstrap_stop_is_owned_and_bounded():
    text = deploy_text()
    assert "function Stop-RaiosC5ForDeploy" in text
    assert "C5_BOOTSTRAP_STOP_PID_MISMATCH" in text
    assert "C5_BOOTSTRAP_STOP_IMAGE_MISMATCH" in text
    assert "Write-MaintenanceIntent -Reason 'CANSTOP_FALSE_BOOTSTRAP_CUTOVER'" in text
    assert 'taskkill.exe" /PID $ExpectedPid /T /F' in text
    assert "BOOTSTRAP_NONSTOPPABLE_SERVICE_STOPPED" in text


def test_c5_deployer_preserves_exact_failure_diagnostics():
    text = deploy_text()
    assert "$FailurePath=Join-Path $Root 'service-deploy-failure.json'" in text
    assert "script_stack_trace=$failureStack" in text
    assert "invocation_position=$failurePosition" in text
    assert "fully_qualified_error_id=$failureId" in text
    assert "failed_phase=$failurePhase" in text


def test_c5_phase_writer_accepts_ordered_diagnostics():
    text = deploy_text()
    assert (
        "function Write-DeployPhase([string]$Name,[System.Collections.IDictionary]$Extra=$null)"
        in text
    )


def test_c5_deployer_has_no_case_only_assignment_collisions():
    text = deploy_text()
    assignments = re.findall(
        r"(?m)^\s*\$([A-Za-z_][A-Za-z0-9_]*)\s*=",
        text,
    )
    spellings_by_logical = {}
    for name in assignments:
        spellings_by_logical.setdefault(name.lower(), set()).add(name)

    collisions = {
        logical: sorted(spellings)
        for logical, spellings in spellings_by_logical.items()
        if len(spellings) > 1
    }
    assert collisions == {}, (
        "PowerShell variable names are case-insensitive; case-only assignment "
        f"collisions are unsafe: {collisions}"
    )



def test_c5_userlane_uses_nine_tool_generation_health():
    text = USERLANE.read_text(encoding="utf-8")
    assert "tool_count -eq 8" not in text
    assert "[int]$m.tool_count -ne 9" in text
    assert "execute_scoped_task" in text
    assert "generation_handoff_complete" in text
    assert "generation_singleton_verdict" in text
    assert "generation_orphan_count" in text
    assert "'PASS'" in text


def test_maintenance_requires_clean_generation_singleton():
    text = MAINTAIN.read_text(encoding="utf-8")
    assert "generation_handoff_complete" in text
    assert "generation_singleton_verdict" in text
    assert "generation_orphan_count" in text
    assert "[int]$Health.generation_orphan_count -ne 0" in text

def test_c5_deployer_parses_when_powershell_is_available(tmp_path):
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell is not available on this test host")

    driver = tmp_path / "parse-c5-deployer.ps1"
    driver.write_text(
        """param([string]$Path)
$ErrorActionPreference='Stop'
$tokens=$null
$errors=$null
[Management.Automation.Language.Parser]::ParseFile(
    $Path,
    [ref]$tokens,
    [ref]$errors
) | Out-Null
if($errors.Count){
    $errors | ForEach-Object {
        [Console]::Error.WriteLine($_.Message)
    }
    exit 1
}
exit 0
""",
        encoding="utf-8",
    )
    for target in (DEPLOY, USERLANE, MAINTAIN):
        proc = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(driver),
                "-Path",
                str(target),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f"{target}: {proc.stderr}"
