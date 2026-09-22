from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "runtime" / "Deploy-RAIOS-C5.ps1"


def source() -> str:
    return DEPLOY.read_text(encoding="utf-8-sig")


def test_validate_only_is_explicit_switch():
    text = source()
    assert "[switch]$ValidateOnly" in text


def test_validate_only_exits_after_stage_before_live_listener_stop():
    text = source()
    gate = text.index('if ($ValidateOnly)')
    old_stop = text.index('Stop-Process -Id $oldPid')
    assert gate < old_stop
    block = text[gate:old_stop]
    assert 'C5_VALIDATE_ONLY=true' in block
    assert 'C5_STAGE_VALIDATION=true' in block
    assert 'return' in block


def test_normal_cutover_path_is_preserved():
    text = source()
    assert 'Move-Item -LiteralPath $StageAppRoot -Destination $AppRoot' in text
    assert 'Start-C5Process -ListenPort $Port -Name "gateway"' in text
