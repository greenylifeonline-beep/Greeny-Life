from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "src/raios/command_center/app.py"


def source() -> str:
    return APP.read_text(encoding="utf-8")


def test_command_center_requires_exact_nine_tool_mcp_contract():
    text = source()
    assert 'int(health.get("tool_count") or 0)==9' in text
    assert '"execute_scoped_task"' in text
    assert 'health.get("ninth_tool") is True' in text
    assert 'health.get("second_gateway") is False' in text
    assert 'health.get("duplicate_mcp") is False' in text
    assert 'health.get("raw_shell") is False' in text


def test_command_center_does_not_reintroduce_legacy_eight_tool_projection():
    text = source()
    assert 'tool_count") or 0)==8' not in text
    assert '"NO_NINTH_TOOL"' not in text
    assert '"EXACT_NINE_TOOLS"' in text
    assert '"NO_RAW_SHELL"' in text
