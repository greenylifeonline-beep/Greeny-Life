from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
INSPECTOR = ROOT / "scripts/runtime/Inspect-RAIOS-Native-Tunnel.ps1"


def inspector_text() -> str:
    return INSPECTOR.read_text(encoding="utf-8")


def test_native_tunnel_inspector_is_read_only():
    text = inspector_text()
    assert "mutation_performed=$false" in text
    assert "@('admin','--json','tunnels','get',$tunnelId)" in text
    for forbidden in ("tunnels','create", "tunnels','update", "tunnels','delete",
                      "runtimes','connect", "runtimes','create"):
        assert forbidden not in text


def test_native_tunnel_inspector_checks_current_mcp_contract():
    text = inspector_text()
    assert "[int]$mcp.tool_count -eq 9" in text
    assert "$mcp.execute_scoped_task -eq $true" in text
    assert "$mcp.second_gateway -eq $false" in text
    assert "$mcp.duplicate_mcp -eq $false" in text
    assert "$mcp.raw_shell -eq $false" in text
    assert "$serverUrl -eq 'http://127.0.0.1:8788/mcp'" in text


def test_native_tunnel_inspector_uses_official_read_surfaces():
    text = inspector_text()
    assert "@('doctor','--profile-dir',$ProfileDir,'--profile',$Profile,'--explain')" in text
    assert "@('admin','--json','tunnels','get',$tunnelId)" in text
    assert "/health?details=true" in text
    assert "/health/mcp" in text
    assert "/readyz" in text


def test_native_tunnel_inspector_redacts_captured_output():
    text = inspector_text()
    assert "<redacted-secret>" in text
    assert "<redacted-key>" in text
    assert "Bearer <redacted>" in text
    assert "[Array]::Clear($plainBytes" in text
    assert "[Array]::Clear($cipher" in text


def test_native_tunnel_inspector_parses_when_powershell_is_available(tmp_path):
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell is not available on this test host")
    driver = tmp_path / "parse-native-tunnel-inspector.ps1"
    driver.write_text(
        """param([string]$Path)
$tokens=$null
$errors=$null
[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors)|Out-Null
if($errors.Count){exit 1}
exit 0
""",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [powershell, "-NoLogo", "-NoProfile", "-NonInteractive",
         "-File", str(driver), "-Path", str(INSPECTOR)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
