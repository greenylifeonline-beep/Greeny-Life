"""Execute the launcher's real readiness function without starting its tunnel."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ai-os"))
from raios_mcp.gateway import REGISTERED_TOOLS

TOOLS = list(REGISTERED_TOOLS)
HEALTH = {"ok": True, "service": "raios-universal-mcp", "transport": "streamable-http",
          "tool_count": len(TOOLS), "tools": TOOLS, "second_gateway": False,
          "get_sse": True, "stateless": False, "channel": "streamable-http-session",
          "hosted_dcr_required": False}
CASES = [
    ("current", {}, True),
    ("reordered", {"tools": list(reversed(TOOLS))}, True),
    ("legacy_eight", {"tools": TOOLS[:-1], "tool_count": 8}, False),
    ("missing_execution", {"tools": TOOLS[:-1] + ["unknown"]}, False),
    ("duplicate", {"tools": TOOLS[:-1] + [TOOLS[0]]}, False),
    ("count_mismatch", {"tool_count": 8}, False),
    ("wrong_service", {"service": "other-service"}, False),
    ("wrong_transport", {"transport": "stdio"}, False),
    ("wrong_channel", {"channel": "stateless"}, False),
    ("no_sse", {"get_sse": False}, False),
    ("stateless", {"stateless": True}, False),
    ("second_gateway", {"second_gateway": True}, False),
    ("hosted_required", {"hosted_dcr_required": True}, False),
    ("not_ok", {"ok": False}, False),
    ("string_bool", {"ok": "true"}, False),
    ("string_count", {"tool_count": "9"}, False),
    ("case_changed", {"tools": ["GET_HEAD"] + TOOLS[1:]}, False),
    ("null_tools", {"tools": None}, False),
]


@pytest.fixture(scope="module")
def readiness_results(tmp_path_factory):
    pwsh = os.getenv("RAIOS_TEST_PWSH") or shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell required: set RAIOS_TEST_PWSH or install pwsh")
    tmp = tmp_path_factory.mktemp("native-readiness")
    fixtures = tmp / "fixtures.json"
    fixtures.write_text(json.dumps([{ "name": name, "health": {**HEALTH, **patch}}
                                    for name, patch, _ in CASES]), encoding="utf-8")
    driver = tmp / "probe.ps1"
    driver.write_text('''param([string]$Launcher,[string]$Fixtures)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Launcher,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'LAUNCHER_PARSE_FAILED'}
$fn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Test-LocalMcpReady'},$true)
if(-not $fn){throw 'READINESS_FUNCTION_MISSING'}
Invoke-Expression $fn.Extent.Text
function Invoke-RestMethod { param($Uri,$TimeoutSec) if($script:fail){throw 'offline'}; return $script:health }
$out=@{}
foreach($case in (Get-Content -LiteralPath $Fixtures -Raw|ConvertFrom-Json)){
 $script:health=$case.health; $script:fail=$false
 $out[$case.name]=[bool](Test-LocalMcpReady)
}
$script:fail=$true; $out['offline']=[bool](Test-LocalMcpReady)
$script:fail=$false; $script:health=[pscustomobject]@{ok=$true}; $out['incomplete']=[bool](Test-LocalMcpReady)
$out|ConvertTo-Json -Compress
''', encoding="utf-8")
    env = dict(os.environ, XDG_CACHE_HOME=str(tmp / "cache"), XDG_CONFIG_HOME=str(tmp / "config"),
               XDG_DATA_HOME=str(tmp / "data"), POWERSHELL_TELEMETRY_OPTOUT="1")
    proc = subprocess.run([pwsh, "-NoLogo", "-NoProfile", "-File", str(driver),
                           "-Launcher", str(ROOT / "scripts/runtime/Start-RAIOS-Native-MCP-System.ps1"),
                           "-Fixtures", str(fixtures)], capture_output=True, text=True, timeout=30, env=env)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.parametrize("name,patch,expected", CASES, ids=[case[0] for case in CASES])
def test_native_readiness_contract(readiness_results, name, patch, expected):
    assert readiness_results[name] is expected


@pytest.mark.parametrize("name", ["offline", "incomplete"])
def test_native_readiness_fails_closed(readiness_results, name):
    assert readiness_results[name] is False
