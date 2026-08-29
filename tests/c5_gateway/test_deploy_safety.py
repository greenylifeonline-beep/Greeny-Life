from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "runtime" / "Deploy-RAIOS-C5.ps1"


def test_deploy_validates_staged_listener_before_cutover():
    text = DEPLOY.read_text(encoding="utf-8")
    stage_start = text.index('$stage = Start-C5Process')
    stage_health = text.index('$stageHealth = Wait-C5Healthy')
    old_stop = text.index('Stop-Process -Id $oldPid')
    final_start = text.index('$proc = Start-C5Process')
    assert stage_start < stage_health < old_stop < final_start
    assert 'C5_STAGE_VALIDATION=true' in text


def test_deploy_fails_closed_on_stage_or_final_health_failure():
    text = DEPLOY.read_text(encoding="utf-8")
    assert 'CANONICAL_C5_STAGE_VALIDATION_FAILED' in text
    assert 'CANONICAL_C5_CUTOVER_FAILED' in text
    assert '$health.canonical_head -eq $Head' in text