from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAINTAIN = ROOT / "scripts/runtime/Maintain-RAIOS-Online.ps1"


def maintain_text() -> str:
    return MAINTAIN.read_text(encoding="utf-8")


def test_maintenance_uses_shared_nine_tool_mcp_contract():
    text = maintain_text()
    assert "function Test-RaiosUniversalMcpHealth" in text
    assert "tool_count -eq 8" not in text
    assert "[int]$Health.tool_count -ne 9" in text
    assert "'execute_scoped_task'" in text
    assert "$Health.execute_scoped_task -ne $true" in text
    assert "$Health.second_gateway -ne $false" in text
    assert "$Health.duplicate_mcp -ne $false" in text
    assert "$Health.raw_shell -ne $false" in text


def test_maintenance_reuses_contract_for_mcp_and_native_tunnel():
    text = maintain_text()
    assert text.count("Test-RaiosUniversalMcpHealth $mcp $Head") == 2
    assert "Test-RaiosUniversalMcpHealth $mcpHealth $Head" in text
